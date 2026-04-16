-- =============================================================================
-- CAPAD 2024 – PostGIS spatial upgrade
-- Run AFTER migrate_capad.py has populated public.capad_protected_areas
-- =============================================================================

-- 1. Enable PostGIS extension (requires superuser on first run)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Add point geometry column (WGS84 / EPSG:4326)
ALTER TABLE public.capad_protected_areas
    ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);

-- 3. Populate from lat/lon
UPDATE public.capad_protected_areas
   SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
 WHERE longitude IS NOT NULL
   AND latitude  IS NOT NULL;

-- 4. Spatial index
CREATE INDEX IF NOT EXISTS idx_capad_geom
    ON public.capad_protected_areas USING GIST (geom);

-- 5. Verification
SELECT
    COUNT(*)                        AS total_rows,
    COUNT(geom)                     AS rows_with_geometry,
    ROUND(COUNT(geom)::numeric
        / NULLIF(COUNT(*), 0) * 100, 2) AS pct_geocoded
FROM public.capad_protected_areas;

-- =============================================================================
-- Example: find protected areas within 50 km of a supplier location
-- (Replace the coordinates with your supplier's lon/lat)
-- =============================================================================
-- SELECT
--     pa.name,
--     pa.pa_type,
--     pa.iucn_cat,
--     pa.state,
--     ROUND(ST_Distance(
--         pa.geom::geography,
--         ST_SetSRID(ST_MakePoint(151.2093, -33.8688), 4326)::geography
--     ) / 1000, 2) AS distance_km
-- FROM public.capad_protected_areas pa
-- WHERE ST_DWithin(
--     pa.geom::geography,
--     ST_SetSRID(ST_MakePoint(151.2093, -33.8688), 4326)::geography,
--     50000  -- metres
-- )
-- ORDER BY distance_km;
