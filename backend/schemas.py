"""
schemas.py — Pydantic response models
"""

from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel


# ─── Supplier ─────────────────────────────────────────────────────────

class SupplierOut(BaseModel):
    """Full supplier row returned by GET /api/suppliers."""
    id:                   str
    name:                 str
    abn:                  Optional[str]   = None
    address:              Optional[str]   = None
    commodity:            Optional[str]   = None
    region:               Optional[str]   = None
    confidence_score:     Optional[int]   = None
    status:               str             = "pending"
    is_validated:         bool            = False
    enriched_name:        Optional[str]   = None
    enriched_address:     Optional[str]   = None
    abr_status:           Optional[str]   = None
    abn_found:            Optional[bool]  = None
    name_discrepancy:     Optional[bool]  = None
    address_discrepancy:  Optional[bool]  = None
    lat:                  Optional[float] = None
    lng:                  Optional[float] = None
    resolution_level:     Optional[str]   = None
    inference_method:     Optional[str]   = None
    file_name:            Optional[str]   = None
    file_type:            Optional[str]   = None
    warnings:             Optional[str]   = None

    class Config:
        from_attributes = True


class SupplierCreate(BaseModel):
    """Body for POST /api/suppliers."""
    id:                   str
    name:                 str
    abn:                  Optional[str]   = None
    address:              Optional[str]   = None
    commodity:            Optional[str]   = None
    region:               Optional[str]   = None
    confidence_score:     Optional[int]   = None
    status:               str             = "pending"
    is_validated:         bool            = False
    enriched_name:        Optional[str]   = None
    enriched_address:     Optional[str]   = None
    abr_status:           Optional[str]   = None
    abn_found:            Optional[bool]  = None
    name_discrepancy:     Optional[bool]  = None
    address_discrepancy:  Optional[bool]  = None
    lat:                  Optional[float] = None
    lng:                  Optional[float] = None
    resolution_level:     Optional[str]   = None
    inference_method:     Optional[str]   = None
    file_name:            Optional[str]   = None
    file_type:            Optional[str]   = None
    warnings:             Optional[str]   = None


class SupplierPatch(BaseModel):
    """Body for PATCH /api/suppliers/{id} — every field is optional."""
    name:                 Optional[str]   = None
    abn:                  Optional[str]   = None
    address:              Optional[str]   = None
    commodity:            Optional[str]   = None
    region:               Optional[str]   = None
    confidence_score:     Optional[int]   = None
    status:               Optional[str]   = None
    is_validated:         Optional[bool]  = None
    enriched_name:        Optional[str]   = None
    enriched_address:     Optional[str]   = None
    abr_status:           Optional[str]   = None
    abn_found:            Optional[bool]  = None
    name_discrepancy:     Optional[bool]  = None
    address_discrepancy:  Optional[bool]  = None
    lat:                  Optional[float] = None
    lng:                  Optional[float] = None
    resolution_level:     Optional[str]   = None
    inference_method:     Optional[str]   = None
    file_name:            Optional[str]   = None
    file_type:            Optional[str]   = None
    warnings:             Optional[str]   = None


# ─── Species ────────────────────────────────────────────────────────

class SpeciesOut(BaseModel):
    occurrence_id:    Optional[str]   = None
    decimallatitude:  Optional[float] = None
    decimallongitude: Optional[float] = None
    scientificname:   Optional[str]   = None
    vernacularname:   Optional[str]   = None
    taxonconceptid:   Optional[str]   = None
    kingdom:          Optional[str]   = None
    occurrencestatus: Optional[str]   = None
    basisofrecord:    Optional[str]   = None
    eventdate:        Optional[str]   = None
    stateprovince:    Optional[str]   = None
    dataresourcename: Optional[str]   = None
    is_obscured:      Optional[bool]  = None
    source_dataset:   Optional[str]   = None
    ala_licence:      Optional[str]   = None
    geom_wkt:         Optional[str]   = None

    class Config:
        from_attributes = True


# ─── KBA ──────────────────────────────────────────────────────────

class KbaOut(BaseModel):
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
    geometry:     Optional[str]   = None

    class Config:
        from_attributes = True


# ─── CAPAD ─────────────────────────────────────────────────────────

class CapadOut(BaseModel):
    id:                int
    pa_id:             Optional[str]   = None
    pa_name:           Optional[str]   = None
    pa_type:           Optional[str]   = None
    pa_type_abbr:      Optional[str]   = None
    iucn_cat:          Optional[str]   = None
    nrs_pa:            Optional[bool]  = None
    gaz_area_ha:       Optional[float] = None
    gis_area_ha:       Optional[float] = None
    state:             Optional[str]   = None
    environ:           Optional[str]   = None
    epbc_trigger:      Optional[str]   = None
    latitude:          Optional[float] = None
    longitude:         Optional[float] = None
    governance:        Optional[str]   = None
    authority:         Optional[str]   = None
    effective_area_ha: Optional[float] = None
    source_dataset:    Optional[str]   = None
    capad_version:     Optional[str]   = None
    is_active:         Optional[bool]  = None
    geom_wkt:          Optional[str]   = None

    class Config:
        from_attributes = True


# ─── IBRA ──────────────────────────────────────────────────────────

class IbraOut(BaseModel):
    id:            int
    ibra_reg_name: Optional[str]   = None
    ibra_reg_code: Optional[str]   = None
    ibra_reg_num:  Optional[int]   = None
    state:         Optional[str]   = None
    shape_area:    Optional[float] = None
    shape_len:     Optional[float] = None
    is_active:     Optional[bool]  = None
    geometry:      Optional[str]   = None

    class Config:
        from_attributes = True


# ─── Risk summary composites ─────────────────────────────────────

class CapadNearby(BaseModel):
    name:       str
    iucn_cat:   Optional[str]   = None
    pa_type:    Optional[str]   = None
    governance: Optional[str]   = None
    area_ha:    Optional[float] = None
    epbc:       Optional[str]   = None
    state:      Optional[str]   = None
    dist_km:    Optional[float] = None


class KbaNearby(BaseModel):
    name:     str
    class_:   Optional[str]   = None
    status:   Optional[str]   = None
    area_km2: Optional[float] = None
    dist_km:  Optional[float] = None


class SupplierRiskSummary(BaseModel):
    # identity
    supplier_id:   str
    supplier_name: str
    lat:           float
    lng:           float

    # IBRA
    ibra_region:    Optional[str]   = None
    ibra_code:      Optional[str]   = None
    ibra_area_km2:  Optional[float] = None

    # CAPAD
    protected_areas_nearby:  int = 0
    capad_nearby:            List[Any] = []
    iucn_distribution:       dict[str, int] = {}
    governance_distribution: dict[str, int] = {}
    epbc_triggered_count:    int = 0

    # KBA
    kba_nearby_count: int = 0
    kba_nearby:       List[Any] = []

    # Species
    species_nearby:           int = 0
    threatened_species_names: List[str] = []
    species_kingdoms:         List[str] = []
    threatened_from_dataset:  int = 0

    # Narrative
    assessment_notes: Optional[str] = None

    # Keep legacy alias so existing callers don't break
    @property
    def kba_nearby_int(self) -> int:
        return self.kba_nearby_count

    class Config:
        from_attributes = True
