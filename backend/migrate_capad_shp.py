"""
migrate_capad_shp.py

Cleans a CAPAD 2024 Terrestrial .shp file and migrates it into the local
PostgreSQL `capad` table used by the ECO backend.

Usage
-----
  # From the backend/ directory:
  pip install geopandas shapely psycopg2-binary python-dotenv sqlalchemy tqdm

  python migrate_capad_shp.py --shp /path/to/CAPAD2024_terrestrial.shp

  # Dry-run (clean + report only, no DB writes):
  python migrate_capad_shp.py --shp /path/to/CAPAD2024_terrestrial.shp --dry-run

  # Drop & recreate (full reload):
  python migrate_capad_shp.py --shp /path/to/CAPAD2024_terrestrial.shp --drop

What this script does
---------------------
  1. Load     - Read the .shp file with GeoPandas.
  2. Inspect  - Print a cleaning report (CRS, row count, null/invalid geom,
                duplicate OBJECTID, column names).
  3. Clean    - Reproject to EPSG:4326 (WGS 84) if needed.
                Fix invalid geometries via make_valid().
                Cast Polygon -> MultiPolygon for schema consistency.
                Normalise column names to match the `capad` table schema.
                Parse date fields (GAZ_DATE, LATEST_GAZ).
                Validate lat/lon ranges; nullify out-of-range values.
                Normalise IUCN categories.
                Deduplicate on OBJECTID (keep last).
  4. Guard    - Introspect live DB VARCHAR column lengths; exit if any value
                would truncate.
  5. Migrate  - UPSERT via ON CONFLICT (objectid) DO UPDATE so re-runs are
                fully idempotent. Batches of 100 rows.
                PostGIS `geom` column populated via EWKB hex string.
                `geom_wkt` populated from the geometry WKT for frontend display.

Column mapping (shapefile -> DB)
---------------------------------
  OBJECTID           -> objectid
  PA_ID              -> pa_id
  NAME / PA_NAME     -> pa_name
  TYPE / PA_TYPE     -> pa_type
  TYPE_ABBR          -> pa_type_abbr
  IUCN               -> iucn_cat
  NRS_PA             -> nrs_pa (Y/N -> bool)
  GAZ_AREA           -> gaz_area_ha
  GIS_AREA           -> gis_area_ha
  STATE              -> state
  ENVIRON            -> environ
  EPBC               -> epbc_trigger
  LAT                -> latitude
  LON / LONG         -> longitude
  GAZ_DATE           -> gaz_date
  LATEST_GAZ         -> latest_gaz
  PA_PID             -> pa_pid
  MGT_PLAN           -> governance
  AUTHORITY          -> authority
  DATASOURCE         -> source_dataset
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

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_IUCN = {"Ia", "Ib", "II", "III", "IV", "V", "VI",
               "Not Reported", "Not Applicable"}

AUS_LAT_RANGE = (-44.0, -10.0)
AUS_LON_RANGE = (112.0, 154.0)

BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Column normalisation
# ---------------------------------------------------------------------------

def _find_col(cols_upper: dict, candidates: list[str]) -> str | None:
    """Return the first shapefile column name (case-insensitive) matching candidates."""
    for c in candidates:
        if c in cols_upper:
            return cols_upper[c]
    return None


def normalise_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Rename shapefile columns to match the `capad` DB table schema."""
    cols_upper = {c.upper(): c for c in gdf.columns}

    mapping = {
        # DB column          candidate names in shapefile (upper-cased)
        "objectid":      ["OBJECTID", "OID", "FID"],
        "pa_id":         ["PA_ID", "PAID", "AREA_ID"],
        "pa_name":       ["NAME", "PA_NAME", "AREANAME"],
        "pa_type":       ["TYPE", "PA_TYPE", "AREATYPE", "DESIG"],
        "pa_type_abbr":  ["TYPE_ABBR", "PA_ABBR", "DESIG_ABB", "TYPEABBR"],
        "iucn_cat":      ["IUCN", "IUCNCAT", "IUCN_CAT", "IUCN_CODE"],
        "nrs_pa":        ["NRS_PA", "NRSPA"],
        "gaz_area_ha":   ["GAZ_AREA", "GAZAREA", "GAZ_AREA_H", "GAZ_AREAHA"],
        "gis_area_ha":   ["GIS_AREA", "GISAREA", "GIS_AREA_H", "GIS_AREAHA", "AREA_HA", "AREA"],
        "state":         ["STATE", "ST", "STATE_CODE", "STA_CODE"],
        "environ":       ["ENVIRON", "ENVIRONMENT"],
        "epbc_trigger":  ["EPBC", "EPBC_TRIG", "EPBCTRIGGE"],
        "latitude":      ["LAT", "LATITUDE", "Y"],
        "longitude":     ["LON", "LONG", "LONGITUDE", "X"],
        "gaz_date":      ["GAZ_DATE", "GAZDATE"],
        "latest_gaz":    ["LATEST_GAZ", "LATESTGAZ", "LATEST_GA"],
        "pa_pid":        ["PA_PID", "PAPID"],
        "governance":    ["MGT_PLAN", "GOVERNANCE", "GOV_TYPE"],
        "authority":     ["AUTHORITY", "MGT_AUTH", "MANAGER"],
        "source_dataset":["DATASOURCE", "DATA_SRC", "SOURCE", "DATASRC"],
    }

    rename = {}
    for db_col, candidates in mapping.items():
        src = _find_col(cols_upper, candidates)
        if src and src not in rename.values():
            rename[src] = db_col

    gdf = gdf.rename(columns=rename)
    return gdf


# ---------------------------------------------------------------------------
# Geometry helpers  (identical to migrate_ibra.py pattern)
# ---------------------------------------------------------------------------

def ensure_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    # GeometryCollection or other heterogeneous — extract polygons
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
    Convert a Shapely geometry to an EWKB hex string with SRID embedded.
    Used as a single bind param via ST_GeomFromEWKB(decode(:geom_ewkb,'hex'))
    to avoid SQLAlchemy CompileError on multiple geometry bind params.
    """
    if geom is None or geom.is_empty:
        return None
    return shapely_wkb.dumps(geom, hex=True, include_srid=True, srid=srid)


# ---------------------------------------------------------------------------
# Field helpers
# ---------------------------------------------------------------------------

def _str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s not in ("", "nan", "None", "NaN") else None


def _float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _bool_yn(val) -> bool | None:
    """Convert Y/N/True/False/1/0 to Python bool."""
    if val is None:
        return None
    s = str(val).strip().upper()
    if s in ("Y", "YES", "TRUE", "1"):
        return True
    if s in ("N", "NO", "FALSE", "0"):
        return False
    return None


def _parse_date(val) -> str | None:
    """Try several common date formats; return ISO-8601 string or None."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ("", "nan", "None", "NaT"):
        return None
    # Already a datetime / Timestamp
    if hasattr(val, "isoformat"):
        try:
            return val.isoformat()
        except Exception:
            pass
    for fmt in ("%Y/%m/%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z",
                "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:len(fmt)], fmt).isoformat()
        except ValueError:
            continue
    return None  # unrecognised format — skip


def _normalise_iucn(val) -> str | None:
    """Map raw IUCN strings to canonical values; return None if unrecognised."""
    if val is None:
        return "Not Reported"
    s = str(val).strip()
    if s in VALID_IUCN:
        return s
    s_upper = s.upper()
    for cat in VALID_IUCN:
        if cat.upper() == s_upper:
            return cat
    # Map common alternatives
    alternatives = {
        "IA": "Ia", "IB": "Ib",
        "NOT APPLICABLE": "Not Applicable",
        "N/A": "Not Applicable",
        "NR": "Not Reported",
        "NONE": "Not Reported",
        "": "Not Reported",
    }
    return alternatives.get(s_upper, "Not Reported")


# ---------------------------------------------------------------------------
# Cleaning report
# ---------------------------------------------------------------------------

def print_report(gdf: gpd.GeoDataFrame, label: str) -> None:
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

def clean_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    print("\n[1/6] Normalising column names...")
    gdf = normalise_columns(gdf)
    print(f"      Mapped columns: {[c for c in gdf.columns if c != 'geometry']}")

    print("[2/6] Reprojecting to EPSG:4326 (WGS 84)...")
    if gdf.crs is None:
        print("      WARNING: No CRS in shapefile. Assuming GDA94 (EPSG:4283).")
        gdf = gdf.set_crs("EPSG:4283", allow_override=True)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
        print(f"      Reprojected from {gdf.crs} -> EPSG:4326")
    else:
        print("      Already EPSG:4326. No reproject needed.")

    print("[3/6] Fixing invalid / null geometries...")
    n_invalid_before = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    gdf["_geom"] = gdf.geometry.apply(
        lambda g: make_valid(g) if g is not None and not g.is_empty and not g.is_valid else g
    )
    gdf = gdf.set_geometry("_geom").drop(columns=[gdf.geometry.name])
    gdf = gdf.rename_geometry("geometry")
    n_invalid_after = gdf.geometry.apply(
        lambda g: g is not None and not g.is_empty and not g.is_valid
    ).sum()
    print(f"      Fixed {n_invalid_before - n_invalid_after} invalid geoms ({n_invalid_after} remaining).")

    n_before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    print(f"      Dropped {n_before - len(gdf)} null/empty geometry rows. Rows remaining: {len(gdf)}")

    print("[4/6] Casting to MultiPolygon...")
    gdf["geometry"] = gdf["geometry"].apply(ensure_multipolygon)
    gdf = gdf[gdf["geometry"].notna()].copy()
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    print(f"      Rows after cast: {len(gdf)}")

    print("[5/6] Cleaning attribute fields...")

    # objectid: deduplicate (keep last occurrence)
    if "objectid" in gdf.columns:
        n_before = len(gdf)
        gdf["objectid"] = gdf["objectid"].apply(_int)
        gdf = gdf.drop_duplicates(subset="objectid", keep="last")
        print(f"      Deduped objectid: dropped {n_before - len(gdf)} duplicates.")
    else:
        # No OBJECTID in file — synthesise from row index
        gdf["objectid"] = range(1, len(gdf) + 1)
        print("      WARNING: No OBJECTID column found. Synthesised from row index.")

    # Drop rows missing the three required identifiers
    n_before = len(gdf)
    req_cols = [c for c in ["objectid", "pa_id", "pa_name"] if c in gdf.columns]
    if req_cols:
        gdf = gdf.dropna(subset=req_cols[:1])  # objectid is the primary key
    print(f"      Dropped {n_before - len(gdf)} rows with null objectid.")

    # IUCN normalise
    if "iucn_cat" in gdf.columns:
        gdf["iucn_cat"] = gdf["iucn_cat"].apply(_normalise_iucn)

    # nrs_pa Y/N -> bool
    if "nrs_pa" in gdf.columns:
        gdf["nrs_pa"] = gdf["nrs_pa"].apply(_bool_yn)

    # Lat/lon: nullify out-of-range values
    for lat_col in ["latitude"]:
        if lat_col in gdf.columns:
            before_null = gdf[lat_col].isna().sum()
            gdf[lat_col] = gdf[lat_col].apply(
                lambda v: _float(v) if AUS_LAT_RANGE[0] <= _float(v or 999) <= AUS_LAT_RANGE[1] else None
            )
            after_null = gdf[lat_col].isna().sum()
            if after_null > before_null:
                print(f"      Nullified {after_null - before_null} out-of-range latitude values.")

    for lon_col in ["longitude"]:
        if lon_col in gdf.columns:
            before_null = gdf[lon_col].isna().sum()
            gdf[lon_col] = gdf[lon_col].apply(
                lambda v: _float(v) if AUS_LON_RANGE[0] <= _float(v or 0) <= AUS_LON_RANGE[1] else None
            )
            after_null = gdf[lon_col].isna().sum()
            if after_null > before_null:
                print(f"      Nullified {after_null - before_null} out-of-range longitude values.")

    print("[6/6] Deriving centroid lat/lon from geometry where attribute values are null...")
    # If the SHP has no LAT/LON columns, or they're all null, derive from polygon centroid
    missing_lat = "latitude"  not in gdf.columns or gdf["latitude"].isna().all()
    missing_lon = "longitude" not in gdf.columns or gdf["longitude"].isna().all()
    if missing_lat or missing_lon:
        centroids = gdf.geometry.centroid
        if missing_lat:
            gdf["latitude"]  = centroids.y
            print("      Derived latitude from polygon centroid.")
        if missing_lon:
            gdf["longitude"] = centroids.x
            print("      Derived longitude from polygon centroid.")
    else:
        # Fill only the nulls
        null_lat = gdf["latitude"].isna()
        null_lon = gdf["longitude"].isna()
        if null_lat.any():
            gdf.loc[null_lat, "latitude"]  = gdf[null_lat].geometry.centroid.y
        if null_lon.any():
            gdf.loc[null_lon, "longitude"] = gdf[null_lon].geometry.centroid.x

    return gdf


# ---------------------------------------------------------------------------
# Pre-insert VARCHAR column-length guard  (mirrors migrate_ibra.py)
# ---------------------------------------------------------------------------

def check_column_lengths(rows: list[dict], engine) -> None:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'capad'
              AND character_maximum_length IS NOT NULL
        """))
        limits = {r[0]: r[1] for r in result.fetchall()}

    if not limits:
        print("[Guard] No VARCHAR length limits on capad table. Skipping.")
        return

    print(f"[Guard] VARCHAR limits: {limits}")

    offenders: dict[str, list] = {}
    for row in rows:
        for col, max_len in limits.items():
            val = row.get(col)
            if val is not None and len(str(val)) > max_len:
                offenders.setdefault(col, []).append((val, len(str(val))))

    if not offenders:
        print("[Guard] All values fit within column limits. Proceeding.")
        return

    print("\n[Guard] *** TRUNCATION RISK DETECTED ***")
    for col, vals in offenders.items():
        print(f"  Column '{col}' (VARCHAR({limits[col]})):")
        for val, length in vals[:5]:
            print(f"    {repr(val)}  ({length} chars)")
        if len(vals) > 5:
            print(f"    ... and {len(vals) - 5} more")
    print(
        "\nFix: ALTER the column lengths in the DB, then re-run this script.\n"
        "Example:\n"
        "  ALTER TABLE capad ALTER COLUMN pa_name TYPE TEXT;\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Build row dicts
# ---------------------------------------------------------------------------

def build_rows(gdf: gpd.GeoDataFrame, capad_version: str = "2024") -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    rows = []

    iter_rows = tqdm(gdf.iterrows(), total=len(gdf), desc="Building rows") if HAS_TQDM else gdf.iterrows()

    for _, row in iter_rows:
        geom = row.geometry

        # WKT for frontend display (geom_wkt column)
        geom_wkt = geom.wkt if geom and not geom.is_empty else None

        # EWKB hex for PostGIS geom column
        geom_ewkb = geom_to_ewkb_hex(geom)

        rows.append({
            "objectid":          _int(row.get("objectid")),
            "pa_id":             _str(row.get("pa_id")),
            "pa_name":           _str(row.get("pa_name")),
            "pa_type":           _str(row.get("pa_type")),
            "pa_type_abbr":      _str(row.get("pa_type_abbr")),
            "iucn_cat":          _normalise_iucn(row.get("iucn_cat")),
            "nrs_pa":            _bool_yn(row.get("nrs_pa")),
            "gaz_area_ha":       _float(row.get("gaz_area_ha")),
            "gis_area_ha":       _float(row.get("gis_area_ha")),
            "state":             _str(row.get("state")),
            "environ":           _str(row.get("environ")),
            "epbc_trigger":      _str(row.get("epbc_trigger")),
            "latitude":          _float(row.get("latitude")),
            "longitude":         _float(row.get("longitude")),
            "gaz_date":          _parse_date(row.get("gaz_date")),
            "latest_gaz":        _parse_date(row.get("latest_gaz")),
            "pa_pid":            _str(row.get("pa_pid")),
            "governance":        _str(row.get("governance")),
            "authority":         _str(row.get("authority")),
            "source_dataset":    _str(row.get("source_dataset")),
            "capad_version":     capad_version,
            "capad_citation":    "DCCEEW (2024) Collaborative Australian Protected Areas Database (CAPAD) 2024",
            "capad_licence":     "CC BY 4.0",
            "is_active":         True,
            "cleaned_at":        now,
            "geom_wkt":          geom_wkt,
            "geom_ewkb":         geom_ewkb,
        })
    return rows


# ---------------------------------------------------------------------------
# Migrate (UPSERT — idempotent)
# ---------------------------------------------------------------------------

UPSERT_SQL = text("""
    INSERT INTO capad (
        objectid, pa_id, pa_name, pa_type, pa_type_abbr,
        iucn_cat, nrs_pa, gaz_area_ha, gis_area_ha,
        state, environ, epbc_trigger,
        latitude, longitude, gaz_date, latest_gaz,
        pa_pid, governance, authority,
        source_dataset, capad_version, capad_citation, capad_licence,
        is_active, cleaned_at, geom_wkt,
        geom
    ) VALUES (
        :objectid, :pa_id, :pa_name, :pa_type, :pa_type_abbr,
        :iucn_cat, :nrs_pa, :gaz_area_ha, :gis_area_ha,
        :state, :environ, :epbc_trigger,
        :latitude, :longitude,
        :gaz_date::timestamptz, :latest_gaz::timestamptz,
        :pa_pid, :governance, :authority,
        :source_dataset, :capad_version, :capad_citation, :capad_licence,
        :is_active, :cleaned_at::timestamptz, :geom_wkt,
        ST_GeomFromEWKB(decode(:geom_ewkb, 'hex'))
    )
    ON CONFLICT (objectid) DO UPDATE SET
        pa_id             = EXCLUDED.pa_id,
        pa_name           = EXCLUDED.pa_name,
        pa_type           = EXCLUDED.pa_type,
        pa_type_abbr      = EXCLUDED.pa_type_abbr,
        iucn_cat          = EXCLUDED.iucn_cat,
        nrs_pa            = EXCLUDED.nrs_pa,
        gaz_area_ha       = EXCLUDED.gaz_area_ha,
        gis_area_ha       = EXCLUDED.gis_area_ha,
        state             = EXCLUDED.state,
        environ           = EXCLUDED.environ,
        epbc_trigger      = EXCLUDED.epbc_trigger,
        latitude          = EXCLUDED.latitude,
        longitude         = EXCLUDED.longitude,
        gaz_date          = EXCLUDED.gaz_date,
        latest_gaz        = EXCLUDED.latest_gaz,
        pa_pid            = EXCLUDED.pa_pid,
        governance        = EXCLUDED.governance,
        authority         = EXCLUDED.authority,
        source_dataset    = EXCLUDED.source_dataset,
        capad_version     = EXCLUDED.capad_version,
        capad_citation    = EXCLUDED.capad_citation,
        capad_licence     = EXCLUDED.capad_licence,
        is_active         = EXCLUDED.is_active,
        cleaned_at        = EXCLUDED.cleaned_at,
        geom_wkt          = EXCLUDED.geom_wkt,
        geom              = EXCLUDED.geom
""")


def migrate(rows: list[dict], engine, drop: bool = False) -> None:
    if drop:
        with engine.begin() as conn:
            print("[Migrate] DROP + TRUNCATE capad table...")
            conn.execute(text("TRUNCATE TABLE capad RESTART IDENTITY CASCADE"))

    # Ensure objectid has a unique constraint (needed for ON CONFLICT)
    with engine.begin() as conn:
        conn.execute(text("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'capad_objectid_unique'
                  AND conrelid = 'capad'::regclass
              ) THEN
                ALTER TABLE capad ADD CONSTRAINT capad_objectid_unique UNIQUE (objectid);
              END IF;
            END$$;
        """))
        print("[Migrate] UNIQUE constraint on capad.objectid verified.")

    total    = len(rows)
    inserted = 0
    errors   = 0

    batch_iter = range(0, total, BATCH_SIZE)
    if HAS_TQDM:
        batch_iter = tqdm(batch_iter, desc="Upserting batches", unit="batch")

    for i in batch_iter:
        batch = rows[i: i + BATCH_SIZE]
        # Skip rows with null geom_ewkb (can't insert null into PostGIS geom)
        valid_batch  = [r for r in batch if r.get("geom_ewkb")]
        skipped      = len(batch) - len(valid_batch)
        if skipped:
            print(f"  [Warning] Skipped {skipped} rows with null geometry in batch {i//BATCH_SIZE}.")
            errors += skipped

        if not valid_batch:
            continue

        try:
            with engine.begin() as conn:
                conn.execute(UPSERT_SQL, valid_batch)
            inserted += len(valid_batch)
        except Exception as exc:
            print(f"\n  [Error] Batch {i//BATCH_SIZE} failed: {exc}")
            errors += len(valid_batch)

    print(f"\n[Migrate] Upserted {inserted}/{total} rows | Skipped/errored: {errors}")

    # Post-insert validation
    with engine.connect() as conn:
        total_db  = conn.execute(text("SELECT COUNT(*) FROM capad")).scalar()
        active    = conn.execute(text("SELECT COUNT(*) FROM capad WHERE is_active = TRUE")).scalar()
        with_geom = conn.execute(text("SELECT COUNT(*) FROM capad WHERE geom IS NOT NULL")).scalar()
        valid_g   = conn.execute(text("SELECT COUNT(*) FROM capad WHERE geom IS NOT NULL AND ST_IsValid(geom)")).scalar()
        by_state  = conn.execute(text(
            "SELECT state, COUNT(*) FROM capad WHERE is_active = TRUE GROUP BY state ORDER BY COUNT(*) DESC LIMIT 10"
        ))
        state_rows = by_state.fetchall()

    print(f"\n[Validate] capad table:")
    print(f"  Total rows   : {total_db}")
    print(f"  Active       : {active}")
    print(f"  With geom    : {with_geom}")
    print(f"  Valid geom   : {valid_g}")
    print(f"  By state (top 10):")
    for s, cnt in state_rows:
        print(f"    {s or 'NULL':<30} {cnt}")

    bad_geom = with_geom - valid_g
    if bad_geom:
        print(f"\n  [Warning] {bad_geom} invalid geoms remaining. Fix with:")
        print("    UPDATE capad SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Clean a CAPAD 2024 .shp file and migrate it into the local `capad` table."
    )
    parser.add_argument("--shp",      required=True, help="Path to the CAPAD shapefile (.shp)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Clean and report only — no DB writes.")
    parser.add_argument("--drop",     action="store_true",
                        help="TRUNCATE capad table before inserting (full reload).")
    parser.add_argument("--version",  default="2024",
                        help="capad_version tag to stamp on every row (default: 2024).")
    parser.add_argument("--db-url",   default=None,
                        help="PostgreSQL DSN (overrides DATABASE_URL env var).")
    parser.add_argument("--batch",    type=int, default=BATCH_SIZE,
                        help=f"Rows per upsert batch (default: {BATCH_SIZE}).")
    args = parser.parse_args()

    if not os.path.exists(args.shp):
        sys.exit(f"ERROR: Shapefile not found: {args.shp}")

    # ── Load ──────────────────────────────────────────────────────────────
    print(f"\nLoading: {args.shp}")
    gdf = gpd.read_file(args.shp)
    print_report(gdf, "RAW shapefile")

    # ── Clean ─────────────────────────────────────────────────────────────
    gdf = clean_gdf(gdf)
    print_report(gdf, "CLEANED shapefile")

    if args.dry_run:
        print("\n[Dry run] Cleaning complete. No database changes made.")
        # Save cleaned GeoJSON for inspection
        out = args.shp.replace(".shp", "_cleaned.geojson")
        gdf.to_file(out, driver="GeoJSON")
        print(f"[Dry run] Cleaned data written to: {out}")
        return

    # ── Connect ───────────────────────────────────────────────────────────
    raw_url  = args.db_url or os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eco_db"
    )
    sync_url = raw_url.replace("postgresql+asyncpg", "postgresql")
    print(f"\nConnecting to: ...@{sync_url.split('@')[-1]}")
    engine = create_engine(sync_url, echo=False)

    with engine.connect() as conn:
        try:
            version = conn.execute(text("SELECT PostGIS_version()")).scalar()
            print(f"PostGIS {version}. OK")
        except Exception:
            sys.exit(
                "ERROR: PostGIS extension not found in this database.\n"
                "Enable with: CREATE EXTENSION IF NOT EXISTS postgis;"
            )

    # ── Build rows ────────────────────────────────────────────────────────
    print("\nBuilding row dicts...")
    global BATCH_SIZE
    BATCH_SIZE = args.batch
    rows = build_rows(gdf, capad_version=args.version)
    print(f"Built {len(rows)} rows.")

    # ── Guard ─────────────────────────────────────────────────────────────
    check_column_lengths(rows, engine)

    # ── Migrate ───────────────────────────────────────────────────────────
    migrate(rows, engine, drop=args.drop)
    print("\nDone. Press F5 in DBeaver to refresh the capad table.")


if __name__ == "__main__":
    main()
