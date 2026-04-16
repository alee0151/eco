#!/usr/bin/env python3
"""
CAPAD 2024 – Terrestrial Protected Areas
Clean & Migrate to Local PostgreSQL Database
=============================================
Prerequisites
-------------
  pip install pandas psycopg2-binary sqlalchemy python-dotenv tqdm

Usage
-----
  python migrate_capad.py                        # uses .env for DB config
  python migrate_capad.py --host localhost \
    --port 5432 --dbname eco --user postgres --password secret

Environment variables (.env)
-----------------------------
  DB_HOST     = localhost
  DB_PORT     = 5432
  DB_NAME     = eco
  DB_USER     = postgres
  DB_PASSWORD = yourpassword
"""

import os, sys, argparse, logging
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import (
    create_engine, text,
    Column, Integer, BigInteger, String, Float, Boolean,
    DateTime, Text, SmallInteger, inspect as sa_inspect
)
from sqlalchemy.orm import DeclarativeBase, Session
from tqdm import tqdm

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # python-dotenv optional

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("capad_migrate")

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
DEFAULT_CSV = Path(
    "/Users/alanleemon/Documents/private_ie_project/eco/Collaborative_Australian_Protected_Areas_Database_(CAPAD)_2024_-_Terrestrial__.csv"
)
TABLE_NAME   = "capad_protected_areas"
SCHEMA_NAME  = "public"           # change to e.g. "biodiversity" if needed
BATCH_SIZE   = 500                # rows per INSERT batch
CAPAD_VER    = "2024"
CAPAD_CITE   = "CAPAD 2024, Commonwealth of Australia (DCCEEW) 2025"
CAPAD_LICENCE= "CC BY 4.0"


# ─────────────────────────────────────────────
# DDL  (pure SQL – runs before ORM insert)
# ─────────────────────────────────────────────
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.{TABLE_NAME} (
    -- Surrogate primary key
    id                  SERIAL          PRIMARY KEY,

    -- CAPAD identifiers
    objectid            INTEGER         NOT NULL,
    pa_id               VARCHAR(64)     NOT NULL,
    pa_pid              VARCHAR(64),

    -- Descriptive attributes
    pa_name             VARCHAR(512)    NOT NULL,
    pa_type             VARCHAR(128)    NOT NULL,
    pa_type_abbr        VARCHAR(16),
    iucn_cat            VARCHAR(16),
    nrs_pa              BOOLEAN,

    -- Area metrics (hectares)
    gaz_area_ha         DOUBLE PRECISION,
    gis_area_ha         DOUBLE PRECISION,
    shape_area          DOUBLE PRECISION,   -- decimal degrees² from source
    shape_length        DOUBLE PRECISION,

    -- Jurisdiction & management
    state               VARCHAR(16),
    authority           VARCHAR(64),
    datasource          VARCHAR(64),
    governance          VARCHAR(8),          -- G=Government, P=Private, I=Indigenous
    epbc_trigger        VARCHAR(64),
    environ             VARCHAR(4),          -- T=Terrestrial, M=Marine
    pa_system           VARCHAR(16),
    overlap             SMALLINT,            -- 0/1 overlap flag
    mgt_plan            VARCHAR(8),
    res_number          VARCHAR(64),
    comments            TEXT,

    -- Spatial (centroid – no PostGIS required for plain PG)
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,

    -- Dates
    gaz_date            TIMESTAMPTZ,
    latest_gaz          TIMESTAMPTZ,

    -- Provenance
    capad_version       VARCHAR(8)      DEFAULT '2024',
    capad_citation      VARCHAR(256),
    capad_licence       VARCHAR(64),

    -- Pipeline metadata
    migrated_at         TIMESTAMPTZ     DEFAULT NOW(),
    is_active           BOOLEAN         DEFAULT TRUE,

    -- Unique constraint so re-runs are idempotent
    CONSTRAINT uq_capad_objectid UNIQUE (objectid)
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_capad_pa_id     ON {SCHEMA_NAME}.{TABLE_NAME} (pa_id);
CREATE INDEX IF NOT EXISTS idx_capad_state     ON {SCHEMA_NAME}.{TABLE_NAME} (state);
CREATE INDEX IF NOT EXISTS idx_capad_pa_type   ON {SCHEMA_NAME}.{TABLE_NAME} (pa_type_abbr);
CREATE INDEX IF NOT EXISTS idx_capad_iucn      ON {SCHEMA_NAME}.{TABLE_NAME} (iucn_cat);
CREATE INDEX IF NOT EXISTS idx_capad_epbc      ON {SCHEMA_NAME}.{TABLE_NAME} (epbc_trigger);
CREATE INDEX IF NOT EXISTS idx_capad_latlon    ON {SCHEMA_NAME}.{TABLE_NAME} (latitude, longitude);
"""

# ─────────────────────────────────────────────
# Cleaning
# ─────────────────────────────────────────────
GOVERNANCE_MAP = {"G": "Government", "P": "Private", "I": "Indigenous", "C": "Community"}

def _parse_ts(val):
    """Parse CAPAD date strings robustly → UTC-aware datetime or None."""
    if pd.isna(val) or str(val).strip() in ("", "nan", "None"):
        return None
    s = str(val).strip()
    for fmt in ("%Y/%m/%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z",
                "%Y/%m/%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:len(fmt)], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def clean_capad(csv_path: Path) -> pd.DataFrame:
    log.info(f"Reading  → {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    raw_rows = len(df)
    log.info(f"Raw rows : {raw_rows:,}  |  columns: {df.shape[1]}")

    # ── 1. Normalise column names
    df.columns = [c.strip().upper() for c in df.columns]

    # ── 2. Drop full duplicates
    df = df.drop_duplicates()

    # ── 3. Drop rows missing required identifiers
    required = ["OBJECTID", "PA_ID", "NAME"]
    before = len(df)
    df = df.dropna(subset=required)
    dropped = before - len(df)
    if dropped:
        log.warning(f"Dropped {dropped} rows missing required fields {required}")

    # ── 4. Numeric fields
    for col in ["OBJECTID", "GAZ_AREA", "GIS_AREA", "LATITUDE", "LONGITUDE",
                "SHAPE__AREA", "SHAPE__LENGTH", "OVERLAP"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 5. Date fields
    for col in ["GAZ_DATE", "LATEST_GAZ"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_ts)

    # ── 6. Boolean: NRS_PA
    if "NRS_PA" in df.columns:
        df["NRS_PA"] = df["NRS_PA"].map(
            {"Y": True, "N": False, "y": True, "n": False,
             True: True, False: False, 1: True, 0: False}
        ).fillna(False).astype(bool)

    # ── 7. String cleaning
    str_cols = ["PA_ID","PA_PID","NAME","TYPE","TYPE_ABBR","IUCN",
                "STATE","AUTHORITY","DATASOURCE","GOVERNANCE",
                "EPBC","ENVIRON","MGT_PLAN","RES_NUMBER","PA_SYSTEM","COMMENTS"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})

    # ── 8. Coordinate sanity check
    invalid_coords = (
        df["LATITUDE"].notna()  & ((df["LATITUDE"]  < -90)  | (df["LATITUDE"]  > 90))  |
        df["LONGITUDE"].notna() & ((df["LONGITUDE"] < -180) | (df["LONGITUDE"] > 180))
    )
    if invalid_coords.any():
        log.warning(f"Nullifying {invalid_coords.sum()} rows with out-of-range coordinates")
        df.loc[invalid_coords, ["LATITUDE", "LONGITUDE"]] = None

    # ── 9. IUCN normalisation
    valid_iucn = {"Ia","Ib","II","III","IV","V","VI","Not Reported","Not Applicable"}
    if "IUCN" in df.columns:
        df["IUCN"] = df["IUCN"].where(df["IUCN"].isin(valid_iucn), other=None)

    log.info(f"Clean rows: {len(df):,}  (removed {raw_rows - len(df):,} total)")
    return df


# ─────────────────────────────────────────────
# Mapping to DB columns
# ─────────────────────────────────────────────
def df_to_records(df: pd.DataFrame) -> list[dict]:
    now = datetime.now(tz=timezone.utc).isoformat()
    records = []
    for _, row in df.iterrows():
        records.append({
            "objectid":       int(row.get("OBJECTID"))   if pd.notna(row.get("OBJECTID"))   else None,
            "pa_id":          row.get("PA_ID"),
            "pa_pid":         row.get("PA_PID"),
            "pa_name":        row.get("NAME"),
            "pa_type":        row.get("TYPE"),
            "pa_type_abbr":   row.get("TYPE_ABBR"),
            "iucn_cat":       row.get("IUCN"),
            "nrs_pa":         bool(row.get("NRS_PA"))    if pd.notna(row.get("NRS_PA"))   else False,
            "gaz_area_ha":    row.get("GAZ_AREA"),
            "gis_area_ha":    row.get("GIS_AREA"),
            "shape_area":     row.get("SHAPE__AREA"),
            "shape_length":   row.get("SHAPE__LENGTH"),
            "state":          row.get("STATE"),
            "authority":      row.get("AUTHORITY"),
            "datasource":     row.get("DATASOURCE"),
            "governance":     row.get("GOVERNANCE"),
            "epbc_trigger":   row.get("EPBC"),
            "environ":        row.get("ENVIRON"),
            "pa_system":      row.get("PA_SYSTEM"),
            "overlap":        int(row.get("OVERLAP"))    if pd.notna(row.get("OVERLAP"))  else None,
            "mgt_plan":       row.get("MGT_PLAN"),
            "res_number":     row.get("RES_NUMBER"),
            "comments":       row.get("COMMENTS"),
            "latitude":       row.get("LATITUDE"),
            "longitude":      row.get("LONGITUDE"),
            "gaz_date":       row.get("GAZ_DATE"),
            "latest_gaz":     row.get("LATEST_GAZ"),
            "capad_version":  CAPAD_VER,
            "capad_citation": CAPAD_CITE,
            "capad_licence":  CAPAD_LICENCE,
            "migrated_at":    now,
            "is_active":      True,
        })
    return records


# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────
def build_engine(args):
    host     = args.host     or os.getenv("DB_HOST",     "localhost")
    port     = args.port     or os.getenv("DB_PORT",     "5432")
    dbname   = args.dbname   or os.getenv("DB_NAME",     "eco")
    user     = args.user     or os.getenv("DB_USER",     "alanleemon")
    password = args.password or os.getenv("DB_PASSWORD", "root")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    log.info(f"Connecting → postgresql://{user}@{host}:{port}/{dbname}")
    return create_engine(url, pool_pre_ping=True)


def ensure_schema(engine):
    with engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
    log.info(f"Table {SCHEMA_NAME}.{TABLE_NAME} ready")


INSERT_SQL = f"""
INSERT INTO {SCHEMA_NAME}.{TABLE_NAME} (
    objectid, pa_id, pa_pid, pa_name, pa_type, pa_type_abbr,
    iucn_cat, nrs_pa, gaz_area_ha, gis_area_ha, shape_area, shape_length,
    state, authority, datasource, governance, epbc_trigger, environ,
    pa_system, overlap, mgt_plan, res_number, comments,
    latitude, longitude, gaz_date, latest_gaz,
    capad_version, capad_citation, capad_licence, migrated_at, is_active
) VALUES (
    :objectid, :pa_id, :pa_pid, :pa_name, :pa_type, :pa_type_abbr,
    :iucn_cat, :nrs_pa, :gaz_area_ha, :gis_area_ha, :shape_area, :shape_length,
    :state, :authority, :datasource, :governance, :epbc_trigger, :environ,
    :pa_system, :overlap, :mgt_plan, :res_number, :comments,
    :latitude, :longitude, :gaz_date, :latest_gaz,
    :capad_version, :capad_citation, :capad_licence, :migrated_at, :is_active
)
ON CONFLICT (objectid) DO UPDATE SET
    pa_name        = EXCLUDED.pa_name,
    gaz_area_ha    = EXCLUDED.gaz_area_ha,
    gis_area_ha    = EXCLUDED.gis_area_ha,
    iucn_cat       = EXCLUDED.iucn_cat,
    epbc_trigger   = EXCLUDED.epbc_trigger,
    gaz_date       = EXCLUDED.gaz_date,
    latest_gaz     = EXCLUDED.latest_gaz,
    capad_version  = EXCLUDED.capad_version,
    migrated_at    = EXCLUDED.migrated_at,
    is_active      = EXCLUDED.is_active;
"""


def insert_batched(engine, records: list[dict]):
    total  = len(records)
    done   = 0
    errors = 0
    with engine.begin() as conn:
        for i in tqdm(range(0, total, BATCH_SIZE), desc="Inserting", unit="batch"):
            batch = records[i : i + BATCH_SIZE]
            try:
                conn.execute(text(INSERT_SQL), batch)
                done += len(batch)
            except Exception as exc:
                log.error(f"Batch {i//BATCH_SIZE} failed – {exc}")
                errors += len(batch)
    log.info(f"Insert complete  |  success: {done:,}  |  errors: {errors:,}")
    return done, errors


# ─────────────────────────────────────────────
# Validation queries (run post-insert)
# ─────────────────────────────────────────────
VALIDATION_QUERIES = {
    "Total rows":        f"SELECT COUNT(*) FROM {SCHEMA_NAME}.{TABLE_NAME}",
    "Rows by state":     f"SELECT state, COUNT(*) AS n FROM {SCHEMA_NAME}.{TABLE_NAME} GROUP BY state ORDER BY n DESC",
    "IUCN distribution": f"SELECT iucn_cat, COUNT(*) AS n FROM {SCHEMA_NAME}.{TABLE_NAME} GROUP BY iucn_cat ORDER BY n DESC",
    "Governance split":  f"SELECT governance, COUNT(*) AS n FROM {SCHEMA_NAME}.{TABLE_NAME} GROUP BY governance ORDER BY n DESC",
    "Null coordinates":  f"SELECT COUNT(*) AS missing_coords FROM {SCHEMA_NAME}.{TABLE_NAME} WHERE latitude IS NULL OR longitude IS NULL",
}

def run_validation(engine):
    log.info("─── Validation report ─────────────────────────────")
    with engine.connect() as conn:
        for label, sql in VALIDATION_QUERIES.items():
            result = conn.execute(text(sql)).fetchall()
            log.info(f"  {label}:")
            for row in result:
                log.info(f"    {dict(row._mapping)}")
    log.info("───────────────────────────────────────────────────")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="Migrate CAPAD 2024 Terrestrial CSV to PostgreSQL")
    p.add_argument("--csv",      default=str(DEFAULT_CSV), help="Path to CAPAD CSV file")
    p.add_argument("--host",     default=None)
    p.add_argument("--port",     default=None, type=int)
    p.add_argument("--dbname",   default=None)
    p.add_argument("--user",     default=None)
    p.add_argument("--password", default=None)
    p.add_argument("--drop",     action="store_true",
                   help="DROP the target table before migrating (full reload)")
    p.add_argument("--dry-run",  action="store_true",
                   help="Clean & validate CSV only – no DB writes")
    return p.parse_args()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    args = parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        log.error(f"CSV not found: {csv_path}")
        sys.exit(1)

    # ── Step 1: Clean
    df = clean_capad(csv_path)

    # ── Step 2: Map to records
    records = df_to_records(df)
    log.info(f"Records prepared: {len(records):,}")

    if args.dry_run:
        log.info("Dry run – skipping all DB operations")
        # Save cleaned CSV for inspection
        out = csv_path.with_name("capad_cleaned_migration_ready.csv")
        df.to_csv(out, index=False)
        log.info(f"Cleaned CSV saved → {out}")
        return

    # ── Step 3: Connect
    engine = build_engine(args)

    # ── Step 4: Optional DROP
    if args.drop:
        log.warning(f"Dropping table {SCHEMA_NAME}.{TABLE_NAME} …")
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {SCHEMA_NAME}.{TABLE_NAME} CASCADE"))

    # ── Step 5: Create schema
    ensure_schema(engine)

    # ── Step 6: Insert
    done, errors = insert_batched(engine, records)

    # ── Step 7: Validate
    run_validation(engine)

    if errors:
        log.warning(f"Migration finished with {errors} errors")
        sys.exit(1)
    else:
        log.info("Migration completed successfully ✓")


if __name__ == "__main__":
    main()
