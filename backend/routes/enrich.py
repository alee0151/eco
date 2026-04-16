"""
routes/enrich.py  —  POST /api/enrich

Calls the Australian Business Register (ABR) ABN Lookup API using a
registered GUID key to validate and enrich supplier data.

ABR API docs:  https://abr.business.gov.au/json/
Register GUID: https://www.abr.business.gov.au/Tools/WebServices

Environment variables
---------------------
ABR_GUID   Your registered ABR Web Services GUID (required)

Endpoint behaviour
------------------
1. Strip + validate ABN format (11 digits).
2. Call ABR JSON endpoint:  searchByABN  with the GUID.
3. Parse business name, address, ABN status from response.
4. Compare with supplied name/address → set discrepancy flags.
5. Compute a confidence score (0–100).
6. Return EnrichResult.

Graceful degradation
--------------------
- If ABR_GUID is not configured → 503 with a clear setup message.
- If ABR is unreachable (network) → 503.
- If ABN is not found in ABR    → abn_found=False, rest null.
- All errors are logged; the frontend handles them gracefully.
"""

import logging
import os
import re

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# ── ABR JSON API base URL ──────────────────────────────────────────────────────
# Returns JSON — no SOAP required.  Only requires a registered GUID.
ABR_BASE = "https://abr.business.gov.au/json/"


# ── Request / Response schemas ─────────────────────────────────────────────────

class EnrichRequest(BaseModel):
    abn:     str
    name:    str = ""
    address: str = ""


class EnrichResult(BaseModel):
    abn:                 str
    abn_found:           bool
    enriched_name:       str | None = None
    enriched_address:    str | None = None
    abr_status:          str | None = None   # e.g. "Active", "Cancelled"
    name_discrepancy:    bool | None = None
    address_discrepancy: bool | None = None
    confidence_score:    int | None = None   # 0–100


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_abn(raw: str) -> str:
    """Strip spaces and hyphens; return 11-digit string or raise."""
    digits = re.sub(r"[\s\-]", "", raw)
    if not re.match(r"^\d{11}$", digits):
        raise ValueError(f"ABN '{raw}' is not 11 digits after stripping non-digits.")
    return digits


def _normalise(s: str) -> str:
    """Lowercase, collapse whitespace — used for fuzzy comparison."""
    return re.sub(r"\s+", " ", s.lower().strip())


def _name_match(abr_name: str, supplied_name: str) -> bool:
    """True if names are similar enough to not flag as a discrepancy."""
    if not supplied_name:
        return True  # no supplied name → nothing to compare
    a = _normalise(abr_name)
    b = _normalise(supplied_name)
    # Exact or substring match
    return a == b or a in b or b in a


def _address_match(abr_addr: str, supplied_addr: str) -> bool:
    """True if addresses share enough tokens to avoid flagging."""
    if not supplied_addr or not abr_addr:
        return True
    a_tokens = set(_normalise(abr_addr).split())
    b_tokens = set(_normalise(supplied_addr).split())
    if not a_tokens or not b_tokens:
        return True
    overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
    return overlap >= 0.4   # 40 % token overlap → not a discrepancy


def _build_address(abr_entity: dict) -> str | None:
    """
    Assemble a human-readable address from the ABR businessAddress block.
    ABR JSON fields: addressLine1, suburb, stateCode, postcode
    """
    addr = abr_entity.get("businessAddress", {})
    parts = [
        addr.get("addressLine1", "").strip(),
        addr.get("suburb",       "").strip(),
        addr.get("stateCode",    "").strip(),
        addr.get("postcode",     "").strip(),
    ]
    joined = ", ".join(p for p in parts if p)
    return joined if joined else None


def _extract_name(abr_entity: dict) -> str | None:
    """
    Extract the best available business name from ABR response.
    Priority: mainName → legalName → tradingName → entityTypeDescription
    """
    # mainName is present for companies; legalName for individuals
    for key in ("mainName", "legalName"):
        block = abr_entity.get(key, {})
        if isinstance(block, dict):
            name = block.get("organisationName") or (
                f"{block.get('givenName', '')} {block.get('familyName', '')}".strip()
            )
            if name:
                return name

    # tradingName array — take the first active one
    trading = abr_entity.get("tradingName")
    if isinstance(trading, list):
        for t in trading:
            if isinstance(t, dict) and t.get("organisationName"):
                return t["organisationName"]
    elif isinstance(trading, dict) and trading.get("organisationName"):
        return trading["organisationName"]

    return None


def _compute_confidence(
    abn_found: bool,
    abr_status: str | None,
    name_discrepancy: bool,
    address_discrepancy: bool,
    has_address: bool,
) -> int:
    """
    Score 0–100 reflecting how trustworthy the enriched record is.

    Scoring rubric:
      +50   ABN found in ABR
      +20   ABN status is 'Active'
      +15   Name matches (no discrepancy)
      +10   Address matches (no discrepancy)
      +5    ABR returned a full address
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
    return min(score, 100)


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/enrich", response_model=EnrichResult)
async def enrich(body: EnrichRequest) -> EnrichResult:
    """
    Validate an ABN against the ABR and return enriched supplier metadata.

    Requires ABR_GUID to be set in backend/.env
    Get your free GUID at: https://www.abr.business.gov.au/Tools/WebServices
    """
    # ── GUID guard ───────────────────────────────────────────────────────────
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

    # ── ABN format check ────────────────────────────────────────────────────
    try:
        abn_clean = _clean_abn(body.abn)
    except ValueError as exc:
        # Return a graceful not-found rather than a 422 — frontend handles it
        logger.warning("[enrich] Invalid ABN format: %s", exc)
        return EnrichResult(
            abn=body.abn,
            abn_found=False,
            confidence_score=0,
        )

    # ── ABR lookup ───────────────────────────────────────────────────────────
    # ABR JSON endpoint — searchByABN
    # Docs: https://abr.business.gov.au/json/
    params = {
        "abn":          abn_clean,
        "guid":         guid,
        "includeHistoricalDetails": "N",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{ABR_BASE}AbnDetails.aspx",
                params=params,
            )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        logger.error("[enrich] ABR unreachable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Cannot reach the ABR API. Check your internet connection.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error("[enrich] ABR HTTP error %s: %s", exc.response.status_code, exc.response.text[:300])
        raise HTTPException(
            status_code=502,
            detail=f"ABR returned HTTP {exc.response.status_code}",
        ) from exc

    # ── Parse JSON response ──────────────────────────────────────────────────
    # ABR JSON wraps the response in a callback:  callback({...})
    # When called without a callback param it returns raw JSON.
    raw_text = resp.text.strip()

    # Strip JSONP wrapper if present (some ABR endpoints still wrap)
    jsonp_match = re.match(r"^[a-zA-Z_$][\w$.]*\((.+)\);?$", raw_text, re.DOTALL)
    if jsonp_match:
        raw_text = jsonp_match.group(1)

    try:
        import json
        data = json.loads(raw_text)
    except Exception as exc:
        logger.error("[enrich] ABR non-JSON response: %s", raw_text[:300])
        raise HTTPException(status_code=502, detail=f"ABR returned unparseable response: {exc}") from exc

    # ABR wraps results in ABRPayloadSearchResults > response > businessEntity
    payload      = data.get("ABRPayloadSearchResults", data)
    response_obj = payload.get("response", payload)
    entity       = response_obj.get("businessEntity", {})

    # ── ABN not found ────────────────────────────────────────────────────────
    # ABR returns a usageStatement or exception block when ABN not found
    exception_desc = response_obj.get("exceptionDescription", "")
    if exception_desc or not entity:
        logger.info("[enrich] ABN %s not found in ABR: %s", abn_clean, exception_desc)
        return EnrichResult(
            abn=abn_clean,
            abn_found=False,
            confidence_score=0,
        )

    # ── Extract fields ───────────────────────────────────────────────────────
    abn_status_block = entity.get("entityStatus", {})
    abr_status       = abn_status_block.get("entityStatusCode", None)  # 'Active' | 'Cancelled' | ...

    enriched_name    = _extract_name(entity)
    enriched_address = _build_address(entity)

    # ── Discrepancy flags ────────────────────────────────────────────────────
    name_discrepancy    = not _name_match(enriched_name or "",    body.name)
    address_discrepancy = not _address_match(enriched_address or "", body.address)

    confidence = _compute_confidence(
        abn_found=True,
        abr_status=abr_status,
        name_discrepancy=name_discrepancy,
        address_discrepancy=address_discrepancy,
        has_address=bool(enriched_address),
    )

    logger.info(
        "[enrich] ABN %s → name=%r status=%r conf=%d discrepancy(name=%s addr=%s)",
        abn_clean, enriched_name, abr_status, confidence,
        name_discrepancy, address_discrepancy,
    )

    return EnrichResult(
        abn=abn_clean,
        abn_found=True,
        enriched_name=enriched_name,
        enriched_address=enriched_address,
        abr_status=abr_status,
        name_discrepancy=name_discrepancy,
        address_discrepancy=address_discrepancy,
        confidence_score=confidence,
    )
