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
               Fix invalid geometries via buffer(0).
               Cast Polygon → MultiPolygon for schema consistency.
               Normalise column names to match the `ibra` table schema.
               Drop rows where ibra_reg_code is null after normalisation.
               Derive `state` from the shapefile's state field if present.
  4. Migrate - Truncate the `ibra` table and bulk-insert all cleaned rows.
               Populates both `geometry` (WKT string for the API) and
               `geom` (PostGIS WKB via ST_GeomFromText for spatial queries).

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
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.validation import make_valid
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
    pass  # optional — DATABASE_URL can be set directly in the environment


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

    # ibra_reg_name
    for candidate in ["REG_NAME", "IBRA_REG_N", "RGN_NAME", "REGIONNAME", "NAME"]:
        if candidate in cols:
            rename[cols[candidate]] = "ibra_reg_name"
            break

    # ibra_reg_code
    for candidate in ["REG_CODE", "IBRA_REG_C", "RGN_CODE", "REGIONCODE", "CODE"]:
        if candidate in cols:
            rename[cols[candidate]] = "ibra_reg_code"
            break

    # ibra_reg_num
    for candidate in ["REG_NUM", "IBRA_CODE", "REGIONNUM", "REGNUM"]:
        if candidate in cols:
            rename[cols[candidate]] = "ibra_reg_num"
            break

    # state
    for candidate in ["STA_CODE", "STATE", "STATE_CODE", "STATEABBR", "ST"]:
        if candidate in cols:
            rename[cols[candidate]] = "state_raw"
            break

    # shape_area
    for candidate in ["SHAPE_AREA", "AREA", "SHAPE_A"]:
        if candidate in cols:
            rename[cols[candidate]] = "shape_area"
            break

    # shape_len
    for candidate in ["SHAPE_LENG", "SHAPE_LENGTH", "PERIMETER", "SHAPE_L"]:
        if candidate in cols:
            rename[cols[candidate]] = "shape_len"
            break

    gdf = gdf.rename(columns=rename)

    # Expand state abbreviation to full name where possible
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
    # GeometryCollection etc. — try to extract polygon parts
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


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(gdf: gpd.GeoDataFrame, label: str) -> None:
    n_total        = len(gdf)
    n_null_geom    = gdf.geometry.isna().sum()
    n_empty_geom   = gdf.geometry.apply(lambda g: g is not None and g.is_empty).sum()
    n_invalid_geom = gdf.geometry.apply(lambda g: g is not None and not g.is_empty and not g.is_valid).sum()

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
        print("      WARNING: No CRS detected — assuming GDA94 (EPSG:4283) and reprojecting.")
        gdf = gdf.set_crs("EPSG:4283", allow_override=True)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
        print(f"      Reprojected from {gdf.crs} → EPSG:4326")
    else:
        print("      Already in EPSG:4326, no reprojection needed.")

    print("[3/4] Fixing invalid / null geometries...")
    before_invalid = gdf.geometry.apply(lambda g: g is not None and not g.is_empty and not g.is_valid).sum()
    gdf["geometry_col"] = gdf.geometry.apply(
        lambda g: make_valid(g) if g is not None and not g.is_empty and not g.is_valid else g
    )
    gdf = gdf.set_geometry("geometry_col").drop(columns=[gdf.geometry.name])
    gdf = gdf.rename_geometry("geometry")
    after_invalid = gdf.geometry.apply(lambda g: g is not None and not g.is_empty and not g.is_valid).sum()
    print(f"      Fixed {before_invalid - after_invalid} invalid geometries (remaining: {after_invalid})")

    # Drop null / empty geometry rows
    n_before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    print(f"      Dropped {n_before - len(gdf)} null/empty geometry rows.")

    print("[4/4] Casting all geometries to MultiPolygon...")
    gdf["geometry"] = gdf["geometry"].apply(ensure_multipolygon)
    gdf = gdf[gdf["geometry"].notna()].copy()
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    print(f"      All geometries are now MultiPolygon. Rows: {len(gdf)}")

    # Drop rows with null ibra_reg_code (cannot be used for spatial lookups)
    if "ibra_reg_code" in gdf.columns:
        n_before = len(gdf)
        gdf = gdf[gdf["ibra_reg_code"].notna() & (gdf["ibra_reg_code"].str.strip() != "")].copy()
        print(f"      Dropped {n_before - len(gdf)} rows with null/empty ibra_reg_code.")

    return gdf


# ── Migrate ───────────────────────────────────────────────────────────────────

def migrate(gdf: gpd.GeoDataFrame, engine) -> None:
    now = datetime.now(timezone.utc).isoformat()

    rows = []
    for _, row in gdf.iterrows():
        wkt = row.geometry.wkt if row.geometry else None
        rows.append({
            "ibra_reg_name" : str(row.get("ibra_reg_name", "") or "").strip() or None,
            "ibra_reg_code" : str(row.get("ibra_reg_code", "") or "").strip() or None,
            "ibra_reg_num"  : int(row["ibra_reg_num"])  if "ibra_reg_num"  in row.index and row["ibra_reg_num"]  is not None and str(row["ibra_reg_num"]) not in ("", "nan", "None") else None,
            "state"         : str(row["state"]).strip() if "state" in row.index and row["state"] and str(row["state"]) not in ("", "nan", "None") else None,
            "shape_area"    : float(row["shape_area"])  if "shape_area"    in row.index and row["shape_area"]  is not None and str(row["shape_area"]) not in ("", "nan", "None") else None,
            "shape_len"     : float(row["shape_len"])   if "shape_len"     in row.index and row["shape_len"]   is not None and str(row["shape_len"])  not in ("", "nan", "None") else None,
            "is_active"     : True,
            "geometry"      : wkt,   # WKT string — used by the API JSON response
            "geom_wkt"      : wkt,   # alias for convenience
            "created_at"    : now,
            "updated_at"    : now,
        })

    with engine.begin() as conn:
        print(f"\n[Migrate] Truncating ibra table...")
        conn.execute(text("TRUNCATE TABLE ibra RESTART IDENTITY CASCADE"))

        print(f"[Migrate] Inserting {len(rows)} rows...")
        conn.execute(
            text("""
                INSERT INTO ibra (
                    ibra_reg_name, ibra_reg_code, ibra_reg_num,
                    state, shape_area, shape_len,
                    is_active, geometry, created_at, updated_at,
                    geom
                ) VALUES (
                    :ibra_reg_name, :ibra_reg_code, :ibra_reg_num,
                    :state, :shape_area, :shape_len,
                    :is_active, :geometry, :created_at, :updated_at,
                    CASE
                        WHEN :geom_wkt IS NOT NULL
                        THEN ST_Multi(ST_SetSRID(ST_GeomFromText(:geom_wkt), 4326))
                        ELSE NULL
                    END
                )
            """),
            rows,
        )

        result = conn.execute(text("SELECT COUNT(*) FROM ibra")).scalar()
        print(f"[Migrate] ✅ ibra table now contains {result} rows.")

        # Verify PostGIS geom column populated correctly
        valid_geom = conn.execute(
            text("SELECT COUNT(*) FROM ibra WHERE geom IS NOT NULL AND ST_IsValid(geom)")
        ).scalar()
        print(f"[Migrate] ✅ {valid_geom} rows have valid PostGIS geom.")

        invalid_geom = conn.execute(
            text("SELECT COUNT(*) FROM ibra WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)")
        ).scalar()
        if invalid_geom > 0:
            print(f"[Migrate] ⚠️  {invalid_geom} rows have invalid PostGIS geom — consider re-running with --fix-postgis.")


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
    # Strip asyncpg driver prefix if present (script uses sync psycopg2)
    sync_url = raw_url.replace("postgresql+asyncpg", "postgresql")
    print(f"\nConnecting to: {sync_url.split('@')[-1]}")
    engine = create_engine(sync_url, echo=False)

    # Quick PostGIS check
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT PostGIS_version()"))
            print("PostGIS extension detected. ✅")
        except Exception:
            sys.exit(
                "ERROR: PostGIS extension not found in the target database.\n"
                "Enable it with: CREATE EXTENSION IF NOT EXISTS postgis;"
            )

    # ── Migrate ───────────────────────────────────────────────────────────────
    migrate(gdf, engine)
    print("\nDone. Refresh the ibra table in DBeaver (F5) to see the new rows.")


if __name__ == "__main__":
    main()
