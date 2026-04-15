"""
routes/suppliers.py  —  Epic 1 supplier CRUD

Endpoints:
  GET    /api/suppliers          list all
  GET    /api/suppliers/{id}     get one
  POST   /api/suppliers          create
  PATCH  /api/suppliers/{id}     update (status, enrichment, coords, etc.)
  DELETE /api/suppliers/{id}     delete
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, DatabaseError
from typing import List
import logging

from database import get_db
from models import Supplier as SupplierModel
from schemas import SupplierOut, SupplierCreate

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/suppliers", response_model=List[SupplierOut])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    """
    Return all suppliers ordered by name.
    Returns 503 (with a clear message) if the database is unreachable
    instead of crashing with a raw 500.
    """
    try:
        result = await db.execute(select(SupplierModel).order_by(SupplierModel.name))
        return result.scalars().all()
    except (OperationalError, DatabaseError) as exc:
        logger.error("[suppliers] DB connection lost: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot reach the database. "
                "Ensure PostgreSQL is running and DATABASE_URL in backend/.env is correct. "
                f"Detail: {exc.orig or exc}"
            ),
        ) from exc


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    try:
        s = await db.get(SupplierModel, supplier_id)
    except (OperationalError, DatabaseError) as exc:
        logger.error("[suppliers] DB connection lost: %s", exc)
        raise HTTPException(status_code=503, detail="Database unreachable") from exc
    if not s:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return s


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db)):
    try:
        existing = await db.get(SupplierModel, body.id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Supplier {body.id} already exists")
        supplier = SupplierModel(**body.model_dump())
        db.add(supplier)
        await db.commit()
        await db.refresh(supplier)
        return supplier
    except HTTPException:
        raise
    except (OperationalError, DatabaseError) as exc:
        logger.error("[suppliers] DB connection lost during create: %s", exc)
        raise HTTPException(status_code=503, detail="Database unreachable") from exc


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    try:
        s = await db.get(SupplierModel, supplier_id)
        if not s:
            raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
        allowed = {
            "name", "abn", "address", "commodity", "region",
            "confidence_score", "status", "is_validated",
            "enriched_name", "enriched_address", "abr_status",
            "abn_found", "name_discrepancy", "address_discrepancy",
            "lat", "lng", "resolution_level", "inference_method",
            "file_name", "file_type", "warnings",
        }
        for key, value in body.items():
            if key in allowed:
                setattr(s, key, value)
        await db.commit()
        await db.refresh(s)
        return s
    except HTTPException:
        raise
    except (OperationalError, DatabaseError) as exc:
        logger.error("[suppliers] DB connection lost during update: %s", exc)
        raise HTTPException(status_code=503, detail="Database unreachable") from exc


@router.delete("/suppliers/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    try:
        s = await db.get(SupplierModel, supplier_id)
        if not s:
            raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
        await db.delete(s)
        await db.commit()
    except HTTPException:
        raise
    except (OperationalError, DatabaseError) as exc:
        logger.error("[suppliers] DB connection lost during delete: %s", exc)
        raise HTTPException(status_code=503, detail="Database unreachable") from exc
