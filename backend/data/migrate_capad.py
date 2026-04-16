#!/usr/bin/env python3
"""
Migrate cleaned CAPAD 2024 Terrestrial data into a local PostgreSQL database.

Usage:
  python migrate_capad.py [options]

Options:
  --csv PATH        Path to CAPAD CSV file (default: CAPAD2024_terrestrial.csv)
  --host HOST       DB host (default: localhost)
  --port PORT       DB port (default: 5432)
  --dbname DBNAME   Database name (default: eco)
  --user USER       DB user (default: postgres)
  --password PASS   DB password
  --drop            Drop and recreate table before loading
  --dry-run         Clean & validate only; no DB writes; saves cleaned CSV
  --batch-size N    Upsert batch size (default: 500)

Environment variables (overridden by CLI flags):
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

Requirements:
  pip install pandas psycopg2-binary sqlalchemy python-dotenv tqdm
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

DEFAULT_CSV = "Collaborative_Australian_Protected_Areas_Database_-CAPAD-_2024_-_Terrestrial.csv"
TABLE = "public.capad_protected_areas"

IUCN_VALID = {"Ia", "Ib", "II", "III", "IV", "V", "VI", "Not Reported"}

COLUMN_MAP = {
    "OBJECTID": "objectid",
    "PA_ID": "pa_id",
    "NAME": "name",
    "TYPE": "pa_type",
    "TYPE_ABBR": "pa_type_abbr",
    "IUCN": "iucn_cat",
    "GAZ_AREA": "gaz_area_ha",
    "GIS_AREA": "gis_area_ha",
    "GAZ_DATE": "gaz_date",
    "LATEST_GAZ": "latest_gaz",
    "STATE": "state",
    "AUTHORITY": "authority",
    "DATASOURCE": "datasource",
    "COMMENTS": "comments",
    "GOVERNANCE": "governance",
    "MANAGEMENT": "management",
    "OVERLAP": "overlap",
    "EPBC": "epbc_trigger",
    "NRS_PA": "nrs_pa",
    "ENVIRON": "environ",
    "LON": "longitude",
    "LAT": "latitude",
    "MAPSCALE": "mapscale",
    "DATASOURCE_ID": "datasource_id",
    "CAPAD_STATUS": "capad_status",
    "PROTECTED_AREA_ID": "protected_area_id",
    "OVERLAP_PCT": "overlap_pct",
    "SHAPE_Length": "shape_length",
    "SHAPE_Area": "shape_area",
}

CREATE_TABLE_SQL = textwrap.dedent(f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        objectid            INTEGER PRIMARY KEY,
        pa_id               TEXT,
        name                TEXT NOT NULL,
        pa_type             TEXT,
        pa_type_abbr        TEXT,
        iucn_cat            TEXT,
        gaz_area_ha         DOUBLE PRECISION,
        gis_area_ha         DOUBLE PRECISION,
        gaz_date            TIMESTAMPTZ,
        latest_gaz          TIMESTAMPTZ,
        state               TEXT,
        authority           TEXT,
        datasource          TEXT,
        comments            TEXT,
        governance          TEXT,
        management          TEXT,
        overlap             TEXT,
        epbc_trigger        TEXT,
        nrs_pa              BOOLEAN,
        environ             TEXT,
        longitude           DOUBLE PRECISION,
        latitude            DOUBLE PRECISION,
        mapscale            TEXT,
        datasource_id       TEXT,
        capad_status        TEXT,
        protected_area_id   TEXT,
        overlap_pct         DOUBLE PRECISION,
        shape_length        DOUBLE PRECISION,
        shape_area          DOUBLE PRECISION,
        inserted_at         TIMESTAMPTZ DEFAULT now(),
        updated_at          TIMESTAMPTZ DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_capad_state        ON {TABLE} (state);
    CREATE INDEX IF NOT EXISTS idx_capad_pa_type_abbr ON {TABLE} (pa_type_abbr);
    CREATE INDEX IF NOT EXISTS idx_capad_iucn_cat     ON {TABLE} (iucn_cat);
    CREATE INDEX IF NOT EXISTS idx_capad_epbc         ON {TABLE} (epbc_trigger);
    CREATE INDEX IF NOT EXISTS idx_capad_latlon       ON {TABLE} (latitude, longitude);
""").strip()


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy of the raw CAPAD DataFrame."""

    # Rename to snake_case; keep only mapped columns
    df = df.rename(columns=COLUMN_MAP)
    keep = [c for c in COLUMN_MAP.values() if c in df.columns]
    df = df[keep].copy()

    # Drop exact duplicates
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Dropped {before - len(df)} exact duplicate rows")

    # Drop rows missing primary key fields
    required = ["objectid", "pa_id", "name"]
    before = len(df)
    df = df.dropna(subset=[c for c in required if c in df.columns])
    print(f"  Dropped {before - len(df)} rows missing objectid/pa_id/name")

    # Parse date columns
    for col in ["gaz_date", "latest_gaz"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    # Numeric columns
    for col in ["gaz_area_ha", "gis_area_ha", "overlap_pct", "shape_length", "shape_area"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Coordinate validation
    for col, lo, hi in [("latitude", -90, 90), ("longitude", -180, 180)]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            invalid = df[col].notna() & ~df[col].between(lo, hi)
            if invalid.any():
                print(f"  Nullified {invalid.sum()} out-of-range {col} values")
                df.loc[invalid, col] = None

    # NRS_PA: Y/N -> boolean
    if "nrs_pa" in df.columns:
        df["nrs_pa"] = df["nrs_pa"].map({"Y": True, "N": False, "y": True, "n": False})

    # Normalise IUCN categories
    if "iucn_cat" in df.columns:
        df["iucn_cat"] = df["iucn_cat"].str.strip()
        df.loc[~df["iucn_cat"].isin(IUCN_VALID), "iucn_cat"] = "Not Reported"

    # String cleanup
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip().replace("", None))

    # Cast objectid to int
    df["objectid"] = df["objectid"].astype(int)

    print(f"  Final row count: {len(df):,}")
    return df


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_engine(args):
    host = args.host or os.getenv("DB_HOST", "localhost")
    port = args.port or os.getenv("DB_PORT", "5432")
    dbname = args.dbname or os.getenv("DB_NAME", "eco")
    user = args.user or os.getenv("DB_USER", "postgres")
    password = args.password or os.getenv("DB_PASSWORD", "")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url, future=True)


def upsert_batch(conn, rows: list[dict]):
    cols = list(rows[0].keys())
    col_list = ", ".join(cols)
    val_list = ", ".join(f":{c}" for c in cols)
    update_list = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in cols if c != "objectid"
    ) + ", updated_at = now()"
    sql = text(f"""
        INSERT INTO {TABLE} ({col_list})
        VALUES ({val_list})
        ON CONFLICT (objectid) DO UPDATE
        SET {update_list};
    """)
    conn.execute(sql, rows)


def run_validation(conn):
    print("\n--- Post-load validation ---")
    total = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar()
    print(f"  Total rows : {total:,}")

    print("  Rows by state:")
    rows = conn.execute(text(f"""
        SELECT state, COUNT(*) AS n
        FROM {TABLE}
        GROUP BY state
        ORDER BY n DESC
        LIMIT 10;
    """)).fetchall()
    for r in rows:
        print(f"    {r[0]:<25} {r[1]:>6,}")

    print("  Rows by IUCN category:")
    rows = conn.execute(text(f"""
        SELECT iucn_cat, COUNT(*) AS n
        FROM {TABLE}
        GROUP BY iucn_cat
        ORDER BY n DESC;
    """)).fetchall()
    for r in rows:
        print(f"    {str(r[0]):<20} {r[1]:>6,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Migrate CAPAD 2024 to PostgreSQL")
    p.add_argument("--csv", default=DEFAULT_CSV)
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--dbname", default=None)
    p.add_argument("--user", default=None)
    p.add_argument("--password", default=None)
    p.add_argument("--drop", action="store_true", help="Drop table before loading")
    p.add_argument("--dry-run", action="store_true", help="Clean only; no DB writes")
    p.add_argument("--batch-size", type=int, default=500)
    return p.parse_args()


def main():
    args = parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        sys.exit(f"ERROR: CSV not found: {csv_path}")

    print(f"Reading {csv_path} ...")
    df = pd.read_csv(csv_path, low_memory=False, encoding="utf-8-sig")
    print(f"  Raw rows: {len(df):,}  columns: {len(df.columns)}")

    print("\nCleaning ...")
    df = clean(df)

    if args.dry_run:
        out = csv_path.stem + "_cleaned.csv"
        df.to_csv(out, index=False)
        print(f"\nDry-run complete. Cleaned CSV saved to: {out}")
        return

    engine = get_engine(args)

    with engine.begin() as conn:
        if args.drop:
            print(f"\nDropping table {TABLE} ...")
            conn.execute(text(f"DROP TABLE IF EXISTS {TABLE} CASCADE;"))

        print(f"\nCreating table & indexes (if not exists): {TABLE}")
        for stmt in CREATE_TABLE_SQL.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))

    # Convert NaT -> None for psycopg2
    df = df.where(pd.notnull(df), other=None)
    records = df.to_dict(orient="records")

    print(f"\nUpserting {len(records):,} rows in batches of {args.batch_size} ...")
    with engine.begin() as conn:
        for i in tqdm(range(0, len(records), args.batch_size)):
            upsert_batch(conn, records[i : i + args.batch_size])

    with engine.begin() as conn:
        run_validation(conn)

    print("\nMigration complete.")


if __name__ == "__main__":
    main()
