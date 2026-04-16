"""
database.py

SQLAlchemy async engine + session factory.
Connects to the PostgreSQL database configured in .env.

Requires:
  pip install sqlalchemy asyncpg psycopg2-binary

SSL
---
Azure PostgreSQL Flexible Server requires SSL.
Set DATABASE_SSL=require in your environment (default) to enable it.
Set DATABASE_SSL=disable for local development without SSL.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import os
import logging
import ssl

logger = logging.getLogger(__name__)

# ── Connection string ───────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/eco_db",
)

# ── SSL config ───────────────────────────────────────────────────────────────────────
#
# DATABASE_SSL env var controls SSL mode:
#   require   — enforce SSL, verify cert (default, required for Azure)
#   disable   — no SSL (local dev without SSL)
#
# Azure PostgreSQL Flexible Server always requires SSL.
# asyncpg needs ssl passed as a connect_arg, NOT in the URL.

_ssl_mode = os.getenv("DATABASE_SSL", "require").strip().lower()

if _ssl_mode == "disable":
    _connect_args = {}
else:
    # Create SSL context that trusts the Azure-signed certificate
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False          # Azure uses wildcard cert
    _ssl_ctx.verify_mode   = ssl.CERT_NONE   # simplest; fine for managed Azure PG
    _connect_args = {"ssl": _ssl_ctx}

logger.info("[database] SSL mode: %s", _ssl_mode)

# ── Engine ────────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

# ── Session factory ─────────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base class for ORM models ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """Yield a DB session; always closes on exit."""
    async with AsyncSessionLocal() as session:
        yield session


# ── Startup connection probe ───────────────────────────────────────────────────────────
async def check_db_connection() -> tuple[bool, str]:
    """
    Fire a trivial SELECT 1 to verify the database is reachable.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, ""
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        logger.error(
            "[database] ❌ Cannot reach PostgreSQL at %s — %s",
            DATABASE_URL.split("@")[-1],
            msg,
        )
        return False, msg
