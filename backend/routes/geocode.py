"""
routes/geocode.py  —  POST /api/geocode

Geocodes a supplier address using the Geoscape Address Geocoder v2 API,
backed by the official Australian G-NAF (Geocoded National Address File).

API docs: https://docs.geoscape.com.au/docs/geocoder

Request body
------------
{
  "address":  "441 St Kilda Road, Melbourne VIC 3004, Australia",  # formatted string
  "street":   "441 St Kilda Road",   # from LLM parser
  "suburb":   "Melbourne",
  "state":    "VIC",
  "postcode": "3004"
}

Formatted address canonical form (used for all geocoding queries):
  "[unit ]street, suburb state postcode, Australia"
  e.g. "441 St Kilda Road, Melbourne VIC 3004, Australia"

Query priority inside the endpoint:
  1. Full formatted string   (street + suburb + state + postcode + country)
  2. Structured components   (street, suburb state postcode)
  3. Suburb + state + postcode  (coarse fallback)
  4. Australia centre  (last resort — no state centroid)

Fallback chain:
  Geoscape G-NAF v2  →  Nominatim OSM  →  Australia centre

Environment variables
---------------------
GEOSCAPE_API_KEY   Geoscape API key (Bearer token).  Free tier: 1,000 calls/month.
                   Register at https://geoscape.com.au/geoscape-developer-centre/
                   If unset, falls back to Nominatim automatically.

v2 API response shape (GeoJSON FeatureCollection):
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lng, lat] },
      "properties": {
        "addressId": "GAACT717940975",
        "formattedAddress": "113 CANBERRA AV, GRIFFITH ACT 2603",
        "geoFeature": "FRONTAGE CENTRE SETBACK",
        "stateTerritory": "ACT",
        "postcode": "2603",
        ...
      },
      "matchType": "Primary Address",
      "matchQuality": "Exact",
      "matchScore": 100
    }
  ],
  "query": "...",
  "parsedQuery": { ... }
}
"""

import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Config ────────────────────────────────────────────────────────────────────

GEOSCAPE_BASE_V2 = "https://api.psma.com.au/v2/addresses/geocoder"

AUS_CENTRE = (-25.2744, 133.7751)

# geoFeature values that indicate property-level precision
_PROPERTY_GEO_FEATURES = {
    "PROPERTY CENTROID",
    "FRONTAGE CENTRE SETBACK",
    "BUILDING CENTROID",
    "PARCEL",
    "UNIT",
    "LOCALITY",
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class GeocodeRequest(BaseModel):
    address:  str = ""   # canonical formatted string: street, suburb state postcode, Australia
    street:   str = ""   # from LLM parser
    suburb:   str = ""   # from LLM parser
    state:    str = ""   # from LLM parser: NSW / VIC / ...
    postcode: str = ""   # from LLM parser


class GeocodeResponse(BaseModel):
    lat:              float
    lng:              float
    gnaf_pid:         str  = ""
    confidence:       int  = 0
    resolution_level: str  = "unknown"   # facility | regional | unknown
    inference_method: str  = "unknown"
    display_address:  str  = ""
    source:           str  = "unknown"   # geoscape | nominatim | centroid


# ── Address query builder ─────────────────────────────────────────────────────

def _build_structured_query(street: str, suburb: str, state: str, postcode: str) -> str:
    """
    Build a clean structured geocoding query from LLM-parsed components.

    Format: "street, suburb state postcode, Australia"

    Examples:
      street="441 St Kilda Road", suburb="Melbourne", state="VIC", postcode="3004"
        → "441 St Kilda Road, Melbourne VIC 3004, Australia"

      suburb="Cooma", state="NSW", postcode="2630"  (no street)
        → "Cooma NSW 2630, Australia"

      state="VIC"  (only state)
        → "VIC, Australia"
    """
    street_part   = street.strip()
    locality_part = " ".join(p for p in [suburb.strip(), state.strip(), postcode.strip()] if p)

    parts = [p for p in [street_part, locality_part, "Australia"] if p]
    return ", ".join(parts)


def _build_queries(body: GeocodeRequest) -> list[str]:
    """
    Return ordered list of query strings to try (most → least specific).
    All queries use the canonical format: street, suburb state postcode, Australia
    """
    queries: list[str] = []

    addr = body.address.strip()
    street   = body.street.strip()
    suburb   = body.suburb.strip()
    state    = body.state.strip().upper()
    postcode = body.postcode.strip()

    # 1. Full formatted address (already in canonical form from parse_address endpoint)
    if addr:
        queries.append(addr)

    # 2. Structured query from LLM components
    if street or suburb:
        structured = _build_structured_query(street, suburb, state, postcode)
        if structured not in queries:
            queries.append(structured)

    # 3. Suburb + state + postcode (coarse, no street)
    if suburb and state:
        coarse = _build_structured_query("", suburb, state, postcode)
        if coarse not in queries:
            queries.append(coarse)

    return queries


# ── Geoscape G-NAF v2 lookup ──────────────────────────────────────────────────

def _resolution_from_geo_feature(geo_feature: str) -> str:
    """
    Map Geoscape v2 geoFeature string to internal resolution level.

    facility  → property / building / frontage precision
    regional  → street / suburb / postcode precision
    """
    gf = geo_feature.upper()
    if any(k in gf for k in ("PROPERTY", "BUILDING", "FRONTAGE", "PARCEL", "UNIT", "LOCALITY")):
        return "facility"
    if any(k in gf for k in ("STREET", "ROAD", "SUBURB", "POSTCODE", "TOWN")):
        return "regional"
    # Default to facility for any unrecognised feature type (GNAF is address-level)
    return "facility"


async def _geoscape_lookup_v2(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
) -> Optional[GeocodeResponse]:
    """
    GET /v2/addresses/geocoder?query=<address>&maxResults=1
    Authorization: Bearer <api_key>

    Returns a GeoJSON FeatureCollection.  Coordinates are [lng, lat].
    matchScore is 0-100; matchQuality is one of: Exact, High, Medium, Low.
    """
    try:
        resp = await client.get(
            GEOSCAPE_BASE_V2,
            params={"query": query, "maxResults": 1},
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/geo+json, application/json",
                "Accept-Crs": "EPSG:4326",
            },
            timeout=10,
        )
    except httpx.RequestError as exc:
        logger.warning("[geocode] Geoscape v2 request error: %s", exc)
        return None

    if resp.status_code == 401:
        logger.error("[geocode] Geoscape v2 401 Unauthorized — check GEOSCAPE_API_KEY")
        return None
    if resp.status_code == 429:
        logger.warning("[geocode] Geoscape v2 429 rate-limited")
        return None
    if not resp.is_success:
        logger.warning("[geocode] Geoscape v2 HTTP %s for %r", resp.status_code, query)
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    features = data.get("features") or []
    if not features:
        logger.info("[geocode] Geoscape v2: no features for %r", query)
        return None

    feature     = features[0]
    geometry    = feature.get("geometry") or {}
    props       = feature.get("properties") or {}
    coordinates = geometry.get("coordinates") or []   # [lng, lat]

    if len(coordinates) < 2:
        return None

    lng, lat = float(coordinates[0]), float(coordinates[1])

    geo_feature      = props.get("geoFeature") or ""
    match_quality    = feature.get("matchQuality") or ""
    match_score      = int(feature.get("matchScore") or 0)
    formatted_addr   = props.get("formattedAddress") or query
    gnaf_pid         = props.get("addressId") or props.get("jurisdictionId") or ""
    resolution_level = _resolution_from_geo_feature(geo_feature)

    # Boost confidence for Exact/High quality matches
    quality_bonus = {"Exact": 5, "High": 0, "Medium": -10, "Low": -20}.get(match_quality, 0)
    confidence = max(0, min(100, match_score + quality_bonus))

    logger.info(
        "[geocode] G-NAF v2 hit: %r → (%.5f, %.5f) geoFeature=%r quality=%s score=%d pid=%s",
        query, lat, lng, geo_feature, match_quality, match_score, gnaf_pid,
    )

    return GeocodeResponse(
        lat              = lat,
        lng              = lng,
        gnaf_pid         = str(gnaf_pid),
        confidence       = confidence,
        resolution_level = resolution_level,
        inference_method = "gnaf-v2",
        display_address  = formatted_addr,
        source           = "geoscape",
    )


# ── Nominatim fallback ────────────────────────────────────────────────────────

async def _nominatim_fallback(
    client: httpx.AsyncClient,
    query: str,
) -> Optional[GeocodeResponse]:
    """
    Nominatim OSM fallback — query must be in canonical form:
    "street, suburb state postcode, Australia"
    """
    try:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q":              query,
                "format":         "jsonv2",
                "countrycodes":   "au",
                "addressdetails": "1",
                "limit":          "1",
            },
            headers={
                "Accept-Language": "en-AU",
                "User-Agent":      "eco-supply-chain-risk/1.0",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("[geocode] Nominatim error for %r: %s", query, exc)
        return None

    if not data:
        return None

    hit      = data[0]
    osm_type = hit.get("type", "")
    level = (
        "facility" if osm_type in {"building", "office", "commercial", "house", "industrial"}
        else "regional" if osm_type in {"suburb", "town", "village", "postcode", "neighbourhood"}
        else "unknown"
    )

    logger.info(
        "[geocode] Nominatim hit: %r → (%.5f, %.5f) type=%s",
        query, float(hit["lat"]), float(hit["lon"]), osm_type,
    )

    return GeocodeResponse(
        lat              = float(hit["lat"]),
        lng              = float(hit["lon"]),
        confidence       = 60,
        resolution_level = level,
        inference_method = "nominatim-fallback",
        display_address  = hit.get("display_name", query),
        source           = "nominatim",
    )


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(body: GeocodeRequest) -> GeocodeResponse:
    """
    Geocode a supplier address via G-NAF v2 (primary) → Nominatim (fallback)
    → Australia centre (last resort).

    State centroid fallback is intentionally excluded — callers should treat
    a country-centroid response (source="centroid") as an unresolved address.

    All query strings are built in canonical form:
      "street, suburb state postcode, Australia"
    """
    api_key = os.getenv("GEOSCAPE_API_KEY", "").strip()
    queries = _build_queries(body)

    if not queries:
        lat, lng = AUS_CENTRE
        return GeocodeResponse(
            lat=lat, lng=lng,
            resolution_level="unknown",
            inference_method="no-address",
            display_address="Australia",
            source="centroid",
        )

    logger.info("[geocode] queries to try: %s", queries)

    async with httpx.AsyncClient() as client:

        # ─ Primary: Geoscape G-NAF v2 ────────────────────────────────────
        if api_key:
            for q in queries:
                result = await _geoscape_lookup_v2(client, api_key, q)
                if result:
                    return result
            logger.info("[geocode] G-NAF v2 exhausted all queries — falling back to Nominatim")
        else:
            logger.warning(
                "[geocode] GEOSCAPE_API_KEY not set — Nominatim fallback active. "
                "Register free at https://geoscape.com.au/geoscape-developer-centre/"
            )

        # ─ Fallback: Nominatim OSM ────────────────────────────────────────
        for q in queries:
            result = await _nominatim_fallback(client, q)
            if result and result.resolution_level != "unknown":
                return result

    # ─ Last resort: Australia centre ─────────────────────────────────────
    lat, lng = AUS_CENTRE
    logger.warning("[geocode] all geocoding failed — returning Australia centre")
    return GeocodeResponse(
        lat=lat, lng=lng,
        resolution_level="unknown",
        inference_method="country-centroid",
        display_address="Australia",
        source="centroid",
    )
