"""
migrate_ibra.py

Cleans IBRARegion_Aust70.shp and migrates it into the local PostgreSQL `ibra`
table used by DBeaver / the ECO backend.

Usage
-----
  # From the backend/ directory:
  pip install geopandas shapely psycopg2-binary python-dotenv sqlalchemy
  python migrate_ibra.py --shp /path/to/IBRARegion_Aust70.shp

  # Dry-run (clean + report only, no DB writes):
  python migrate_ibra.py --shp /path/to/IBRARegion_Aust70.shp --dry-run

What this script does
---------------------
  1. Load    - Read the .shp file with geopandas.
  2. Inspect - Print a cleaning report (CRS, row count, null geometry,
               invalid geometry, duplicate IBRA codes, column names).
  3. Clean   - Reproject to EPSG:4326 (WGS 84) if needed.
               Fix invalid geometries via make_valid().
               Cast Polygon -> MultiPolygon for schema consistency.
               Normalise column names to match the `ibra` table schema.
               Drop rows where ibra_reg_code is null after normalisation.
               Derive `state` from the shapefile's state field if present.
  4. Guard   - Introspect the live DB column lengths and print any values
               that would truncate.  Exits with a clear message if the DB
               columns are too narrow, directing the operator to run
               alter_ibra_columns.py first.
  5. Migrate - Truncate the `ibra` table and bulk-insert all cleaned rows
               in batches of 50.  The PostGIS `geom` column is populated by
               pre-computing an EWKB hex string in Python (one bind param per
               row, no CASE expression -- avoids SQLAlchemy CompileError 9h9h).

Column mapping (shapefile -> DB)
---------------------------------
  REG_NAME / IBRA_REG_N / RGN_NAME  ->  ibra_reg_name
  REG_CODE / IBRA_REG_C / RGN_CODE  ->  ibra_reg_code
  REG_NUM  / IBRA_REG_N2            ->  ibra_reg_num
  STA_CODE / STATE / STATE_CODE      ->  state
  SHAPE_Area                         ->  shape_area
  SHAPE_Leng / SHAPE_Length          ->  shape_len
"""

import argparse
import os
import sys
from datetime import datetime, timezone

try:
    import geopandas as gpd
except ImportError:
    sys.exit("ERROR: geopandas is not installed. Run: pip install geopandas")

try:
    from shapely.geometry import MultiPolygon
    from shapely.validation import make_valid
    from shapely import wkb as shapely_wkb
except ImportError:
    sys.exit("ERROR: shapely is not installed. Run: pip install shapely")

try:
    from sqlalchemy import create_engine, text
except ImportError:
    sys.exit("ERROR: sqlalchemy is not installed. Run: pip install sqlalchemy")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# -- State abbreviation map ---------------------------------------------------

STATE_ABBREV_MAP = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "SA":  "South Australia",
    "WA":  "Western Australia",
    "TAS": "Tasmania",
    "NT":  "Northern Territory",
    "ACT": "Australian Capital Territory",
    "OT":  "Other Territories",
}


# -- Column normalisation -----------------------------------------------------

def normalise_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    cols = {c.upper(): c for c in gdf.columns}
    rename = {}

    for candidate in ["REG_NAME", "IBRA_REG_N", "RGN_NAME", "REGIONNAME", "NAME"]:
        if candidate in cols:
            rename[cols[candidate]] = "ibra_reg_name"
            break

    for candidate in ["REG_CODE", "IBRA_REG_C", "RGN_CODE", "REGIONCODE", "CODE"]:
        if candidate in cols:
            rename[cols[candidate]] = "ibra_reg_code"
            break

    for candidate in ["REG_NUM", "IBRA_CODE", "REGIONNUM", "REGNUM"]:
        if candidate in cols:
            rename[cols[candidate]] = "ibra_reg_num"
            break

    for candidate in ["STA_CODE", "STATE", "STATE_CODE", "STATEABBR", "ST"]:
        if candidate in cols:
            rename[cols[candidate]] = "state_raw"
            break

    for candidate in ["SHAPE_AREA", "AREA", "SHAPE_A"]:
        if candidate in cols:
            rename[cols[candidate]] = "shape_area"
            break

    for candidate in ["SHAPE_LENG", "SHAPE_LENGTH", "PERIMETER", "SHAPE_L"]:
        if candidate in cols:
            rename[cols[candidate]] = "shape_len"
            break

    gdf = gdf.rename(columns=rename)

    if "state_raw" in gdf.columns:
        gdf["state"] = gdf["state_raw"].apply(
            lambda v: STATE_ABBREV_MAP.get(str(v).upper().strip(), str(v).strip())
            if v and str(v).strip() not in ("", "nan", "None") else None
        )
        gdf = gdf.drop(columns=["state_raw"])
    else:
        gdf["state"] = None

    return gdf


# -- Geometry helpers ---------------------------------------------------------

def ensure_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    polys = [
        p for p in (geom.geoms if hasattr(geom, "geoms") else [])
        if p.geom_type in ("Polygon", "MultiPolygon")
    ]
    if polys:
        parts = []
        for p in polys:
            if p.geom_type == "Polygon":
                parts.append(p)
            else:
                parts.extend(p.geoms)
        return MultiPolygon(parts) if parts else None
    return None


def geom_to_ewkb_hex(geom, srid: int = 4326):
    """
    Convert a Shapely geometry to an EWKB hex string with the SRID embedded.
    Inserted via ST_GeomFromEWKB(decode(:geom_ewkb, 'hex')) -- ONE bind param,
    no CASE expression needed (avoids SQLAlchemy CompileError 9h9h).
    """
    if geom is None or geom.is_empty:
        return None
    return shapely_wkb.dumps(geom, hex=True, include_srid=True, srid=srid)


# -- Cleaning report ----------------------------------------------------------

def print_report(gdf: gpd.GeoDataFrame, label: str) -> None:
    n_null    = gdf.geometry.isna().sum()
    n_empty   = gdf.geometry.apply(lambda g: g is not None and g.is_empty).sum()
    n_invalid = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  CRS           : {gdf.crs}")
    print(f"  Rows          : {len(gdf)}")
    print(f"  Null geometry : {n_null}")
    print(f"  Empty geometry: {n_empty}")
    print(f"  Invalid geom  : {n_invalid}")
    print(f"  Columns       : {list(gdf.columns)}")

    if "ibra_reg_code" in gdf.columns:
        print(f"  Null reg_code : {gdf['ibra_reg_code'].isna().sum()}")
        print(f"  Dup  reg_code : {gdf['ibra_reg_code'].duplicated().sum()}")
        max_code_len = gdf["ibra_reg_code"].dropna().str.len().max()
        print(f"  Max code len  : {max_code_len}")

    if "ibra_reg_name" in gdf.columns:
        print(f"  Unique regions: {gdf['ibra_reg_name'].nunique()}")
        max_name_len = gdf["ibra_reg_name"].dropna().str.len().max()
        print(f"  Max name len  : {max_name_len}")

    if "state" in gdf.columns:
        print(f"  States        : {sorted(gdf['state'].dropna().unique().tolist())}")
        max_state_len = gdf["state"].dropna().str.len().max()
        print(f"  Max state len : {max_state_len}")


# -- Clean --------------------------------------------------------------------

def clean_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    print("\n[1/4] Normalising column names...")
    gdf = normalise_columns(gdf)
    print(f"      Columns: {list(gdf.columns)}")

    print("[2/4] Reprojecting to EPSG:4326...")
    if gdf.crs is None:
        print("      No CRS detected -- assuming GDA94 (EPSG:4283).")
        gdf = gdf.set_crs("EPSG:4283", allow_override=True)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
        print("      Reprojected -> EPSG:4326")
    else:
        print("      Already EPSG:4326.")

    print("[3/4] Fixing invalid / null geometries...")
    before = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    gdf["geometry_col"] = gdf.geometry.apply(
        lambda g: make_valid(g)
        if g is not None and not g.is_empty and not g.is_valid else g
    )
    gdf = gdf.set_geometry("geometry_col").drop(columns=[gdf.geometry.name])
    gdf = gdf.rename_geometry("geometry")
    after = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    print(f"      Fixed {before - after} invalid geometries (remaining: {after}).")

    n_before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    print(f"      Dropped {n_before - len(gdf)} null/empty geometry rows.")

    print("[4/4] Casting to MultiPolygon...")
    gdf["geometry"] = gdf["geometry"].apply(ensure_multipolygon)
    gdf = gdf[gdf["geometry"].notna()].copy()
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    print(f"      Rows after cast: {len(gdf)}")

    if "ibra_reg_code" in gdf.columns:
        n_before = len(gdf)
        gdf = gdf[
            gdf["ibra_reg_code"].notna() &
            (gdf["ibra_reg_code"].str.strip() != "")
        ].copy()
        print(f"      Dropped {n_before - len(gdf)} rows with null/empty ibra_reg_code.")

    return gdf


# -- Pre-insert column-length guard -------------------------------------------

def check_column_lengths(rows: list[dict], engine) -> None:
    """
    Introspect the live DB to find VARCHAR columns with length limits on the
    `ibra` table, then scan every row we are about to insert and report any
    values that exceed those limits.

    If any overflow is found, the script exits with a clear instruction to
    run alter_ibra_columns.py first.
    """
    # Fetch column character_maximum_length from information_schema
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'ibra'
              AND character_maximum_length IS NOT NULL
        """))
        limits = {r[0]: r[1] for r in result.fetchall()}

    if not limits:
        print("[Guard] No VARCHAR length limits found on ibra table -- skipping check.")
        return

    print(f"[Guard] VARCHAR limits detected: {limits}")

    offenders = {}  # col_name -> list of (value, length)
    for row in rows:
        for col, max_len in limits.items():
            val = row.get(col)
            if val is not None and len(str(val)) > max_len:
                offenders.setdefault(col, []).append((val, len(str(val))))

    if not offenders:
        print("[Guard] All values fit within the current column lengths. Proceeding.")
        return

    print("\n[Guard] *** TRUNCATION RISK DETECTED ***")
    print("  The following values exceed the current VARCHAR limits:\n")
    for col, vals in offenders.items():
        max_len = limits[col]
        print(f"  Column '{col}' (VARCHAR({max_len})):")
        for val, length in vals[:10]:  # show at most 10 examples per column
            print(f"    {repr(val)}  ({length} chars)")
        if len(vals) > 10:
            print(f"    ... and {len(vals) - 10} more")

    print(
        "\n  Fix: run this first, then re-run migrate_ibra.py:\n"
        "       python alter_ibra_columns.py\n"
    )
    sys.exit(1)


# -- Migrate ------------------------------------------------------------------

def migrate(rows: list[dict], engine) -> None:
    INSERT_SQL = text("""
        INSERT INTO ibra (
            ibra_reg_name, ibra_reg_code, ibra_reg_num,
            state, shape_area, shape_len,
            is_active, geometry, created_at, updated_at,
            geom
        ) VALUES (
            :ibra_reg_name, :ibra_reg_code, :ibra_reg_num,
            :state, :shape_area, :shape_len,
            :is_active, :geometry, :created_at, :updated_at,
            ST_GeomFromEWKB(decode(:geom_ewkb, 'hex'))
        )
    """)

    BATCH_SIZE = 50

    with engine.begin() as conn:
        print("\n[Migrate] Truncating ibra table...")
        conn.execute(text("TRUNCATE TABLE ibra RESTART IDENTITY CASCADE"))

    total = len(rows)
    inserted = 0
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i: i + BATCH_SIZE]
        with engine.begin() as conn:
            conn.execute(INSERT_SQL, batch)
        inserted += len(batch)
        print(f"[Migrate] {inserted}/{total} rows inserted...", end="\r")

    print(f"\n[Migrate] All {inserted} rows inserted.")

    with engine.connect() as conn:
        total_db  = conn.execute(text("SELECT COUNT(*) FROM ibra")).scalar()
        valid     = conn.execute(text("SELECT COUNT(*) FROM ibra WHERE geom IS NOT NULL AND ST_IsValid(geom)")).scalar()
        null_geom = conn.execute(text("SELECT COUNT(*) FROM ibra WHERE geom IS NULL")).scalar()
        bad_geom  = conn.execute(text("SELECT COUNT(*) FROM ibra WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)")).scalar()

    print(f"[Migrate] ibra table: {total_db} rows | {valid} valid geoms | {null_geom} null | {bad_geom} invalid")
    if bad_geom:
        print("[Migrate] Fix residual invalid geoms with:")
        print("          UPDATE ibra SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);")


# -- Build row dicts ----------------------------------------------------------

def build_rows(gdf: gpd.GeoDataFrame) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()

    def _str(row, key):
        v = row[key] if key in row.index else None
        return str(v).strip() or None if v is not None and str(v) not in ("", "nan", "None") else None

    def _float(row, key):
        v = row[key] if key in row.index else None
        try:
            return float(v) if v is not None and str(v) not in ("", "nan", "None") else None
        except (TypeError, ValueError):
            return None

    def _int(row, key):
        v = row[key] if key in row.index else None
        try:
            return int(v) if v is not None and str(v) not in ("", "nan", "None") else None
        except (TypeError, ValueError):
            return None

    rows = []
    for _, row in gdf.iterrows():
        rows.append({
            "ibra_reg_name": _str(row, "ibra_reg_name"),
            "ibra_reg_code": _str(row, "ibra_reg_code"),
            "ibra_reg_num" : _int(row, "ibra_reg_num"),
            "state"        : _str(row, "state"),
            "shape_area"   : _float(row, "shape_area"),
            "shape_len"    : _float(row, "shape_len"),
            "is_active"    : True,
            "geometry"     : row.geometry.wkt if row.geometry else None,
            "geom_ewkb"    : geom_to_ewkb_hex(row.geometry),
            "created_at"   : now,
            "updated_at"   : now,
        })
    return rows


# -- Entry point --------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Clean IBRARegion_Aust70.shp and migrate to the local ibra table."
    )
    parser.add_argument("--shp", required=True,
                        help="Path to IBRARegion_Aust70.shp")
    parser.add_argument("--dry-run", action="store_true",
                        help="Clean and report only -- no DB writes.")
    parser.add_argument("--db-url", default=None,
                        help="PostgreSQL connection string (overrides DATABASE_URL).")
    args = parser.parse_args()

    # Load
    print(f"\nLoading: {args.shp}")
    if not os.path.exists(args.shp):
        sys.exit(f"ERROR: File not found: {args.shp}")
    gdf = gpd.read_file(args.shp)
    print_report(gdf, "RAW shapefile")

    # Clean
    gdf = clean_gdf(gdf)
    print_report(gdf, "CLEANED shapefile")

    if args.dry_run:
        print("\n[Dry run] No database changes made.")
        return

    # Connect
    raw_url = (
        args.db_url
        or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eco_db")
    )
    sync_url = raw_url.replace("postgresql+asyncpg", "postgresql")
    print(f"\nConnecting to: {sync_url.split('@')[-1]}")
    engine = create_engine(sync_url, echo=False)

    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT PostGIS_version()"))
            print("PostGIS detected. OK")
        except Exception:
            sys.exit(
                "ERROR: PostGIS not found.\n"
                "Enable with: CREATE EXTENSION IF NOT EXISTS postgis;"
            )

    # Build rows
    rows = build_rows(gdf)

    # Guard: check column lengths BEFORE touching the DB
    check_column_lengths(rows, engine)

    # Migrate
    migrate(rows, engine)
    print("\nDone. Press F5 in DBeaver to refresh the ibra table.")


if __name__ == "__main__":
    main()
