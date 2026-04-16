"""
routes/enrich.py  —  POST /api/enrich

Two-stage ABR enrichment + inline geocoding pipeline.

  Stage 1 — ABN Lookup (when a valid 11-digit ABN is present)
    GET https://abr.business.gov.au/json/AbnDetails.aspx
        ?abn=<11digits>&callback=callback&guid=<GUID>

  Stage 2 — Name Lookup fallback (when ABN is missing/invalid OR Stage 1 finds nothing)
    GET https://abr.business.gov.au/json/MatchingNames.aspx
        ?name=<supplier+name>&maxResults=10&callback=callback&guid=<GUID>

  Stage 3 — Geocoding (always, if suburb+state or postcode available)
    Uses suburb, state, postcode extracted from:
      a) The ABR response (AddressSuburb, AddressState, AddressPostcode), or
      b) The address string passed by the caller.
    Query sent to GNAF v2: "<suburb> <state> <postcode>"
    Geocoding is done ONCE here — the frontend does NOT need a separate /api/geocode call.

Environment variables
---------------------
ABR_GUID           ABR Web Services GUID (required)
GEOSCAPE_API_KEY   Geoscape G-NAF v2 API key (optional — falls back to AU centroid)
"""

import json
import logging
import os
import re

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# ── ABR JSON API endpoints ─────────────────────────────────────────────────────────
ABR_ABN_URL   = "https://abr.business.gov.au/json/AbnDetails.aspx"
ABR_NAME_URL  = "https://abr.business.gov.au/json/MatchingNames.aspx"
CALLBACK_NAME = "callback"

# ── Geoscape G-NAF v2 ─────────────────────────────────────────────────────────────
GNAF_V2_URL = "https://api.psma.com.au/v2/addresses/geocoder"
AUS_CENTRE  = (-25.2744, 133.7751)   # fallback when geocoding fails


# ── Request / Response schemas ─────────────────────────────────────────────────

class EnrichRequest(BaseModel):
    abn:     str = ""
    name:    str = ""
    address: str = ""   # full address string from extract (street suburb state postcode)


class EnrichResult(BaseModel):
    abn:                 str
    abn_found:           bool
    enriched_name:       str | None = None
    enriched_address:    str | None = None   # "state postcode" from ABR
    abr_status:          str | None = None
    entity_type:         str | None = None
    name_discrepancy:    bool | None = None
    address_discrepancy: bool | None = None
    confidence_score:    int  | None = None
    lookup_method:       str  | None = None  # "abn" | "name" | "name+abn"
    # ── Geocode result (filled inline, no separate /api/geocode call needed) ──
    lat:              float | None = None
    lng:              float | None = None
    gnaf_pid:         str   | None = None
    geocode_confidence:   int   | None = None   # GNAF matchScore 0-100
    geocode_resolution:   str   | None = None   # facility | regional | unknown
    geocode_address:      str   | None = None   # GNAF formattedAddress
    geocode_source:       str   | None = None   # geoscape | centroid | skipped


# ── JSONP stripper ────────────────────────────────────────────────────────────────

def _strip_jsonp(text: str) -> str:
    text = text.strip()
    m = re.match(r"^[a-zA-Z_$][\w$.]*\s*\((.+)\)\s*;?\s*$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def _parse_abr_json(raw_text: str) -> dict | list:
    try:
        return json.loads(_strip_jsonp(raw_text))
    except Exception as exc:
        logger.error("[enrich] ABR unparseable response: %s", raw_text[:300])
        raise HTTPException(status_code=502,
            detail=f"ABR returned unparseable response: {exc}") from exc


# ── ABN cleaner ─────────────────────────────────────────────────────────────────────

def _clean_abn(raw: str) -> str | None:
    digits = re.sub(r"[\s\-]", "", raw or "")
    return digits if re.match(r"^\d{11}$", digits) else None


# ── ABR flat-response helpers ──────────────────────────────────────────────────

def _is_abn_found(data: dict) -> bool:
    message     = (data.get("Message") or "").strip()
    entity_name = (data.get("EntityName") or "").strip()
    return (not message) and bool(entity_name)


def _extract_name_from_flat(data: dict) -> str | None:
    name = (data.get("EntityName") or "").strip()
    if name:
        return name
    biz_names = data.get("BusinessName", [])
    if isinstance(biz_names, list):
        for entry in biz_names:
            n = (entry.get("Name") if isinstance(entry, dict) else str(entry)).strip()
            if n:
                return n
    return None


def _build_address_from_flat(data: dict) -> str | None:
    """
    ABR AbnDetails only gives AddressState + AddressPostcode (no street).
    Returns e.g. "NSW 2630, Australia" for display/discrepancy checks.
    """
    state    = (data.get("AddressState")    or "").strip()
    postcode = (data.get("AddressPostcode") or "").strip()
    parts    = [p for p in [state, postcode] if p]
    return ", ".join(parts) + ", Australia" if parts else None


def _get_status_from_flat(data: dict) -> str | None:
    return (data.get("AbnStatus") or "").strip() or None


def _get_entity_type_from_flat(data: dict) -> str | None:
    return (data.get("EntityTypeName") or "").strip() or None


# ── MatchingNames response parser ──────────────────────────────────────────────────

def _parse_name_results(data: dict | list) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("Names", "names", "ABRPayloadSearchResults"):
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                inner = val.get("Names") or val.get("names") or []
                if isinstance(inner, list):
                    return inner
    return []


# ── Fuzzy comparison helpers ────────────────────────────────────────────────────

def _normalise(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _name_discrepancy(abr_name: str, supplied_name: str) -> bool:
    if not supplied_name:
        return False
    a, b = _normalise(abr_name), _normalise(supplied_name)
    return not (a == b or a in b or b in a)


def _address_discrepancy(abr_addr: str, supplied_addr: str) -> bool:
    if not supplied_addr or not abr_addr:
        return False
    a_tok = set(_normalise(abr_addr).split())
    b_tok = set(_normalise(supplied_addr).split())
    if not a_tok or not b_tok:
        return False
    overlap = len(a_tok & b_tok) / max(len(a_tok), len(b_tok))
    return overlap < 0.4


# ── Confidence scoring ────────────────────────────────────────────────────────────

def _compute_confidence(
    abn_found: bool,
    abr_status: str | None,
    name_discrepancy: bool,
    address_discrepancy: bool,
    has_address: bool,
    used_name_lookup: bool,
) -> int:
    if not abn_found:
        return 0
    score = 50
    if abr_status and abr_status.lower() == "active":
        score += 20
    if not name_discrepancy:
        score += 15
    if not address_discrepancy:
        score += 10
    if has_address:
        score += 5
    if used_name_lookup:
        score -= 10
    return max(0, min(score, 100))


# ── ABR HTTP helpers ──────────────────────────────────────────────────────────────

async def _abr_lookup_by_abn(client: httpx.AsyncClient, abn: str, guid: str) -> dict | None:
    try:
        resp = await client.get(
            ABR_ABN_URL,
            params={"abn": abn, "callback": CALLBACK_NAME, "guid": guid},
        )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail="Cannot reach the ABR API.") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502,
            detail=f"ABR returned HTTP {exc.response.status_code}") from exc

    data = _parse_abr_json(resp.text)
    if not isinstance(data, dict):
        return None
    return data if _is_abn_found(data) else None


async def _abr_lookup_by_name(client: httpx.AsyncClient, name: str, guid: str) -> list[dict]:
    try:
        resp = await client.get(
            ABR_NAME_URL,
            params={"name": name, "maxResults": "10",
                    "callback": CALLBACK_NAME, "guid": guid},
        )
        resp.raise_for_status()
        data = _parse_abr_json(resp.text)
        return _parse_name_results(data)
    except Exception:
        return []


def _best_name_match(records: list[dict], supplied_name: str) -> dict | None:
    if not records or not supplied_name:
        return None
    s_tok = set(_normalise(supplied_name).split())
    best, best_score = None, 0.0
    for rec in records:
        c_tok = set(_normalise(rec.get("Name", "")).split())
        if not c_tok:
            continue
        score = len(s_tok & c_tok) / max(len(s_tok), len(c_tok))
        if score > best_score:
            best_score, best = score, rec
    return best if best_score >= 0.3 else None


# ── Geocode helpers ───────────────────────────────────────────────────────────────

_AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}


def _geocode_query_from_abr(flat_data: dict, caller_address: str) -> str | None:
    """
    Build the geocode query string from ABR data and/or the caller's address.

    Priority:
      1. ABR AddressState + AddressPostcode  (always suburb-level accurate)
      2. Parse suburb+state+postcode from the caller's address string

    Returns a string like "Melbourne VIC 3000" ready to send to GNAF v2.
    We intentionally use suburb/state/postcode only (no street number)
    because ABR does not provide street-level data.
    """
    # ── Option 1: use ABR fields directly ────────────────────────────────────
    state    = (flat_data.get("AddressState")    or "").strip().upper()
    postcode = (flat_data.get("AddressPostcode") or "").strip()
    suburb   = (flat_data.get("AddressSuburb")   or "").strip()  # present in some responses

    if state and postcode:
        q = " ".join(p for p in [suburb, state, postcode] if p)
        logger.info("[enrich] geocode query from ABR: %r", q)
        return q

    # ── Option 2: parse from caller address string ────────────────────────────
    # Matches patterns like "Collins Street Melbourne VIC 3000"
    #                    or "Melbourne VIC 3000"
    m = re.search(
        r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})\b",
        caller_address or "", re.IGNORECASE,
    )
    if m:
        found_state    = m.group(1).upper()
        found_postcode = m.group(2)
        # Grab the word(s) immediately before the state as suburb
        before = caller_address[: m.start()].strip().rstrip(",")
        # Last "word group" before state = suburb (strip street number / street name)
        suburb_candidate = before.split()[-1] if before.split() else ""
        q = " ".join(p for p in [suburb_candidate, found_state, found_postcode] if p)
        logger.info("[enrich] geocode query from caller address: %r", q)
        return q

    return None


def _gnaf_resolution(geo_feature: str) -> str:
    gf = (geo_feature or "").upper()
    if any(k in gf for k in ("PROPERTY", "BUILDING", "FRONTAGE", "PARCEL", "UNIT")):
        return "facility"
    if any(k in gf for k in ("STREET", "ROAD", "SUBURB", "POSTCODE", "TOWN", "LOCALITY")):
        return "regional"
    return "regional"


async def _geocode_once(
    client: httpx.AsyncClient,
    query: str,
    api_key: str,
) -> dict:
    """
    Single GET to GNAF v2 geocoder with suburb+state+postcode.
    Returns a dict with lat, lng, gnaf_pid, confidence, resolution, address, source.
    Always returns something (falls back to AU centroid on any failure).
    """
    fallback = {
        "lat": AUS_CENTRE[0], "lng": AUS_CENTRE[1],
        "gnaf_pid": "", "geocode_confidence": 0,
        "geocode_resolution": "unknown",
        "geocode_address": query,
        "geocode_source": "centroid",
    }

    if not api_key:
        logger.warning("[enrich] GEOSCAPE_API_KEY not set — skipping geocode")
        fallback["geocode_source"] = "skipped"
        return fallback

    try:
        resp = await client.get(
            GNAF_V2_URL,
            params={"address": query, "maxNumberOfResults": 1},
            headers={"Authorization": api_key, "Accept": "application/json"},
            timeout=10,
        )
    except httpx.RequestError as exc:
        logger.warning("[enrich] GNAF request error: %s", exc)
        return fallback

    if not resp.is_success:
        logger.warning("[enrich] GNAF HTTP %s for query=%r", resp.status_code, query)
        return fallback

    try:
        body = resp.json()
    except Exception:
        return fallback

    features = body.get("features") or []
    if not features:
        logger.info("[enrich] GNAF: no features for query=%r", query)
        return fallback

    feature  = features[0]
    props    = feature.get("properties") or {}
    coords   = (feature.get("geometry") or {}).get("coordinates") or []

    if len(coords) < 2:
        return fallback

    gnaf_pid = str(props.get("addressId") or props.get("localityId") or "")
    geo_feature = str(props.get("geoFeature") or "")

    result = {
        "lat":                float(coords[1]),
        "lng":                float(coords[0]),
        "gnaf_pid":           gnaf_pid,
        "geocode_confidence": int(feature.get("matchScore") or 0),
        "geocode_resolution": _gnaf_resolution(geo_feature),
        "geocode_address":    str(props.get("formattedAddress") or query),
        "geocode_source":     "geoscape",
    }
    logger.info(
        "[enrich] GNAF hit: %r → lat=%.5f lng=%.5f gnaf=%s score=%d",
        query, result["lat"], result["lng"], gnaf_pid, result["geocode_confidence"],
    )
    return result


# ── Main endpoint ───────────────────────────────────────────────────────────────────

@router.post("/enrich", response_model=EnrichResult)
async def enrich(body: EnrichRequest) -> EnrichResult:
    """
    ABR enrichment + inline geocoding.

    Stage 1  ABN lookup  (AbnDetails.aspx)
    Stage 2  Name fallback  (MatchingNames.aspx) when ABN missing/invalid
    Stage 3  Geocode ONCE using suburb+state+postcode from ABR (or caller address)
             — no separate /api/geocode call needed from the frontend.
    """
    guid = os.getenv("ABR_GUID", "").strip()
    if not guid:
        raise HTTPException(status_code=503,
            detail="ABR_GUID not configured. Add ABR_GUID=<your-guid> to backend/.env")

    api_key = os.getenv("GEOSCAPE_API_KEY", "").strip()

    abn_clean        = _clean_abn(body.abn)
    flat_data: dict | None = None
    resolved_abn     = abn_clean or ""
    used_name_lookup = False
    lookup_method    = "abn"

    async with httpx.AsyncClient(timeout=15) as client:

        # ── Stage 1: direct ABN lookup ─────────────────────────────────────
        if abn_clean:
            logger.info("[enrich] Stage 1: ABN lookup %s", abn_clean)
            flat_data = await _abr_lookup_by_abn(client, abn_clean, guid)
            if flat_data:
                lookup_method = "abn"
                logger.info("[enrich] Stage 1 hit: %s", flat_data.get("EntityName"))

        # ── Stage 2: name fallback ─────────────────────────────────────────
        if flat_data is None and body.name.strip():
            logger.info("[enrich] Stage 2: name lookup %r", body.name.strip())
            records = await _abr_lookup_by_name(client, body.name.strip(), guid)
            best    = _best_name_match(records, body.name)

            if best:
                matched_abn = _clean_abn(best.get("Abn", ""))
                logger.info("[enrich] Stage 2 matched %r → ABN %s", body.name, matched_abn)
                if matched_abn:
                    flat_data = await _abr_lookup_by_abn(client, matched_abn, guid)
                    resolved_abn     = matched_abn
                    used_name_lookup = True
                    lookup_method    = "name+abn" if flat_data else "name"

                if not flat_data:
                    flat_data = {
                        "Abn":             resolved_abn,
                        "AbnStatus":       "Active",
                        "EntityName":      best.get("Name", ""),
                        "AddressSuburb":   "",
                        "AddressState":    best.get("State",    ""),
                        "AddressPostcode": best.get("Postcode", ""),
                        "EntityTypeName":  "",
                        "BusinessName":    [],
                        "Message":         "",
                    }

        # ── Stage 3: geocode ONCE ──────────────────────────────────────────
        geo: dict = {
            "lat": None, "lng": None, "gnaf_pid": None,
            "geocode_confidence": None, "geocode_resolution": None,
            "geocode_address": None, "geocode_source": None,
        }

        if flat_data is not None:
            geo_query = _geocode_query_from_abr(flat_data, body.address)
        else:
            # No ABR hit — still try geocoding from the caller's address string
            geo_query = _geocode_query_from_abr({}, body.address)

        if geo_query:
            geo = await _geocode_once(client, geo_query, api_key)
        else:
            logger.info("[enrich] no geocodable location found — skipping geocode")
            geo["geocode_source"] = "skipped"

    # ── Nothing found at all in ABR ────────────────────────────────────────────
    if flat_data is None:
        logger.info("[enrich] No ABR record for ABN=%r name=%r", body.abn, body.name)
        return EnrichResult(
            abn=body.abn or "",
            abn_found=False,
            confidence_score=0,
            lookup_method=lookup_method,
            **geo,
        )

    # ── Extract ABR fields ─────────────────────────────────────────────────────
    enriched_name    = _extract_name_from_flat(flat_data)
    enriched_address = _build_address_from_flat(flat_data)
    abr_status       = _get_status_from_flat(flat_data)
    entity_type      = _get_entity_type_from_flat(flat_data)
    confirmed_abn    = _clean_abn(flat_data.get("Abn", "")) or resolved_abn

    name_disc    = _name_discrepancy(enriched_name or "", body.name)
    address_disc = _address_discrepancy(enriched_address or "", body.address)

    confidence = _compute_confidence(
        abn_found=True,
        abr_status=abr_status,
        name_discrepancy=name_disc,
        address_discrepancy=address_disc,
        has_address=bool(enriched_address),
        used_name_lookup=used_name_lookup,
    )

    logger.info(
        "[enrich] ✓ ABN=%s name=%r status=%r conf=%d geo_source=%s lat=%s lng=%s",
        confirmed_abn, enriched_name, abr_status, confidence,
        geo.get("geocode_source"), geo.get("lat"), geo.get("lng"),
    )

    return EnrichResult(
        abn=confirmed_abn,
        abn_found=True,
        enriched_name=enriched_name,
        enriched_address=enriched_address,
        abr_status=abr_status,
        entity_type=entity_type,
        name_discrepancy=name_disc,
        address_discrepancy=address_disc,
        confidence_score=confidence,
        lookup_method=lookup_method,
        **geo,
    )
