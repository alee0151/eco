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
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from geoalchemy2.functions import ST_Within, ST_SetSRID, ST_MakePoint
from typing import Optional, List

from database import get_db
from models import Species, Kba, Capad, Ibra
from schemas import SpeciesOut, KbaOut, CapadOut, IbraOut, SupplierRiskSummary

router = APIRouter()

# Default spatial buffer in degrees (~50 km at Australian latitudes)
DEFAULT_BUFFER_DEG = 0.5

# ---------------------------------------------------------------------------
# State abbreviation → full stateprovince name
# The ALA dataset stores full names (e.g. "Queensland") in stateprovince.
# Frontend callers typically pass abbreviated codes ("QLD", "NSW" etc.).
# ---------------------------------------------------------------------------
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
    """Return the full stateprovince string for an abbreviated or full state name."""
    return STATE_ABBREV_MAP.get(raw.upper().strip(), raw)


# ---------------------------------------------------------------------------
# Threatened-species dataset filter
# Only count species from ALA threatened-species data resources.
# ---------------------------------------------------------------------------
THREATENED_RESOURCE_FILTER = Species.dataresourcename.ilike("%threatened%")

# ---------------------------------------------------------------------------
# Species quality filters
# Applied to all proximity / risk queries to exclude:
#   - absent records (occurrencestatus != 'present')
#   - obscured records (ALA fuzzes coordinates ±10 km for sensitive species)
#   - unreliable basis of record (museum specimens, literature refs with bad coords)
# ---------------------------------------------------------------------------
SPECIES_QUALITY_FILTERS = [
    Species.occurrencestatus.ilike("present"),
    Species.is_obscured.is_(False),
    Species.basisofrecord.in_([
        "HUMAN_OBSERVATION",
        "MACHINE_OBSERVATION",
    ]),
]


# ── Species ───────────────────────────────────────────────────────────────────

@router.get("/biodiversity/species", response_model=List[SpeciesOut])
async def list_species(
    limit:   int  = Query(100, ge=1, le=1000, description="Max records to return"),
    offset:  int  = Query(0,   ge=0,          description="Pagination offset"),
    state:   Optional[str] = Query(None, description="Filter by state — accepts abbreviation (QLD) or full name"),
    kingdom: Optional[str] = Query(None, description="Filter by kingdom e.g. Animalia"),
    db: AsyncSession = Depends(get_db),
):
    """Return species occurrence records, optionally filtered."""
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
    min_lat:  float = Query(..., description="South boundary latitude"),
    max_lat:  float = Query(..., description="North boundary latitude"),
    min_lng:  float = Query(..., description="West boundary longitude"),
    max_lng:  float = Query(..., description="East boundary longitude"),
    limit:    int   = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Return species occurrences within a lat/lng bounding box."""
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


# ── KBA ──────────────────────────────────────────────────────────────────────

@router.get("/biodiversity/kba", response_model=List[KbaOut])
async def list_kba(
    limit:  int           = Query(200, ge=1, le=2000),
    offset: int           = Query(0,   ge=0),
    region: Optional[str] = Query(None, description="Filter by region name"),
    db: AsyncSession = Depends(get_db),
):
    """Return Key Biodiversity Areas, optionally filtered by region."""
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


# ── CAPAD ────────────────────────────────────────────────────────────────────

@router.get("/biodiversity/capad", response_model=List[CapadOut])
async def list_capad(
    limit:    int           = Query(200, ge=1, le=2000),
    offset:   int           = Query(0,   ge=0),
    state:    Optional[str] = Query(None, description="Filter by state e.g. VIC"),
    pa_type:  Optional[str] = Query(None, description="Filter by type e.g. 'National Park'"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    """Return protected areas from CAPAD, with optional filters."""
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
    state:    Optional[str] = Query(None, description="Filter by state e.g. VIC"),
    limit:    int           = Query(2000, ge=1, le=5000),
    offset:   int           = Query(0,   ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Return CAPAD protected areas as a lightweight list for polygon rendering.
    Only rows with a non-null geom_wkt are returned.

    Fields: id, pa_id, pa_name, pa_type, pa_type_abbr, iucn_cat, state,
            gis_area_ha, governance, authority, epbc_trigger, geom_wkt.

    Ordered by area descending so the largest regions render first and smaller
    regions paint on top (correct z-ordering without explicit z-index).
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
    """Return all protected areas for a given Australian state."""
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
    state:  Optional[str] = Query(None, description="Filter by state e.g. NSW"),
    db: AsyncSession = Depends(get_db),
):
    """Return IBRA bioregions."""
    q = select(Ibra)
    if state:
        q = q.where(Ibra.state.ilike(f"%{state}%"))
    q = q.order_by(Ibra.ibra_reg_name).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/biodiversity/ibra/{code}", response_model=IbraOut)
async def get_ibra_by_code(code: str, db: AsyncSession = Depends(get_db)):
    """Return a single IBRA bioregion by its 3-letter code (e.g. BBS)."""
    result = await db.execute(
        select(Ibra).where(Ibra.ibra_reg_code.ilike(code))
    )
    ibra = result.scalar_one_or_none()
    if not ibra:
        raise HTTPException(status_code=404, detail=f"IBRA region '{code}' not found")
    return ibra


# ── DB Counts (real row totals for stat cards) ────────────────────────────────

@router.get("/biodiversity/counts")
async def biodiversity_counts(db: AsyncSession = Depends(get_db)):
    """
    Return real row counts for CAPAD (active), KBA, and Species tables.
    Used by the frontend stat cards so they show live numbers, not hardcoded strings.
    """
    capad_result   = await db.execute(select(func.count()).select_from(Capad).where(Capad.is_active == True))  # noqa: E712
    kba_result     = await db.execute(select(func.count()).select_from(Kba))
    species_result = await db.execute(select(func.count()).select_from(Species))

    return {
        "capad_active":  capad_result.scalar() or 0,
        "kba_total":     kba_result.scalar()   or 0,
        "species_total": species_result.scalar() or 0,
    }


# ── Supplier Risk Summary ─────────────────────────────────────────────────────

@router.get("/biodiversity/risk-summary", response_model=SupplierRiskSummary)
async def risk_summary(
    supplier_id:   str   = Query(..., description="Supplier ID e.g. SUP-001"),
    supplier_name: str   = Query(..., description="Supplier name"),
    lat:           float = Query(..., description="Supplier latitude"),
    lng:           float = Query(..., description="Supplier longitude"),
    buffer_deg:    float = Query(DEFAULT_BUFFER_DEG, description="Search radius in degrees (~0.5 ≈ 50 km)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Given a supplier lat/lng, compute a biodiversity risk summary by:

    1. IBRA lookup  — ST_Within(supplier_point, ibra.geom) against the real
                      MULTIPOLYGON boundaries.  No approximation, no guessing.
                      Falls back to ST_DWithin (nearest region) if the point
                      sits exactly on a boundary or in a gap between regions.

    2. Species      — Count distinct threatened species (by taxonconceptid) whose
                      confirmed occurrences (present, non-obscured, reliable basis)
                      fall within the bounding box around the supplier.
                      The names list is derived from the SAME CTE so count and
                      list are always consistent.

    3. CAPAD        — Count protected area centroids within the buffer.

    4. KBA          — Count Key Biodiversity Area centroids within the buffer.
    """
    min_lat = lat - buffer_deg
    max_lat = lat + buffer_deg
    min_lng = lng - buffer_deg
    max_lng = lng + buffer_deg

    # ──────────────────────────────────────────────────────────────────────────
    # 1. IBRA region — exact ST_Within against MULTIPOLYGON boundaries
    # ──────────────────────────────────────────────────────────────────────────
    supplier_point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

    ibra_exact_result = await db.execute(
        select(Ibra.ibra_reg_name, Ibra.ibra_reg_code)
        .where(Ibra.geom.isnot(None))
        .where(ST_Within(supplier_point, Ibra.geom))
        .limit(1)
    )
    ibra_row = ibra_exact_result.first()

    if not ibra_row:
        ibra_near_result = await db.execute(
            text("""
                SELECT ibra_reg_name, ibra_reg_code
                FROM ibra
                WHERE geom IS NOT NULL
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                LIMIT 1
            """),
            {"lng": lng, "lat": lat},
        )
        ibra_row = ibra_near_result.first()

    ibra_name = ibra_row[0] if ibra_row else None
    ibra_code = ibra_row[1] if ibra_row else None

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Threatened species — distinct count + names, both from the same CTE
    # ──────────────────────────────────────────────────────────────────────────
    threatened_cte = (
        select(
            Species.taxonconceptid,
            func.min(Species.vernacularname).filter(
                Species.vernacularname.isnot(None)
            ).label("representative_name"),
        )
        .where(Species.taxonconceptid.isnot(None))
        .where(Species.decimallatitude.isnot(None))
        .where(Species.decimallongitude.isnot(None))
        .where(Species.decimallatitude.between(min_lat, max_lat))
        .where(Species.decimallongitude.between(min_lng, max_lng))
        .where(THREATENED_RESOURCE_FILTER)
        .where(Species.occurrencestatus.ilike("present"))
        .where(Species.is_obscured.is_(False))
        .where(Species.basisofrecord.in_([
            "HUMAN_OBSERVATION",
            "MACHINE_OBSERVATION",
        ]))
        .group_by(Species.taxonconceptid)
        .cte("threatened_species")
    )

    count_result = await db.execute(
        select(func.count()).select_from(threatened_cte)
    )
    species_count = count_result.scalar() or 0

    names_result = await db.execute(
        select(threatened_cte.c.representative_name)
        .where(threatened_cte.c.representative_name.isnot(None))
        .order_by(threatened_cte.c.representative_name)
        .limit(20)
    )
    species_names = [row[0] for row in names_result.fetchall()]

    # ──────────────────────────────────────────────────────────────────────────
    # 3. CAPAD — protected area centroids within the buffer
    # ──────────────────────────────────────────────────────────────────────────
    capad_count_result = await db.execute(
        select(func.count()).select_from(Capad)
        .where(Capad.latitude.isnot(None))
        .where(Capad.longitude.isnot(None))
        .where(Capad.latitude.between(min_lat, max_lat))
        .where(Capad.longitude.between(min_lng, max_lng))
    )
    capad_count = capad_count_result.scalar() or 0

    # ──────────────────────────────────────────────────────────────────────────
    # 4. KBA — Key Biodiversity Area centroids within the buffer
    # ──────────────────────────────────────────────────────────────────────────
    kba_count_result = await db.execute(
        select(func.count()).select_from(Kba)
        .where(Kba.sit_lat.isnot(None))
        .where(Kba.sit_long.isnot(None))
        .where(Kba.sit_lat.between(min_lat, max_lat))
        .where(Kba.sit_long.between(min_lng, max_lng))
    )
    kba_count = kba_count_result.scalar() or 0

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
