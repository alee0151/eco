"""
eco - Supply Chain Risk Assessment
Backend API  (FastAPI)

Start with:
  uvicorn main:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()  # load .env before anything reads os.getenv()

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
