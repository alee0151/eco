"""
routes/biodiversity.py

Epic 2 — Biodiversity / environmental risk endpoints.
Replaces the static mock data in frontend/src/app/data/epic2-data.ts.

Endpoints:
  GET /api/biodiversity/suppliers              — list all biodiversity suppliers
  GET /api/biodiversity/suppliers/{id}         — get one supplier + threatened species
  POST /api/biodiversity/suppliers             — create a new record
  PATCH /api/biodiversity/suppliers/{id}       — update fields
  DELETE /api/biodiversity/suppliers/{id}      — delete a record
  GET /api/biodiversity/suppliers/{id}/species — list threatened species for a supplier
  POST /api/biodiversity/suppliers/{id}/species — add a threatened species record
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import BiodiversitySupplier, ThreatenedSpecies
from schemas import BiodiversitySupplierOut, ThreatenedSpeciesOut

router = APIRouter()


# ── Biodiversity Suppliers ─────────────────────────────────────────────────────

@router.get("/biodiversity/suppliers", response_model=list[BiodiversitySupplierOut])
async def list_bio_suppliers(db: AsyncSession = Depends(get_db)):
    """Returns all biodiversity suppliers with their threatened species."""
    result = await db.execute(
        select(BiodiversitySupplier)
        .options(selectinload(BiodiversitySupplier.threatened_species))
        .order_by(BiodiversitySupplier.risk_score.desc())
    )
    return result.scalars().all()


@router.get("/biodiversity/suppliers/{supplier_id}", response_model=BiodiversitySupplierOut)
async def get_bio_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BiodiversitySupplier)
        .options(selectinload(BiodiversitySupplier.threatened_species))
        .where(BiodiversitySupplier.id == supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    return supplier


@router.post("/biodiversity/suppliers", response_model=BiodiversitySupplierOut, status_code=201)
async def create_bio_supplier(body: dict, db: AsyncSession = Depends(get_db)):
    supplier = BiodiversitySupplier(**{k: v for k, v in body.items() if k != "threatened_species"})
    db.add(supplier)
    await db.flush()  # get the ID before inserting species

    for sp in body.get("threatened_species", []):
        species = ThreatenedSpecies(supplier_id=supplier.id, **sp)
        db.add(species)

    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.patch("/biodiversity/suppliers/{supplier_id}", response_model=BiodiversitySupplierOut)
async def update_bio_supplier(
    supplier_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    supplier = await db.get(BiodiversitySupplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    for field, value in body.items():
        if hasattr(supplier, field) and field != "threatened_species":
            setattr(supplier, field, value)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.delete("/biodiversity/suppliers/{supplier_id}", status_code=204)
async def delete_bio_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(BiodiversitySupplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    await db.delete(supplier)
    await db.commit()


# ── Threatened Species sub-resource ───────────────────────────────────────────

@router.get(
    "/biodiversity/suppliers/{supplier_id}/species",
    response_model=list[ThreatenedSpeciesOut],
)
async def list_species(supplier_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ThreatenedSpecies).where(ThreatenedSpecies.supplier_id == supplier_id)
    )
    return result.scalars().all()


@router.post(
    "/biodiversity/suppliers/{supplier_id}/species",
    response_model=ThreatenedSpeciesOut,
    status_code=201,
)
async def add_species(
    supplier_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    supplier = await db.get(BiodiversitySupplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' not found")
    species = ThreatenedSpecies(supplier_id=supplier_id, **body)
    db.add(species)
    await db.commit()
    await db.refresh(species)
    return species
