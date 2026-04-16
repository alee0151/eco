"""
routes/parse_address.py  —  POST /api/parse-address

Parses a raw Australian address string into structured components for GNAF geocoding.

Approach
--------
Pure regex — no LLM.  The LLM was unreliable: it filled `formatted` with the
entire address and left street/suburb/state/postcode all empty.  Australian
addresses follow a predictable pattern that regex handles completely:

  [unit] [number] <street name> <street type>, <suburb> <state> <postcode>

Response shape:
  {
    "street":    "St Kilda Road",
    "suburb":    "Melbourne",
    "state":     "VIC",
    "postcode":  "3004",
    "formatted": "St Kilda Road Melbourne VIC 3004"
  }

All fields default to "" if not found.
"formatted" is always server-computed as: street suburb state postcode
"""

import logging
import re

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ParseAddressRequest(BaseModel):
    address: str


class ParsedAddress(BaseModel):
    street:    str = ""   # street name + type, NO unit/number
    suburb:    str = ""
    state:     str = ""
    postcode:  str = ""
    formatted: str = ""   # server-computed: "street suburb state postcode"


# ── Constants ────────────────────────────────────────────────────────────────

_AU_STATES = r"NSW|VIC|QLD|WA|SA|TAS|ACT|NT"

# Recognised street type words (covers the vast majority of AU addresses)
_STREET_TYPES = (
    r"Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Place|Pl|Lane|Ln"
    r"|Boulevard|Blvd|Way|Court|Ct|Circuit|Cct|Crescent|Cres"
    r"|Parade|Pde|Highway|Hwy|Freeway|Fwy|Close|Cl|Grove|Gr"
    r"|Terrace|Tce|Square|Sq|Walk|Track|Rise|Row|Loop|Link"
    r"|Mews|Quay|Esplanade|Esp|Promenade|Prom"
)

# Strip leading unit/floor/level designators
_UNIT_PREFIX_RE = re.compile(
    r"^(?:unit|u|suite|ste|level|lvl|floor|fl|apt|apartment|lot|shop)\s+[\w/-]+[\s,]+",
    re.IGNORECASE,
)

# Strip leading street number (handles "441", "441A", "1/441", "441-443")
_STREET_NUMBER_RE = re.compile(r"^[\d]+(?:[A-Za-z]|[-/][\dA-Za-z]+)?\s+")

# Core parser:
#   Group 1: street name words + street type word
#   Group 2: suburb (one or more title-case or ALL-CAPS words, may include spaces)
#   Group 3: state abbreviation
#   Group 4: 4-digit postcode
_ADDRESS_RE = re.compile(
    r"(?P<street>[A-Za-z][\w\s]*?(?:" + _STREET_TYPES + r"))"
    r"[\s,]+"
    r"(?P<suburb>[A-Za-z][A-Za-z\s]+?)"
    r"[\s,]+"
    r"(?P<state>" + _AU_STATES + r")"
    r"[\s,]+"
    r"(?P<postcode>\d{4})",
    re.IGNORECASE,
)

# Fallback: suburb + state + postcode only (no street)
_SUBURB_STATE_RE = re.compile(
    r"(?P<suburb>[A-Za-z][A-Za-z\s]+?)"
    r"[\s,]+"
    r"(?P<state>" + _AU_STATES + r")"
    r"[\s,]+"
    r"(?P<postcode>\d{4})",
    re.IGNORECASE,
)

# Fallback: state + postcode only
_STATE_POSTCODE_RE = re.compile(
    r"(?P<state>" + _AU_STATES + r")"
    r"[\s,]+"
    r"(?P<postcode>\d{4})",
    re.IGNORECASE,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _strip_unit_and_number(addr: str) -> str:
    """Remove unit prefix and leading street number from address string."""
    s = _UNIT_PREFIX_RE.sub("", addr.strip()).strip().lstrip(",").strip()
    s = _STREET_NUMBER_RE.sub("", s).strip()
    return s


def _title(s: str) -> str:
    """Title-case a string, preserving existing capitalisation of state codes."""
    return s.strip().title()


def _build_formatted(street: str, suburb: str, state: str, postcode: str) -> str:
    parts = [p for p in [street, suburb, state, postcode] if p]
    return " ".join(parts)


def _parse(raw: str) -> ParsedAddress:
    """
    Deterministic regex parser for Australian addresses.

    Cascade:
      1. Full match:  street + suburb + state + postcode
      2. Partial:     suburb + state + postcode  (no recognisable street type)
      3. Minimal:     state + postcode only
      4. Raw fallback: return formatted=raw, all others empty
    """
    # Strip unit designators and street numbers before matching
    cleaned = _strip_unit_and_number(raw)

    # ── Attempt 1: full street + suburb + state + postcode ──────────────────────
    m = _ADDRESS_RE.search(cleaned)
    if m:
        street   = _title(m.group("street"))
        suburb   = _title(m.group("suburb"))
        state    = m.group("state").upper()
        postcode = m.group("postcode")
        formatted = _build_formatted(street, suburb, state, postcode)
        logger.info(
            "[parse-address] full match: %r → street=%r suburb=%r state=%r postcode=%r",
            raw, street, suburb, state, postcode,
        )
        return ParsedAddress(street=street, suburb=suburb, state=state,
                             postcode=postcode, formatted=formatted)

    # ── Attempt 2: suburb + state + postcode ─────────────────────────────────
    m = _SUBURB_STATE_RE.search(raw)   # search original — cleaned may strip too much
    if m:
        suburb   = _title(m.group("suburb"))
        state    = m.group("state").upper()
        postcode = m.group("postcode")
        formatted = _build_formatted("", suburb, state, postcode)
        logger.info(
            "[parse-address] suburb match: %r → suburb=%r state=%r postcode=%r",
            raw, suburb, state, postcode,
        )
        return ParsedAddress(suburb=suburb, state=state,
                             postcode=postcode, formatted=formatted)

    # ── Attempt 3: state + postcode only ────────────────────────────────────
    m = _STATE_POSTCODE_RE.search(raw)
    if m:
        state    = m.group("state").upper()
        postcode = m.group("postcode")
        formatted = _build_formatted("", "", state, postcode)
        logger.info(
            "[parse-address] state+postcode only: %r → state=%r postcode=%r",
            raw, state, postcode,
        )
        return ParsedAddress(state=state, postcode=postcode, formatted=formatted)

    # ── Attempt 4: raw fallback ───────────────────────────────────────────────
    logger.warning("[parse-address] no pattern matched for %r — using raw", raw)
    return ParsedAddress(formatted=raw)


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/parse-address", response_model=ParsedAddress)
async def parse_address(body: ParseAddressRequest) -> ParsedAddress:
    """
    Parse a raw Australian address string into street, suburb, state, postcode.
    Uses deterministic regex — no LLM, no external calls, no latency.
    """
    raw_addr = (body.address or "").strip()
    if not raw_addr:
        return ParsedAddress()

    result = _parse(raw_addr)
    return result
