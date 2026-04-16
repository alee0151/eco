"""
POST /api/extract

Accepts a multipart upload of a PDF or image file.

OCR  : Tesseract (pytesseract) — free, runs 100 % locally.
LLM  : Ollama — free, runs 100 % locally.
        Install Ollama from https://ollama.com and pull a model:
          ollama pull llama3.2          # default
          ollama pull mistral            # lighter alternative

Address extraction scope
------------------------
Only street NAME (no unit, no street number), suburb, state, and postcode
are extracted.  These four components are passed to the GNAF geocoder.

Environment variables
---------------------
OLLAMA_MODEL      Model name to use (default: llama3.2)
OLLAMA_BASE_URL   Ollama server URL   (default: http://localhost:11434)
"""

import io
import json
import logging
import os
import re

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Response schema ───────────────────────────────────────────────────────────

class FieldConfidence(BaseModel):
    name:      float = 0.0
    abn:       float = 0.0
    address:   float = 0.0
    commodity: float = 0.0


class ExtractResult(BaseModel):
    name:      str = ""
    abn:       str = ""
    # address holds "street_name suburb state postcode" — no unit, no street number
    address:   str = ""
    commodity: str = ""
    confidence: FieldConfidence = FieldConfidence()
    warnings:  list[str] = []


# ── OCR — Tesseract only ──────────────────────────────────────────────────────

def run_ocr(file_bytes: bytes, content_type: str) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "pytesseract or Pillow is not installed. "
                f"Run: pip install pytesseract Pillow pdf2image  ({exc})"
            ),
        )

    if "pdf" in content_type:
        try:
            from pdf2image import convert_from_bytes
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"pdf2image is not installed. Run: pip install pdf2image  ({exc})",
            )
        pages = convert_from_bytes(file_bytes, dpi=200)
        texts = [pytesseract.image_to_string(p) for p in pages[:2]]
        return "\n".join(texts)
    else:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img)


# ── LLM — Ollama only (free) ──────────────────────────────────────────────────

EXTRACT_PROMPT = """\
You are a data-extraction assistant for an Australian supply-chain risk platform.
Your task is to extract structured information from the raw OCR text of a supplier document
(invoice, purchase order, delivery docket, supplier registration form, or similar).

=== FIELDS TO EXTRACT ===

1. name
   The legal name of the SUPPLIER (the company or individual SELLING or DELIVERING goods/services).
   - Look for labels like: "Supplier", "From:", "Sold by:", "Issued by:", "Vendor:",
     "ABN holder", or a company name near an ABN.
   - Do NOT return the buyer / customer / "Bill To" / "Ship To" / "Deliver To" company name.

2. abn
   The Australian Business Number of the SUPPLIER (11 digits, spaces allowed).
   - Must be associated with the supplier name, not the buyer.
   - Format example: "51 824 753 556" or "51824753556".

3. address
   The SUPPLIER'S location for GNAF geocoding.
   Return ONLY these four components joined in this exact format:
     "<street_name> <suburb> <state> <postcode>"

   STRICT RULES:
   a) MUST be the supplier's OWN address — NOT the buyer/customer address.
   b) Priority order when multiple addresses appear:
      1st — Address labelled "From:", "Supplier Address:", "Our Address:",
             "Business Address:", "Registered Address:", "Principal Place of Business:"
      2nd — Address immediately below or beside the supplier name / ABN.
      3rd — Address in the header/letterhead of the document.
      IGNORE labels: "To:", "Bill To:", "Ship To:", "Deliver To:",
             "Remittance Address:", "Customer Address:", "Attention:"
   c) street_name  — The street NAME and TYPE ONLY (e.g. "Collins Street", "St Kilda Road",
                      "Settlement Road").  Do NOT include the street number or unit/level.
   d) suburb       — The suburb or town name (e.g. "Melbourne", "Keperra", "Griffith").
   e) state        — Two-or-three-letter abbreviation: NSW VIC QLD WA SA TAS ACT NT.
   f) postcode     — 4-digit Australian postcode.
   g) Do NOT include unit numbers, suite numbers, floor/level numbers, or street numbers.
   h) Do NOT include the country name.
   i) Do NOT include PO Box unless no physical address exists; add a warning if used.
   j) If the suburb + state + postcode are known but the street name is not, omit street_name.

   Example outputs for the address field:
     "Collins Street Melbourne VIC 3000"
     "Settlement Road Keperra QLD 4054"
     "Canberra Avenue Griffith ACT 2603"
     "Melbourne VIC 3000"  (no street name found)

4. commodity
   The primary product or commodity supplied (e.g. Timber, Seafood, Grain, Steel,
   Electrical Components). Use a short noun phrase (1–4 words).

=== OUTPUT FORMAT ===

Return ONLY valid JSON in this exact shape (no prose, no markdown fences):
{{
  "name":      "...",
  "abn":       "...",
  "address":   "...",
  "commodity": "...",
  "confidence": {{
    "name":      0.0,
    "abn":       0.0,
    "address":   0.0,
    "commodity": 0.0
  }},
  "warnings": []
}}

=== GENERAL RULES ===
- If a field cannot be found, use an empty string "".
- confidence values are 0.0 – 1.0 reflecting how certain you are.
- For address confidence:
    1.0 = street name + suburb + state + postcode all present
    0.7 = suburb + state + postcode (no street name)
    0.4 = state + postcode only
    0.0 = not found
- Add human-readable strings to warnings[] for anything suspicious:
    "Address is a PO Box — no physical street name found"
    "Address missing postcode"
    "Address missing state abbreviation"
    "Address may belong to buyer, not supplier — verify manually"
    "ABN digit count incorrect"
    "Multiple supplier addresses found — used address nearest to ABN"
- Do NOT invent data that is not present in the text.

OCR TEXT:
---
{ocr_text}
---
"""


def run_llm(ocr_text: str) -> dict:
    model    = os.getenv("OLLAMA_MODEL",    "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url      = f"{base_url}/api/generate"

    payload = {
        "model":  model,
        "prompt": EXTRACT_PROMPT.format(ocr_text=ocr_text[:8000]),
        "stream": False,
        "format": "json",
    }

    try:
        resp = httpx.post(url, json=payload, timeout=120)
        resp.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Ollama. Make sure Ollama is running: ollama serve",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:300]}",
        )

    raw = resp.json().get("response", "{}")
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
    raw = re.sub(r"\n?```$",       "", raw.strip())

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Ollama non-JSON response: %s", raw[:500])
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned unparseable JSON: {exc}",
        )


# ── ABN validation (ATO checksum) ─────────────────────────────────────────────

def _validate_abn(abn: str) -> list[str]:
    warnings: list[str] = []
    digits = re.sub(r"\D", "", abn)
    if not digits:
        return warnings
    if len(digits) != 11:
        warnings.append(f"ABN '{abn}' does not have 11 digits.")
        return warnings
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    d = [int(c) for c in digits]
    d[0] -= 1
    total = sum(w * v for w, v in zip(weights, d))
    if total % 89 != 0:
        warnings.append(f"ABN '{abn}' fails the ATO checksum — may be invalid.")
    return warnings


# ── Address post-processing & validation ──────────────────────────────────────

_AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}

_STATE_POSTCODE_RE = re.compile(
    r"(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})\b",
    re.IGNORECASE,
)

_PO_BOX_RE = re.compile(r"\bP\.?\s*O\.?\s*Box\b", re.IGNORECASE)

_BUYER_LABEL_RE = re.compile(
    r"^(bill\s+to|ship\s+to|deliver\s+to|delivery\s+address|remittance|customer|attention|attn)",
    re.IGNORECASE,
)

# Strip any leading street number (digits + optional letter) from the address
_LEADING_NUMBER_RE = re.compile(r"^\d+[A-Za-z]?[\s,/\\-]+")
# Strip unit/level/suite/floor prefixes
_UNIT_PREFIX_RE = re.compile(
    r"^(unit|u|suite|ste|level|lvl|floor|fl|apt|apartment|lot)\s+[\w/]+[\s,]+",
    re.IGNORECASE,
)


def _strip_number_and_unit(address: str) -> str:
    """
    Remove any leading unit/level prefix and street number from the address string.
    e.g. "Unit 3 42 Collins Street Melbourne VIC 3000"
      -> "Collins Street Melbourne VIC 3000"
    e.g. "42 Collins Street Melbourne VIC 3000"
      -> "Collins Street Melbourne VIC 3000"
    """
    cleaned = address.strip()
    # Remove unit/level/suite prefix first
    cleaned = _UNIT_PREFIX_RE.sub("", cleaned).strip()
    # Then remove leading street number
    cleaned = _LEADING_NUMBER_RE.sub("", cleaned).strip()
    return cleaned


def _validate_address(address: str, existing_warnings: list[str]) -> tuple[str, list[str], float]:
    warnings = list(existing_warnings)

    if not address:
        return address, warnings, 0.0

    # Strip country
    cleaned = re.sub(r",?\s*Australia\s*$", "", address, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r",?\s*AU\s*$",        "", cleaned,  flags=re.IGNORECASE).strip()

    # Strip unit / street number (defensive — LLM should not include these)
    cleaned = _strip_number_and_unit(cleaned)

    if _BUYER_LABEL_RE.match(cleaned):
        warnings.append("Address may belong to buyer, not supplier — verify manually.")

    if _PO_BOX_RE.search(cleaned):
        warnings.append("Address is a PO Box — no physical street name found.")

    state_match = _STATE_POSTCODE_RE.search(cleaned)
    if not state_match:
        warnings.append(
            "Address missing recognised Australian state abbreviation and/or 4-digit postcode."
        )
        return cleaned, warnings, 0.3

    state_found = state_match.group(1).upper()
    if state_found not in _AU_STATES:
        warnings.append(f"Address state abbreviation '{state_found}' not recognised.")

    # Confidence floor: street name present = 1.0; suburb+state+postcode only = 0.7
    # A street name is present if there is text before the state token
    text_before_state = cleaned[: state_match.start()].strip().rstrip(",")
    has_street_name = bool(text_before_state)
    confidence_floor = 0.9 if has_street_name else 0.7

    return cleaned, warnings, confidence_floor


# ── Endpoint ──────────────────────────────────────────────────────────────────

ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
}


@router.post("/extract", response_model=ExtractResult)
async def extract(
    file: UploadFile = File(..., description="PDF or image of a supplier document"),
) -> ExtractResult:
    """
    Pipeline:
      1. Validate file type & size.
      2. Run Tesseract OCR  →  raw text.
      3. Send raw text to Ollama  →  structured JSON.
         address = "street_name suburb state postcode" (no unit, no street number).
      4. Validate ABN checksum.
      5. Post-process address: strip any accidental unit/number, validate AU format.
      6. Return ExtractResult.
    """
    ct = (file.content_type or "").lower()
    if file.filename and file.filename.lower().endswith(".pdf"):
        ct = "application/pdf"
    if ct not in ALLOWED_TYPES and not ct.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ct}'. Please upload a PDF or image.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    ocr_text = run_ocr(file_bytes, ct)
    logger.debug("OCR produced %d chars for '%s'", len(ocr_text), file.filename)

    if not ocr_text.strip():
        return ExtractResult(
            warnings=[
                "OCR returned no text. The document may be blank, "
                "encrypted, or a scanned image with very low resolution."
            ]
        )

    raw = run_llm(ocr_text)

    conf_raw  = raw.get("confidence", {})
    warnings  = list(raw.get("warnings", []))
    abn_value = str(raw.get("abn", "")).strip()
    llm_addr  = str(raw.get("address", "")).strip()

    if abn_value:
        warnings.extend(_validate_abn(abn_value))

    llm_addr_conf = float(conf_raw.get("address", 0))
    cleaned_addr, warnings, addr_conf_floor = _validate_address(llm_addr, warnings)
    final_addr_conf = max(llm_addr_conf, addr_conf_floor) if cleaned_addr else 0.0

    result = ExtractResult(
        name      = str(raw.get("name",      "")).strip(),
        abn       = abn_value,
        address   = cleaned_addr,
        commodity = str(raw.get("commodity", "")).strip(),
        confidence=FieldConfidence(
            name      = float(conf_raw.get("name",      0)),
            abn       = float(conf_raw.get("abn",       0)),
            address   = round(final_addr_conf, 2),
            commodity = float(conf_raw.get("commodity", 0)),
        ),
        warnings=warnings,
    )

    logger.info(
        "extract: file=%s name=%r abn=%r address=%r addr_conf=%.2f warnings=%d",
        file.filename, result.name, result.abn,
        result.address, result.confidence.address, len(warnings),
    )
    return result
