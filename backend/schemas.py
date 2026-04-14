"""
schemas.py

Pydantic response schemas for the real DB tables:
  species, kba, capad, ibra

Also keeps the Epic 1 Supplier schemas used by routes/suppliers.py.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


# ── species ────────────────────────────────────────────────────────────────────

class SpeciesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    occurrence_id:    str
    decimallatitude:  Optional[float]  = None
    decimallongitude: Optional[float]  = None
    scientificname:   Optional[str]    = None
    vernacularname:   Optional[str]    = None
    taxonconceptid:   Optional[str]    = None
    kingdom:          Optional[str]    = None
    occurrencestatus: Optional[str]    = None
    basisofrecord:    Optional[str]    = None
    eventdate:        Optional[str]    = None
    stateprovince:    Optional[str]    = None
    dataresourcename: Optional[str]    = None
    is_obscured:      Optional[bool]   = None
    source_dataset:   Optional[str]    = None
    ala_licence:      Optional[str]    = None
    geom_wkt:         Optional[str]    = None


# ── kba ──────────────────────────────────────────────────────────────────────

class KbaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    sit_rec_id:   Optional[int]   = None
    region:       Optional[str]   = None
    country:      Optional[str]   = None
    iso3:         Optional[str]   = None
    nat_name:     Optional[str]   = None
    int_name:     Optional[str]   = None
    sit_lat:      Optional[float] = None
    sit_long:     Optional[float] = None
    sit_area_km2: Optional[float] = None
    kba_status:   Optional[str]   = None
    kba_class:    Optional[str]   = None
    iba_status:   Optional[str]   = None
    source:       Optional[str]   = None
    shape_area:   Optional[float] = None
    geometry:     Optional[str]   = None  # WKT for frontend mapping


# ── capad ─────────────────────────────────────────────────────────────────────

class CapadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    pa_id:            Optional[str]   = None
    pa_name:          Optional[str]   = None
    pa_type:          Optional[str]   = None
    pa_type_abbr:     Optional[str]   = None
    iucn_cat:         Optional[str]   = None
    nrs_pa:           Optional[bool]  = None
    gaz_area_ha:      Optional[float] = None
    gis_area_ha:      Optional[float] = None
    state:            Optional[str]   = None
    environ:          Optional[str]   = None
    epbc_trigger:     Optional[str]   = None
    latitude:         Optional[float] = None
    longitude:        Optional[float] = None
    governance:       Optional[str]   = None
    authority:        Optional[str]   = None
    effective_area_ha: Optional[float] = None
    source_dataset:   Optional[str]   = None
    capad_version:    Optional[str]   = None
    is_active:        Optional[bool]  = None
    geom_wkt:         Optional[str]   = None  # WKT for frontend mapping


# ── ibra ──────────────────────────────────────────────────────────────────────

class IbraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             int
    ibra_reg_name:  Optional[str]   = None
    ibra_reg_code:  Optional[str]   = None
    ibra_reg_num:   Optional[int]   = None
    state:          Optional[str]   = None
    shape_area:     Optional[float] = None
    shape_len:      Optional[float] = None
    is_active:      Optional[bool]  = None
    geometry:       Optional[str]   = None  # WKT for frontend mapping


# ── Supplier risk summary — joins real GIS data to a supplier location ──────
# Used by Epic 2 risk profile panel (replaces mock epic2-data.ts)

class SupplierRiskSummary(BaseModel):
    """
    Computed risk profile for a supplier lat/lng against real DB data.

    species_nearby counts only distinct threatened species (Fix 2+3).
    threatened_species_names is sourced from the same query as species_nearby
    so the count and list are always consistent (Fix 3).
    """
    supplier_id:              str
    supplier_name:            str
    lat:                      float
    lng:                      float
    ibra_region:              Optional[str]  = None
    ibra_code:                Optional[str]  = None
    protected_areas_nearby:   int            = 0
    kba_nearby:               int            = 0
    species_nearby:           int            = 0   # distinct threatened species, not raw occurrence count
    threatened_species_names: List[str]      = []


# ── Epic 1 Supplier schemas (unchanged) ───────────────────────────────────────

class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                  str
    name:                str
    abn:                 Optional[str]  = None
    address:             Optional[str]  = None
    commodity:           Optional[str]  = None
    region:              Optional[str]  = None
    confidence_score:    Optional[int]  = None
    status:              str
    is_validated:        bool
    enriched_name:       Optional[str]  = None
    enriched_address:    Optional[str]  = None
    abr_status:          Optional[str]  = None
    abn_found:           Optional[bool] = None
    name_discrepancy:    Optional[bool] = None
    address_discrepancy: Optional[bool] = None
    lat:                 Optional[float] = None
    lng:                 Optional[float] = None
    resolution_level:    Optional[str]  = None
    inference_method:    Optional[str]  = None
    file_name:           Optional[str]  = None
    file_type:           Optional[str]  = None
    warnings:            Optional[str]  = None


class SupplierCreate(BaseModel):
    id:               str
    name:             str
    abn:              Optional[str]  = None
    address:          Optional[str]  = None
    commodity:        Optional[str]  = None
    region:           Optional[str]  = None
    confidence_score: Optional[int]  = None
    status:           str            = "pending"
    file_name:        Optional[str]  = None
    file_type:        Optional[str]  = None
    warnings:         Optional[str]  = None
