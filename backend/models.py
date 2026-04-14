"""
models.py

SQLAlchemy ORM table definitions.
These must match the tables you created in DBeaver / PostgreSQL.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    Text, DateTime, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class SupplierStatus(str, enum.Enum):
    pending   = "pending"
    validated = "validated"
    approved  = "approved"
    rejected  = "rejected"


class RiskLevel(str, enum.Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


class SpeciesType(str, enum.Enum):
    mammal    = "mammal"
    bird      = "bird"
    reptile   = "reptile"
    amphibian = "amphibian"
    plant     = "plant"
    insect    = "insect"


class SpeciesStatus(str, enum.Enum):
    critically_endangered = "critically_endangered"
    endangered            = "endangered"
    vulnerable            = "vulnerable"


# ── Epic 1 — Supplier (document-extracted) ────────────────────────────────────

class Supplier(Base):
    """
    Mirrors the `suppliers` table.
    Populated when the /api/extract endpoint processes a document
    and the user approves the extracted data.
    """
    __tablename__ = "suppliers"

    id               = Column(String(20),  primary_key=True)          # e.g. SUP-001
    name             = Column(String(255), nullable=False)
    abn              = Column(String(20),  nullable=True)
    address          = Column(Text,        nullable=True)
    commodity        = Column(String(100), nullable=True)
    region           = Column(String(100), nullable=True)
    confidence_score = Column(Integer,     nullable=True)              # 0-100
    status           = Column(
        SAEnum(SupplierStatus, name="supplier_status"),
        nullable=False,
        default=SupplierStatus.pending,
    )
    is_validated       = Column(Boolean,   default=False)
    enriched_name      = Column(String(255), nullable=True)
    enriched_address   = Column(Text,        nullable=True)
    abr_status         = Column(String(50),  nullable=True)
    abn_found          = Column(Boolean,     nullable=True)
    name_discrepancy   = Column(Boolean,     nullable=True)
    address_discrepancy = Column(Boolean,    nullable=True)
    lat                = Column(Float,       nullable=True)
    lng                = Column(Float,       nullable=True)
    resolution_level   = Column(String(20),  nullable=True)
    inference_method   = Column(String(50),  nullable=True)
    file_name          = Column(String(255), nullable=True)
    file_type          = Column(String(10),  nullable=True)
    warnings           = Column(Text,        nullable=True)  # JSON array stored as text
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), onupdate=func.now())


# ── Epic 2 — Biodiversity / Environmental risk ────────────────────────────────

class BiodiversitySupplier(Base):
    """
    Mirrors the `biodiversity_suppliers` table.
    Stores environmental risk metrics per supplier/site.
    """
    __tablename__ = "biodiversity_suppliers"

    id                       = Column(String(20),  primary_key=True)  # e.g. SUP-001
    name                     = Column(String(255), nullable=False)
    region                   = Column(String(100), nullable=True)
    lat                      = Column(Float,       nullable=True)
    lng                      = Column(Float,       nullable=True)
    risk_score               = Column(Integer,     nullable=True)     # 0-100
    risk_level               = Column(
        SAEnum(RiskLevel, name="risk_level"),
        nullable=True,
    )
    protected_area_overlap   = Column(Float,  nullable=True)          # %
    threatened_species_count = Column(Integer, nullable=True)
    vegetation_condition     = Column(Float,  nullable=True)          # 0-100
    deforestation_rate       = Column(Float,  nullable=True)          # % per year
    water_stress_index       = Column(Float,  nullable=True)          # 0-100
    carbon_stock             = Column(Float,  nullable=True)          # tonnes/ha
    last_assessment          = Column(String(20), nullable=True)      # ISO date
    industry                 = Column(String(100), nullable=True)
    notes                    = Column(Text, nullable=True)

    # One-to-many: each site can have multiple threatened species records
    threatened_species = relationship(
        "ThreatenedSpecies",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )


class ThreatenedSpecies(Base):
    """
    Mirrors the `threatened_species` table.
    Each row is one species observed at a supplier/site.
    """
    __tablename__ = "threatened_species"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(String(20), ForeignKey("biodiversity_suppliers.id"), nullable=False)
    name        = Column(String(255), nullable=False)
    species_type = Column(
        SAEnum(SpeciesType, name="species_type"),
        nullable=True,
    )
    status      = Column(
        SAEnum(SpeciesStatus, name="species_status"),
        nullable=True,
    )

    supplier = relationship("BiodiversitySupplier", back_populates="threatened_species")
