# CAPAD 2024 – Database Migration

Scripts to ingest the **Collaborative Australian Protected Areas Database (CAPAD) 2024 – Terrestrial** into a local PostgreSQL instance used by the Eco supply-chain risk platform.

## Files

| File | Purpose |
|---|---|
| `migrate_capad.py` | Clean raw CSV → upsert into `public.capad_protected_areas` |
| `capad_postgis_upgrade.sql` | Add PostGIS point geometry + spatial index (optional) |

## Quick start

```bash
# Install dependencies
pip install pandas psycopg2-binary sqlalchemy python-dotenv tqdm

# Configure DB (or use CLI flags)
cp .env.example .env  # fill in DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Run migration
python migrate_capad.py

# Dry run (no DB writes – saves cleaned CSV)
python migrate_capad.py --dry-run

# Full reload (drops and recreates table)
python migrate_capad.py --drop

# Custom connection
python migrate_capad.py --host localhost --port 5432 --dbname eco --user postgres --password secret
```

## What the script does

1. **Reads** the raw CAPAD CSV (UTF-8-BOM safe)
2. **Cleans**:
   - Normalises all columns to `snake_case`
   - Drops fully duplicate rows and rows missing `objectid` / `pa_id` / `name`
   - Parses `gaz_date` / `latest_gaz` → UTC-aware timestamps
   - Casts `nrs_pa` Y/N → boolean
   - Validates lat/lon ranges; nullifies out-of-range coordinates
   - Normalises `iucn_cat` to valid IUCN categories (Ia, Ib, II–VI, Not Reported)
3. **Creates** `public.capad_protected_areas` with appropriate column types, a `PRIMARY KEY` on `objectid`, and indexes on `state`, `pa_type_abbr`, `iucn_cat`, `epbc_trigger`, and `latitude/longitude`
4. **Upserts** in batches of 500 (`ON CONFLICT (objectid) DO UPDATE`) – fully idempotent
5. **Validates** row count and distribution by state and IUCN category after insert

## PostGIS spatial upgrade (optional)

If your DB has PostGIS installed:

```bash
psql -d eco -f capad_postgis_upgrade.sql
```

This adds a `geom geometry(Point, 4326)` column and a GIST spatial index, enabling distance queries between supplier locations and protected areas.

## Table schema

```sql
CREATE TABLE public.capad_protected_areas (
    objectid          INTEGER PRIMARY KEY,
    pa_id             TEXT,
    name              TEXT NOT NULL,
    pa_type           TEXT,
    pa_type_abbr      TEXT,
    iucn_cat          TEXT,
    gaz_area_ha       DOUBLE PRECISION,
    gis_area_ha       DOUBLE PRECISION,
    gaz_date          TIMESTAMPTZ,
    latest_gaz        TIMESTAMPTZ,
    state             TEXT,
    authority         TEXT,
    datasource        TEXT,
    comments          TEXT,
    governance        TEXT,
    management        TEXT,
    overlap           TEXT,
    epbc_trigger      TEXT,
    nrs_pa            BOOLEAN,
    environ           TEXT,
    longitude         DOUBLE PRECISION,
    latitude          DOUBLE PRECISION,
    mapscale          TEXT,
    datasource_id     TEXT,
    capad_status      TEXT,
    protected_area_id TEXT,
    overlap_pct       DOUBLE PRECISION,
    shape_length      DOUBLE PRECISION,
    shape_area        DOUBLE PRECISION,
    inserted_at       TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now()
);
```
