"""
migrate_capad_shp.py

Drops the existing `capad` table, recreates it from the SQLAlchemy model,
cleans the CAPAD 2024 Terrestrial shapefile, and bulk-inserts all rows.

Usage
-----
  # From the backend/ directory:
  pip install geopandas shapely psycopg2-binary python-dotenv sqlalchemy geoalchemy2 tqdm

  python migrate_capad_shp.py --shp /path/to/CAPAD2024_terrestrial.shp

  # Dry-run (clean + report, no DB writes, saves cleaned GeoJSON):
  python migrate_capad_shp.py --shp /path/to/CAPAD2024_terrestrial.shp --dry-run

Shapefile columns handled
-------------------------
  OBJECTID, PA_ID, PA_PID, NAME, TYPE, TYPE_ABBR, IUCN,
  NRS_PA, NRS_MPA, GAZ_AREA, GIS_AREA, GAZ_DATE, LATEST_GAZ,
  STATE, AUTHORITY, DATASOURCE, GOVERNANCE, COMMENTS, ENVIRON,
  OVERLAP, MGT_PLAN, RES_NUMBER, ZONE_TYPE, EPBC,
  LONGITUDE, LATITUDE, PA_SYSTEM, Shape__Are, Shape__Len

DB column mapping
-----------------
  OBJECTID      -> objectid          (INTEGER, primary-key-like, UNIQUE)
  PA_ID         -> pa_id
  PA_PID        -> pa_pid
  NAME          -> pa_name
  TYPE          -> pa_type
  TYPE_ABBR     -> pa_type_abbr
  IUCN          -> iucn_cat
  NRS_PA        -> nrs_pa            (bool)
  NRS_MPA       -> nrs_mpa           (bool)
  GAZ_AREA      -> gaz_area_ha
  GIS_AREA      -> gis_area_ha
  GAZ_DATE      -> gaz_date
  LATEST_GAZ    -> latest_gaz
  STATE         -> state
  AUTHORITY     -> authority
  DATASOURCE    -> source_dataset
  GOVERNANCE    -> governance
  COMMENTS      -> comments
  ENVIRON       -> environ
  OVERLAP       -> overlap
  MGT_PLAN      -> mgt_plan
  RES_NUMBER    -> res_number
  ZONE_TYPE     -> zone_type
  EPBC          -> epbc_trigger
  LONGITUDE     -> longitude
  LATITUDE      -> latitude
  PA_SYSTEM     -> pa_system
  Shape__Are    -> shape_area
  Shape__Len    -> shape_len
"""

import argparse
import os
import sys
from datetime import datetime, timezone

try:
    import geopandas as gpd
except ImportError:
    sys.exit("ERROR: geopandas not installed.  Run: pip install geopandas")

try:
    from shapely.geometry import MultiPolygon
    from shapely.validation import make_valid
    from shapely import wkb as shapely_wkb
except ImportError:
    sys.exit("ERROR: shapely not installed.  Run: pip install shapely")

try:
    from sqlalchemy import create_engine, text
except ImportError:
    sys.exit("ERROR: sqlalchemy not installed.  Run: pip install sqlalchemy")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_IUCN = {
    "Ia", "Ib", "II", "III", "IV", "V", "VI",
    "Not Reported", "Not Applicable",
}

AUS_LAT = (-44.0, -10.0)
AUS_LON = (112.0, 154.0)

BATCH_SIZE = 100

# Exact SHP column -> DB column mapping (uppercase keys = shapefile names)
COL_MAP = {
    "OBJECTID":   "objectid",
    "PA_ID":      "pa_id",
    "PA_PID":     "pa_pid",
    "NAME":       "pa_name",
    "TYPE":       "pa_type",
    "TYPE_ABBR":  "pa_type_abbr",
    "IUCN":       "iucn_cat",
    "NRS_PA":     "nrs_pa",
    "NRS_MPA":    "nrs_mpa",
    "GAZ_AREA":   "gaz_area_ha",
    "GIS_AREA":   "gis_area_ha",
    "GAZ_DATE":   "gaz_date",
    "LATEST_GAZ": "latest_gaz",
    "STATE":      "state",
    "AUTHORITY":  "authority",
    "DATASOURCE": "source_dataset",
    "GOVERNANCE": "governance",
    "COMMENTS":   "comments",
    "ENVIRON":    "environ",
    "OVERLAP":    "overlap",
    "MGT_PLAN":   "mgt_plan",
    "RES_NUMBER": "res_number",
    "ZONE_TYPE":  "zone_type",
    "EPBC":       "epbc_trigger",
    "LONGITUDE":  "longitude",
    "LATITUDE":   "latitude",
    "PA_SYSTEM":  "pa_system",
    "SHAPE__ARE": "shape_area",   # geopandas uppercases these
    "SHAPE__LEN": "shape_len",
}


# ---------------------------------------------------------------------------
# DDL — matches the updated Capad model in models.py
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE capad (
    id              SERIAL PRIMARY KEY,
    objectid        INTEGER,
    pa_id           TEXT,
    pa_pid          TEXT,
    pa_name         TEXT,
    pa_type         TEXT,
    pa_type_abbr    TEXT,
    iucn_cat        TEXT,
    nrs_pa          BOOLEAN,
    nrs_mpa         BOOLEAN,
    gaz_area_ha     DOUBLE PRECISION,
    gis_area_ha     DOUBLE PRECISION,
    gaz_date        TIMESTAMPTZ,
    latest_gaz      TIMESTAMPTZ,
    state           TEXT,
    authority       TEXT,
    source_dataset  TEXT,
    governance      TEXT,
    comments        TEXT,
    environ         TEXT,
    overlap         TEXT,
    mgt_plan        TEXT,
    res_number      TEXT,
    zone_type       TEXT,
    epbc_trigger    TEXT,
    longitude       DOUBLE PRECISION,
    latitude        DOUBLE PRECISION,
    pa_system       TEXT,
    shape_area      DOUBLE PRECISION,
    shape_len       DOUBLE PRECISION,
    capad_version   TEXT,
    capad_citation  TEXT,
    capad_licence   TEXT,
    is_active       BOOLEAN         DEFAULT TRUE,
    cleaned_at      TIMESTAMPTZ,
    geom_wkt        TEXT,
    geom            geometry(MultiPolygon, 4326)
);

CREATE UNIQUE INDEX capad_objectid_uidx ON capad (objectid);
CREATE INDEX capad_state_idx        ON capad (state);
CREATE INDEX capad_iucn_idx         ON capad (iucn_cat);
CREATE INDEX capad_epbc_idx         ON capad (epbc_trigger);
CREATE INDEX capad_pa_type_idx      ON capad (pa_type_abbr);
CREATE INDEX capad_geom_idx         ON capad USING GIST (geom);
"""


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------

def _s(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s not in ("", "nan", "None", "NaN") else None


def _f(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _i(v) -> int | None:
    if v is None:
        return None
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return None


def _bool_yn(v) -> bool | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in ("Y", "YES", "TRUE", "1"):
        return True
    if s in ("N", "NO", "FALSE", "0"):
        return False
    return None


def _date(v) -> str | None:
    """Return ISO-8601 string or None. psycopg2 will bind this as TEXT;
    the INSERT SQL casts it to TIMESTAMPTZ via CAST(... AS TIMESTAMPTZ)."""
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "nan", "None", "NaT"):
        return None
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            pass
    for fmt in (
        "%Y/%m/%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z",
        "%Y/%m/%d %H:%M:%S",   "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",             "%Y-%m-%d",
        "%d/%m/%Y",             "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(s[:len(fmt)], fmt).isoformat()
        except ValueError:
            continue
    return None


def _iucn(v) -> str:
    if v is None:
        return "Not Reported"
    s = str(v).strip()
    if s in VALID_IUCN:
        return s
    aliases = {
        "IA": "Ia", "IB": "Ib",
        "NOT APPLICABLE": "Not Applicable", "N/A": "Not Applicable",
        "NR": "Not Reported", "NONE": "Not Reported", "": "Not Reported",
    }
    return aliases.get(s.upper(), "Not Reported")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _to_multipolygon(geom):
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
    if not polys:
        return None
    parts = []
    for p in polys:
        if p.geom_type == "Polygon":
            parts.append(p)
        else:
            parts.extend(p.geoms)
    return MultiPolygon(parts) if parts else None


def _ewkb(geom, srid: int = 4326) -> str | None:
    """EWKB hex string — passed as :geom_ewkb and decoded in SQL."""
    if geom is None or geom.is_empty:
        return None
    return shapely_wkb.dumps(geom, hex=True, include_srid=True, srid=srid)


# ---------------------------------------------------------------------------
# Cleaning report
# ---------------------------------------------------------------------------

def report(gdf: gpd.GeoDataFrame, label: str) -> None:
    n_null    = gdf.geometry.isna().sum()
    n_empty   = gdf.geometry.apply(lambda g: g is not None and g.is_empty).sum()
    n_invalid = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    print(f"\n{'='*62}")
    print(f"  {label}")
    print(f"{'='*62}")
    print(f"  CRS            : {gdf.crs}")
    print(f"  Rows           : {len(gdf)}")
    print(f"  Null geometry  : {n_null}")
    print(f"  Empty geometry : {n_empty}")
    print(f"  Invalid geom   : {n_invalid}")
    print(f"  Columns        : {list(gdf.columns)}")
    for col in ("objectid", "pa_id", "pa_name"):
        if col in gdf.columns:
            print(f"  Null {col:<12}: {gdf[col].isna().sum()}")
    if "objectid" in gdf.columns:
        print(f"  Dup objectid   : {gdf['objectid'].duplicated().sum()}")
    if "iucn_cat" in gdf.columns:
        print(f"  IUCN values    : {sorted(gdf['iucn_cat'].dropna().unique().tolist())}")
    if "state" in gdf.columns:
        print(f"  States         : {sorted(gdf['state'].dropna().unique().tolist())}")


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

def clean(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # 1. Rename columns using the exact COL_MAP
    print("\n[1/6] Renaming columns...")
    rename = {}
    cols_upper = {c.upper(): c for c in gdf.columns}
    for shp_col_upper, db_col in COL_MAP.items():
        if shp_col_upper in cols_upper:
            src = cols_upper[shp_col_upper]
            if src != db_col:
                rename[src] = db_col
    gdf = gdf.rename(columns=rename)
    print(f"      Renamed: {rename}")

    # 2. Reproject -> EPSG:4326
    print("[2/6] Reprojecting to EPSG:4326...")
    if gdf.crs is None:
        print("      WARNING: No CRS. Assuming GDA94 (EPSG:4283).")
        gdf = gdf.set_crs("EPSG:4283", allow_override=True)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
        print("      Reprojected -> EPSG:4326")
    else:
        print("      Already EPSG:4326.")

    # 3. Fix invalid geometries
    print("[3/6] Fixing invalid geometries...")
    n_bad = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    gdf["_g"] = gdf.geometry.apply(
        lambda g: make_valid(g) if g is not None and not g.is_empty and not g.is_valid else g
    )
    orig_geom_col = gdf.geometry.name
    gdf = gdf.set_geometry("_g").drop(columns=[orig_geom_col]).rename_geometry("geometry")
    n_still_bad = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    print(f"      Fixed {n_bad - n_still_bad} geoms ({n_still_bad} still invalid).")

    n_before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    print(f"      Dropped {n_before - len(gdf)} null/empty geometry rows.")

    # 4. Cast to MultiPolygon
    print("[4/6] Casting to MultiPolygon...")
    gdf["geometry"] = gdf["geometry"].apply(_to_multipolygon)
    gdf = gdf[gdf["geometry"].notna()].copy()
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    print(f"      Rows after cast: {len(gdf)}")

    # 5. Clean attribute columns
    print("[5/6] Cleaning attribute fields...")

    if "objectid" in gdf.columns:
        gdf["objectid"] = gdf["objectid"].apply(_i)
        n_b = len(gdf)
        gdf = gdf.drop_duplicates(subset="objectid", keep="last")
        print(f"      Deduped objectid: removed {n_b - len(gdf)} duplicates.")
    else:
        gdf["objectid"] = range(1, len(gdf) + 1)
        print("      WARNING: No OBJECTID column. Synthesised from row index.")

    n_b = len(gdf)
    gdf = gdf[gdf["objectid"].notna()].copy()
    print(f"      Dropped {n_b - len(gdf)} rows with null objectid.")

    if "iucn_cat" in gdf.columns:
        gdf["iucn_cat"] = gdf["iucn_cat"].apply(_iucn)

    for bool_col in ("nrs_pa", "nrs_mpa"):
        if bool_col in gdf.columns:
            gdf[bool_col] = gdf[bool_col].apply(_bool_yn)

    if "latitude" in gdf.columns:
        gdf["latitude"] = gdf["latitude"].apply(
            lambda v: _f(v) if v is not None and AUS_LAT[0] <= (_f(v) or 999) <= AUS_LAT[1] else None
        )
    if "longitude" in gdf.columns:
        gdf["longitude"] = gdf["longitude"].apply(
            lambda v: _f(v) if v is not None and AUS_LON[0] <= (_f(v) or 0) <= AUS_LON[1] else None
        )

    # 6. Fill missing lat/lon from centroid
    print("[6/6] Deriving missing lat/lon from polygon centroid...")
    for col, axis in (("latitude", "y"), ("longitude", "x")):
        if col not in gdf.columns or gdf[col].isna().all():
            gdf[col] = getattr(gdf.geometry.centroid, axis)
            print(f"      Derived {col} from centroid.")
        else:
            null_mask = gdf[col].isna()
            if null_mask.any():
                gdf.loc[null_mask, col] = getattr(gdf[null_mask].geometry.centroid, axis)

    return gdf


# ---------------------------------------------------------------------------
# Build row dicts
# ---------------------------------------------------------------------------

def build_rows(gdf: gpd.GeoDataFrame, version: str = "2024") -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    rows = []

    iter_fn = (
        tqdm(gdf.iterrows(), total=len(gdf), desc="Building rows", unit="row")
        if HAS_TQDM else gdf.iterrows()
    )

    def _g(row, col):
        return row[col] if col in row.index else None

    for _, row in iter_fn:
        geom = row.geometry
        rows.append({
            "objectid":       _i(_g(row, "objectid")),
            "pa_id":          _s(_g(row, "pa_id")),
            "pa_pid":         _s(_g(row, "pa_pid")),
            "pa_name":        _s(_g(row, "pa_name")),
            "pa_type":        _s(_g(row, "pa_type")),
            "pa_type_abbr":   _s(_g(row, "pa_type_abbr")),
            "iucn_cat":       _iucn(_g(row, "iucn_cat")),
            "nrs_pa":         _bool_yn(_g(row, "nrs_pa")),
            "nrs_mpa":        _bool_yn(_g(row, "nrs_mpa")),
            "gaz_area_ha":    _f(_g(row, "gaz_area_ha")),
            "gis_area_ha":    _f(_g(row, "gis_area_ha")),
            "gaz_date":       _date(_g(row, "gaz_date")),
            "latest_gaz":     _date(_g(row, "latest_gaz")),
            "state":          _s(_g(row, "state")),
            "authority":      _s(_g(row, "authority")),
            "source_dataset": _s(_g(row, "source_dataset")),
            "governance":     _s(_g(row, "governance")),
            "comments":       _s(_g(row, "comments")),
            "environ":        _s(_g(row, "environ")),
            "overlap":        _s(_g(row, "overlap")),
            "mgt_plan":       _s(_g(row, "mgt_plan")),
            "res_number":     _s(_g(row, "res_number")),
            "zone_type":      _s(_g(row, "zone_type")),
            "epbc_trigger":   _s(_g(row, "epbc_trigger")),
            "longitude":      _f(_g(row, "longitude")),
            "latitude":       _f(_g(row, "latitude")),
            "pa_system":      _s(_g(row, "pa_system")),
            "shape_area":     _f(_g(row, "shape_area")),
            "shape_len":      _f(_g(row, "shape_len")),
            "capad_version":  version,
            "capad_citation": "DCCEEW (2024) Collaborative Australian Protected Areas Database (CAPAD) 2024",
            "capad_licence":  "CC BY 4.0",
            "is_active":      True,
            "cleaned_at":     now,
            "geom_wkt":       geom.wkt if geom and not geom.is_empty else None,
            "geom_ewkb":      _ewkb(geom),
        })
    return rows


# ---------------------------------------------------------------------------
# DDL helpers
# ---------------------------------------------------------------------------

def drop_and_create(engine) -> None:
    with engine.begin() as conn:
        print("[DDL] Dropping capad table (CASCADE)...")
        conn.execute(text("DROP TABLE IF EXISTS capad CASCADE"))
        print("[DDL] Creating capad table + indexes...")
        for stmt in CREATE_TABLE_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    print("[DDL] Done.")


# ---------------------------------------------------------------------------
# Migrate (bulk INSERT)
# ---------------------------------------------------------------------------
# NOTE: psycopg2 chokes on `:param::TYPE` because `::` immediately after a
# bind-param marker confuses its parser.  Use CAST(:param AS TYPE) instead.
# ---------------------------------------------------------------------------

INSERT_SQL = text("""
    INSERT INTO capad (
        objectid, pa_id, pa_pid, pa_name, pa_type, pa_type_abbr,
        iucn_cat, nrs_pa, nrs_mpa,
        gaz_area_ha, gis_area_ha, gaz_date, latest_gaz,
        state, authority, source_dataset, governance, comments,
        environ, overlap, mgt_plan, res_number, zone_type, epbc_trigger,
        longitude, latitude, pa_system, shape_area, shape_len,
        capad_version, capad_citation, capad_licence,
        is_active, cleaned_at, geom_wkt, geom
    ) VALUES (
        :objectid, :pa_id, :pa_pid, :pa_name, :pa_type, :pa_type_abbr,
        :iucn_cat, :nrs_pa, :nrs_mpa,
        :gaz_area_ha, :gis_area_ha,
        CAST(:gaz_date AS TIMESTAMPTZ),
        CAST(:latest_gaz AS TIMESTAMPTZ),
        :state, :authority, :source_dataset, :governance, :comments,
        :environ, :overlap, :mgt_plan, :res_number, :zone_type, :epbc_trigger,
        :longitude, :latitude, :pa_system, :shape_area, :shape_len,
        :capad_version, :capad_citation, :capad_licence,
        :is_active,
        CAST(:cleaned_at AS TIMESTAMPTZ),
        :geom_wkt,
        ST_GeomFromEWKB(decode(:geom_ewkb, 'hex'))
    )
""")


def migrate(rows: list[dict], engine) -> None:
    total    = len(rows)
    inserted = 0
    errors   = 0

    batch_range = range(0, total, BATCH_SIZE)
    if HAS_TQDM:
        batch_range = tqdm(batch_range, desc="Inserting batches", unit="batch")

    for i in batch_range:
        batch = rows[i: i + BATCH_SIZE]
        valid = [r for r in batch if r.get("geom_ewkb")]
        skipped = len(batch) - len(valid)
        if skipped:
            print(f"  [Warning] Skipped {skipped} rows with null geometry in batch starting at {i}.")
            errors += skipped
        if not valid:
            continue
        try:
            with engine.begin() as conn:
                conn.execute(INSERT_SQL, valid)
            inserted += len(valid)
        except Exception as exc:
            print(f"\n  [Error] Batch {i // BATCH_SIZE} failed: {exc}")
            errors += len(valid)

    print(f"\n[Migrate] Inserted {inserted}/{total} rows | Skipped/errored: {errors}")

    with engine.connect() as conn:
        total_db  = conn.execute(text("SELECT COUNT(*) FROM capad")).scalar()
        with_geom = conn.execute(text("SELECT COUNT(*) FROM capad WHERE geom IS NOT NULL")).scalar()
        valid_g   = conn.execute(text("SELECT COUNT(*) FROM capad WHERE geom IS NOT NULL AND ST_IsValid(geom)")).scalar()
        by_state  = conn.execute(text(
            "SELECT state, COUNT(*) cnt FROM capad GROUP BY state ORDER BY cnt DESC LIMIT 12"
        )).fetchall()

    print(f"\n[Validate] capad:")
    print(f"  Total rows  : {total_db}")
    print(f"  With geom   : {with_geom}")
    print(f"  Valid geom  : {valid_g}")
    print("  By state:")
    for s, cnt in by_state:
        print(f"    {(s or 'NULL'):<30} {cnt}")

    bad = with_geom - valid_g
    if bad:
        print(f"\n  [Warning] {bad} invalid geoms. Fix with:")
        print("    UPDATE capad SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    # global BATCH_SIZE must be declared before any reference inside this
    # function so Python's compile-time scan does not raise SyntaxError.
    global BATCH_SIZE

    parser = argparse.ArgumentParser(
        description="Drop capad table, recreate, clean CAPAD .shp, and bulk-insert."
    )
    parser.add_argument("--shp",     required=True, help="Path to the CAPAD .shp file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Clean + report only — no DB writes. Saves cleaned GeoJSON.")
    parser.add_argument("--version", default="2024", help="capad_version tag (default: 2024)")
    parser.add_argument("--db-url",  default=None,
                        help="PostgreSQL DSN (overrides DATABASE_URL env var)")
    parser.add_argument("--batch",   type=int, default=BATCH_SIZE,
                        help=f"Rows per INSERT batch (default: {BATCH_SIZE})")
    args = parser.parse_args()

    BATCH_SIZE = args.batch

    if not os.path.exists(args.shp):
        sys.exit(f"ERROR: Shapefile not found: {args.shp}")

    # ── Load ───────────────────────────────────────────────────────────
    print(f"\nLoading: {args.shp}")
    gdf = gpd.read_file(args.shp)
    report(gdf, "RAW shapefile")

    # ── Clean ──────────────────────────────────────────────────────────
    gdf = clean(gdf)
    report(gdf, "CLEANED shapefile")

    if args.dry_run:
        out = args.shp.replace(".shp", "_cleaned.geojson")
        gdf.to_file(out, driver="GeoJSON")
        print(f"\n[Dry run] Saved cleaned GeoJSON to: {out}")
        print("[Dry run] No DB changes made.")
        return

    # ── Connect ────────────────────────────────────────────────────────
    raw_url  = args.db_url or os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eco_db"
    )
    sync_url = raw_url.replace("postgresql+asyncpg", "postgresql")
    print(f"\nConnecting to: ...@{sync_url.split('@')[-1]}")
    engine = create_engine(sync_url, echo=False)

    with engine.connect() as conn:
        try:
            ver = conn.execute(text("SELECT PostGIS_version()")).scalar()
            print(f"PostGIS {ver} — OK")
        except Exception:
            sys.exit(
                "ERROR: PostGIS extension not found.\n"
                "Enable with: CREATE EXTENSION IF NOT EXISTS postgis;"
            )

    # ── Drop + recreate table ──────────────────────────────────────────
    drop_and_create(engine)

    # ── Build rows ───────────────────────────────────────────────────
    print("\nBuilding row dicts...")
    rows = build_rows(gdf, version=args.version)
    print(f"Built {len(rows)} rows.")

    # ── Insert ─────────────────────────────────────────────────────────
    migrate(rows, engine)
    print("\nDone. Press F5 in DBeaver to refresh the capad table.")


if __name__ == "__main__":
    main()
