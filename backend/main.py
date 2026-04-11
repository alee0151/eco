"""
eco – Supply Chain Risk Assessment
Backend API  (FastAPI)

Start with:
  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.extract import router as extract_router

app = FastAPI(title="eco API", version="0.1.0")

# Allow the Vite dev server to call the API directly (dev only).
# In production, sit behind a reverse proxy so CORS is handled externally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
