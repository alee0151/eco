"""
routes/parse_address.py  —  POST /api/parse-address

Sends a raw address string to the local Ollama LLM and returns a structured
JSON object with individual address components for GNAF geocoding.

Address scope
-------------
Only street NAME (no unit, no street number), suburb, state, and postcode
are extracted and returned.  These are the components passed to the GNAF
Addresses API v1 (GET /v1/addresses?addressString=...).

Response shape:
{
  "street":    "Collins Street",
  "suburb":    "Melbourne",
  "state":     "VIC",
  "postcode":  "3004",
  "formatted": "Collins Street Melbourne VIC 3004"
}

All fields default to "" if not present in the input.
"formatted" is ALWAYS recomputed server-side — never trusted from the LLM.

Formatting rule (GNAF addressString form):
  [street_name] suburb state postcode
  e.g. "Collins Street Melbourne VIC 3000"
       "Melbourne VIC 3000"  (no street name)

Environment variables
---------------------
OLLAMA_MODEL      Model name (default: llama3.2)
OLLAMA_BASE_URL   Ollama server URL (default: http://localhost:11434)
"""

import json
import logging
import os
import re

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ParseAddressRequest(BaseModel):
    address: str


class ParsedAddress(BaseModel):
    street:    str = ""   # street name + type only, NO unit or street number
    suburb:    str = ""
    state:     str = ""
    postcode:  str = ""
    formatted: str = ""   # server-computed GNAF addressString


# ── Prompt ────────────────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = (
    'You are an Australian address parser for a GNAF geocoding pipeline.\n'
    '\n'
    'Parse the address below into EXACTLY these JSON fields:\n'
    '\n'
    '  street    - The street NAME and TYPE ONLY (e.g. "Collins Street", "St Kilda Road",\n'
    '              "Settlement Road", "Canberra Avenue").\n'
    '              Do NOT include the street number, unit number, suite, floor, or level.\n'
    '              Empty string if there is no street component.\n'
    '  suburb    - Suburb or city name (e.g. "Melbourne", "Keperra", "Griffith").\n'
    '              Empty string if not present.\n'
    '  state     - Australian state/territory abbreviation: NSW VIC QLD SA WA TAS NT ACT.\n'
    '              Empty string if unclear.\n'
    '  postcode  - 4-digit Australian postcode. Empty string if not present.\n'
    '  formatted - Leave as empty string "". The server computes this.\n'
    '\n'
    'RULES:\n'
    '  - street must contain ONLY the street name and street type word\n'
    '    (Street, Road, Avenue, Drive, Place, Lane, Boulevard, Way, Court, etc.).\n'
    '  - Do NOT put any number in the street field.\n'
    '  - Do NOT put suburb or state into the street field.\n'
    '  - Do NOT include postcode or state in the suburb field.\n'
    '  - The formatted field MUST be left as "".\n'
    '\n'
    'Return ONLY valid JSON with exactly these 5 keys:\n'
    '  street, suburb, state, postcode, formatted\n'
    'No prose, no markdown, no explanation.\n'
    '\n'
    'Examples:\n'
    '  Input:  "Unit 3, 441 St Kilda Road, Melbourne VIC 3004"\n'
    '  Output: {{"street":"St Kilda Road","suburb":"Melbourne",'
    '"state":"VIC","postcode":"3004","formatted":""}}\n'
    '\n'
    '  Input:  "42 Settlement Road Keperra QLD 4054"\n'
    '  Output: {{"street":"Settlement Road","suburb":"Keperra",'
    '"state":"QLD","postcode":"4054","formatted":""}}\n'
    '\n'
    '  Input:  "Level 5 123 Collins Street Melbourne VIC 3000"\n'
    '  Output: {{"street":"Collins Street","suburb":"Melbourne",'
    '"state":"VIC","postcode":"3000","formatted":""}}\n'
    '\n'
    '  Input:  "Melbourne VIC 3000"\n'
    '  Output: {{"street":"","suburb":"Melbourne",'
    '"state":"VIC","postcode":"3000","formatted":""}}\n'
    '\n'
    'Address to parse:\n'
    '{address}'
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_formatted(street: str, suburb: str, state: str, postcode: str) -> str:
    """
    Build the GNAF addressString: "street_name suburb state postcode"
    All components are space-separated; empty components are omitted.

    Examples:
      street="Collins Street", suburb="Melbourne", state="VIC", postcode="3000"
        -> "Collins Street Melbourne VIC 3000"

      street="", suburb="Melbourne", state="VIC", postcode="3000"
        -> "Melbourne VIC 3000"
    """
    parts = [p for p in [street, suburb, state, postcode] if p]
    return " ".join(parts)


def _strip_fences(raw: str) -> str:
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\n?```$",       "", raw.strip())
    return raw.strip()


def _clean_field(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


# Strip leading street number from street field if LLM accidentally includes one
_LEADING_NUMBER_RE = re.compile(r"^\d+[A-Za-z]?[\s,/\\-]+")
_UNIT_PREFIX_RE    = re.compile(
    r"^(unit|u|suite|ste|level|lvl|floor|fl|apt|apartment|lot)\s+[\w/]+[\s,]+",
    re.IGNORECASE,
)


def _clean_street(street: str) -> str:
    """
    Defensive cleanup: remove any unit prefix or street number the LLM
    may have accidentally left in the street field.
    e.g. "Level 5 123 Collins Street" -> "Collins Street"
         "42 Settlement Road"         -> "Settlement Road"
    """
    s = street.strip()
    s = _UNIT_PREFIX_RE.sub("", s).strip()
    s = _LEADING_NUMBER_RE.sub("", s).strip()
    return s


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/parse-address", response_model=ParsedAddress)
async def parse_address(body: ParseAddressRequest) -> ParsedAddress:
    """
    Parse a raw address string into street name, suburb, state, postcode
    for use as a GNAF addressString.
    Unit numbers and street numbers are intentionally excluded.
    """
    raw_addr = (body.address or "").strip()
    if not raw_addr:
        return ParsedAddress()

    model    = os.getenv("OLLAMA_MODEL",    "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url      = f"{base_url}/api/generate"

    payload = {
        "model":  model,
        "prompt": _PROMPT_TEMPLATE.format(address=raw_addr),
        "stream": False,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
        resp.raise_for_status()
    except httpx.ConnectError:
        logger.warning("[parse-address] Ollama not running at %s — using raw address", url)
        return ParsedAddress(formatted=raw_addr)
    except httpx.HTTPStatusError as exc:
        logger.error("[parse-address] Ollama HTTP %s — using raw address", exc.response.status_code)
        return ParsedAddress(formatted=raw_addr)

    raw_response = resp.json().get("response", "{}")

    try:
        parsed = json.loads(_strip_fences(raw_response))
    except json.JSONDecodeError as exc:
        logger.error("[parse-address] Non-JSON from LLM: %s — %s", exc, raw_response[:200])
        return ParsedAddress(formatted=raw_addr)

    street   = _clean_street(_clean_field(parsed.get("street")))
    suburb   = _clean_field(parsed.get("suburb"))
    state    = _clean_field(parsed.get("state")).upper()
    postcode = _clean_field(parsed.get("postcode"))

    formatted = _build_formatted(street, suburb, state, postcode)

    # Fallback: if formatted is empty or useless, use raw input
    if not formatted or formatted.strip() in ("", "Australia"):
        formatted = raw_addr

    logger.info(
        "[parse-address] %r -> street=%r suburb=%r state=%r postcode=%r -> %r",
        raw_addr, street, suburb, state, postcode, formatted,
    )

    return ParsedAddress(
        street   = street,
        suburb   = suburb,
        state    = state,
        postcode = postcode,
        formatted = formatted,
    )
