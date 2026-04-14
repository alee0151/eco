"""
models.py

SQLAlchemy ORM table definitions mapped to the REAL tables
already present in the PostgreSQL / DBeaver database:

  - species   : species occurrence records (ALA / GBIF data)
  - kba       : Key Biodiversity Areas
  - capad     : Conservation and Protected Areas Database of Australia
  - ibra      : Interim Biogeographic Regionalisation for Australia

PostGIS system tables (spatial_ref_sys, geometry_columns, etc.)
are read-only views managed by PostGIS — not mapped here.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    Text, DateTime, BigInteger,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ── species ────────────────────────────────────────────────────────────────────

class Species(Base):
    """
    Species occurrence records sourced from ALA / GBIF.
    Each row is one sighting of a species at a location.
    """
    __tablename__ = "species"

    occurrence_id      = Column(String,  primary_key=True)
    decimallatitude    = Column(Float,   nullable=True)
    decimallongitude   = Column(Float,   nullable=True)
    scientificname     = Column(String,  nullable=True)
    vernacularname     = Column(String,  nullable=True)
    taxonconceptid     = Column(String,  nullable=True)
    kingdom            = Column(String,  nullable=True)
    occurrencestatus   = Column(String,  nullable=True)  # e.g. PRESENT / ABSENT
    basisofrecord      = Column(String,  nullable=True)  # e.g. HUMAN_OBSERVATION
    eventdate          = Column(String,  nullable=True)  # stored as text in source data
    stateprovince      = Column(String,  nullable=True)
    dataresourcename   = Column(String,  nullable=True)
    is_obscured        = Column(Boolean, nullable=True)
    source_dataset     = Column(String,  nullable=True)
    ala_licence        = Column(String,  nullable=True)
    cleaned_at         = Column(DateTime(timezone=True), nullable=True)
    geom_wkt           = Column(Text,    nullable=True)  # WKT geometry string
    geom               = Column(Text,    nullable=True)  # PostGIS geometry (raw)


# ── kba ──────────────────────────────────────────────────────────────────────

class Kba(Base):
    """
    Key Biodiversity Areas — internationally recognised sites
    critical for biodiversity conservation.
    """
    __tablename__ = "kba"

    id            = Column(Integer, primary_key=True)
    sit_rec_id    = Column(Integer, nullable=True)    # site record ID
    region        = Column(String,  nullable=True)
    country       = Column(String,  nullable=True)
    iso3          = Column(String,  nullable=True)    # ISO 3166-1 alpha-3
    nat_name      = Column(String,  nullable=True)    # national name
    int_name      = Column(String,  nullable=True)    # international name
    sit_lat       = Column(Float,   nullable=True)
    sit_long      = Column(Float,   nullable=True)
    sit_area_km2  = Column(Float,   nullable=True)
    kba_status    = Column(String,  nullable=True)    # e.g. "KBA"
    kba_class     = Column(String,  nullable=True)
    iba_status    = Column(String,  nullable=True)    # Important Bird Area status
    last_update   = Column(DateTime(timezone=True), nullable=True)
    source        = Column(String,  nullable=True)
    shape_leng    = Column(Float,   nullable=True)
    shape_area    = Column(Float,   nullable=True)
    geometry      = Column(Text,    nullable=True)    # WKT / GeoJSON text
    geom          = Column(Text,    nullable=True)    # PostGIS geometry


# ── capad ─────────────────────────────────────────────────────────────────────

class Capad(Base):
    """
    Conservation and Protected Areas Database of Australia.
    Contains every gazetted protected area in Australia.
    """
    __tablename__ = "capad"

    id                = Column(Integer, primary_key=True)
    objectid          = Column(Integer, nullable=True)
    pa_id             = Column(String,  nullable=True)   # protected area ID
    pa_name           = Column(String,  nullable=True)
    pa_type           = Column(String,  nullable=True)   # e.g. "National Park"
    pa_type_abbr      = Column(String,  nullable=True)
    iucn_cat          = Column(String,  nullable=True)   # IUCN category e.g. "II"
    nrs_pa            = Column(Boolean, nullable=True)   # in National Reserve System?
    gaz_area_ha       = Column(Float,   nullable=True)   # gazetted area (ha)
    gis_area_ha       = Column(Float,   nullable=True)   # GIS-calculated area (ha)
    state             = Column(String,  nullable=True)
    environ           = Column(String,  nullable=True)   # e.g. "Terrestrial"
    epbc_trigger      = Column(String,  nullable=True)
    latitude          = Column(Float,   nullable=True)
    longitude         = Column(Float,   nullable=True)
    latest_gaz        = Column(DateTime(timezone=True), nullable=True)
    pa_pid            = Column(String,  nullable=True)
    governance        = Column(String,  nullable=True)
    authority         = Column(String,  nullable=True)
    gaz_date          = Column(DateTime(timezone=True), nullable=True)
    effective_area_ha = Column(Float,   nullable=True)
    source_dataset    = Column(String,  nullable=True)
    capad_version     = Column(String,  nullable=True)
    capad_citation    = Column(String,  nullable=True)
    capad_licence     = Column(String,  nullable=True)
    cleaned_at        = Column(DateTime(timezone=True), nullable=True)
    is_active         = Column(Boolean, nullable=True)
    geom_wkt          = Column(Text,    nullable=True)
    geom              = Column(Text,    nullable=True)


# ── ibra ──────────────────────────────────────────────────────────────────────

class Ibra(Base):
    """
    Interim Biogeographic Regionalisation for Australia.
    Defines Australia's 89 bioregions and 419 sub-regions.
    Used to map supplier locations to bioregional context.
    """
    __tablename__ = "ibra"

    id           = Column(Integer, primary_key=True)
    objectid     = Column(Integer, nullable=True)
    ibra_reg_name = Column(String, nullable=True)   # e.g. "Brigalow Belt South"
    ibra_reg_code = Column(String, nullable=True)   # e.g. "BBS"
    ibra_reg_num  = Column(Integer, nullable=True)
    state         = Column(String, nullable=True)
    shape_area    = Column(Float,  nullable=True)
    shape_len     = Column(Float,  nullable=True)
    is_active     = Column(Boolean, nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=True)
    updated_at    = Column(DateTime(timezone=True), nullable=True)
    geometry      = Column(Text,   nullable=True)   # WKT / GeoJSON text
    geom          = Column(Text,   nullable=True)   # PostGIS geometry
