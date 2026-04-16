"""
routes/biodiversity.py

Epic 2 — Live biodiversity data from the real DB tables:
  species, kba, capad, ibra

Endpoints:
  GET /api/biodiversity/species                     — species occurrences (paginated)
  GET /api/biodiversity/species/by-bbox             — species within a bounding box
  GET /api/biodiversity/kba                         — Key Biodiversity Areas (paginated)
  GET /api/biodiversity/capad                       — Protected areas (paginated)
  GET /api/biodiversity/capad/regions               — Protected area polygons (geom_wkt, for map rendering)
  GET /api/biodiversity/capad/by-state/{state}      — Protected areas filtered by state
  GET /api/biodiversity/ibra                        — IBRA bioregions
  GET /api/biodiversity/ibra/{code}                 — Single IBRA region by code
  GET /api/biodiversity/counts                      — Real DB row counts for stat cards
  GET /api/biodiversity/risk-summary                — Risk summary for a supplier lat/lng

Performance notes
-----------------
* /counts        — three COUNT queries run in parallel with asyncio.gather.
* /risk-summary  — four independent sub-queries (IBRA, species count, CAPAD count,
                   KBA count) all run in parallel with asyncio.gather.
* IBRA lookup    — single query ordered by ST_Distance; returns the containing region
                   first (distance = 0) and falls back to nearest without a second
                   round-trip.
* CAPAD count    — uses ST_DWithin on the real polygon geometry (geom) rather than a
                   bounding-box centroid filter.  This correctly counts parks that
                   *overlap* the search radius even when their centroid is outside it.
                   Falls back to bbox centroid filter when PostGIS is unavailable.
* Species count  — count and names derived from the same CTE in a single round-trip.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from geoalchemy2.functions import ST_Within, ST_SetSRID, ST_MakePoint, ST_DWithin
from typing import Optional, List

from database import get_db
from models import Species, Kba, Capad, Ibra
from schemas import SpeciesOut, KbaOut, CapadOut, IbraOut, SupplierRiskSummary

router = APIRouter()

# Default spatial buffer: ~50 km at Australian latitudes
DEFAULT_BUFFER_DEG = 0.5
# 0.5 degrees ≈ 55 km — used as the ST_DWithin metre radius too
DEFAULT_BUFFER_METRES = 55_000

STATE_ABBREV_MAP: dict[str, str] = {
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "WA":  "Western Australia",
    "SA":  "South Australia",
    "TAS": "Tasmania",
    "ACT": "Australian Capital Territory",
    "NT":  "Northern Territory",
}


def _resolve_state(raw: str) -> str:
    return STATE_ABBREV_MAP.get(raw.upper().strip(), raw)


# ---------------------------------------------------------------------------
# Quality filters applied to all species proximity / risk queries
# ---------------------------------------------------------------------------
SPECIES_QUALITY_FILTERS = [
    Species.occurrencestatus.ilike("present"),
    Species.is_obscured.is_(False),
    Species.basisofrecord.in_(["HUMAN_OBSERVATION", "MACHINE_OBSERVATION"]),
]


# ── Species ───────────────────────────────────────────────────────────────────

@router.get("/biodiversity/species", response_model=List[SpeciesOut])
async def list_species(
    limit:   int  = Query(100, ge=1, le=1000),
    offset:  int  = Query(0,   ge=0),
    state:   Optional[str] = Query(None),
    kingdom: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Species)
    if state:
        resolved = _resolve_state(state)
        q = q.where(Species.stateprovince.ilike(f"%{resolved}%"))
    if kingdom:
        q = q.where(Species.kingdom.ilike(f"%{kingdom}%"))
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/biodiversity/species/by-bbox", response_model=List[SpeciesOut])
async def species_by_bbox(
    min_lat: float = Query(...),
    max_lat: float = Query(...),
    min_lng: float = Query(...),
    max_lng: float = Query(...),
    limit:   int   = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Species)
        .where(Species.decimallatitude.isnot(None))
        .where(Species.decimallongitude.isnot(None))
        .where(Species.decimallatitude.between(min_lat, max_lat))
        .where(Species.decimallongitude.between(min_lng, max_lng))
        .where(*SPECIES_QUALITY_FILTERS)
        .limit(limit)
    )
    result = await db.execute(q)
    return result.scalars().all()


# ── KBA ───────────────────────────────────────────────────────────────────────

@router.get("/biodiversity/kba", response_model=List[KbaOut])
async def list_kba(
    limit:  int           = Query(200, ge=1, le=2000),
    offset: int           = Query(0,   ge=0),
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Kba)
    if region:
        q = q.where(Kba.region.ilike(f"%{region}%"))
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/biodiversity/kba/{kba_id}", response_model=KbaOut)
async def get_kba(kba_id: int, db: AsyncSession = Depends(get_db)):
    kba = await db.get(Kba, kba_id)
    if not kba:
        raise HTTPException(status_code=404, detail=f"KBA {kba_id} not found")
    return kba


# ── CAPAD ─────────────────────────────────────────────────────────────────────

@router.get("/biodiversity/capad", response_model=List[CapadOut])
async def list_capad(
    limit:     int           = Query(200, ge=1, le=2000),
    offset:    int           = Query(0,   ge=0),
    state:     Optional[str] = Query(None),
    pa_type:   Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Capad)
    if state:
        q = q.where(Capad.state.ilike(f"%{state}%"))
    if pa_type:
        q = q.where(Capad.pa_type.ilike(f"%{pa_type}%"))
    if is_active is not None:
        q = q.where(Capad.is_active == is_active)
    q = q.order_by(Capad.gis_area_ha.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/biodiversity/capad/regions")
async def capad_regions(
    state:  Optional[str] = Query(None),
    limit:  int           = Query(2000, ge=1, le=5000),
    offset: int           = Query(0,   ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Lightweight CAPAD polygon list for map rendering.
    Ordered by area DESC so large regions paint first and smaller parks sit on top.
    """
    q = (
        select(
            Capad.id, Capad.pa_id, Capad.pa_name, Capad.pa_type,
            Capad.pa_type_abbr, Capad.iucn_cat, Capad.state,
            Capad.gis_area_ha, Capad.governance, Capad.authority,
            Capad.epbc_trigger, Capad.geom_wkt,
        )
        .where(Capad.geom_wkt.isnot(None))
        .where(Capad.is_active == True)  # noqa: E712
    )
    if state:
        q = q.where(Capad.state.ilike(f"%{state}%"))
    q = q.order_by(Capad.gis_area_ha.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).mappings().all()
    return [dict(r) for r in rows]


@router.get("/biodiversity/capad/by-state/{state}", response_model=List[CapadOut])
async def capad_by_state(
    state: str,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Capad)
        .where(Capad.state.ilike(f"%{state}%"))
        .where(Capad.is_active == True)  # noqa: E712
        .order_by(Capad.gis_area_ha.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/biodiversity/capad/{capad_id}", response_model=CapadOut)
async def get_capad(capad_id: int, db: AsyncSession = Depends(get_db)):
    capad = await db.get(Capad, capad_id)
    if not capad:
        raise HTTPException(status_code=404, detail=f"CAPAD record {capad_id} not found")
    return capad


# ── IBRA ──────────────────────────────────────────────────────────────────────

@router.get("/biodiversity/ibra", response_model=List[IbraOut])
async def list_ibra(
    limit:  int           = Query(200, ge=1, le=500),
    offset: int           = Query(0,   ge=0),
    state:  Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Ibra)
    if state:
        q = q.where(Ibra.state.ilike(f"%{state}%"))
    q = q.order_by(Ibra.ibra_reg_name).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/biodiversity/ibra/{code}", response_model=IbraOut)
async def get_ibra_by_code(code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ibra).where(Ibra.ibra_reg_code.ilike(code))
    )
    ibra = result.scalar_one_or_none()
    if not ibra:
        raise HTTPException(status_code=404, detail=f"IBRA region '{code}' not found")
    return ibra


# ── DB Counts ─────────────────────────────────────────────────────────────────

@router.get("/biodiversity/counts")
async def biodiversity_counts(db: AsyncSession = Depends(get_db)):
    """
    Return live row counts for stat cards.
    All three COUNT queries run in parallel via asyncio.gather — no serial waiting.
    """
    capad_q   = db.execute(select(func.count()).select_from(Capad).where(Capad.is_active == True))   # noqa: E712
    kba_q     = db.execute(select(func.count()).select_from(Kba))
    species_q = db.execute(select(func.count()).select_from(Species))

    capad_res, kba_res, species_res = await asyncio.gather(capad_q, kba_q, species_q)

    return {
        "capad_active":  capad_res.scalar()   or 0,
        "kba_total":     kba_res.scalar()     or 0,
        "species_total": species_res.scalar() or 0,
    }


# ── Supplier Risk Summary ─────────────────────────────────────────────────────

@router.get("/biodiversity/risk-summary", response_model=SupplierRiskSummary)
async def risk_summary(
    supplier_id:   str   = Query(...),
    supplier_name: str   = Query(...),
    lat:           float = Query(...),
    lng:           float = Query(...),
    buffer_deg:    float = Query(DEFAULT_BUFFER_DEG),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute a biodiversity risk summary for a supplier location.

    All four sub-queries run in **parallel** with asyncio.gather:

    1. IBRA region  — single query ordered by ST_Distance (0 = containing polygon,
                      > 0 = nearest fallback).  No second round-trip needed.

    2. Species      — distinct threatened-species count + representative names,
                      both from the same CTE in a single DB round-trip.
                      Threatened filter covers: threatened, sensitive, epbc resources.

    3. CAPAD count  — ST_DWithin on real polygon geometry so parks that *overlap*
                      the search radius are counted even if their centroid is outside
                      it.  Falls back to bbox centroid filter if PostGIS unavailable.

    4. KBA count    — bounding-box centroid filter (KBA table has no polygon geom).
    """
    min_lat = lat - buffer_deg
    max_lat = lat + buffer_deg
    min_lng = lng - buffer_deg
    max_lng = lng + buffer_deg

    supplier_point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

    # ── 1. IBRA — single distance-ordered query ────────────────────────────
    async def _ibra() -> tuple[str | None, str | None]:
        result = await db.execute(
            text("""
                SELECT ibra_reg_name, ibra_reg_code
                FROM   ibra
                WHERE  geom IS NOT NULL
                ORDER  BY geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                LIMIT  1
            """),
            {"lng": lng, "lat": lat},
        )
        row = result.first()
        return (row[0] if row else None, row[1] if row else None)

    # ── 2. Species — count + names in one CTE round-trip ──────────────────
    # Threatened filter widened to cover all ALA sensitive/threatened resources:
    #   %%threatened%%  — ALA Threatened Species lists
    #   %%sensitive%%   — ALA Sensitive Species List
    #   %%epbc%%        — EPBC Act listed species
    async def _species() -> tuple[int, list[str]]:
        rows = (await db.execute(
            text("""
                WITH threatened AS (
                    SELECT
                        taxonconceptid,
                        MIN(vernacularname) FILTER (WHERE vernacularname IS NOT NULL)
                            AS representative_name
                    FROM   species
                    WHERE  taxonconceptid IS NOT NULL
                      AND  decimallatitude  IS NOT NULL
                      AND  decimallongitude IS NOT NULL
                      AND  decimallatitude  BETWEEN :min_lat AND :max_lat
                      AND  decimallongitude BETWEEN :min_lng AND :max_lng
                      AND  (
                               dataresourcename ILIKE '%%threatened%%'
                            OR dataresourcename ILIKE '%%sensitive%%'
                            OR dataresourcename ILIKE '%%epbc%%'
                           )
                      AND  occurrencestatus ILIKE 'present'
                      AND  is_obscured IS NOT TRUE
                      AND  basisofrecord IN ('HUMAN_OBSERVATION', 'MACHINE_OBSERVATION')
                    GROUP BY taxonconceptid
                )
                SELECT
                    COUNT(*)                                          AS species_count,
                    ARRAY_AGG(representative_name ORDER BY representative_name)
                        FILTER (WHERE representative_name IS NOT NULL) AS names
                FROM threatened
            """),
            {"min_lat": min_lat, "max_lat": max_lat,
             "min_lng": min_lng, "max_lng": max_lng},
        )).first()
        count = int(rows[0] or 0) if rows else 0
        names = list((rows[1] or [])[:20]) if rows else []
        return count, names

    # ── 3. CAPAD — ST_DWithin on real polygon geometry ────────────────────
    async def _capad() -> int:
        buffer_metres = buffer_deg * 111_000  # 1 deg ≈ 111 km
        try:
            result = await db.execute(
                select(func.count()).select_from(Capad)
                .where(Capad.geom.isnot(None))
                .where(Capad.is_active == True)  # noqa: E712
                .where(
                    ST_DWithin(
                        Capad.geom.cast(text("geography")),
                        func.ST_SetSRID(
                            func.ST_MakePoint(lng, lat), 4326
                        ).cast(text("geography")),
                        buffer_metres,
                    )
                )
            )
            return result.scalar() or 0
        except Exception:
            # Fallback: centroid bbox filter if PostGIS geography cast unavailable
            result = await db.execute(
                select(func.count()).select_from(Capad)
                .where(Capad.latitude.isnot(None))
                .where(Capad.longitude.isnot(None))
                .where(Capad.latitude.between(min_lat, max_lat))
                .where(Capad.longitude.between(min_lng, max_lng))
                .where(Capad.is_active == True)  # noqa: E712
            )
            return result.scalar() or 0

    # ── 4. KBA — bbox centroid (no polygon geom in KBA table) ─────────────
    async def _kba() -> int:
        result = await db.execute(
            select(func.count()).select_from(Kba)
            .where(Kba.sit_lat.isnot(None))
            .where(Kba.sit_long.isnot(None))
            .where(Kba.sit_lat.between(min_lat, max_lat))
            .where(Kba.sit_long.between(min_lng, max_lng))
        )
        return result.scalar() or 0

    # ── Run all four sub-queries in parallel ───────────────────────────────
    (ibra_name, ibra_code), (species_count, species_names), capad_count, kba_count = (
        await asyncio.gather(_ibra(), _species(), _capad(), _kba())
    )

    return SupplierRiskSummary(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        lat=lat,
        lng=lng,
        ibra_region=ibra_name,
        ibra_code=ibra_code,
        protected_areas_nearby=capad_count,
        kba_nearby=kba_count,
        species_nearby=species_count,
        threatened_species_names=species_names,
    )
