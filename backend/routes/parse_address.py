"""
routes/parse_address.py  —  POST /api/parse-address

Sends a raw address string to the local Ollama LLM and returns a structured
JSON object with individual address components.

Response shape:
{
  "unit":     "12",
  "street":   "Main Street",
  "suburb":   "Cooma",
  "state":    "NSW",
  "postcode": "2630",
  "country":  "Australia",
  "formatted": "12 Main Street, Cooma NSW 2630, Australia"
}

All fields default to "" if not present in the input.
"formatted" is the geocodable string built from the parsed components.

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
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ParseAddressRequest(BaseModel):
    address: str   # raw address string from OCR/LLM extraction


class ParsedAddress(BaseModel):
    unit:      str = ""   # unit / apartment / suite number
    street:    str = ""   # house number + street name
    suburb:    str = ""   # suburb or city
    state:     str = ""   # state abbreviation e.g. NSW, VIC, QLD
    postcode:  str = ""   # 4-digit Australian postcode
    country:   str = "Australia"
    formatted: str = ""   # geocodable single-line address


# ── Prompt ────────────────────────────────────────────────────────────────────

PARSE_ADDRESS_PROMPT = """\
You are an Australian address parser.

Parse the address below into EXACTLY these JSON fields:
  unit      - Unit, apartment, suite or level number (e.g. "12", "Suite 3", "Level 2"). Empty string if not present.
  street    - House/building number + street name (e.g. "42 Wallaby Way"). Empty string if not present.
  suburb    - Suburb or city name (e.g. "Sydney", "Cooma", "Port Augusta").
  state     - Australian state or territory abbreviation: NSW, VIC, QLD, SA, WA, TAS, NT, ACT. Empty string if unclear.
  postcode  - 4-digit Australian postcode. Empty string if not present.
  country   - Always "Australia".
  formatted - A clean geocodable address string assembled from the above components in this order:
              "<unit> <street>, <suburb> <state> <postcode>, Australia"
              Omit any component that is empty. Do not add extra punctuation.

Return ONLY valid JSON with exactly these 7 keys. No prose, no markdown fences, no explanation.

Address to parse:
"""{address}"""
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_formatted(parsed: dict) -> str:
    """
    Assemble a geocodable single-line address from the parsed components.
    Order: [unit] [street], [suburb] [state] [postcode], [country]
    """
    unit     = parsed.get("unit",     "").strip()
    street   = parsed.get("street",   "").strip()
    suburb   = parsed.get("suburb",   "").strip()
    state    = parsed.get("state",    "").strip()
    postcode = parsed.get("postcode", "").strip()
    country  = parsed.get("country",  "Australia").strip() or "Australia"

    line1_parts = [p for p in [unit, street] if p]
    line1       = " ".join(line1_parts)

    line2_parts = [p for p in [suburb, state, postcode] if p]
    line2       = " ".join(line2_parts)

    parts = [p for p in [line1, line2, country] if p]
    return ", ".join(parts)


def _clean_json(raw: str) -> str:
    """Strip markdown code fences if the model ignores format=json."""
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\n?```$",       "", raw.strip())
    return raw.strip()


# ── Endpoint ─────────────────────────────────────────────────────────────────────

@router.post("/parse-address", response_model=ParsedAddress)
async def parse_address(body: ParseAddressRequest) -> ParsedAddress:
    """
    Send a raw address string to the local Ollama LLM and return
    a structured ParsedAddress with individual components + a
    formatted geocodable string.

    Returns a best-effort empty ParsedAddress (with formatted=address)
    if Ollama is unavailable rather than crashing the enrichment pipeline.
    """
    raw_addr = (body.address or "").strip()
    if not raw_addr:
        return ParsedAddress()

    model    = os.getenv("OLLAMA_MODEL",    "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url      = f"{base_url}/api/generate"

    payload = {
        "model":  model,
        "prompt": PARSE_ADDRESS_PROMPT.format(address=raw_addr),
        "stream": False,
        "format": "json",   # Ollama native JSON mode
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
        resp.raise_for_status()
    except httpx.ConnectError:
        # Ollama not running — return graceful fallback so enrichment continues
        logger.warning("[parse-address] Ollama unavailable at %s — returning raw address", url)
        return ParsedAddress(formatted=raw_addr, country="Australia")
    except httpx.HTTPStatusError as exc:
        logger.error("[parse-address] Ollama HTTP %s: %s", exc.response.status_code, exc.response.text[:200])
        return ParsedAddress(formatted=raw_addr, country="Australia")

    raw_response = resp.json().get("response", "{}")
    cleaned      = _clean_json(raw_response)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("[parse-address] LLM non-JSON: %s — %s", exc, cleaned[:200])
        return ParsedAddress(formatted=raw_addr, country="Australia")

    # Ensure country is always "Australia"
    parsed["country"] = "Australia"

    # Always recompute formatted from parsed components for consistency
    # (overwrite whatever the LLM produced to avoid hallucinated punctuation)
    parsed["formatted"] = _build_formatted(parsed)

    # If LLM produced an empty formatted (e.g. all fields blank), fall back
    # to the raw input so geocoding always has something to work with.
    if not parsed["formatted"]:
        parsed["formatted"] = raw_addr

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
        country   = parsed.get("country",  "Australia"),
        formatted = parsed["formatted"],
    )
