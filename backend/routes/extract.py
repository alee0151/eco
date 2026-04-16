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
Only suburb, state abbreviation, and postcode are extracted.
Format: "<suburb> <state> <postcode>"  e.g. "Keperra QLD 4054"
No street name, no street number, no unit, no country.

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
    # address = "suburb state postcode" only, e.g. "Keperra QLD 4054"
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


# ── LLM prompt ─────────────────────────────────────────────────────────────────

EXTRACT_PROMPT = """\
You are a strict data-extraction engine for an Australian supply-chain risk platform.
You extract exactly four fields from OCR text of supplier documents
(invoices, purchase orders, delivery dockets, supplier registration forms).

════════════════════════════════════════════════════════
FIELD 1 — name
════════════════════════════════════════════════════════
The legal trading name of the SUPPLIER.

HOW TO FIND IT:
  ✓ Look for labels: "Supplier:", "From:", "Sold by:", "Issued by:",
    "Vendor:", "ABN holder:", "Prepared by:"
  ✓ A company name printed near an ABN is almost always the supplier.
  ✓ The supplier name often appears in the document header or letterhead.

HARD RULES:
  ✗ Do NOT return the buyer, customer, or consignee name.
  ✗ Do NOT return names near "To:", "Bill To:", "Ship To:",
    "Deliver To:", "Attention:", "Customer:", "Consignee:".
  ✗ Do NOT return a person's name unless it is the registered business name.

════════════════════════════════════════════════════════
FIELD 2 — abn
════════════════════════════════════════════════════════
The Australian Business Number (ABN) of the SUPPLIER only.

HOW TO FIND IT:
  ✓ Look for "ABN", "A.B.N.", "ABN:" followed by 11 digits (spaces allowed).
  ✓ Must belong to the supplier, not the buyer.

HARD RULES:
  ✗ Must be exactly 11 digits (spaces allowed: "51 824 753 556" or "51824753556").
  ✗ Do NOT return ACN (9 digits) or any other identifier.
  ✗ If two ABNs appear, choose the one associated with the supplier name.

════════════════════════════════════════════════════════
FIELD 3 — address
════════════════════════════════════════════════════════
The SUPPLIER'S location in THIS EXACT FORMAT:

  "<suburb> <state> <postcode>"

EXACT FORMAT RULES — read every rule carefully:
  RULE 1:  Output ONLY suburb, state abbreviation, and postcode.
  RULE 2:  Do NOT include the street name (e.g. NOT "Collins Street Melbourne VIC 3000").
  RULE 3:  Do NOT include the street number (e.g. NOT "441 Melbourne VIC 3000").
  RULE 4:  Do NOT include unit, suite, level, floor, or lot numbers.
  RULE 5:  Do NOT include the country name "Australia" or "AU".
  RULE 6:  Do NOT include a comma anywhere in the address field.
  RULE 7:  State MUST be a standard abbreviation: NSW VIC QLD WA SA TAS ACT NT
  RULE 8:  Postcode MUST be exactly 4 digits.
  RULE 9:  If only state + postcode are visible (no suburb), return "<state> <postcode>".
  RULE 10: If nothing identifiable is found, return empty string "".

HOW TO FIND THE CORRECT ADDRESS (supplier's OWN address only):
  PRIORITY 1 — Address with label: "From:", "Supplier Address:", "Our Address:",
                "Business Address:", "Registered Address:",
                "Principal Place of Business:"
  PRIORITY 2 — Address printed directly below or beside the supplier name or ABN.
  PRIORITY 3 — Address in the document header or letterhead.
  ALWAYS IGNORE addresses with labels: "To:", "Bill To:", "Ship To:",
                "Deliver To:", "Remittance Address:", "Customer Address:",
                "Attention:", "Consignee:"

CORRECT EXAMPLES — study these carefully:
  Full address in document:  "Unit 3, 441 St Kilda Road, Melbourne VIC 3004"
  Correct address field:     "Melbourne VIC 3004"

  Full address in document:  "42 Settlement Road, Keperra QLD 4054, Australia"
  Correct address field:     "Keperra QLD 4054"

  Full address in document:  "Level 5, 123 Collins Street, Melbourne VIC 3000"
  Correct address field:     "Melbourne VIC 3000"

  Full address in document:  "113 Canberra Ave Griffith ACT 2603"
  Correct address field:     "Griffith ACT 2603"

  Full address in document:  "Snowy Hydro Limited, Cooma NSW 2630"
  Correct address field:     "Cooma NSW 2630"

  Full address in document:  "PO Box 332, Cooma NSW 2630"
  Correct address field:     "Cooma NSW 2630"  (use suburb/state/postcode; add PO Box warning)

  Only postcode + state visible: "NSW 2630"
  Correct address field:     "NSW 2630"

  Buyer address is "Sydney NSW 2000", supplier address is "Keperra QLD 4054":
  Correct address field:     "Keperra QLD 4054"  (supplier only, never the buyer)

WRONG EXAMPLES — never produce these:
  ✗ "441 St Kilda Road Melbourne VIC 3004"  (contains street name and number)
  ✗ "Melbourne VIC 3004, Australia"          (contains country)
  ✗ "Unit 3, Melbourne VIC 3004"             (contains unit number and comma)
  ✗ "Collins Street Melbourne VIC 3000"      (contains street name)

════════════════════════════════════════════════════════
FIELD 4 — commodity
════════════════════════════════════════════════════════
The primary product or service supplied.
Use a short noun phrase of 1–4 words.
Examples: "Timber", "Seafood", "Grain", "Steel", "Electrical Components",
          "Hydro Power", "Construction Materials", "Fresh Produce".

HARD RULES:
  ✗ Do NOT describe the document type (e.g. NOT "Invoice", NOT "Purchase Order").
  ✗ Do NOT return a vague term like "Goods" or "Services" unless no better term exists.

════════════════════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════════════════════
Return ONLY valid JSON — no prose, no markdown fences, no explanation:
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

CONFIDENCE SCORING:
  name      1.0 = clearly labelled supplier name
            0.5 = inferred from context
            0.0 = not found
  abn       1.0 = 11 digits found near supplier name
            0.5 = 11 digits found but association uncertain
            0.0 = not found
  address   1.0 = suburb + state + postcode all present
            0.5 = state + postcode only (no suburb)
            0.0 = not found
  commodity 1.0 = explicitly named product/commodity
            0.5 = inferred from context
            0.0 = not found

WARNINGS — add a warning string for each of these situations:
  "Address is a PO Box — used suburb/state/postcode only"
  "Address missing postcode"
  "Address missing state abbreviation"
  "Address missing suburb"
  "Address may belong to buyer, not supplier — verify manually"
  "Multiple addresses found — used address nearest to supplier ABN"
  "ABN does not have 11 digits"
  "Two ABNs found — used ABN nearest to supplier name"

GENERAL RULES:
  • If a field cannot be found, use empty string "".
  • Do NOT invent or guess data that is not present in the text.
  • Do NOT copy the buyer’s data into any field.

OCR TEXT:
---
{ocr_text}
---
"""


# ── LLM call ───────────────────────────────────────────────────────────────────

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


# ── ABN validation (ATO checksum) ────────────────────────────────────────────

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


# ── Address post-processing ────────────────────────────────────────────────────────

_AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}

# Matches state + 4-digit postcode anywhere in the string
_STATE_POSTCODE_RE = re.compile(
    r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})\b",
    re.IGNORECASE,
)

_PO_BOX_RE = re.compile(r"\bP\.?\s*O\.?\s*Box\b", re.IGNORECASE)

_BUYER_LABEL_RE = re.compile(
    r"^(bill\s+to|ship\s+to|deliver\s+to|delivery\s+address"
    r"|remittance|customer|attention|attn|consignee)",
    re.IGNORECASE,
)

# Anything that looks like a street: leading digits, or known street-type words
_STREET_POLLUTION_RE = re.compile(
    r"(^\d+[A-Za-z]?\s)"                            # leading street number
    r"|(\b(street|st|road|rd|avenue|ave|drive|dr"
    r"|place|pl|lane|ln|boulevard|blvd|way|court"
    r"|ct|crescent|cres|terrace|tce|close|cl"
    r"|parade|pde|highway|hwy|circuit|cct)\b)",      # street type word
    re.IGNORECASE,
)


def _sanitise_address(address: str, existing_warnings: list[str]) -> tuple[str, list[str], float]:
    """
    Defensive post-processor for the LLM-extracted address.

    Expected input:  "suburb state postcode"  (LLM should already be clean)
    This function:
      1. Strips country name, commas, unit/level prefixes, leading numbers.
      2. Detects and warns if street name/type words remain.
      3. Validates state abbreviation and 4-digit postcode are present.
      4. Returns (cleaned, warnings, confidence_floor).
    """
    warnings = list(existing_warnings)

    if not address:
        return "", warnings, 0.0

    # ─ Strip country
    cleaned = re.sub(r",?\s*\bAustralia\b", "", address, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r",?\s*\bAU\b",        "", cleaned,  flags=re.IGNORECASE).strip()

    # ─ Strip commas (rule 6)
    cleaned = cleaned.replace(",", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    # ─ Strip unit/level/suite/PO Box prefix
    cleaned = re.sub(
        r"^(unit|u|suite|ste|level|lvl|floor|fl|apt|apartment|lot|p\.?o\.?\s*box)\s+[\w/]+\s*",
        "", cleaned, flags=re.IGNORECASE
    ).strip()

    # ─ Strip leading street number
    cleaned = re.sub(r"^\d+[A-Za-z]?[\s,/\\-]+", "", cleaned).strip()

    # ─ Flag buyer-side label
    if _BUYER_LABEL_RE.match(cleaned):
        warnings.append("Address may belong to buyer, not supplier — verify manually.")

    # ─ Flag PO Box
    if _PO_BOX_RE.search(address):   # check original before stripping
        warnings.append("Address is a PO Box — used suburb/state/postcode only.")

    # ─ Warn if street pollution still detected after stripping
    if _STREET_POLLUTION_RE.search(cleaned):
        warnings.append(
            "Address appears to contain a street name or number — "
            "only suburb/state/postcode expected."
        )

    # ─ Validate state + postcode
    state_match = _STATE_POSTCODE_RE.search(cleaned)
    if not state_match:
        warnings.append(
            "Address missing recognised Australian state abbreviation "
            "and/or 4-digit postcode."
        )
        return cleaned, warnings, 0.3

    state_found = state_match.group(1).upper()
    if state_found not in _AU_STATES:
        warnings.append(f"Address state '{state_found}' not recognised.")

    # ─ Check for suburb (text before the state token)
    text_before_state = cleaned[: state_match.start()].strip()
    has_suburb = bool(text_before_state)
    if not has_suburb:
        warnings.append("Address missing suburb.")

    confidence_floor = 1.0 if has_suburb else 0.5

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
         address = "suburb state postcode" only.
      4. Validate ABN checksum.
      5. Sanitise address: strip any street/unit/country pollution, validate AU format.
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
    cleaned_addr, warnings, addr_conf_floor = _sanitise_address(llm_addr, warnings)
    final_addr_conf = max(llm_addr_conf, addr_conf_floor) if cleaned_addr else 0.0

    result = ExtractResult(
        name      = str(raw.get("name",      "")).strip(),
        abn       = abn_value,
        address   = cleaned_addr,
        commodity = str(raw.get("commodity", "")).strip(),
        confidence = FieldConfidence(
            name      = float(conf_raw.get("name",      0)),
            abn       = float(conf_raw.get("abn",       0)),
            address   = round(final_addr_conf, 2),
            commodity = float(conf_raw.get("commodity", 0)),
        ),
        warnings = warnings,
    )

    logger.info(
        "extract: file=%s name=%r abn=%r address=%r addr_conf=%.2f warnings=%d",
        file.filename, result.name, result.abn,
        result.address, result.confidence.address, len(warnings),
    )
    return result
