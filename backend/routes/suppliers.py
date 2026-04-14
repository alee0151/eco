"""
routes/suppliers.py

Epic 1 — Supplier CRUD endpoints.
All data is read from / written to PostgreSQL via SQLAlchemy async.

Endpoints:
  GET  /api/suppliers          — list all suppliers
  GET  /api/suppliers/{id}     — get one supplier
  POST /api/suppliers          — create / upsert a supplier
  PATCH /api/suppliers/{id}    — update status or fields
  DELETE /api/suppliers/{id}   — delete a supplier
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Supplier
from schemas import SupplierOut, SupplierCreate

router = APIRouter()


@router.get("/suppliers", response_model=list[SupplierOut])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    """Return all suppliers ordered by creation date desc."""
    result = await db.execute(
        select(Supplier).order_by(Supplier.created_at.desc())
    )
    return result.scalars().all()


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    return supplier


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db)):
    """Insert a new supplier, or update if the ID already exists (upsert)."""
    existing = await db.get(Supplier, body.id)
    if existing:
        # Update editable fields
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Partial update — useful for status changes and validation flags."""
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    for field, value in body.items():
        if hasattr(supplier, field):
            setattr(supplier, field, value)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.delete("/suppliers/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    await db.delete(supplier)
    await db.commit()
