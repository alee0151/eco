"""
routes/enrich.py  —  POST /api/enrich

Two-stage ABR enrichment pipeline using the official JSON endpoints:

  Stage 1 — ABN Lookup (when a valid 11-digit ABN is present)
    GET https://abr.business.gov.au/json/AbnDetails.aspx
        ?abn=<11digits>&callback=callback&guid=<GUID>
    → Returns full entity record: name, address, status.

  Stage 2 — Name Lookup fallback (when ABN is missing/invalid OR Stage 1 finds nothing)
    GET https://abr.business.gov.au/json/MatchingNames.aspx
        ?name=<supplier+name>&maxResults=10&callback=callback&guid=<GUID>
    → Returns list of matching entities; we pick the best ABN match.
    → If a match is found, we re-run Stage 1 with the matched ABN for full details.

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
from urllib.parse import quote_plus

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# ── ABR JSON API endpoints (exact URLs provided) ─────────────────────────────────
ABR_ABN_URL   = "https://abr.business.gov.au/json/AbnDetails.aspx"
ABR_NAME_URL  = "https://abr.business.gov.au/json/MatchingNames.aspx"
CALLBACK_NAME = "callback"   # JSONP callback param — ABR always wraps in this


# ── Request / Response schemas ──────────────────────────────────────────────────

class EnrichRequest(BaseModel):
    abn:     str  = ""
    name:    str  = ""
    address: str  = ""


class EnrichResult(BaseModel):
    abn:                 str
    abn_found:           bool
    enriched_name:       str | None = None
    enriched_address:    str | None = None
    abr_status:          str | None = None   # "Active" | "Cancelled" | ...
    name_discrepancy:    bool | None = None
    address_discrepancy: bool | None = None
    confidence_score:    int  | None = None  # 0–100
    lookup_method:       str  | None = None  # "abn" | "name" | "name+abn"


# ── JSONP stripper ─────────────────────────────────────────────────────────────────

def _strip_jsonp(text: str) -> str:
    """
    ABR always wraps its JSON in a JSONP callback, e.g.:
        callback({...})
    Strip the wrapper and return raw JSON.
    Also handles optional trailing semicolon.
    """
    text = text.strip()
    # Match:  identifier(   ...JSON...   );
    m = re.match(r"^[a-zA-Z_$][\w$.]*\s*\((.+)\)\s*;?\s*$", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text  # already raw JSON (e.g. future ABR upgrade)


def _parse_abr_json(raw_text: str) -> dict:
    """Strip JSONP wrapper and parse JSON; raise HTTPException on failure."""
    try:
        return json.loads(_strip_jsonp(raw_text))
    except Exception as exc:
        logger.error("[enrich] ABR unparseable response: %s", raw_text[:300])
        raise HTTPException(
            status_code=502,
            detail=f"ABR returned unparseable response: {exc}",
        ) from exc


# ── ABN helpers ────────────────────────────────────────────────────────────────────

def _clean_abn(raw: str) -> str | None:
    """Return 11-digit ABN string or None if format is invalid."""
    digits = re.sub(r"[\s\-]", "", raw or "")
    return digits if re.match(r"^\d{11}$", digits) else None


# ── Field extractors from ABR AbnDetails entity block ──────────────────────────

def _extract_name(entity: dict) -> str | None:
    """
    Extract best available business name from AbnDetails entity block.
    Priority: mainName.organisationName
              → legalName.organisationName
              → legalName.givenName + familyName
              → tradingName[0].organisationName
    """
    for key in ("mainName", "legalName"):
        block = entity.get(key)
        if isinstance(block, dict):
            name = block.get("organisationName", "").strip()
            if name:
                return name
            given  = block.get("givenName",  "").strip()
            family = block.get("familyName", "").strip()
            full   = f"{given} {family}".strip()
            if full:
                return full

    trading = entity.get("tradingName")
    if isinstance(trading, list):
        for t in trading:
            if isinstance(t, dict):
                n = t.get("organisationName", "").strip()
                if n:
                    return n
    elif isinstance(trading, dict):
        n = trading.get("organisationName", "").strip()
        if n:
            return n

    return None


def _build_address(entity: dict) -> str | None:
    """
    Assemble geocodable address string from ABR businessAddress block.
    ABR fields: addressLine1, suburb, stateCode, postcode
    """
    addr = entity.get("businessAddress", {})
    if not isinstance(addr, dict):
        return None
    parts = [
        addr.get("addressLine1", "").strip(),
        addr.get("suburb",       "").strip(),
        addr.get("stateCode",    "").strip(),
        addr.get("postcode",     "").strip(),
    ]
    joined = ", ".join(p for p in parts if p)
    return joined or None


def _get_abr_status(entity: dict) -> str | None:
    """Return entityStatusCode from entityStatus block."""
    block = entity.get("entityStatus", {})
    if isinstance(block, dict):
        return block.get("entityStatusCode")   # "Active" | "Cancelled" | ...
    return None


def _get_entity_from_abn_response(data: dict) -> dict | None:
    """
    Navigate ABR AbnDetails response structure:
      ABRPayloadSearchResults.response.businessEntity
    Returns the entity dict or None if not found / exception returned.
    """
    payload      = data.get("ABRPayloadSearchResults", data)
    response_obj = payload.get("response", payload)
    if response_obj.get("exceptionDescription"):
        return None
    entity = response_obj.get("businessEntity")
    return entity if isinstance(entity, dict) and entity else None


# ── Fuzzy comparison helpers ─────────────────────────────────────────────────────

def _normalise(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _name_discrepancy(abr_name: str, supplied_name: str) -> bool:
    """True = names do NOT match well enough (flag as discrepancy)."""
    if not supplied_name:
        return False   # nothing to compare
    a, b = _normalise(abr_name), _normalise(supplied_name)
    return not (a == b or a in b or b in a)


def _address_discrepancy(abr_addr: str, supplied_addr: str) -> bool:
    """True = addresses share < 40 % token overlap (flag as discrepancy)."""
    if not supplied_addr or not abr_addr:
        return False
    a_tok = set(_normalise(abr_addr).split())
    b_tok = set(_normalise(supplied_addr).split())
    if not a_tok or not b_tok:
        return False
    overlap = len(a_tok & b_tok) / max(len(a_tok), len(b_tok))
    return overlap < 0.4


# ── Confidence scoring ───────────────────────────────────────────────────────────────

def _compute_confidence(
    abn_found:          bool,
    abr_status:         str | None,
    name_discrepancy:   bool,
    address_discrepancy: bool,
    has_address:        bool,
    used_name_lookup:   bool,
) -> int:
    """
    0–100 score reflecting enrichment trustworthiness.

    +50   ABN confirmed in ABR
    +20   Status is Active
    +15   Name matches (no discrepancy)
    +10   Address matches (no discrepancy)
    +5    Full address returned by ABR
    -10   Name-lookup fallback used (lower certainty than direct ABN hit)
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
        score -= 10   # penalty: matched by name, not by ABN directly
    return max(0, min(score, 100))


# ── ABR HTTP calls ───────────────────────────────────────────────────────────────────

async def _abr_lookup_by_abn(client: httpx.AsyncClient, abn: str, guid: str) -> dict | None:
    """
    Stage 1: GET AbnDetails.aspx?abn=<11digits>&callback=callback&guid=<GUID>
    Returns the parsed entity dict or None if not found.
    """
    try:
        resp = await client.get(
            ABR_ABN_URL,
            params={
                "abn":      abn,
                "callback": CALLBACK_NAME,
                "guid":     guid,
            },
        )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail="Cannot reach the ABR API. Check your internet connection.") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"ABR returned HTTP {exc.response.status_code}") from exc

    data = _parse_abr_json(resp.text)
    return _get_entity_from_abn_response(data)


async def _abr_lookup_by_name(client: httpx.AsyncClient, name: str, guid: str) -> list[dict]:
    """
    Stage 2: GET MatchingNames.aspx?name=<name>&maxResults=10&callback=callback&guid=<GUID>
    Returns list of matching name records (each has Abn, Name, State, Postcode, Type).
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
    except (httpx.ConnectError, httpx.HTTPStatusError):
        return []   # name lookup failure is non-fatal; just return empty

    data = _parse_abr_json(resp.text)

    # MatchingNames response structure:
    # ABRPayloadSearchResults.response.searchResultsList.searchResultsRecord[]
    payload   = data.get("ABRPayloadSearchResults", data)
    resp_obj  = payload.get("response", {})
    results   = resp_obj.get("searchResultsList", {}).get("searchResultsRecord", [])
    if isinstance(results, dict):
        results = [results]   # single result returned as object, not list
    return results if isinstance(results, list) else []


def _best_name_match(records: list[dict], supplied_name: str) -> dict | None:
    """
    From MatchingNames results, pick the record whose Name is closest
    to the supplied name using token overlap.
    Returns the best record dict or None.
    """
    if not records:
        return None
    supplied_tok = set(_normalise(supplied_name).split())
    best_record  = None
    best_score   = 0.0
    for rec in records:
        candidate = _normalise(rec.get("Name", ""))
        cand_tok  = set(candidate.split())
        if not cand_tok:
            continue
        overlap = len(supplied_tok & cand_tok) / max(len(supplied_tok), len(cand_tok))
        if overlap > best_score:
            best_score  = overlap
            best_record = rec
    # Require at least 30 % overlap to accept the match
    return best_record if best_score >= 0.3 else None


# ── Main endpoint ─────────────────────────────────────────────────────────────────────

@router.post("/enrich", response_model=EnrichResult)
async def enrich(body: EnrichRequest) -> EnrichResult:
    """
    Two-stage ABR enrichment:

    Stage 1 — Direct ABN lookup (AbnDetails.aspx)
      Called when a valid 11-digit ABN is provided.
      Returns full entity: name, address, status, entity type.

    Stage 2 — Name-based fallback (MatchingNames.aspx)
      Called when:
        (a) No valid ABN was supplied, OR
        (b) Stage 1 returned abn_found=False
      Searches by company name, picks the closest match,
      then re-runs Stage 1 with the matched ABN for full details.
    """

    # ── GUID guard ────────────────────────────────────────────────────────────
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
    entity: dict | None = None
    resolved_abn     = abn_clean or ""
    used_name_lookup = False
    lookup_method    = "abn"

    async with httpx.AsyncClient(timeout=15) as client:

        # ── Stage 1: Direct ABN lookup ──────────────────────────────────────────
        if abn_clean:
            logger.info("[enrich] Stage 1: ABN lookup for %s", abn_clean)
            entity = await _abr_lookup_by_abn(client, abn_clean, guid)
            if entity:
                lookup_method = "abn"
                logger.info("[enrich] Stage 1 hit for ABN %s", abn_clean)

        # ── Stage 2: Name fallback ───────────────────────────────────────────────
        # Triggered if: no valid ABN supplied  OR  Stage 1 returned nothing
        if entity is None and body.name.strip():
            logger.info("[enrich] Stage 2: name lookup for %r", body.name.strip())
            name_records = await _abr_lookup_by_name(client, body.name.strip(), guid)
            best = _best_name_match(name_records, body.name)

            if best:
                matched_abn = _clean_abn(best.get("Abn", ""))
                if matched_abn:
                    logger.info(
                        "[enrich] Stage 2 matched %r → ABN %s (name: %s)",
                        body.name, matched_abn, best.get("Name"),
                    )
                    # Re-run Stage 1 with the matched ABN for full details
                    entity = await _abr_lookup_by_abn(client, matched_abn, guid)
                    if entity:
                        resolved_abn     = matched_abn
                        used_name_lookup = True
                        lookup_method    = "name+abn"
                    else:
                        # Stage 1 miss after name match: use name record directly
                        resolved_abn     = matched_abn
                        used_name_lookup = True
                        lookup_method    = "name"
                        # Build a minimal entity from MatchingNames record
                        entity = {
                            "mainName": {"organisationName": best.get("Name", "")},
                            "businessAddress": {
                                "stateCode": best.get("State",    ""),
                                "postcode":  best.get("Postcode", ""),
                            },
                            "entityStatus": {"entityStatusCode": "Active"},
                        }

    # ── Nothing found ──────────────────────────────────────────────────────────────────
    if entity is None:
        logger.info(
            "[enrich] No ABR record found for ABN=%r name=%r",
            body.abn, body.name,
        )
        return EnrichResult(
            abn=body.abn or "",
            abn_found=False,
            confidence_score=0,
            lookup_method=lookup_method,
        )

    # ── Extract enriched fields ────────────────────────────────────────────────────
    enriched_name    = _extract_name(entity)
    enriched_address = _build_address(entity)
    abr_status       = _get_abr_status(entity)

    name_disc    = _name_discrepancy(enriched_name or "",    body.name)
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
        "[enrich] ✓ ABN=%s method=%s name=%r status=%r conf=%d "
        "discrepancy(name=%s addr=%s)",
        resolved_abn, lookup_method, enriched_name, abr_status,
        confidence, name_disc, address_disc,
    )

    return EnrichResult(
        abn=resolved_abn,
        abn_found=True,
        enriched_name=enriched_name,
        enriched_address=enriched_address,
        abr_status=abr_status,
        name_discrepancy=name_disc,
        address_discrepancy=address_disc,
        confidence_score=confidence,
        lookup_method=lookup_method,
    )
