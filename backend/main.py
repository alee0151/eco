"""
eco - Supply Chain Risk Assessment
Backend API  (FastAPI)

Start with:
  uvicorn main:app --reload --port 8000

uvicorn is configured below to watch only the backend/ source directory.
Without this, WatchFiles watches the entire working directory including
.venv, which causes infinite reload loops every time numpy or shapely
import their own files during startup.
"""

from dotenv import load_dotenv
load_dotenv()  # load .env before anything reads os.getenv()

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import check_db_connection, DATABASE_URL
from routes.extract      import router as extract_router
from routes.suppliers    import router as suppliers_router
from routes.biodiversity import router as biodiversity_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks before accepting traffic."""
    ok, err = await check_db_connection()
    if ok:
        # Mask credentials in the log (show only host:port/db)
        safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
        logger.info("[startup] ✅ Database connection OK — %s", safe_url)
    else:
        logger.error(
            "[startup] ❌ Database UNREACHABLE. "
            "Check DATABASE_URL in backend/.env and that PostgreSQL is running. "
            "Error: %s",
            err,
        )
        # App still starts so /api/health can report the failure;
        # individual routes handle the OperationalError gracefully.
    yield  # application is now running


app = FastAPI(
    title="eco API",
    version="0.3.0",
    description="Supply Chain Biodiversity Risk Assessment API",
    lifespan=lifespan,
)

# Vite's dev server starts at 5173 and auto-increments (5174, 5175 ...)
# when the preferred port is already in use.  List all common Vite ports so
# CORS is never blocked just because another process held 5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Vite dev server (auto-increments when port is busy)
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        # Vite preview mode
        "http://localhost:4173",
        "http://localhost:4174",
        # Common alternatives
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(extract_router,      prefix="/api")
app.include_router(suppliers_router,    prefix="/api")
app.include_router(biodiversity_router, prefix="/api")


@app.get("/api/health")
async def health():
    """Returns API status + live database reachability check."""
    db_ok, db_err = await check_db_connection()
    safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    return {
        "status": "ok",
        "version": "0.3.0",
        "database": {
            "connected": db_ok,
            "host": safe_url,
            **({
                "error": db_err
            } if not db_ok else {}),
        },
    }


if __name__ == "__main__":
    # When run directly (`python main.py`) restrict the reload watcher to
    # the backend source directory only.  This prevents WatchFiles from
    # picking up changes inside .venv and triggering infinite restart loops.
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["."],           # only watch backend/ (current dir)
        reload_excludes=[
            ".venv/*",
            "__pycache__/*",
            "*.pyc",
            "*.pyo",
            ".git/*",
        ],
    )
