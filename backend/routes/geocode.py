"""
routes/geocode.py  —  POST /api/geocode

Geocodes a supplier address using the Geoscape Address Lookup API,
which is backed by the official Australian G-NAF (Geocoded National
Address File) — the most authoritative address dataset in Australia.

API docs: https://docs.geoscape.com.au/docs/address-lookup

Request:
  { "address": "<free-text address string>" }
  or with structured fields from the LLM parser:
  {
    "address":  "<free-text>",
    "street":   "42 Wallaby Way",
    "suburb":   "Cooma",
    "state":    "NSW",
    "postcode": "2630"
  }

Response:
  {
    "lat":              -36.2345,
    "lng":              149.1234,
    "gnaf_pid":         "GANSW123456789",
    "confidence":       90,
    "resolution_level": "facility",    # facility | regional | state | unknown
    "inference_method": "gnaf",
    "display_address":  "42 Wallaby Way, Cooma NSW 2630",
    "source":           "geoscape"
  }

Fallback chain (if G-NAF returns no result):
  structured → free-text → suburb+state → state centroid → Australia centre

Environment variables
---------------------
GEOSCAPE_API_KEY   Geoscape API key (required for G-NAF lookups).
                   Register at https://geoscape.com.au/geoscape-developer-centre/
                   Free tier: 1,000 calls/month. Paid plans available.

Fallback behaviour
------------------
If GEOSCAPE_API_KEY is not set or the API returns no result, the endpoint
falls back to Nominatim OSM so the pipeline never returns empty coordinates.
This lets the app work in development without a Geoscape key.
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

GEOSCAPE_BASE = "https://api.geoscape.com.au/v1/addresses"

STATE_CENTROIDS = {
    "NSW": (-32.1656, 147.0000),
    "VIC": (-37.0201, 144.9646),
    "QLD": (-22.5750, 144.0850),
    "WA":  (-25.0419, 121.8989),
    "SA":  (-30.0002, 136.2092),
    "TAS": (-42.0409, 146.5978),
    "ACT": (-35.4735, 149.0124),
    "NT":  (-19.4914, 132.5510),
}
AUS_CENTRE = (-25.2744, 133.7751)


# ── Schemas ───────────────────────────────────────────────────────────────────

class GeocodeRequest(BaseModel):
    address:  str = ""     # free-text (formatted) address
    street:   str = ""     # from LLM parser: house number + street
    suburb:   str = ""     # from LLM parser
    state:    str = ""     # from LLM parser: NSW / VIC / ...
    postcode: str = ""     # from LLM parser


class GeocodeResponse(BaseModel):
    lat:              float
    lng:              float
    gnaf_pid:         str   = ""          # G-NAF persistent identifier
    confidence:       int   = 0           # 0–100
    resolution_level: str   = "unknown"   # facility | regional | state | unknown
    inference_method: str   = "unknown"
    display_address:  str   = ""
    source:           str   = "unknown"   # geoscape | nominatim | centroid


# ── Geoscape G-NAF lookup ─────────────────────────────────────────────────

async def _geoscape_lookup(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
) -> Optional[GeocodeResponse]:
    """
    Call the Geoscape /v1/addresses/bulk-geocode endpoint.
    Returns a GeocodeResponse on success, None on no-match or error.

    Geoscape API reference:
      GET /v1/addresses?query=<address>&maxResults=1
      Authorization: apikey <key>
    """
    try:
        resp = await client.get(
            GEOSCAPE_BASE,
            params={"query": query, "maxResults": 1},
            headers={"Authorization": f"apikey {api_key}"},
            timeout=10,
        )
    except httpx.RequestError as exc:
        logger.warning("[geocode] Geoscape request error: %s", exc)
        return None

    if resp.status_code == 401:
        logger.error("[geocode] Geoscape 401 Unauthorized — check GEOSCAPE_API_KEY")
        return None
    if resp.status_code == 429:
        logger.warning("[geocode] Geoscape 429 rate-limited")
        return None
    if not resp.is_success:
        logger.warning("[geocode] Geoscape HTTP %s for %r", resp.status_code, query)
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    # Geoscape response shape:
    # { "addressResults": [ { "address": {...}, "geocode": {"latitude": x, "longitude": y, ...} } ] }
    results = data.get("addressResults") or data.get("candidates") or []
    if not results:
        logger.info("[geocode] Geoscape no result for %r", query)
        return None

    hit     = results[0]
    addr    = hit.get("address", {})
    geocode = hit.get("geocode", {})

    lat = geocode.get("latitude")  or geocode.get("lat")
    lng = geocode.get("longitude") or geocode.get("lon") or geocode.get("lng")

    if lat is None or lng is None:
        return None

    # G-NAF geocode types → resolution level
    geocode_type = (geocode.get("geocodeType") or geocode.get("type") or "").upper()
    if any(k in geocode_type for k in ("PROPERTY", "BUILDING", "PARCEL", "FRONTAGE", "LOCALITY")):
        level = "facility"
    elif any(k in geocode_type for k in ("STREET", "ROAD")):
        level = "regional"
    elif any(k in geocode_type for k in ("SUBURB", "POSTCODE", "TOWN")):
        level = "regional"
    elif any(k in geocode_type for k in ("STATE",)):
        level = "state"
    else:
        level = "facility"  # default for matched G-NAF records

    display = addr.get("formattedAddress") or addr.get("addressLine") or query
    gnaf_pid = addr.get("gnafAddressDetailPid") or addr.get("gnafId") or ""
    score    = hit.get("score") or hit.get("matchScore") or 95

    logger.info(
        "[geocode] G-NAF hit: %r → (%.5f, %.5f) type=%s pid=%s",
        query, lat, lng, geocode_type, gnaf_pid,
    )

    return GeocodeResponse(
        lat              = float(lat),
        lng              = float(lng),
        gnaf_pid         = str(gnaf_pid),
        confidence       = int(min(score, 100)),
        resolution_level = level,
        inference_method = "gnaf",
        display_address  = display,
        source           = "geoscape",
    )


# ── Nominatim fallback ────────────────────────────────────────────────────

async def _nominatim_fallback(
    client: httpx.AsyncClient,
    query: str,
) -> Optional[GeocodeResponse]:
    """
    Nominatim OSM fallback — used when Geoscape API key is absent or
    the G-NAF lookup returns no result.
    """
    try:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "jsonv2", "countrycodes": "au", "addressdetails": "1", "limit": "1"},
            headers={"Accept-Language": "en-AU", "User-Agent": "eco-supply-chain-risk/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("[geocode] Nominatim error for %r: %s", query, exc)
        return None

    if not data:
        return None

    hit = data[0]
    osm_type = hit.get("type", "")
    level = (
        "facility" if osm_type in {"building", "office", "commercial", "house", "industrial"}
        else "regional" if osm_type in {"suburb", "town", "village", "postcode", "neighbourhood"}
        else "state"   if osm_type in {"state", "county"}
        else "unknown"
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


# ── Endpoint ─────────────────────────────────────────────────────────────────────

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(body: GeocodeRequest) -> GeocodeResponse:
    """
    Geocode a supplier address using G-NAF (Geoscape) as primary source
    with Nominatim OSM as fallback, and state/country centroids as last resort.

    Query construction priority:
      1. Full formatted address (most specific)
      2. street + suburb + state + postcode (structured from LLM parser)
      3. suburb + state + postcode
      4. state centroid
    """
    api_key = os.getenv("GEOSCAPE_API_KEY", "").strip()

    # Build candidate query strings from most → least specific
    queries: list[str] = []

    if body.address.strip():
        queries.append(body.address.strip())

    # Structured query from LLM-parsed components
    if body.suburb and body.state:
        parts = [p for p in [body.street, body.suburb, body.state, body.postcode] if p.strip()]
        structured = ", ".join(parts)
        if structured not in queries:
            queries.append(structured)

    # Suburb + state fallback
    if body.suburb and body.state:
        coarse = f"{body.suburb} {body.state} {body.postcode}".strip()
        if coarse not in queries:
            queries.append(coarse)

    if not queries:
        # No address at all — return Australia centre
        return GeocodeResponse(
            lat=AUS_CENTRE[0], lng=AUS_CENTRE[1],
            resolution_level="unknown", inference_method="no-address",
            display_address="Australia", source="centroid",
        )

    async with httpx.AsyncClient() as client:

        # ── Primary: Geoscape G-NAF ────────────────────────────────────────
        if api_key:
            for q in queries:
                result = await _geoscape_lookup(client, api_key, q)
                if result:
                    return result
            logger.info("[geocode] G-NAF returned no result for all queries — falling back to Nominatim")
        else:
            logger.warning(
                "[geocode] GEOSCAPE_API_KEY not set — using Nominatim fallback. "
                "Register at https://geoscape.com.au/geoscape-developer-centre/"
            )

        # ── Fallback: Nominatim OSM ─────────────────────────────────────────
        for q in queries:
            result = await _nominatim_fallback(client, q)
            if result and result.resolution_level != "unknown":
                return result

    # ── Last resort: state centroid or Australia centre ─────────────────────
    state_upper = body.state.upper().strip()
    if state_upper in STATE_CENTROIDS:
        lat, lng = STATE_CENTROIDS[state_upper]
        logger.info("[geocode] State centroid fallback → %s", state_upper)
        return GeocodeResponse(
            lat=lat, lng=lng,
            resolution_level="state",
            inference_method="state-centroid",
            display_address=state_upper,
            source="centroid",
        )

    lat, lng = AUS_CENTRE
    logger.warning("[geocode] All geocoding failed — returning Australia centre")
    return GeocodeResponse(
        lat=lat, lng=lng,
        resolution_level="unknown",
        inference_method="country-centroid",
        display_address="Australia",
        source="centroid",
    )
