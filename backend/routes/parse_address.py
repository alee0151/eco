"""
routes/parse_address.py  —  POST /api/parse-address

Sends a raw address string to the local Ollama LLM and returns a structured
JSON object with individual address components.

Response shape:
{
  "unit":      "12",
  "street":    "441 St Kilda Road",
  "suburb":    "Melbourne",
  "state":     "VIC",
  "postcode":  "3004",
  "country":   "Australia",
  "formatted": "441 St Kilda Road, Melbourne VIC 3004, Australia"
}

All fields default to "" if not present in the input.
"formatted" is ALWAYS recomputed server-side from parsed components —
never trusted from the LLM.

Formatting rule (canonical geocodable form):
  [unit] [street], [suburb] [state] [postcode], Australia

Examples:
  street=441 St Kilda Road, suburb=Melbourne, state=VIC, postcode=3004
  → "441 St Kilda Road, Melbourne VIC 3004, Australia"

  unit=Suite 3, street=42 Wallaby Way, suburb=Cooma, state=NSW, postcode=2630
  → "Suite 3 42 Wallaby Way, Cooma NSW 2630, Australia"

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
    unit:      str = ""
    street:    str = ""
    suburb:    str = ""
    state:     str = ""
    postcode:  str = ""
    country:   str = "Australia"
    formatted: str = ""


# ── Prompt ────────────────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = (
    'You are an Australian address parser.\n'
    '\n'
    'Parse the address below into EXACTLY these JSON fields:\n'
    '\n'
    '  unit      - Unit, apartment, suite or level number (e.g. "12", "Suite 3", "Level 2").\n'
    '              Empty string if not present.\n'
    '  street    - Building/house NUMBER plus STREET NAME (e.g. "441 St Kilda Road", "1 Martin Place").\n'
    '              MUST include the number if it appears in the input.\n'
    '              Empty string only if there is genuinely no street component.\n'
    '  suburb    - Suburb or city name (e.g. "Melbourne", "Sydney", "Cooma", "Port Augusta").\n'
    '              Empty string if not present.\n'
    '  state     - Australian state/territory abbreviation: NSW VIC QLD SA WA TAS NT ACT.\n'
    '              Empty string if unclear.\n'
    '  postcode  - 4-digit Australian postcode. Empty string if not present.\n'
    '  country   - Always "Australia".\n'
    '\n'
    'RULES:\n'
    '  - Do NOT put the suburb or state into the street field.\n'
    '  - Do NOT leave street empty if a street name exists in the input.\n'
    '  - Do NOT include postcode or state in the suburb field.\n'
    '  - The formatted field is NOT required — leave it as an empty string "".\n'
    '    The server will compute it correctly.\n'
    '\n'
    'Return ONLY valid JSON with exactly these 7 keys:\n'
    '  unit, street, suburb, state, postcode, country, formatted\n'
    'No prose, no markdown, no explanation.\n'
    '\n'
    'Examples:\n'
    '  Input:  "441 St Kilda Road, Melbourne VIC 3004"\n'
    '  Output: {{"unit":"","street":"441 St Kilda Road","suburb":"Melbourne",'
    '"state":"VIC","postcode":"3004","country":"Australia","formatted":""}}\n'
    '\n'
    '  Input:  "Suite 3, 42 Wallaby Way, Cooma NSW 2630, Australia"\n'
    '  Output: {{"unit":"Suite 3","street":"42 Wallaby Way","suburb":"Cooma",'
    '"state":"NSW","postcode":"2630","country":"Australia","formatted":""}}\n'
    '\n'
    '  Input:  "Level 5 123 Collins Street Melbourne VIC 3000"\n'
    '  Output: {{"unit":"Level 5","street":"123 Collins Street","suburb":"Melbourne",'
    '"state":"VIC","postcode":"3000","country":"Australia","formatted":""}}\n'
    '\n'
    'Address to parse:\n'
    '{address}'
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_formatted(unit: str, street: str, suburb: str, state: str, postcode: str) -> str:
    """
    Build a canonical geocodable single-line address.

    Format: "[unit ]street, suburb state postcode, Australia"

    Examples:
      street=441 St Kilda Road, suburb=Melbourne, state=VIC, postcode=3004
        → "441 St Kilda Road, Melbourne VIC 3004, Australia"

      unit=Suite 3, street=42 Wallaby Way, suburb=Cooma, state=NSW, postcode=2630
        → "Suite 3 42 Wallaby Way, Cooma NSW 2630, Australia"

    Only non-empty components are included; no double spaces or trailing commas.
    """
    # Part 1: unit + street (space-separated)
    street_part = " ".join(p for p in [unit, street] if p)

    # Part 2: suburb + state + postcode (space-separated, suburb first)
    locality_part = " ".join(p for p in [suburb, state, postcode] if p)

    # Join with ", " only between non-empty parts
    parts = [p for p in [street_part, locality_part, "Australia"] if p]
    return ", ".join(parts)


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences that some models add despite format=json."""
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\n?```$",       "", raw.strip())
    return raw.strip()


def _clean_field(value: object) -> str:
    """Coerce LLM output to a clean string, stripping None / non-string values."""
    if value is None:
        return ""
    return str(value).strip()


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/parse-address", response_model=ParsedAddress)
async def parse_address(body: ParseAddressRequest) -> ParsedAddress:
    """
    Parse a raw address string into structured components via Ollama LLM.
    The `formatted` field is always recomputed server-side — never taken
    from the LLM response.
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
        return ParsedAddress(formatted=raw_addr, country="Australia")
    except httpx.HTTPStatusError as exc:
        logger.error("[parse-address] Ollama HTTP %s — using raw address", exc.response.status_code)
        return ParsedAddress(formatted=raw_addr, country="Australia")

    raw_response = resp.json().get("response", "{}")

    try:
        parsed = json.loads(_strip_fences(raw_response))
    except json.JSONDecodeError as exc:
        logger.error("[parse-address] Non-JSON from LLM: %s — %s", exc, raw_response[:200])
        return ParsedAddress(formatted=raw_addr, country="Australia")

    # Extract and clean every field
    unit     = _clean_field(parsed.get("unit"))
    street   = _clean_field(parsed.get("street"))
    suburb   = _clean_field(parsed.get("suburb"))
    state    = _clean_field(parsed.get("state")).upper()
    postcode = _clean_field(parsed.get("postcode"))

    # Sanity guard: if the LLM put suburb/state in the street field,
    # and we have a suburb separately, clear the contamination.
    # (e.g. street="Melbourne VIC" when input was "VIC, 3004")
    if street and not suburb and not postcode:
        # street might actually be suburb+state — leave as-is, geocoder handles it
        pass

    # Always recompute formatted — never trust the LLM value
    formatted = _build_formatted(unit, street, suburb, state, postcode)

    # Last-resort: if formatted is just ", Australia" or "Australia", fall back to raw
    if not formatted or formatted in (", Australia", "Australia"):
        formatted = raw_addr

    logger.info(
        "[parse-address] %r → unit=%r street=%r suburb=%r state=%r postcode=%r → %r",
        raw_addr, unit, street, suburb, state, postcode, formatted,
    )

    return ParsedAddress(
        unit      = unit,
        street    = street,
        suburb    = suburb,
        state     = state,
        postcode  = postcode,
        country   = "Australia",
        formatted = formatted,
    )
