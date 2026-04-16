"""
eco - Supply Chain Risk Assessment
Backend API  (FastAPI)

Start with:
  uvicorn main:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import check_db_connection, DATABASE_URL
from routes.extract        import router as extract_router
from routes.suppliers      import router as suppliers_router
from routes.biodiversity   import router as biodiversity_router
from routes.enrich         import router as enrich_router
from routes.parse_address  import router as parse_address_router
from routes.geocode        import router as geocode_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ok, err = await check_db_connection()
    if ok:
        safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
        logger.info("[startup] ✅ Database OK — %s", safe_url)
    else:
        logger.error("[startup] ❌ Database UNREACHABLE: %s", err)

    import os
    if os.getenv("ABR_GUID", "").strip():
        logger.info("[startup] ✅ ABR_GUID configured — /api/enrich is live")
    else:
        logger.warning("[startup] ⚠️  ABR_GUID not set — /api/enrich will return 503")

    if os.getenv("GEOSCAPE_API_KEY", "").strip():
        logger.info("[startup] ✅ GEOSCAPE_API_KEY configured — G-NAF geocoding active")
    else:
        logger.warning(
            "[startup] ⚠️  GEOSCAPE_API_KEY not set — /api/geocode will fall back to Nominatim. "
            "Register free at https://geoscape.com.au/geoscape-developer-centre/"
        )

    yield


app = FastAPI(
    title="eco API",
    version="0.6.0",
    description="Supply Chain Biodiversity Risk Assessment API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
        "http://localhost:5176", "http://localhost:4173", "http://localhost:4174",
        "http://localhost:3000", "http://localhost:3001",
        "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:8000",
        "https://eco-ynvb.onrender.com "
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(extract_router,       prefix="/api")
app.include_router(suppliers_router,     prefix="/api")
app.include_router(biodiversity_router,  prefix="/api")
app.include_router(enrich_router,        prefix="/api")
app.include_router(parse_address_router, prefix="/api")
app.include_router(geocode_router,       prefix="/api")


@app.get("/api/health")
async def health():
    import os
    db_ok, db_err = await check_db_connection()
    safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    return {
        "status":   "ok",
        "version":  "0.6.0",
        "database": {"connected": db_ok, "host": safe_url, **(({"error": db_err}) if not db_ok else {})},
        "abr":      {"configured": bool(os.getenv("ABR_GUID",          "").strip())},
        "geoscape": {"configured": bool(os.getenv("GEOSCAPE_API_KEY",  "").strip())},
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000, reload=True,
        reload_dirs=["."],
        reload_excludes=[".venv/*", "__pycache__/*", "*.pyc", "*.pyo", ".git/*"],
    )
