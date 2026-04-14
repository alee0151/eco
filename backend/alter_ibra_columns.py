"""
alter_ibra_columns.py

One-off migration: widen the VARCHAR columns on the `ibra` table so that
all values from IBRARegion_Aust70.shp fit without truncation errors.

Why this is needed
------------------
The `ibra` table was originally created with VARCHAR(10) on ibra_reg_code
(and similarly tight limits on ibra_reg_name / state).  IBRA 7 region codes
are always 2-3 characters (e.g. 'AUA', 'SEH'), but a small number of
records in the shapefile carry longer composite codes that exceed the limit.
Altering to TEXT removes the constraint entirely while keeping the data type.

Usage
-----
  cd backend
  python alter_ibra_columns.py

This script is idempotent: if the columns are already TEXT, the ALTER TABLE
commands are no-ops (Postgres allows altering TEXT -> TEXT silently).
"""

import os
import sys

try:
    from sqlalchemy import create_engine, text
except ImportError:
    sys.exit("ERROR: sqlalchemy not installed. Run: pip install sqlalchemy")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


ALTER_STATEMENTS = [
    # Widen every string column on ibra that could receive unbounded input
    # from the shapefile.  TEXT in PostgreSQL is equivalent to VARCHAR with
    # no length limit and has no storage overhead vs VARCHAR.
    "ALTER TABLE ibra ALTER COLUMN ibra_reg_code  TYPE TEXT",
    "ALTER TABLE ibra ALTER COLUMN ibra_reg_name  TYPE TEXT",
    "ALTER TABLE ibra ALTER COLUMN state          TYPE TEXT",
]


def main():
    raw_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/eco_db",
    )
    sync_url = raw_url.replace("postgresql+asyncpg", "postgresql")
    print(f"Connecting to: {sync_url.split('@')[-1]}")
    engine = create_engine(sync_url, echo=False)

    with engine.begin() as conn:
        for stmt in ALTER_STATEMENTS:
            print(f"  Executing: {stmt}")
            conn.execute(text(stmt))

    print("\n✅  ibra column widths updated to TEXT.")
    print("   Re-run migrate_ibra.py now — the truncation error will be gone.")


if __name__ == "__main__":
    main()
