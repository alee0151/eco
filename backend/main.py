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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract_router,      prefix="/api")
app.include_router(suppliers_router,    prefix="/api")
app.include_router(biodiversity_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0"}
