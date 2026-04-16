"""
routes/enrich.py  —  POST /api/enrich

Two-stage ABR enrichment pipeline using the official JSON endpoints:

  Stage 1 — ABN Lookup (when a valid 11-digit ABN is present)
    GET https://abr.business.gov.au/json/AbnDetails.aspx
        ?abn=<11digits>&callback=callback&guid=<GUID>

    Real response shape (flat, inside JSONP wrapper):
    {
      "Abn": "17090574431",
      "AbnStatus": "Active",
      "AbnStatusEffectiveFrom": "2001-06-27",
      "Acn": "090574431",
      "AddressDate": "2016-11-14",
      "AddressPostcode": "2630",
      "AddressState": "NSW",
      "BusinessName": [],
      "EntityName": "SNOWY HYDRO LIMITED",
      "EntityTypeCode": "PUB",
      "EntityTypeName": "Australian Public Company",
      "Gst": "2001-06-27",
      "Message": ""
    }

  Stage 2 — Name Lookup fallback (when ABN is missing/invalid OR Stage 1 finds nothing)
    GET https://abr.business.gov.au/json/MatchingNames.aspx
        ?name=<supplier+name>&maxResults=10&callback=callback&guid=<GUID>
    → Returns list of matching entities; we pick the best name match.
    → If a match is found, re-run Stage 1 with the matched ABN for full details.

Environment variables
---------------------
ABR_GUID   Your registered ABR Web Services GUID (required)
           Register free at: https://www.abr.business.gov.au/Tools/WebServices

Graceful degradation
--------------------
- ABR_GUID not configured  →  503 with setup instructions
- ABR unreachable          →  503
- ABN not found + no name match →  abn_found=False, confidence=0
- All errors logged; frontend handles them without crashing
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


# ── Request / Response schemas ─────────────────────────────────────────────────

class EnrichRequest(BaseModel):
    abn:     str = ""
    name:    str = ""
    address: str = ""


class EnrichResult(BaseModel):
    abn:                 str
    abn_found:           bool
    enriched_name:       str | None = None
    enriched_address:    str | None = None
    abr_status:          str | None = None   # "Active" | "Cancelled" | ...
    entity_type:         str | None = None   # e.g. "Australian Public Company"
    name_discrepancy:    bool | None = None
    address_discrepancy: bool | None = None
    confidence_score:    int  | None = None  # 0–100
    lookup_method:       str  | None = None  # "abn" | "name" | "name+abn"


# ── JSONP stripper ────────────────────────────────────────────────────────────────

def _strip_jsonp(text: str) -> str:
    """
    ABR wraps every response in a JSONP callback:  callback({...})
    Strip the wrapper and return raw JSON.
    """
    text = text.strip()
    m = re.match(r"^[a-zA-Z_$][\w$.]*\s*\((.+)\)\s*;?\s*$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def _parse_abr_json(raw_text: str) -> dict | list:
    """Strip JSONP and parse JSON; raise 502 on failure."""
    try:
        return json.loads(_strip_jsonp(raw_text))
    except Exception as exc:
        logger.error("[enrich] ABR unparseable response: %s", raw_text[:300])
        raise HTTPException(
            status_code=502,
            detail=f"ABR returned unparseable response: {exc}",
        ) from exc


# ── ABN cleaner ─────────────────────────────────────────────────────────────────────

def _clean_abn(raw: str) -> str | None:
    """Strip spaces/hyphens; return 11-digit string or None."""
    digits = re.sub(r"[\s\-]", "", raw or "")
    return digits if re.match(r"^\d{11}$", digits) else None


# ── Field extractors for REAL AbnDetails flat response ─────────────────────────
#
# Real ABR AbnDetails.aspx response (flat JSON, no nested entity block):
#   Abn              – 11-digit string
#   AbnStatus        – "Active" | "Cancelled" | ...
#   EntityName       – primary legal/trading name
#   BusinessName     – list of additional trading names (may be [])
#   AddressState     – state code e.g. "NSW"
#   AddressPostcode  – 4-digit postcode string
#   EntityTypeName   – e.g. "Australian Public Company"
#   Message          – non-empty string means error / not found
# ─────────────────────────────────────────────────────────────────────────

def _is_abn_found(data: dict) -> bool:
    """
    ABR signals ABN-not-found by setting Message to a non-empty string
    (e.g. "Search text is not a valid ABN or ACN") AND leaving
    EntityName empty.  An empty Message + non-empty EntityName = found.
    """
    message     = (data.get("Message") or "").strip()
    entity_name = (data.get("EntityName") or "").strip()
    return (not message) and bool(entity_name)


def _extract_name_from_flat(data: dict) -> str | None:
    """
    Extract best name from the flat AbnDetails response.
    Priority: EntityName → first entry in BusinessName list.
    """
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
    Build a geocodable address string from the flat AbnDetails response.
    ABR provides only AddressState + AddressPostcode in this endpoint
    (no street-level address in the JSON API).
    Returns e.g. "NSW 2630, Australia"
    """
    state    = (data.get("AddressState")    or "").strip()
    postcode = (data.get("AddressPostcode") or "").strip()
    parts    = [p for p in [state, postcode] if p]
    return ", ".join(parts) + ", Australia" if parts else None


def _get_status_from_flat(data: dict) -> str | None:
    """Return AbnStatus field e.g. 'Active' | 'Cancelled'."""
    return (data.get("AbnStatus") or "").strip() or None


def _get_entity_type_from_flat(data: dict) -> str | None:
    """Return EntityTypeName e.g. 'Australian Public Company'."""
    return (data.get("EntityTypeName") or "").strip() or None


# ── MatchingNames response parser ──────────────────────────────────────────────────

def _parse_name_results(data: dict | list) -> list[dict]:
    """
    MatchingNames returns either:
      { "Names": [ {"Abn":"...", "Name":"...", "State":"...", "Postcode":"..."}, ... ] }
    or a direct list.  Normalise to a list of dicts.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common wrapper keys
        for key in ("Names", "names", "ABRPayloadSearchResults"):
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                # Dig one level deeper for nested wrappers
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
    abn_found:           bool,
    abr_status:          str | None,
    name_discrepancy:    bool,
    address_discrepancy: bool,
    has_address:         bool,
    used_name_lookup:    bool,
) -> int:
    """
    +50  ABN confirmed in ABR
    +20  Status is Active
    +15  Name matches (no discrepancy)
    +10  Address matches (no discrepancy)
    +5   ABR returned address data
    -10  Name-lookup fallback used (lower certainty)
    """
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


# ── ABR HTTP helpers ─────────────────────────────────────────────────────────────────

async def _abr_lookup_by_abn(client: httpx.AsyncClient, abn: str, guid: str) -> dict | None:
    """
    Stage 1: AbnDetails.aspx
    Returns the flat data dict if ABN is found, or None.
    """
    try:
        resp = await client.get(
            ABR_ABN_URL,
            params={"abn": abn, "callback": CALLBACK_NAME, "guid": guid},
        )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail="Cannot reach the ABR API.") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"ABR returned HTTP {exc.response.status_code}") from exc

    data = _parse_abr_json(resp.text)
    if not isinstance(data, dict):
        return None
    return data if _is_abn_found(data) else None


async def _abr_lookup_by_name(client: httpx.AsyncClient, name: str, guid: str) -> list[dict]:
    """
    Stage 2: MatchingNames.aspx
    Returns list of candidate records; each has Abn, Name, State, Postcode.
    Non-fatal: returns [] on any network/parse error.
    """
    try:
        resp = await client.get(
            ABR_NAME_URL,
            params={
                "name":       name,
                "maxResults": "10",
                "callback":   CALLBACK_NAME,
                "guid":       guid,
            },
        )
        resp.raise_for_status()
        data = _parse_abr_json(resp.text)
        return _parse_name_results(data)
    except Exception:
        return []


def _best_name_match(records: list[dict], supplied_name: str) -> dict | None:
    """Pick the record with the highest token-overlap vs supplied_name (≥30%)."""
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


# ── Main endpoint ───────────────────────────────────────────────────────────────────

@router.post("/enrich", response_model=EnrichResult)
async def enrich(body: EnrichRequest) -> EnrichResult:
    """
    Two-stage ABR enrichment.

    Stage 1 (AbnDetails.aspx)  — direct ABN hit, returns full flat record.
    Stage 2 (MatchingNames.aspx) — name-based fallback when ABN invalid/absent;
      picks best token-overlap match, then re-runs Stage 1 for full details.
    """
    guid = os.getenv("ABR_GUID", "").strip()
    if not guid:
        raise HTTPException(
            status_code=503,
            detail=(
                "ABR_GUID is not configured. "
                "Register at https://www.abr.business.gov.au/Tools/WebServices "
                "and add ABR_GUID=<your-guid> to backend/.env"
            ),
        )

    abn_clean        = _clean_abn(body.abn)
    flat_data: dict | None = None
    resolved_abn     = abn_clean or ""
    used_name_lookup = False
    lookup_method    = "abn"

    async with httpx.AsyncClient(timeout=15) as client:

        # ── Stage 1: direct ABN lookup ──────────────────────────────────────────
        if abn_clean:
            logger.info("[enrich] Stage 1: ABN lookup %s", abn_clean)
            flat_data = await _abr_lookup_by_abn(client, abn_clean, guid)
            if flat_data:
                lookup_method = "abn"
                logger.info("[enrich] Stage 1 hit: %s", flat_data.get("EntityName"))

        # ── Stage 2: name fallback ──────────────────────────────────────────────
        if flat_data is None and body.name.strip():
            logger.info("[enrich] Stage 2: name lookup %r", body.name.strip())
            records = await _abr_lookup_by_name(client, body.name.strip(), guid)
            best = _best_name_match(records, body.name)

            if best:
                matched_abn = _clean_abn(best.get("Abn", ""))
                logger.info(
                    "[enrich] Stage 2 matched %r → ABN %s (ABR name: %s)",
                    body.name, matched_abn, best.get("Name"),
                )
                if matched_abn:
                    # Re-run Stage 1 with the matched ABN for full flat record
                    flat_data = await _abr_lookup_by_abn(client, matched_abn, guid)
                    resolved_abn     = matched_abn
                    used_name_lookup = True
                    lookup_method    = "name+abn" if flat_data else "name"

                if not flat_data:
                    # Stage 1 miss: build minimal flat record from MatchingNames entry
                    flat_data = {
                        "Abn":            resolved_abn,
                        "AbnStatus":      "Active",
                        "EntityName":     best.get("Name", ""),
                        "AddressState":   best.get("State",    ""),
                        "AddressPostcode": best.get("Postcode", ""),
                        "EntityTypeName": "",
                        "BusinessName":   [],
                        "Message":        "",
                    }

    # ── Nothing found at all ────────────────────────────────────────────────────────
    if flat_data is None:
        logger.info("[enrich] No ABR record for ABN=%r name=%r", body.abn, body.name)
        return EnrichResult(
            abn=body.abn or "",
            abn_found=False,
            confidence_score=0,
            lookup_method=lookup_method,
        )

    # ── Extract fields from flat response ─────────────────────────────────────────
    enriched_name    = _extract_name_from_flat(flat_data)
    enriched_address = _build_address_from_flat(flat_data)
    abr_status       = _get_status_from_flat(flat_data)
    entity_type      = _get_entity_type_from_flat(flat_data)

    # Use the ABN from the response if it resolves differently
    confirmed_abn = _clean_abn(flat_data.get("Abn", "")) or resolved_abn

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
        "[enrich] ✓ ABN=%s method=%s name=%r status=%r type=%r conf=%d "
        "discrepancy(name=%s addr=%s)",
        confirmed_abn, lookup_method, enriched_name, abr_status,
        entity_type, confidence, name_disc, address_disc,
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
    )
