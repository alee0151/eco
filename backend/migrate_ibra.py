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
               Cast Polygon → MultiPolygon for schema consistency.
               Normalise column names to match the `ibra` table schema.
               Drop rows where ibra_reg_code is null after normalisation.
               Derive `state` from the shapefile's state field if present.
  4. Migrate - Truncate the `ibra` table and bulk-insert all cleaned rows.
               Populates both `geometry` (WKT string for the API) and
               `geom` (PostGIS geometry) without using CASE expressions or
               referencing the same bind parameter twice (avoids
               SQLAlchemy CompileError 9h9h).

               The PostGIS `geom` column is populated by pre-computing an
               EWKB hex string in Python (via shapely.wkb.dumps with
               include_srid=True) and inserting it with
               ST_GeomFromEWKB(decode(:geom_ewkb, 'hex')).
               This uses exactly ONE bind parameter per row — no CASE needed.

Column mapping (shapefile → DB)
-------------------------------
  REG_NAME / IBRA_REG_N / RGN_NAME  →  ibra_reg_name
  REG_CODE / IBRA_REG_C / RGN_CODE  →  ibra_reg_code
  REG_NUM  / IBRA_REG_N₂            →  ibra_reg_num
  STA_CODE / STATE / STATE_CODE      →  state
  SHAPE_Area                         →  shape_area
  SHAPE_Leng / SHAPE_Length          →  shape_len
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
    pass  # optional — DATABASE_URL can be set via environment


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def normalise_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Map shapefile column names (which vary across IBRA releases) to the
    canonical names used by the `ibra` table schema.
    """
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


def ensure_multipolygon(geom):
    """Cast Polygon → MultiPolygon; pass MultiPolygon through; skip others."""
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


def geom_to_ewkb_hex(geom, srid: int = 4326) -> str | None:
    """
    Convert a Shapely geometry to an EWKB hex string with the given SRID
    embedded.  This is inserted via ST_GeomFromEWKB(decode(:geom_ewkb,'hex'))
    which requires exactly ONE bind parameter — avoiding the SQLAlchemy
    CompileError (9h9h) caused by referencing :geom_wkt twice inside a
    CASE expression.
    """
    if geom is None or geom.is_empty:
        return None
    # shapely_wkb.dumps(include_srid=True) writes the SRID into the WKB header
    return shapely_wkb.dumps(geom, hex=True, include_srid=True, srid=srid)


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(gdf: gpd.GeoDataFrame, label: str) -> None:
    n_total        = len(gdf)
    n_null_geom    = gdf.geometry.isna().sum()
    n_empty_geom   = gdf.geometry.apply(lambda g: g is not None and g.is_empty).sum()
    n_invalid_geom = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  CRS           : {gdf.crs}")
    print(f"  Rows          : {n_total}")
    print(f"  Null geometry : {n_null_geom}")
    print(f"  Empty geometry: {n_empty_geom}")
    print(f"  Invalid geom  : {n_invalid_geom}")
    print(f"  Columns       : {list(gdf.columns)}")

    if "ibra_reg_code" in gdf.columns:
        n_null_code = gdf["ibra_reg_code"].isna().sum()
        n_dup_code  = gdf["ibra_reg_code"].duplicated().sum()
        print(f"  Null reg_code : {n_null_code}")
        print(f"  Dup  reg_code : {n_dup_code}")

    if "ibra_reg_name" in gdf.columns:
        print(f"  Unique regions: {gdf['ibra_reg_name'].nunique()}")

    if "state" in gdf.columns:
        print(f"  States        : {sorted(gdf['state'].dropna().unique().tolist())}")


# ── Clean ─────────────────────────────────────────────────────────────────────

def clean_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    print("\n[1/4] Normalising column names...")
    gdf = normalise_columns(gdf)
    print(f"      Columns after rename: {list(gdf.columns)}")

    print("[2/4] Reprojecting to EPSG:4326 (WGS 84)...")
    if gdf.crs is None:
        print("      WARNING: No CRS detected — assuming GDA94 (EPSG:4283).")
        gdf = gdf.set_crs("EPSG:4283", allow_override=True)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
        print(f"      Reprojected → EPSG:4326")
    else:
        print("      Already EPSG:4326, no reprojection needed.")

    print("[3/4] Fixing invalid / null geometries...")
    before_invalid = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    gdf["geometry_col"] = gdf.geometry.apply(
        lambda g: make_valid(g)
        if g is not None and not g.is_empty and not g.is_valid else g
    )
    gdf = gdf.set_geometry("geometry_col").drop(columns=[gdf.geometry.name])
    gdf = gdf.rename_geometry("geometry")
    after_invalid = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    print(f"      Fixed {before_invalid - after_invalid} invalid geometries "
          f"(remaining: {after_invalid})")

    n_before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    print(f"      Dropped {n_before - len(gdf)} null/empty geometry rows.")

    print("[4/4] Casting all geometries to MultiPolygon...")
    gdf["geometry"] = gdf["geometry"].apply(ensure_multipolygon)
    gdf = gdf[gdf["geometry"].notna()].copy()
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    print(f"      All geometries are now MultiPolygon. Rows: {len(gdf)}")

    if "ibra_reg_code" in gdf.columns:
        n_before = len(gdf)
        gdf = gdf[
            gdf["ibra_reg_code"].notna() &
            (gdf["ibra_reg_code"].str.strip() != "")
        ].copy()
        print(f"      Dropped {n_before - len(gdf)} rows with null/empty ibra_reg_code.")

    return gdf


# ── Migrate ───────────────────────────────────────────────────────────────────

def migrate(gdf: gpd.GeoDataFrame, engine) -> None:
    now = datetime.now(timezone.utc).isoformat()

    def _safe_str(row, key):
        v = row.get(key, "") if hasattr(row, "get") else row[key] if key in row.index else ""
        return str(v).strip() or None

    def _safe_float(row, key):
        if key not in row.index:
            return None
        v = row[key]
        return float(v) if v is not None and str(v) not in ("", "nan", "None") else None

    def _safe_int(row, key):
        if key not in row.index:
            return None
        v = row[key]
        return int(v) if v is not None and str(v) not in ("", "nan", "None") else None

    rows = []
    for _, row in gdf.iterrows():
        wkt      = row.geometry.wkt if row.geometry else None
        ewkb_hex = geom_to_ewkb_hex(row.geometry)   # SRID=4326 baked in
        rows.append({
            "ibra_reg_name" : _safe_str(row, "ibra_reg_name"),
            "ibra_reg_code" : _safe_str(row, "ibra_reg_code"),
            "ibra_reg_num"  : _safe_int(row, "ibra_reg_num"),
            "state"         : _safe_str(row, "state"),
            "shape_area"    : _safe_float(row, "shape_area"),
            "shape_len"     : _safe_float(row, "shape_len"),
            "is_active"     : True,
            "geometry"      : wkt,        # WKT string — returned by the REST API
            "geom_ewkb"     : ewkb_hex,   # EWKB hex — decoded by PostGIS directly
            "created_at"    : now,
            "updated_at"    : now,
        })

    # ── INSERT statement — ONE bind parameter per column, no CASE expression ──
    # ST_GeomFromEWKB(decode(:geom_ewkb, 'hex')) reads the SRID from the WKB
    # header itself, so ST_SetSRID is not needed.
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

    BATCH_SIZE = 50  # keep individual transactions small for large WKT payloads

    with engine.begin() as conn:
        print("\n[Migrate] Truncating ibra table...")
        conn.execute(text("TRUNCATE TABLE ibra RESTART IDENTITY CASCADE"))

    total = len(rows)
    inserted = 0
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        with engine.begin() as conn:
            conn.execute(INSERT_SQL, batch)
        inserted += len(batch)
        print(f"[Migrate] Inserted {inserted}/{total} rows...", end="\r")

    print(f"\n[Migrate] ✅ All {inserted} rows inserted.")

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM ibra")).scalar()
        print(f"[Migrate] ✅ ibra table now contains {result} rows.")

        valid_geom = conn.execute(
            text("SELECT COUNT(*) FROM ibra WHERE geom IS NOT NULL AND ST_IsValid(geom)")
        ).scalar()
        print(f"[Migrate] ✅ {valid_geom} rows have a valid PostGIS geom.")

        null_geom = conn.execute(
            text("SELECT COUNT(*) FROM ibra WHERE geom IS NULL")
        ).scalar()
        if null_geom:
            print(f"[Migrate] ⚠️  {null_geom} rows have NULL geom "
                  f"(geometry was null or empty in the shapefile).")

        invalid_geom = conn.execute(
            text("SELECT COUNT(*) FROM ibra WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)")
        ).scalar()
        if invalid_geom:
            print(f"[Migrate] ⚠️  {invalid_geom} rows have invalid PostGIS geom — "
                  f"run UPDATE ibra SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Clean IBRARegion_Aust70.shp and migrate to the local ibra table."
    )
    parser.add_argument(
        "--shp",
        required=True,
        help="Absolute or relative path to IBRARegion_Aust70.shp",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Clean and report only — do not write to the database.",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help=(
            "PostgreSQL connection string. Defaults to DATABASE_URL env var, "
            "then postgresql://postgres:postgres@localhost:5432/eco_db."
        ),
    )
    args = parser.parse_args()

    # ── Load ──────────────────────────────────────────────────────────────────
    print(f"\nLoading: {args.shp}")
    if not os.path.exists(args.shp):
        sys.exit(f"ERROR: File not found: {args.shp}")
    gdf = gpd.read_file(args.shp)
    print_report(gdf, "RAW shapefile")

    # ── Clean ─────────────────────────────────────────────────────────────────
    gdf = clean_gdf(gdf)
    print_report(gdf, "CLEANED shapefile")

    if args.dry_run:
        print("\n[Dry run] No database changes made.")
        return

    # ── Connect ───────────────────────────────────────────────────────────────
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
            print("PostGIS extension detected. ✅")
        except Exception:
            sys.exit(
                "ERROR: PostGIS extension not found.\n"
                "Enable it with: CREATE EXTENSION IF NOT EXISTS postgis;"
            )

    # ── Migrate ───────────────────────────────────────────────────────────────
    migrate(gdf, engine)
    print("\nDone. Refresh the ibra table in DBeaver (F5) to see the new rows.")


if __name__ == "__main__":
    main()
