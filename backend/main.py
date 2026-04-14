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

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.extract      import router as extract_router
from routes.suppliers    import router as suppliers_router
from routes.biodiversity import router as biodiversity_router

app = FastAPI(
    title="eco API",
    version="0.3.0",
    description="Supply Chain Biodiversity Risk Assessment API",
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
def health():
    return {"status": "ok", "version": "0.3.0"}


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
