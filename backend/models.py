"""
models.py

SQLAlchemy ORM table definitions.

Real tables already in the DB (read from DBeaver):
  species, kba, capad, ibra

App-managed tables (created by create_tables.py):
  suppliers  — Epic 1 supplier records
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    Text, DateTime,
)
from sqlalchemy.orm import DeclarativeBase
from geoalchemy2 import Geometry


class Base(DeclarativeBase):
    pass


# ── Supplier (app-managed) ────────────────────────────────────────────────────

class Supplier(Base):
    """
    Epic 1 supplier records extracted from uploaded files.
    Created/updated by the application — not a pre-existing table.
    """
    __tablename__ = "suppliers"

    id                   = Column(String,  primary_key=True)
    name                 = Column(String,  nullable=False)
    abn                  = Column(String,  nullable=True)
    address              = Column(String,  nullable=True)
    commodity            = Column(String,  nullable=True)
    region               = Column(String,  nullable=True)
    confidence_score     = Column(Integer, nullable=True)
    status               = Column(String,  nullable=False, default="pending")
    is_validated         = Column(Boolean, nullable=False, default=False)
    enriched_name        = Column(String,  nullable=True)
    enriched_address     = Column(String,  nullable=True)
    abr_status           = Column(String,  nullable=True)
    abn_found            = Column(Boolean, nullable=True)
    name_discrepancy     = Column(Boolean, nullable=True)
    address_discrepancy  = Column(Boolean, nullable=True)
    lat                  = Column(Float,   nullable=True)
    lng                  = Column(Float,   nullable=True)
    resolution_level     = Column(String,  nullable=True)
    inference_method     = Column(String,  nullable=True)
    file_name            = Column(String,  nullable=True)
    file_type            = Column(String,  nullable=True)
    warnings             = Column(Text,    nullable=True)  # pipe-separated list


# ── Species (pre-existing, read-only from the app) ───────────────────────────

class Species(Base):
    __tablename__ = "species"

    occurrence_id      = Column(String,  primary_key=True)
    decimallatitude    = Column(Float,   nullable=True)
    decimallongitude   = Column(Float,   nullable=True)
    scientificname     = Column(String,  nullable=True)
    vernacularname     = Column(String,  nullable=True)
    taxonconceptid     = Column(String,  nullable=True)
    kingdom            = Column(String,  nullable=True)
    occurrencestatus   = Column(String,  nullable=True)
    basisofrecord      = Column(String,  nullable=True)
    eventdate          = Column(String,  nullable=True)
    stateprovince      = Column(String,  nullable=True)
    dataresourcename   = Column(String,  nullable=True)
    is_obscured        = Column(Boolean, nullable=True)
    source_dataset     = Column(String,  nullable=True)
    ala_licence        = Column(String,  nullable=True)
    cleaned_at         = Column(DateTime(timezone=True), nullable=True)
    geom_wkt           = Column(Text,    nullable=True)
    geom               = Column(Text,    nullable=True)  # raw WKB — use geom_wkt for display


# ── Kba (pre-existing, read-only) ─────────────────────────────────────────────

class Kba(Base):
    __tablename__ = "kba"

    id            = Column(Integer, primary_key=True)
    sit_rec_id    = Column(Integer, nullable=True)
    region        = Column(String,  nullable=True)
    country       = Column(String,  nullable=True)
    iso3          = Column(String,  nullable=True)
    nat_name      = Column(String,  nullable=True)
    int_name      = Column(String,  nullable=True)
    sit_lat       = Column(Float,   nullable=True)
    sit_long      = Column(Float,   nullable=True)
    sit_area_km2  = Column(Float,   nullable=True)
    kba_status    = Column(String,  nullable=True)
    kba_class     = Column(String,  nullable=True)
    iba_status    = Column(String,  nullable=True)
    last_update   = Column(DateTime(timezone=True), nullable=True)
    source        = Column(String,  nullable=True)
    shape_leng    = Column(Float,   nullable=True)
    shape_area    = Column(Float,   nullable=True)
    geometry      = Column(Text,    nullable=True)
    geom          = Column(Text,    nullable=True)


# ── Capad (pre-existing — recreated by migrate_capad_shp.py) ─────────────────
#
#  All 29 shapefile columns are mapped here.
#  geom is a PostGIS MultiPolygon (SRID 4326), matching the ibra pattern.
#  geom_wkt holds the WKT string for frontend display.

class Capad(Base):
    __tablename__ = "capad"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    objectid        = Column(Integer, nullable=True, unique=True)
    pa_id           = Column(Text,    nullable=True)
    pa_pid          = Column(Text,    nullable=True)
    pa_name         = Column(Text,    nullable=True)
    pa_type         = Column(Text,    nullable=True)
    pa_type_abbr    = Column(Text,    nullable=True)
    iucn_cat        = Column(Text,    nullable=True)
    nrs_pa          = Column(Boolean, nullable=True)   # NRS_PA  Y/N -> bool
    nrs_mpa         = Column(Boolean, nullable=True)   # NRS_MPA Y/N -> bool
    gaz_area_ha     = Column(Float,   nullable=True)
    gis_area_ha     = Column(Float,   nullable=True)
    gaz_date        = Column(DateTime(timezone=True), nullable=True)
    latest_gaz      = Column(DateTime(timezone=True), nullable=True)
    state           = Column(Text,    nullable=True)
    authority       = Column(Text,    nullable=True)
    source_dataset  = Column(Text,    nullable=True)   # DATASOURCE
    governance      = Column(Text,    nullable=True)
    comments        = Column(Text,    nullable=True)
    environ         = Column(Text,    nullable=True)
    overlap         = Column(Text,    nullable=True)
    mgt_plan        = Column(Text,    nullable=True)
    res_number      = Column(Text,    nullable=True)
    zone_type       = Column(Text,    nullable=True)
    epbc_trigger    = Column(Text,    nullable=True)   # EPBC
    longitude       = Column(Float,   nullable=True)
    latitude        = Column(Float,   nullable=True)
    pa_system       = Column(Text,    nullable=True)
    shape_area      = Column(Float,   nullable=True)   # Shape__Are
    shape_len       = Column(Float,   nullable=True)   # Shape__Len
    capad_version   = Column(Text,    nullable=True)
    capad_citation  = Column(Text,    nullable=True)
    capad_licence   = Column(Text,    nullable=True)
    is_active       = Column(Boolean, nullable=True,   default=True)
    cleaned_at      = Column(DateTime(timezone=True),  nullable=True)
    geom_wkt        = Column(Text,    nullable=True)   # WKT string — frontend display
    geom            = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)  # PostGIS — spatial queries


# ── Ibra (pre-existing, read-only) ────────────────────────────────────────────

class Ibra(Base):
    """
    IBRA 7 bioregions.

    The geom column stores a PostGIS MULTIPOLYGON (SRID 4326) representing
    the exact boundary of each bioregion. Mapped as GeoAlchemy2 Geometry so
    SQLAlchemy can pass it directly to PostGIS functions (ST_Within,
    ST_Intersects) without raw SQL string construction.

    Previously mapped as Text, which returned a raw WKB hex string and made
    spatial queries impossible through the ORM.
    """
    __tablename__ = "ibra"

    id             = Column(Integer, primary_key=True)
    objectid       = Column(Integer, nullable=True)
    ibra_reg_name  = Column(String,  nullable=True)
    ibra_reg_code  = Column(String,  nullable=True)
    ibra_reg_num   = Column(Integer, nullable=True)
    state          = Column(String,  nullable=True)
    shape_area     = Column(Float,   nullable=True)
    shape_len      = Column(Float,   nullable=True)
    is_active      = Column(Boolean, nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=True)
    updated_at     = Column(DateTime(timezone=True), nullable=True)
    geometry       = Column(Text,    nullable=True)   # WKT string — for display only
    geom           = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)  # PostGIS — used for ST_Within
