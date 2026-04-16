"""
routes/geocode.py  —  POST /api/geocode

Geocodes a supplier address using the Geoscape Addresses API v2 geocoder,
backed by the official Australian G-NAF (Geocoded National Address File).

Endpoint
--------
GET https://api.psma.com.au/v2/addresses/geocoder
  ?address=<street_name suburb state postcode>
  &maxNumberOfResults=1

Example:
  https://api.psma.com.au/v2/addresses/geocoder
    ?maxNumberOfResults=1
    &address=Cooma NSW 2630

Flow  (single call, no two-step lookup)
-----
1. Build ordered query strings from the request body (most → least specific).
2. For each query: GET /v2/addresses/geocoder?address=<q>&maxNumberOfResults=1
3. Parse lat/lng from the first result.
4. If no result for any query → return Australia centre
   (source="centroid", resolution_level="unknown").

No Nominatim / OSM fallback.  No state centroid fallback.

Request body
------------
{
  "address":  "Collins Street Melbourne VIC 3000",
  "street":   "Collins Street",
  "suburb":   "Melbourne",
  "state":    "VIC",
  "postcode": "3000"
}
All fields are optional but at least one should be non-empty.

Environment variables
---------------------
GEOSCAPE_API_KEY   Geoscape API key — passed as the raw Authorization header value.
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


# ── Config ──────────────────────────────────────────────────────────────────

GNAF_V2_GEOCODER = "https://api.psma.com.au/v2/addresses/geocoder"
AUS_CENTRE       = (-25.2744, 133.7751)


# ── Schemas ──────────────────────────────────────────────────────────────────

class GeocodeRequest(BaseModel):
    address:  str = ""   # pre-formatted GNAF addressString (street_name suburb state postcode)
    street:   str = ""   # street name + type, NO unit or street number
    suburb:   str = ""
    state:    str = ""   # NSW / VIC / QLD / WA / SA / TAS / ACT / NT
    postcode: str = ""


class GeocodeResponse(BaseModel):
    lat:              float
    lng:              float
    gnaf_pid:         str = ""
    confidence:       int = 0
    resolution_level: str = "unknown"   # facility | regional | unknown
    inference_method: str = "unknown"
    display_address:  str = ""
    source:           str = "unknown"   # geoscape | centroid


# ── Query builder ────────────────────────────────────────────────────────────────

def _join(*parts: str) -> str:
    """Join non-empty parts with a single space."""
    return " ".join(p for p in parts if p)


def _build_queries(body: GeocodeRequest) -> list[str]:
    """
    Return an ordered list of `address=` values to try, most → least specific.

    All queries follow the format expected by the v2 geocoder example:
      "<street_name> <suburb> <state> <postcode>"
    e.g. "Collins Street Melbourne VIC 3000"
         "Cooma NSW 2630"
    """
    queries: list[str] = []

    addr     = body.address.strip()
    street   = body.street.strip()
    suburb   = body.suburb.strip()
    state    = body.state.strip().upper()
    postcode = body.postcode.strip()

    # 1. Pre-formatted address string from the caller (parse-address output)
    if addr:
        queries.append(addr)

    # 2. Assembled from components: street + suburb + state + postcode
    if street or suburb:
        q = _join(street, suburb, state, postcode)
        if q not in queries:
            queries.append(q)

    # 3. Locality only: suburb + state + postcode (drop street if street failed)
    if suburb and state:
        q = _join(suburb, state, postcode)
        if q not in queries:
            queries.append(q)

    return queries


# ── Resolution level ───────────────────────────────────────────────────────────────

def _resolution_from_geo_feature(geo_feature: str) -> str:
    """
    Map G-NAF geoFeature to internal resolution level.
      facility → PROPERTY CENTROID, FRONTAGE, BUILDING CENTROID, PARCEL, UNIT
      regional → STREET, ROAD, SUBURB, POSTCODE, TOWN, LOCALITY
    """
    gf = geo_feature.upper()
    if any(k in gf for k in ("PROPERTY", "BUILDING", "FRONTAGE", "PARCEL", "UNIT")):
        return "facility"
    if any(k in gf for k in ("STREET", "ROAD", "SUBURB", "POSTCODE", "TOWN", "LOCALITY")):
        return "regional"
    return "facility"


# ── GNAF v2 geocoder call ───────────────────────────────────────────────────────────

async def _gnaf_geocode(
    client: httpx.AsyncClient,
    api_key: str,
    address: str,
) -> Optional[GeocodeResponse]:
    """
    Single call to the v2 geocoder.

    GET https://api.psma.com.au/v2/addresses/geocoder
      ?address=<address>
      &maxNumberOfResults=1

    Expected response shape (v2):
    {
      "addressMatches": [
        {
          "addressId":       "GAACT715055052",
          "addressString":   "COOMA NSW 2630",
          "matchScore":      100,
          "geocodeType":     "LOCALITY",
          "latitude":        -36.234,
          "longitude":       149.123
        }
      ]
    }

    Returns a GeocodeResponse on success, or None if no match.
    """
    try:
        resp = await client.get(
            GNAF_V2_GEOCODER,
            params={
                "address":            address,
                "maxNumberOfResults": 1,
            },
            headers={
                "Authorization": api_key,
                "Accept":        "application/json",
            },
            timeout=10,
        )
    except httpx.RequestError as exc:
        logger.warning("[geocode] GNAF v2 request error: %s", exc)
        return None

    if resp.status_code == 401:
        logger.error("[geocode] GNAF v2 401 Unauthorized — check GEOSCAPE_API_KEY")
        return None
    if resp.status_code == 429:
        logger.warning("[geocode] GNAF v2 429 rate-limited")
        return None
    if not resp.is_success:
        logger.warning("[geocode] GNAF v2 HTTP %s for address=%r", resp.status_code, address)
        return None

    try:
        body = resp.json()
    except Exception:
        logger.warning("[geocode] GNAF v2 non-JSON response for address=%r", address)
        return None

    matches = body.get("addressMatches") or []
    if not matches:
        logger.info("[geocode] GNAF v2: no matches for address=%r", address)
        return None

    hit = matches[0]

    lat         = hit.get("latitude")
    lng         = hit.get("longitude")
    address_id  = str(hit.get("addressId")  or "")
    addr_str    = str(hit.get("addressString") or address)
    match_score = int(hit.get("matchScore")  or 0)
    geocode_type = str(hit.get("geocodeType") or "")

    if lat is None or lng is None:
        logger.warning("[geocode] GNAF v2: missing lat/lng for address=%r", address)
        return None

    resolution_level = _resolution_from_geo_feature(geocode_type)

    logger.info(
        "[geocode] GNAF v2 hit: %r → addressId=%s lat=%.5f lng=%.5f score=%d type=%s",
        address, address_id, float(lat), float(lng), match_score, geocode_type,
    )

    return GeocodeResponse(
        lat              = float(lat),
        lng              = float(lng),
        gnaf_pid         = address_id,
        confidence       = match_score,
        resolution_level = resolution_level,
        inference_method = "gnaf-v2",
        display_address  = addr_str,
        source           = "geoscape",
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(body: GeocodeRequest) -> GeocodeResponse:
    """
    Geocode a supplier address via the GNAF Addresses API v2 geocoder.
    Single HTTP call per query attempt — no two-step lookup.
    No Nominatim / OSM fallback.  No state centroid fallback.

    Returns Australia centre (source="centroid") if:
      - GEOSCAPE_API_KEY is not set, or
      - all query attempts return no GNAF matches.
    """
    api_key = os.getenv("GEOSCAPE_API_KEY", "").strip()

    if not api_key:
        logger.warning(
            "[geocode] GEOSCAPE_API_KEY not set — returning Australia centre. "
            "Register at https://geoscape.com.au/geoscape-developer-centre/"
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

    logger.info("[geocode] v2 queries to try: %s", queries)

    async with httpx.AsyncClient() as client:
        for q in queries:
            result = await _gnaf_geocode(client, api_key, q)
            if result:
                return result

    lat, lng = AUS_CENTRE
    logger.warning("[geocode] GNAF v2 returned no results for any query — returning Australia centre")
    return GeocodeResponse(
        lat=lat, lng=lng,
        resolution_level="unknown",
        inference_method="country-centroid",
        display_address="Australia",
        source="centroid",
    )
