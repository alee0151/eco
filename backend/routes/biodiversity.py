"""
routes/biodiversity.py

Epic 2 — Live biodiversity data from the real DB tables:
  species, kba, capad, ibra

Endpoints:
  GET /api/biodiversity/species                 — species occurrences (paginated)
  GET /api/biodiversity/species/by-bbox         — species within a bounding box
  GET /api/biodiversity/kba                     — Key Biodiversity Areas (paginated)
  GET /api/biodiversity/capad                   — Protected areas (paginated)
  GET /api/biodiversity/capad/regions           — Protected area polygons (geom_wkt)
  GET /api/biodiversity/capad/regions/by-bbox   — Protected area polygons within a bounding box
  GET /api/biodiversity/capad/by-state/{state}  — Protected areas filtered by state
  GET /api/biodiversity/ibra                    — IBRA bioregions
  GET /api/biodiversity/ibra/{code}             — Single IBRA region by code
  GET /api/biodiversity/counts                  — Real DB row counts for stat cards
  GET /api/biodiversity/risk-summary            — Detailed risk summary for a supplier lat/lng
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional, List

from database import get_db
from models import Species, Kba, Capad, Ibra
from schemas import SpeciesOut, KbaOut, CapadOut, IbraOut, SupplierRiskSummary

router = APIRouter()

DEFAULT_BUFFER_DEG = 0.5

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


# ── Species ────────────────────────────────────────────────────────────────

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
        .limit(limit)
    )
    result = await db.execute(q)
    return result.scalars().all()


# ── KBA ────────────────────────────────────────────────────────────────────

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


# ── CAPAD ──────────────────────────────────────────────────────────────────

@router.get("/biodiversity/capad", response_model=List[CapadOut])
async def list_capad(
    limit:     int            = Query(200, ge=1, le=2000),
    offset:    int            = Query(0,   ge=0),
    state:     Optional[str]  = Query(None),
    pa_type:   Optional[str]  = Query(None),
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


@router.get("/biodiversity/capad/regions/by-bbox")
async def capad_regions_by_bbox(
    min_lat: float = Query(...),
    max_lat: float = Query(...),
    min_lng: float = Query(...),
    max_lng: float = Query(...),
    limit:   int   = Query(2000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(
            Capad.id, Capad.pa_id, Capad.pa_name, Capad.pa_type,
            Capad.pa_type_abbr, Capad.iucn_cat, Capad.state,
            Capad.gis_area_ha, Capad.governance, Capad.authority,
            Capad.epbc_trigger, Capad.geom_wkt,
        )
        .where(Capad.geom_wkt.isnot(None))
        .where(Capad.is_active == True)       # noqa: E712
        .where(Capad.latitude.isnot(None))
        .where(Capad.longitude.isnot(None))
        .where(Capad.latitude.between(min_lat, max_lat))
        .where(Capad.longitude.between(min_lng, max_lng))
        .order_by(Capad.gis_area_ha.desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).mappings().all()
    return [dict(r) for r in rows]


@router.get("/biodiversity/capad/regions")
async def capad_regions(
    state:  Optional[str] = Query(None),
    limit:  int           = Query(2000, ge=1, le=5000),
    offset: int           = Query(0,   ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(
            Capad.id, Capad.pa_id, Capad.pa_name, Capad.pa_type,
            Capad.pa_type_abbr, Capad.iucn_cat, Capad.state,
            Capad.gis_area_ha, Capad.governance, Capad.authority,
            Capad.epbc_trigger, Capad.geom_wkt,
        )
        .where(Capad.geom_wkt.isnot(None))
        .where(Capad.is_active == True)       # noqa: E712
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
        .where(Capad.is_active == True)       # noqa: E712
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


# ── IBRA ───────────────────────────────────────────────────────────────────

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


# ── DB counts ──────────────────────────────────────────────────────────────

@router.get("/biodiversity/counts")
async def biodiversity_counts(db: AsyncSession = Depends(get_db)):
    capad_res   = await db.execute(
        select(func.count()).select_from(Capad)
        .where(Capad.is_active == True)       # noqa: E712
    )
    kba_res     = await db.execute(
        select(func.count()).select_from(Kba)
    )
    species_res = await db.execute(
        select(func.count()).select_from(Species)
    )
    return {
        "capad_active":  capad_res.scalar()   or 0,
        "kba_total":     kba_res.scalar()     or 0,
        "species_total": species_res.scalar() or 0,
    }


# ── Risk Summary ───────────────────────────────────────────────────────────

@router.get("/biodiversity/risk-summary", response_model=SupplierRiskSummary)
async def risk_summary(
    supplier_id:   str   = Query(...),
    supplier_name: str   = Query(...),
    lat:           float = Query(...),
    lng:           float = Query(...),
    buffer_deg:    float = Query(DEFAULT_BUFFER_DEG),
    db: AsyncSession = Depends(get_db),
):
    min_lat = lat - buffer_deg
    max_lat = lat + buffer_deg
    min_lng = lng - buffer_deg
    max_lng = lng + buffer_deg

    # ── 1. IBRA nearest region ─────────────────────────────────────────────
    ibra_row = (
        await db.execute(
            text("""
                SELECT ibra_reg_name, ibra_reg_code, shape_area
                FROM   ibra
                WHERE  geom IS NOT NULL
                ORDER  BY geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                LIMIT  1
            """),
            {"lng": lng, "lat": lat},
        )
    ).first()
    ibra_name       = ibra_row[0] if ibra_row else None
    ibra_code       = ibra_row[1] if ibra_row else None
    ibra_area_km2   = round(float(ibra_row[2]) / 1_000_000, 0) if (ibra_row and ibra_row[2]) else None

    # ── 2. Species — count distinct threatened taxa ────────────────────────
    # Strategy: bbox filter on lat/lng columns only, NO basisofrecord or
    # dataresourcename filter so we don't miss records stored with
    # different capitalisation or dataset names in the local DB.
    # We deduplicate on taxonconceptid so one species sighted many times
    # counts once.
    species_row = (
        await db.execute(
            text("""
                WITH nearby AS (
                    SELECT
                        COALESCE(taxonconceptid, occurrence_id::text)   AS taxon_key,
                        COALESCE(
                            NULLIF(TRIM(vernacularname), ''),
                            NULLIF(TRIM(scientificname), ''),
                            'Unknown'
                        )                                               AS display_name,
                        kingdom,
                        dataresourcename
                    FROM   species
                    WHERE  decimallatitude  IS NOT NULL
                      AND  decimallongitude IS NOT NULL
                      AND  decimallatitude  BETWEEN :min_lat AND :max_lat
                      AND  decimallongitude BETWEEN :min_lng AND :max_lng
                ),
                deduped AS (
                    SELECT DISTINCT ON (taxon_key)
                        taxon_key,
                        display_name,
                        kingdom,
                        dataresourcename
                    FROM   nearby
                    ORDER  BY taxon_key, display_name
                )
                SELECT
                    COUNT(*)                                                          AS species_count,
                    ARRAY_AGG(display_name ORDER BY display_name)
                        FILTER (WHERE display_name IS NOT NULL)                      AS names,
                    ARRAY_AGG(DISTINCT kingdom)
                        FILTER (WHERE kingdom IS NOT NULL)                           AS kingdoms,
                    COUNT(*) FILTER (
                        WHERE dataresourcename ILIKE '%%threatened%%'
                           OR dataresourcename ILIKE '%%sensitive%%'
                           OR dataresourcename ILIKE '%%epbc%%'
                           OR dataresourcename ILIKE '%%conservation%%'
                    )                                                                 AS threatened_from_dataset
                FROM deduped
            """),
            {"min_lat": min_lat, "max_lat": max_lat,
             "min_lng": min_lng, "max_lng": max_lng},
        )
    ).first()

    species_count   = int(species_row[0] or 0)        if species_row else 0
    species_names   = list((species_row[1] or [])[:20]) if species_row else []
    species_kingdoms = list((species_row[2] or []))   if species_row else []
    threatened_ds   = int(species_row[3] or 0)        if species_row else 0

    # ── 3. CAPAD nearby — also collect IUCN + governance breakdown ─────────
    capad_detail_rows = (
        await db.execute(
            text("""
                SELECT
                    pa_name,
                    iucn_cat,
                    pa_type,
                    governance,
                    gis_area_ha,
                    epbc_trigger,
                    state,
                    SQRT(
                        POWER(latitude  - :lat, 2) +
                        POWER(longitude - :lng, 2)
                    ) * 111.0 AS dist_km
                FROM  capad
                WHERE is_active = TRUE
                  AND latitude   IS NOT NULL
                  AND longitude  IS NOT NULL
                  AND latitude   BETWEEN :min_lat AND :max_lat
                  AND longitude  BETWEEN :min_lng AND :max_lng
                ORDER BY dist_km ASC
                LIMIT 50
            """),
            {"lat": lat, "lng": lng,
             "min_lat": min_lat, "max_lat": max_lat,
             "min_lng": min_lng, "max_lng": max_lng},
        )
    ).fetchall()

    capad_count = len(capad_detail_rows)

    # Nearest 5 protected areas with detail
    capad_nearby: list[dict] = [
        {
            "name":        row[0] or "Unknown",
            "iucn_cat":    row[1] or "Not Reported",
            "pa_type":     row[2] or "",
            "governance":  row[3] or "",
            "area_ha":     round(float(row[4]), 0) if row[4] else None,
            "epbc":        row[5] or "",
            "state":       row[6] or "",
            "dist_km":     round(float(row[7]), 1) if row[7] else None,
        }
        for row in capad_detail_rows[:5]
    ]

    # IUCN category distribution
    from collections import Counter
    iucn_counts = dict(Counter(
        r[1] or "Not Reported" for r in capad_detail_rows
    ))

    # Governance distribution
    gov_counts = dict(Counter(
        r[3] or "Unknown" for r in capad_detail_rows
    ))

    # EPBC-triggered count
    epbc_count = sum(
        1 for r in capad_detail_rows if r[5] and r[5].strip().upper() == "YES"
    )

    # ── 4. KBAs ────────────────────────────────────────────────────────────
    kba_detail_rows = (
        await db.execute(
            text("""
                SELECT
                    COALESCE(int_name, nat_name, 'KBA')   AS kba_name,
                    kba_class,
                    kba_status,
                    sit_area_km2,
                    SQRT(
                        POWER(sit_lat  - :lat, 2) +
                        POWER(sit_long - :lng, 2)
                    ) * 111.0 AS dist_km
                FROM  kba
                WHERE sit_lat  IS NOT NULL
                  AND sit_long IS NOT NULL
                  AND sit_lat  BETWEEN :min_lat AND :max_lat
                  AND sit_long BETWEEN :min_lng AND :max_lng
                ORDER BY dist_km ASC
                LIMIT 10
            """),
            {"lat": lat, "lng": lng,
             "min_lat": min_lat, "max_lat": max_lat,
             "min_lng": min_lng, "max_lng": max_lng},
        )
    ).fetchall()

    kba_count = len(kba_detail_rows)
    kba_nearby: list[dict] = [
        {
            "name":     row[0],
            "class":    row[1] or "",
            "status":   row[2] or "",
            "area_km2": round(float(row[3]), 1) if row[3] else None,
            "dist_km":  round(float(row[4]), 1) if row[4] else None,
        }
        for row in kba_detail_rows[:5]
    ]

    # ── 5. Build assessment notes ──────────────────────────────────────────
    notes_parts: list[str] = []
    if ibra_name:
        area_str = f" ({int(ibra_area_km2):,} km²)" if ibra_area_km2 else ""
        notes_parts.append(f"Located within the {ibra_name}{area_str} IBRA bioregion.")
    if capad_count:
        pa_word = "protected area" if capad_count == 1 else "protected areas"
        notes_parts.append(
            f"{capad_count} {pa_word} found within {round(buffer_deg * 111)} km."
            + (f" {epbc_count} trigger EPBC Act provisions." if epbc_count else "")
        )
    if kba_count:
        kba_word = "Key Biodiversity Area" if kba_count == 1 else "Key Biodiversity Areas"
        notes_parts.append(f"{kba_count} {kba_word} in proximity.")
    if species_count:
        notes_parts.append(
            f"{species_count} species occurrence{'s' if species_count != 1 else ''} recorded nearby"
            + (f", including {threatened_ds} from conservation-priority datasets." if threatened_ds else ".")
        )
    if not notes_parts:
        notes_parts.append("No significant biodiversity features detected in the immediate vicinity.")

    assessment_notes = " ".join(notes_parts)

    return SupplierRiskSummary(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        lat=lat,
        lng=lng,
        ibra_region=ibra_name,
        ibra_code=ibra_code,
        ibra_area_km2=ibra_area_km2,
        protected_areas_nearby=capad_count,
        capad_nearby=capad_nearby,
        iucn_distribution=iucn_counts,
        governance_distribution=gov_counts,
        epbc_triggered_count=epbc_count,
        kba_nearby_count=kba_count,
        kba_nearby=kba_nearby,
        species_nearby=species_count,
        threatened_species_names=species_names,
        species_kingdoms=species_kingdoms,
        threatened_from_dataset=threatened_ds,
        assessment_notes=assessment_notes,
    )
