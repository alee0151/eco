"""
database.py

SQLAlchemy async engine + session factory.
Connects to the PostgreSQL database configured in .env.

Requires:
  pip install sqlalchemy asyncpg psycopg2-binary
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

# ── Connection string ─────────────────────────────────────────────────────────
# Reads DATABASE_URL from .env (set via python-dotenv in main.py)
# Format: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/eco_db",
)

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # set True to log all SQL to stdout
    pool_pre_ping=True,  # drops stale connections automatically
    pool_size=5,
    max_overflow=10,
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base class for ORM models ─────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """Yield a DB session; always closes on exit."""
    async with AsyncSessionLocal() as session:
        yield session
