"""
routes/parse_address.py  —  POST /api/parse-address

Sends a raw address string to the local Ollama LLM and returns a structured
JSON object with individual address components.

Response shape:
{
  "unit":      "12",
  "street":    "42 Wallaby Way",
  "suburb":    "Cooma",
  "state":     "NSW",
  "postcode":  "2630",
  "country":   "Australia",
  "formatted": "42 Wallaby Way, Cooma NSW 2630, Australia"
}

All fields default to "" if not present in the input.
"formatted" is recomputed from the parsed components (not trusted from LLM).

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


# ── Prompt template ──────────────────────────────────────────────────────────────
#
# NOTE: Uses single-quoted string to avoid collision with triple-quote
# delimiters when the address itself contains quotes.
# {address} is substituted via .format() at call time.

_PROMPT_TEMPLATE = (
    'You are an Australian address parser.\n'
    '\n'
    'Parse the address below into EXACTLY these JSON fields:\n'
    '  unit      - Unit, apartment, suite or level number (e.g. "12", "Suite 3", "Level 2"). Empty string if not present.\n'
    '  street    - House/building number + street name (e.g. "42 Wallaby Way"). Empty string if not present.\n'
    '  suburb    - Suburb or city name (e.g. "Sydney", "Cooma", "Port Augusta").\n'
    '  state     - Australian state/territory abbreviation: NSW, VIC, QLD, SA, WA, TAS, NT, ACT. Empty string if unclear.\n'
    '  postcode  - 4-digit Australian postcode. Empty string if not present.\n'
    '  country   - Always "Australia".\n'
    '  formatted - Clean geocodable string: "<unit> <street>, <suburb> <state> <postcode>, Australia".\n'
    '              Omit empty components. No extra punctuation.\n'
    '\n'
    'Return ONLY valid JSON with exactly these 7 keys. No prose, no markdown, no explanation.\n'
    '\n'
    'Address to parse:\n'
    '{address}'
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_formatted(parsed: dict) -> str:
    """
    Assemble a geocodable single-line address from the parsed components.
    Order: [unit] [street], [suburb] [state] [postcode], [country]
    Always recomputed from parts — never trusted from LLM output.
    """
    unit     = parsed.get("unit",     "").strip()
    street   = parsed.get("street",   "").strip()
    suburb   = parsed.get("suburb",   "").strip()
    state    = parsed.get("state",    "").strip()
    postcode = parsed.get("postcode", "").strip()
    country  = (parsed.get("country", "") or "Australia").strip()

    line1 = " ".join(p for p in [unit, street] if p)
    line2 = " ".join(p for p in [suburb, state, postcode] if p)
    return ", ".join(p for p in [line1, line2, country] if p)


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences that some models add despite format=json."""
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\n?```$",       "", raw.strip())
    return raw.strip()


# ── Endpoint ─────────────────────────────────────────────────────────────────────

@router.post("/parse-address", response_model=ParsedAddress)
async def parse_address(body: ParseAddressRequest) -> ParsedAddress:
    """
    Send raw address string to local Ollama and return structured ParsedAddress.
    Gracefully returns raw address as `formatted` if Ollama is unavailable.
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

    parsed["country"]   = "Australia"
    parsed["formatted"] = _build_formatted(parsed) or raw_addr

    logger.info(
        "[parse-address] %r → street=%r suburb=%r state=%r postcode=%r formatted=%r",
        raw_addr,
        parsed.get("street"),
        parsed.get("suburb"),
        parsed.get("state"),
        parsed.get("postcode"),
        parsed.get("formatted"),
    )

    return ParsedAddress(
        unit      = parsed.get("unit",     ""),
        street    = parsed.get("street",   ""),
        suburb    = parsed.get("suburb",   ""),
        state     = parsed.get("state",    ""),
        postcode  = parsed.get("postcode", ""),
        country   = "Australia",
        formatted = parsed["formatted"],
    )
