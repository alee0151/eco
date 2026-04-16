"""
routes/geocode.py  —  POST /api/geocode

Geocodes a supplier address using the Geoscape Addresses API v2 geocoder,
backed by the official Australian G-NAF (Geocoded National Address File).

Endpoint
--------
GET https://api.psma.com.au/v2/addresses/geocoder
  ?address=<street_name suburb state postcode>
  &maxNumberOfResults=1

Example request:
  https://api.psma.com.au/v2/addresses/geocoder
    ?maxNumberOfResults=1
    &address=Cooma NSW 2630

Example response (GeoJSON FeatureCollection):
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "properties": {
          "geoFeature":       "LOCALITY",
          "formattedAddress": "COOMA NSW 2630",
          "localityId":       "loc2ea88964023a",   # locality-level match
          # for street/address-level matches: "addressId": "GAACT..."
        },
        "geometry": {
          "type":        "Point",
          "coordinates": [149.12022377, -36.25076511]   # [lng, lat]
        },
        "matchScore":   100,
        "matchType":    "Locality",
        "matchQuality": "Exact"
      }
    ]
  }

Flow  (single call per query attempt)
-----
1. Build ordered query strings (most → least specific).
2. GET /v2/addresses/geocoder?address=<q>&maxNumberOfResults=1
3. Parse features[0]:  geometry.coordinates[lng,lat], properties.geoFeature,
   properties.formattedAddress, matchScore, properties.addressId / localityId.
4. If no features for any query → return Australia centre
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

Environment variables
---------------------
GEOSCAPE_API_KEY   Geoscape API key — passed as the raw Authorization header value.
                   Register at https://geoscape.com.au/geoscape-developer-centre/
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
    address:  str = ""   # pre-formatted GNAF addressString: street_name suburb state postcode
    street:   str = ""   # street name + type only (no unit, no street number)
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

    Format mirrors the v2 example: "<street_name> <suburb> <state> <postcode>"
      e.g. "Collins Street Melbourne VIC 3000"
           "Cooma NSW 2630"
    """
    queries: list[str] = []

    addr     = body.address.strip()
    street   = body.street.strip()
    suburb   = body.suburb.strip()
    state    = body.state.strip().upper()
    postcode = body.postcode.strip()

    # 1. Pre-formatted address from the caller (parse-address output)
    if addr:
        queries.append(addr)

    # 2. Assembled from components: street + suburb + state + postcode
    if street or suburb:
        q = _join(street, suburb, state, postcode)
        if q not in queries:
            queries.append(q)

    # 3. Locality fallback: suburb + state + postcode (drop street)
    if suburb and state:
        q = _join(suburb, state, postcode)
        if q not in queries:
            queries.append(q)

    return queries


# ── Resolution level from geoFeature ────────────────────────────────────────────────

def _resolution_from_geo_feature(geo_feature: str) -> str:
    """
    Map G-NAF geoFeature (from properties.geoFeature) to internal resolution level.

    Observed v2 values:
      LOCALITY                        → regional
      STREET LOCALITY                 → regional
      PROPERTY CENTROID               → facility
      FRONTAGE CENTRE SETBACK         → facility
      BUILDING CENTROID               → facility
      PARCEL CENTROID                 → facility
    """
    gf = geo_feature.upper()
    if any(k in gf for k in ("PROPERTY", "BUILDING", "FRONTAGE", "PARCEL", "UNIT")):
        return "facility"
    if any(k in gf for k in ("STREET", "ROAD", "SUBURB", "POSTCODE", "TOWN", "LOCALITY")):
        return "regional"
    return "facility"


# ── GNAF v2 geocoder call ─────────────────────────────────────────────────────────

async def _gnaf_geocode(
    client: httpx.AsyncClient,
    api_key: str,
    address: str,
) -> Optional[GeocodeResponse]:
    """
    Single GET to /v2/addresses/geocoder.

    Response is a GeoJSON FeatureCollection:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "properties": {
            "geoFeature":       "LOCALITY",
            "formattedAddress": "COOMA NSW 2630",
            "localityId":       "loc2ea88964023a",  # locality match
            # OR "addressId": "GAACT..."           # street/property match
          },
          "geometry": {
            "type":        "Point",
            "coordinates": [149.12022377, -36.25076511]  # [lng, lat]
          },
          "matchScore":   100,
          "matchType":    "Locality",
          "matchQuality": "Exact"
        }
      ]
    }

    Returns GeocodeResponse on success, or None if no features.
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

    # v2 response is a GeoJSON FeatureCollection
    features = body.get("features") or []
    if not features:
        logger.info("[geocode] GNAF v2: no features for address=%r", address)
        return None

    feature    = features[0]
    props      = feature.get("properties") or {}
    geometry   = feature.get("geometry")   or {}
    coords     = geometry.get("coordinates") or []  # [lng, lat]

    if len(coords) < 2:
        logger.warning("[geocode] GNAF v2: missing coordinates for address=%r", address)
        return None

    lng = float(coords[0])
    lat = float(coords[1])

    # GNAF PID: addressId for property/street matches, localityId for locality matches
    gnaf_pid = str(
        props.get("addressId") or
        props.get("localityId") or
        ""
    )

    formatted_address = str(props.get("formattedAddress") or address)
    geo_feature       = str(props.get("geoFeature")       or "")
    match_score       = int(feature.get("matchScore")      or 0)
    match_type        = str(feature.get("matchType")       or "")

    resolution_level = _resolution_from_geo_feature(geo_feature)

    logger.info(
        "[geocode] GNAF v2 hit: %r → gnaf_pid=%s lat=%.5f lng=%.5f "
        "score=%d geoFeature=%r matchType=%s",
        address, gnaf_pid, lat, lng, match_score, geo_feature, match_type,
    )

    return GeocodeResponse(
        lat              = lat,
        lng              = lng,
        gnaf_pid         = gnaf_pid,
        confidence       = match_score,
        resolution_level = resolution_level,
        inference_method = "gnaf-v2",
        display_address  = formatted_address,
        source           = "geoscape",
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(body: GeocodeRequest) -> GeocodeResponse:
    """
    Geocode a supplier address via the GNAF Addresses API v2 geocoder.
    Single HTTP call per query attempt.
    No Nominatim / OSM fallback.  No state centroid fallback.

    Returns Australia centre (source="centroid") if:
      - GEOSCAPE_API_KEY is not set, or
      - all query attempts return empty features[].
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
    logger.warning(
        "[geocode] GNAF v2 returned no features for any query — returning Australia centre"
    )
    return GeocodeResponse(
        lat=lat, lng=lng,
        resolution_level="unknown",
        inference_method="country-centroid",
        display_address="Australia",
        source="centroid",
    )
