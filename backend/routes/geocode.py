"""
routes/geocode.py  —  POST /api/geocode

Geocodes a supplier address using the Geoscape Addresses API v1,
backed by the official Australian G-NAF (Geocoded National Address File).

API spec: addresses.v1.yaml  (https://api.psma.com.au/v1)

Flow
----
1. Build ordered query strings from the request body (most → least specific).
2. For each query: GET /v1/addresses?addressString=<q>&perPage=1
   → returns data[0].addressId + data[0].matchConfidence
3. Fetch geo for the winning addressId:
   GET /v1/addresses/{addressId}?include=geo
   → returns geo.geometry.coordinates [lng, lat] + geo.geoFeature
4. If no GNAF result is found for any query → return Australia centre
   (source="centroid", resolution_level="unknown").

No Nominatim / OSM fallback.  No state centroid fallback.

Request body
------------
{
  "address":  "441 St Kilda Road, Melbourne VIC 3004",
  "street":   "441 St Kilda Road",
  "suburb":   "Melbourne",
  "state":    "VIC",
  "postcode": "3004"
}

Environment variables
---------------------
GEOSCAPE_API_KEY   Geoscape API key.  Set as the raw Authorization header value.
                   Register at https://geoscape.com.au/geoscape-developer-centre/
                   If unset, the endpoint returns Australia centre immediately.
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

GNAF_BASE = "https://api.psma.com.au/v1/addresses"
AUS_CENTRE = (-25.2744, 133.7751)


# ── Schemas ───────────────────────────────────────────────────────────────────

class GeocodeRequest(BaseModel):
    address:  str = ""   # canonical formatted string: street, suburb state postcode
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
    source:           str  = "unknown"   # geoscape | centroid


# ── Address query builder ─────────────────────────────────────────────────────

def _build_structured_query(street: str, suburb: str, state: str, postcode: str) -> str:
    """
    Build addressString in the format expected by /v1/addresses:
      "street suburb state postcode"
    e.g. "441 St Kilda Road Melbourne VIC 3004"
    """
    parts = [p for p in [street.strip(), suburb.strip(), state.strip(), postcode.strip()] if p]
    return " ".join(parts)


def _build_queries(body: GeocodeRequest) -> list[str]:
    """
    Return ordered list of addressStrings to try (most → least specific).
    """
    queries: list[str] = []

    addr     = body.address.strip()
    street   = body.street.strip()
    suburb   = body.suburb.strip()
    state    = body.state.strip().upper()
    postcode = body.postcode.strip()

    # 1. Full formatted address supplied by caller
    if addr:
        queries.append(addr)

    # 2. Structured from LLM components (street + locality)
    if street or suburb:
        structured = _build_structured_query(street, suburb, state, postcode)
        if structured not in queries:
            queries.append(structured)

    # 3. Locality only (suburb + state + postcode, no street)
    if suburb and state:
        coarse = _build_structured_query("", suburb, state, postcode)
        if coarse not in queries:
            queries.append(coarse)

    return queries


# ── Resolution level from geoFeature ──────────────────────────────────────────────

def _resolution_from_geo_feature(geo_feature: str) -> str:
    """
    Map G-NAF geoFeature to internal resolution level.
      facility → PROPERTY CENTROID, FRONTAGE CENTRE SETBACK, BUILDING CENTROID, PARCEL, UNIT
      regional → STREET, ROAD, SUBURB, POSTCODE, TOWN
    """
    gf = geo_feature.upper()
    if any(k in gf for k in ("PROPERTY", "BUILDING", "FRONTAGE", "PARCEL", "UNIT")):
        return "facility"
    if any(k in gf for k in ("STREET", "ROAD", "SUBURB", "POSTCODE", "TOWN", "LOCALITY")):
        return "regional"
    return "facility"   # default: GNAF is always address-level


# ── GNAF v1 geocode ────────────────────────────────────────────────────────────────

async def _gnaf_search(
    client: httpx.AsyncClient,
    api_key: str,
    address_string: str,
) -> Optional[tuple[str, str, int]]:
    """
    Step 1 — GET /v1/addresses?addressString=<q>&perPage=1

    Returns (addressId, formattedAddress, matchConfidence) or None.

    Response shape:
      {
        "data": [
          {
            "addressId": "GAQLD156713910",
            "formattedAddress": "481 SETTLEMENT RD, KEPERRA QLD 4054",
            "matchConfidence": 100
          }
        ],
        "links": { ... }
      }
    """
    try:
        resp = await client.get(
            GNAF_BASE,
            params={"addressString": address_string, "perPage": 1},
            headers={
                "Authorization": api_key,
                "Accept": "application/json",
            },
            timeout=10,
        )
    except httpx.RequestError as exc:
        logger.warning("[geocode] GNAF search request error: %s", exc)
        return None

    if resp.status_code == 401:
        logger.error("[geocode] GNAF 401 Unauthorized — check GEOSCAPE_API_KEY")
        return None
    if resp.status_code == 429:
        logger.warning("[geocode] GNAF 429 rate-limited")
        return None
    if not resp.is_success:
        logger.warning("[geocode] GNAF search HTTP %s for %r", resp.status_code, address_string)
        return None

    try:
        data = resp.json().get("data") or []
    except Exception:
        return None

    if not data:
        logger.info("[geocode] GNAF: no results for %r", address_string)
        return None

    hit = data[0]
    address_id       = hit.get("addressId") or ""
    formatted_addr   = hit.get("formattedAddress") or address_string
    match_confidence = int(hit.get("matchConfidence") or 0)

    if not address_id:
        return None

    logger.info(
        "[geocode] GNAF search hit: %r → addressId=%s confidence=%d",
        address_string, address_id, match_confidence,
    )
    return address_id, formatted_addr, match_confidence


async def _gnaf_geo(
    client: httpx.AsyncClient,
    api_key: str,
    address_id: str,
) -> Optional[tuple[float, float, str]]:
    """
    Step 2 — GET /v1/addresses/{addressId}?include=geo

    Returns (lat, lng, geoFeature) or None.

    Response shape:
      {
        "addressId": "GANSW704420210",
        "geo": {
          "geoDatumCode": "GDA94",
          "geoFeature": "PROPERTY CENTROID",
          "geometry": {
            "type": "Point",
            "coordinates": [151.19923332, -33.78555372]   # [lng, lat]
          }
        }
      }
    """
    try:
        resp = await client.get(
            f"{GNAF_BASE}/{address_id}",
            params={"include": "geo"},
            headers={
                "Authorization": api_key,
                "Accept": "application/json",
            },
            timeout=10,
        )
    except httpx.RequestError as exc:
        logger.warning("[geocode] GNAF geo request error for %s: %s", address_id, exc)
        return None

    if not resp.is_success:
        logger.warning("[geocode] GNAF geo HTTP %s for addressId=%s", resp.status_code, address_id)
        return None

    try:
        body = resp.json()
    except Exception:
        return None

    geo         = body.get("geo") or {}
    geometry    = geo.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []   # [lng, lat]
    geo_feature = geo.get("geoFeature") or ""

    if len(coordinates) < 2:
        logger.warning("[geocode] GNAF geo: missing coordinates for addressId=%s", address_id)
        return None

    lng, lat = float(coordinates[0]), float(coordinates[1])

    logger.info(
        "[geocode] GNAF geo: addressId=%s → (%.5f, %.5f) geoFeature=%r",
        address_id, lat, lng, geo_feature,
    )
    return lat, lng, geo_feature


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(body: GeocodeRequest) -> GeocodeResponse:
    """
    Geocode a supplier address via G-NAF Addresses API v1 only.
    No Nominatim / OSM fallback.  No state centroid fallback.

    If GEOSCAPE_API_KEY is unset or no GNAF result is found, returns
    Australia centre with source="centroid" and resolution_level="unknown".
    """
    api_key = os.getenv("GEOSCAPE_API_KEY", "").strip()

    if not api_key:
        logger.warning(
            "[geocode] GEOSCAPE_API_KEY not set — returning Australia centre. "
            "Register free at https://geoscape.com.au/geoscape-developer-centre/"
        )
        lat, lng = AUS_CENTRE
        return GeocodeResponse(
            lat=lat, lng=lng,
            resolution_level="unknown",
            inference_method="no-api-key",
            display_address="Australia",
            source="centroid",
        )

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
        for q in queries:
            # Step 1: search for address → get addressId
            search_result = await _gnaf_search(client, api_key, q)
            if not search_result:
                continue

            address_id, formatted_addr, match_confidence = search_result

            # Step 2: fetch geo for the addressId
            geo_result = await _gnaf_geo(client, api_key, address_id)
            if not geo_result:
                logger.warning(
                    "[geocode] GNAF geo failed for addressId=%s (query=%r) — trying next query",
                    address_id, q,
                )
                continue

            lat, lng, geo_feature = geo_result
            resolution_level = _resolution_from_geo_feature(geo_feature)

            return GeocodeResponse(
                lat              = lat,
                lng              = lng,
                gnaf_pid         = address_id,
                confidence       = match_confidence,
                resolution_level = resolution_level,
                inference_method = "gnaf-v1",
                display_address  = formatted_addr,
                source           = "geoscape",
            )

    # All queries exhausted — no GNAF result found
    lat, lng = AUS_CENTRE
    logger.warning("[geocode] GNAF returned no results for any query — returning Australia centre")
    return GeocodeResponse(
        lat=lat, lng=lng,
        resolution_level="unknown",
        inference_method="country-centroid",
        display_address="Australia",
        source="centroid",
    )
