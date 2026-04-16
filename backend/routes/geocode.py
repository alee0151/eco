"""
routes/geocode.py  —  POST /api/geocode

Geocodes a supplier address using the Geoscape Address Lookup API,
backed by the official Australian G-NAF (Geocoded National Address File).

API docs: https://docs.geoscape.com.au/docs/address-lookup

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
  4. State centroid / Australia centre  (last resort)

Fallback chain:
  Geoscape G-NAF  →  Nominatim OSM  →  state centroid  →  Australia centre

Environment variables
---------------------
GEOSCAPE_API_KEY   Geoscape API key.  Free tier: 1,000 calls/month.
                   Register at https://geoscape.com.au/geoscape-developer-centre/
                   If unset, falls back to Nominatim automatically.
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
    resolution_level: str  = "unknown"   # facility | regional | state | unknown
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


# ── Geoscape G-NAF lookup ─────────────────────────────────────────────────

async def _geoscape_lookup(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
) -> Optional[GeocodeResponse]:
    """
    POST /v1/addresses?query=<canonical address>&maxResults=1
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

    results = data.get("addressResults") or data.get("candidates") or []
    if not results:
        logger.info("[geocode] Geoscape: no result for %r", query)
        return None

    hit     = results[0]
    addr    = hit.get("address", {})
    geocode = hit.get("geocode", {})

    lat = geocode.get("latitude")  or geocode.get("lat")
    lng = geocode.get("longitude") or geocode.get("lon") or geocode.get("lng")

    if lat is None or lng is None:
        return None

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
        level = "facility"

    display  = addr.get("formattedAddress") or addr.get("addressLine") or query
    gnaf_pid = addr.get("gnafAddressDetailPid") or addr.get("gnafId") or ""
    score    = int(min(hit.get("score") or hit.get("matchScore") or 95, 100))

    logger.info(
        "[geocode] G-NAF hit: %r → (%.5f, %.5f) type=%s pid=%s",
        query, lat, lng, geocode_type, gnaf_pid,
    )

    return GeocodeResponse(
        lat              = float(lat),
        lng              = float(lng),
        gnaf_pid         = str(gnaf_pid),
        confidence       = score,
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
    Nominatim OSM fallback — query must be in canonical form:
    "street, suburb state postcode, Australia"
    """
    try:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q":             query,
                "format":        "jsonv2",
                "countrycodes":  "au",
                "addressdetails": "1",
                "limit":         "1",
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
        else "state"    if osm_type in {"state", "county"}
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
    Geocode a supplier address via G-NAF (primary) → Nominatim (fallback)
    → state centroid → Australia centre.

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

        # ─ Primary: Geoscape G-NAF ────────────────────────────────────────
        if api_key:
            for q in queries:
                result = await _geoscape_lookup(client, api_key, q)
                if result:
                    return result
            logger.info("[geocode] G-NAF exhausted all queries — falling back to Nominatim")
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

    # ─ Last resort: state centroid or Australia centre ───────────────────
    state_upper = body.state.upper().strip()
    if state_upper in STATE_CENTROIDS:
        lat, lng = STATE_CENTROIDS[state_upper]
        logger.info("[geocode] state centroid fallback → %s", state_upper)
        return GeocodeResponse(
            lat=lat, lng=lng,
            resolution_level="state",
            inference_method="state-centroid",
            display_address=state_upper,
            source="centroid",
        )

    lat, lng = AUS_CENTRE
    logger.warning("[geocode] all geocoding failed — returning Australia centre")
    return GeocodeResponse(
        lat=lat, lng=lng,
        resolution_level="unknown",
        inference_method="country-centroid",
        display_address="Australia",
        source="centroid",
    )
