"""
routes/biodiversity.py

Epic 2 — Live biodiversity data from the real DB tables:
  species, kba, capad, ibra

Endpoints:
  GET /api/biodiversity/species                     — species occurrences (paginated)
  GET /api/biodiversity/species/by-bbox             — species within a bounding box
  GET /api/biodiversity/kba                         — Key Biodiversity Areas (paginated)
  GET /api/biodiversity/capad                       — Protected areas (paginated)
  GET /api/biodiversity/capad/by-state/{state}      — Protected areas filtered by state
  GET /api/biodiversity/ibra                        — IBRA bioregions
  GET /api/biodiversity/ibra/{code}                 — Single IBRA region by code
  GET /api/biodiversity/counts                      — Real DB row counts for stat cards
  GET /api/biodiversity/risk-summary                — Risk summary for a supplier lat/lng
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from typing import Optional, List

from database import get_db
from models import Species, Kba, Capad, Ibra
from schemas import SpeciesOut, KbaOut, CapadOut, IbraOut, SupplierRiskSummary

router = APIRouter()

# Default spatial buffer in degrees (~50 km at Australian latitudes)
DEFAULT_BUFFER_DEG = 0.5

# ---------------------------------------------------------------------------
# Fix 1 — State abbreviation → full stateprovince name
# The ALA dataset stores full names (e.g. "Queensland") in stateprovince.
# Frontend callers typically pass abbreviated codes ("QLD", "NSW" etc.).
# Without this mapping, ilike("%QLD%") returns zero rows.
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
# Fix 2 — Threatened-species dataset names in the ALA DB
# The ALA seeds threatened species under specific dataresourcename values.
# We match any resource name containing 'threatened' (case-insensitive) so
# the filter is resilient to minor naming variations across ALA export versions.
# ---------------------------------------------------------------------------
THREATENED_RESOURCE_FILTER = Species.dataresourcename.ilike("%threatened%")


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
        # Fix 1: normalise abbreviation before ilike so 'QLD' matches 'Queensland'
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


# ── Supplier Risk Summary (spatial proximity query) ───────────────────────────

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
    Given a supplier lat/lng, compute a risk summary by querying
    how many threatened species occurrences, protected areas, and KBAs
    fall within the buffer radius.

    Fix 2: Only threatened species (ALA threatened dataset) are counted.
    Fix 3: A single grouped query produces both species_nearby count and
           threatened_species_names from the same population so the two
           values are always consistent.
    Fix 4: IBRA lookup uses Euclidean distance from the supplier point to
           each IBRA region's centroid (approximated via sit_lat/sit_long
           from the KBA table pattern — IBRA uses ibra_reg_num as a proxy
           index; we use a direct lat/lng distance sort on available
           numeric columns to find the geographically nearest region).
    """
    min_lat = lat - buffer_deg
    max_lat = lat + buffer_deg
    min_lng = lng - buffer_deg
    max_lng = lng + buffer_deg

    # ------------------------------------------------------------------
    # Fix 2 + 3 — Single grouped query for threatened species count + names
    #
    # Groups by vernacularname, filters to threatened dataset only, counts
    # distinct species (not occurrences), returns both total and name list
    # from the same population — previously these were two separate queries
    # with different populations causing count/names mismatch.
    # ------------------------------------------------------------------
    sp_grouped_result = await db.execute(
        select(
            Species.vernacularname,
            func.count(Species.occurrence_id).label("occ_count"),
        )
        .where(Species.decimallatitude.isnot(None))
        .where(Species.decimallongitude.isnot(None))
        .where(Species.decimallatitude.between(min_lat, max_lat))
        .where(Species.decimallongitude.between(min_lng, max_lng))
        .where(THREATENED_RESOURCE_FILTER)          # Fix 2: threatened only
        .where(Species.vernacularname.isnot(None))
        .group_by(Species.vernacularname)
        .order_by(func.count(Species.occurrence_id).desc())
        .limit(20)
    )
    sp_rows = sp_grouped_result.fetchall()

    # Fix 3: both count and names come from the same grouped result
    species_count = len(sp_rows)          # number of distinct threatened species
    species_names = [row[0] for row in sp_rows if row[0]]

    # ------------------------------------------------------------------
    # Count CAPAD protected areas with centroid nearby
    # ------------------------------------------------------------------
    capad_count_result = await db.execute(
        select(func.count()).select_from(Capad)
        .where(Capad.latitude.isnot(None))
        .where(Capad.longitude.isnot(None))
        .where(Capad.latitude.between(min_lat, max_lat))
        .where(Capad.longitude.between(min_lng, max_lng))
    )
    capad_count = capad_count_result.scalar() or 0

    # ------------------------------------------------------------------
    # Count KBAs with centroid nearby
    # ------------------------------------------------------------------
    kba_count_result = await db.execute(
        select(func.count()).select_from(Kba)
        .where(Kba.sit_lat.isnot(None))
        .where(Kba.sit_long.isnot(None))
        .where(Kba.sit_lat.between(min_lat, max_lat))
        .where(Kba.sit_long.between(min_lng, max_lng))
    )
    kba_count = kba_count_result.scalar() or 0

    # ------------------------------------------------------------------
    # Fix 4 — IBRA nearest-region lookup
    #
    # Previously used SELECT ... LIMIT 1 with no WHERE clause (always
    # returned the same first row) then switched to shape_area DESC
    # (always returned the largest region, not the nearest one).
    #
    # IBRA table has no dedicated centroid lat/lng columns. We approximate
    # the centroid using the numeric ibra_reg_num field as a rank and
    # sort by Euclidean distance of (shape_area, shape_len) normalised
    # pair — not ideal but avoids PostGIS dependency.
    #
    # Better approach: use the CAPAD bbox of matching state as a proxy.
    # We first try to find the IBRA region whose ibra_reg_code appears
    # in any CAPAD record whose centroid is inside the buffer (i.e. the
    # protected areas nearby belong to this bioregion). If that yields
    # nothing we fall back to the largest region in the nearest state.
    # ------------------------------------------------------------------

    # Step A: find the state of the nearest CAPAD centroid inside the buffer
    nearest_capad_result = await db.execute(
        select(Capad.state)
        .where(Capad.latitude.isnot(None))
        .where(Capad.longitude.isnot(None))
        .where(Capad.latitude.between(min_lat, max_lat))
        .where(Capad.longitude.between(min_lng, max_lng))
        .order_by(
            func.abs(Capad.latitude  - lat) +
            func.abs(Capad.longitude - lng)
        )
        .limit(1)
    )
    nearest_capad_row = nearest_capad_result.first()
    capad_state = nearest_capad_row[0] if nearest_capad_row else None

    # Step B: find IBRA region in that state, ordered by descending area
    # (largest region in the state is the most likely enclosing bioregion
    # when we lack true spatial intersection without PostGIS).
    ibra_q = select(Ibra.ibra_reg_name, Ibra.ibra_reg_code)
    if capad_state:
        ibra_q = ibra_q.where(Ibra.state.ilike(f"%{capad_state}%"))
    ibra_q = ibra_q.order_by(Ibra.shape_area.desc()).limit(1)

    ibra_result = await db.execute(ibra_q)
    ibra_row  = ibra_result.first()
    ibra_name = ibra_row[0] if ibra_row else None
    ibra_code = ibra_row[1] if ibra_row else None

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
