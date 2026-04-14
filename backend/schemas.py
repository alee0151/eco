"""
schemas.py

Pydantic response schemas — what the API returns to the frontend.
These match the TypeScript interfaces in frontend/src/app/data/types.ts
and frontend/src/app/data/epic2-data.ts.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


# ── Epic 1 Schemas ────────────────────────────────────────────────────────────

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
    warnings:            Optional[str]  = None  # JSON string


class SupplierCreate(BaseModel):
    """Body accepted when saving an extracted supplier record."""
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


# ── Epic 2 Schemas ────────────────────────────────────────────────────────────

class ThreatenedSpeciesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    name:         str
    species_type: Optional[str] = None
    status:       Optional[str] = None


class BiodiversitySupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                       str
    name:                     str
    region:                   Optional[str]   = None
    lat:                      Optional[float] = None
    lng:                      Optional[float] = None
    risk_score:               Optional[int]   = None
    risk_level:               Optional[str]   = None
    protected_area_overlap:   Optional[float] = None
    threatened_species_count: Optional[int]   = None
    vegetation_condition:     Optional[float] = None
    deforestation_rate:       Optional[float] = None
    water_stress_index:       Optional[float] = None
    carbon_stock:             Optional[float] = None
    last_assessment:          Optional[str]   = None
    industry:                 Optional[str]   = None
    notes:                    Optional[str]   = None
    threatened_species:       List[ThreatenedSpeciesOut] = []
