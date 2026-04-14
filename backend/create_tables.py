"""
create_tables.py

Creates all ORM-defined tables in PostgreSQL.
Run ONCE before seeding or starting the server:

  python create_tables.py
"""

import asyncio
from dotenv import load_dotenv
load_dotenv()

from database import engine, Base
import models  # noqa: F401 — must import models so Base knows about them


async def create_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created (or already exist).")


if __name__ == "__main__":
    asyncio.run(create_all())
