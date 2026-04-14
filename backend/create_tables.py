"""
create_tables.py

Run ONCE to create the app-managed 'suppliers' table in your PostgreSQL DB.
Does NOT touch the pre-existing tables (species, kba, capad, ibra).

Usage:
  cd backend
  python create_tables.py
"""

import asyncio
from dotenv import load_dotenv
load_dotenv()

from database import engine
from models import Base, Supplier  # only Supplier is app-managed


async def main():
    async with engine.begin() as conn:
        # create_all is safe — it skips tables that already exist
        await conn.run_sync(Base.metadata.create_all, tables=[Supplier.__table__])
    print("✅  'suppliers' table ready.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
