"""
POST /api/extract

Accepts a multipart upload of a PDF or image file.

Pipeline
--------
  1. Validate file type & size.
  2. Run Tesseract OCR  →  raw text  (100 % local, no API key needed).
  3. POST the OCR text to Ollama /api/generate  →  structured JSON.
     Endpoint : {OLLAMA_URL}/api/generate
     Payload  : { "model": "...", "prompt": "...", "stream": false }
  4. Regex fallback: if LLM returns empty strings for any field,
     extract them directly from the OCR text using deterministic patterns.
  5. Validate ABN checksum (ATO algorithm).
  6. Post-process address  →  strip unit/number, validate AU format.
  7. Return ExtractResult  (includes ocr_text + llm_raw for debugging).

Environment variables
---------------------
OLLAMA_URL          Required. Full base URL of the Ollama server.
                    Example: https://my-ollama-server.example.com
OLLAMA_MODEL        Model name to use (default: gpt-oss:20b)
OLLAMA_TIMEOUT      HTTP timeout in seconds (default: 600).
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

DEFAULT_MODEL   = "gpt-oss:20b"
DEFAULT_TIMEOUT = 600


# ── Response schema ───────────────────────────────────────────────────────────

class FieldConfidence(BaseModel):
    name:      float = 0.0
    abn:       float = 0.0
    address:   float = 0.0
    commodity: float = 0.0


class ExtractResult(BaseModel):
    name:       str = ""
    abn:        str = ""
    address:    str = ""   # "street_name suburb state postcode"
    commodity:  str = ""
    confidence: FieldConfidence = FieldConfidence()
    warnings:   list[str] = []
    ocr_text:   str = ""   # full OCR output — inspect to debug empty fields
    llm_raw:    str = ""   # raw JSON string returned by Ollama


# ── OCR — Tesseract ───────────────────────────────────────────────────────────

def run_ocr(file_bytes: bytes, content_type: str) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(status_code=500,
            detail=f"pytesseract or Pillow not installed: {exc}")

    if "pdf" in content_type:
        try:
            from pdf2image import convert_from_bytes
        except ImportError as exc:
            raise HTTPException(status_code=500,
                detail=f"pdf2image not installed: {exc}")
        pages = convert_from_bytes(file_bytes, dpi=200)
        return "\n".join(pytesseract.image_to_string(p) for p in pages[:2])
    else:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img)


# ── Prompt ───────────────────────────────────────────────────────────────────

EXTRACT_PROMPT = """\
You are a JSON-only data-extraction engine for an Australian supply-chain risk platform.
You output ONLY a single valid JSON object. You NEVER output prose, explanation, or commentary.

=== YOUR TASK ===
Extract four fields from the OCR text of an Australian supplier document
(invoice, purchase order, delivery docket, supplier registration form, or similar).

=== FIELDS TO EXTRACT ===

1. name
   The legal trading name of the SUPPLIER — the entity SELLING or DELIVERING the goods/services.
   HOW TO FIND IT:
   ✓ Look for labels: "Supplier:", "From:", "Sold by:", "Issued by:", "Vendor:", "ABN holder:"
   ✓ A company name printed immediately above or beside an ABN is almost always the supplier.
   ✓ The supplier name is usually in the document header or letterhead.
   DO NOT return:
   ✗ The buyer, customer, or consignee name.
   ✗ Names near labels "To:", "Bill To:", "Ship To:", "Deliver To:", "Attention:", "Customer:".
   ✗ A person's name unless it is the registered business name.

2. abn
   The Australian Business Number (ABN) of the SUPPLIER only.
   HOW TO FIND IT:
   ✓ Look for "ABN", "A.B.N.", or "ABN:" followed by 11 digits (spaces are allowed).
   ✓ Must belong to the supplier, not the buyer.
   RULES:
   ✗ Must be exactly 11 digits. Spaces are allowed: "51 824 753 556" or "51824753556".
   ✗ Do NOT return ACN (9 digits) or any other identifier.
   ✗ If two ABNs appear, choose the one beside or below the supplier name.

3. address
   The SUPPLIER'S physical location.
   Return ONLY these components in this exact format:
     "<street_name> <suburb> <state_abbreviation> <postcode>"

   STRICT FORMAT RULES:
   a) Output ONLY street name, suburb, state abbreviation, and 4-digit postcode.
   b) State MUST be one of: NSW  VIC  QLD  WA  SA  TAS  ACT  NT
   c) Postcode MUST be exactly 4 digits.
   d) Do NOT include the street number (e.g. "42"), unit, suite, level, or floor.
   e) Do NOT include the country name (e.g. "Australia").
   f) Do NOT include a comma anywhere in the address string.
   g) If no street name is visible, return just "<suburb> <state> <postcode>".
   h) If nothing identifiable is found, return empty string "".

   ADDRESS PRIORITY — when multiple addresses appear, use this order:
   1st — labelled "From:", "Supplier Address:", "Our Address:", "Business Address:",
          "Registered Address:", "Principal Place of Business:"
   2nd — address immediately beside or below the supplier name or ABN
   3rd — address in the document header or letterhead
   IGNORE labels: "To:", "Bill To:", "Ship To:", "Deliver To:",
                  "Remittance Address:", "Customer Address:", "Attention:"

   EXAMPLES of valid address output:
     "Collins Street Melbourne VIC 3000"
     "Settlement Road Keperra QLD 4054"
     "Canberra Avenue Griffith ACT 2603"
     "Melbourne VIC 3000"   (no street name found)

4. commodity
   The primary product or service being supplied.
   Use a short noun phrase of 1–4 words.
   EXAMPLES: "Timber", "Seafood", "Grain", "Steel", "Electrical Components", "Fresh Produce".
   DO NOT describe the document type (e.g. "Invoice" or "Purchase Order").
   DO NOT use vague terms like "Goods" or "Services" unless nothing more specific is present.

=== FORBIDDEN — YOUR RESPONSE MUST NOT CONTAIN ===
  ✗ Any sentence, word, or phrase outside the JSON object
  ✗ Markdown code fences (```json ... ``` or ``` ... ```)
  ✗ Any explanation of what you found or did not find
  ✗ Any apology or uncertainty statement
  ✗ Any text before the opening brace {{
  ✗ Any text after the closing brace }}

=== REQUIRED OUTPUT FORMAT ===
Your entire response must be exactly this JSON structure and nothing else:
{{
  "name":      "<supplier name or empty string>",
  "abn":       "<11-digit ABN with spaces or empty string>",
  "address":   "<street suburb state postcode or empty string>",
  "commodity": "<1-4 word noun phrase or empty string>",
  "confidence": {{
    "name":      0.0,
    "abn":       0.0,
    "address":   0.0,
    "commodity": 0.0
  }},
  "warnings": []
}}

=== CONFIDENCE VALUES (0.0 to 1.0) ===
  name / abn / commodity:
    1.0 = clearly labelled in the document
    0.5 = inferred from context (not explicitly labelled)
    0.0 = not found
  address:
    1.0 = street name + suburb + state + postcode all present
    0.7 = suburb + state + postcode (no street name)
    0.4 = state + postcode only
    0.0 = not found

=== WARNINGS ARRAY ===
Add one string per issue detected:
  "Address is a PO Box — no physical street address found"
  "Address missing postcode"
  "Address missing state abbreviation"
  "Address may belong to buyer not supplier — verify manually"
  "ABN does not have 11 digits"
  "Two ABNs found — used ABN nearest to supplier name"
  "Multiple addresses found — used address nearest to supplier ABN"

=== GENERAL RULES ===
  • If a field cannot be found, use empty string "" — never null or undefined.
  • Do NOT invent or guess data that is not present in the OCR text.
  • Do NOT copy text from the FORBIDDEN examples above into the output.

OCR TEXT TO EXTRACT FROM:
---
{ocr_text}
---

REMEMBER: Output the JSON object and absolutely nothing else.
Do not write anything before {{ or after }}.
"""


# ── JSON extraction helper ───────────────────────────────────────────────────────

def _extract_json(raw: str) -> tuple[dict, str]:
    """
    Robustly extract a JSON object from the model's raw response.
    Returns (parsed_dict, cleaned_raw_string).

    Attempt order:
      1. Strip markdown fences, try direct parse.
      2. Regex-extract first {...} block.
      3. Log and raise HTTP 502.
    """
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$",           "", cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned), cleaned
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\{[\s\S]*\})", cleaned)
    if match:
        try:
            return json.loads(match.group(1)), match.group(1)
        except json.JSONDecodeError:
            pass

    logger.error(
        "[extract] Could not parse JSON from Ollama.\n"
        "--- RAW (first 1000 chars) ---\n%s\n--- END ---", raw[:1000]
    )
    raise HTTPException(
        status_code=502,
        detail="Ollama returned unparseable JSON. Check backend logs for raw output.",
    )


# ── Regex fallback — runs when LLM returns empty strings ──────────────────────────
#
# Deterministic patterns applied directly to the OCR text.
# These are fast, reliable, and do not require a model.
# Used ONLY to fill fields that the LLM left blank.
# ───────────────────────────────────────────────────────────────────

# ABN: "ABN" or "A.B.N" followed by optional colon/space then 11 digits
_RE_ABN = re.compile(
    r"\bA\.?B\.?N\.?\s*:?\s*([\d]{2}\s?[\d]{3}\s?[\d]{3}\s?[\d]{3})",
    re.IGNORECASE,
)

# AU state + 4-digit postcode (used to anchor address detection)
_RE_STATE_PC = re.compile(
    r"([\w\s,./]+?)\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})\b",
    re.IGNORECASE,
)


def _regex_fallback(ocr_text: str, llm: dict, warnings: list[str]) -> tuple[dict, list[str]]:
    """
    For every field that the LLM returned as empty string,
    attempt to fill it using deterministic regex on the raw OCR text.
    Appends a warning for each field recovered this way.
    """
    result = dict(llm)

    # ── ABN ─────────────────────────────────────────────────────────────────
    if not result.get("abn", "").strip():
        m = _RE_ABN.search(ocr_text)
        if m:
            result["abn"] = m.group(1).strip()
            warnings.append("ABN extracted via regex fallback — LLM returned empty.")
            logger.info("[extract] regex ABN fallback: %r", result["abn"])

    # ── Address ─────────────────────────────────────────────────────────────
    if not result.get("address", "").strip():
        m = _RE_STATE_PC.search(ocr_text)
        if m:
            prefix  = m.group(1).strip().strip(",").split("\n")[-1].strip()
            state   = m.group(2).upper()
            postcode = m.group(3)
            addr = f"{prefix} {state} {postcode}".strip() if prefix else f"{state} {postcode}"
            result["address"] = addr
            warnings.append("Address extracted via regex fallback — LLM returned empty.")
            logger.info("[extract] regex address fallback: %r", addr)

    # ── Name ─────────────────────────────────────────────────────────────────
    if not result.get("name", "").strip():
        # Look for lines following common supplier labels
        m = re.search(
            r"(?:supplier|from|sold\s+by|issued\s+by|vendor)[:\s]+([^\n]{3,80})",
            ocr_text, re.IGNORECASE,
        )
        if m:
            result["name"] = m.group(1).strip()
            warnings.append("Supplier name extracted via regex fallback — LLM returned empty.")
            logger.info("[extract] regex name fallback: %r", result["name"])

    return result, warnings


# ── Ollama LLM call (async) ───────────────────────────────────────────────────

async def run_llm(ocr_text: str) -> tuple[dict, str]:
    """
    POST to {OLLAMA_URL}/api/generate.
    Returns (parsed_dict, raw_response_string).
    """
    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    if not ollama_url:
        raise HTTPException(status_code=503,
            detail="OLLAMA_URL is not configured. Add it to backend/.env")

    model   = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    url     = f"{ollama_url.rstrip('/')}/api/generate"
    timeout = float(os.getenv("OLLAMA_TIMEOUT", DEFAULT_TIMEOUT))

    payload = {
        "model":  model,
        "prompt": EXTRACT_PROMPT.format(ocr_text=ocr_text[:8000]),
        "stream": False,
        "format": "json",
    }

    logger.info("[extract] POST %s  model=%s  timeout=%.0fs", url, model, timeout)
    logger.info("[extract] OCR text sent to Ollama (first 500 chars):\n%s", ocr_text[:500])

    http_timeout = httpx.Timeout(timeout, connect=30.0)

    try:
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504,
            detail=f"Ollama timed out after {timeout:.0f}s. Set OLLAMA_TIMEOUT=900 in .env")
    except httpx.ConnectError:
        raise HTTPException(status_code=503,
            detail=f"Cannot reach Ollama at '{ollama_url}'. Check OLLAMA_URL.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502,
            detail=f"Ollama HTTP {exc.response.status_code}: {exc.response.text[:300]}")

    raw = resp.json().get("response", "")
    logger.info("[extract] raw Ollama response (first 800 chars):\n%s", raw[:800])

    parsed, cleaned = _extract_json(raw)
    logger.info("[extract] parsed LLM fields: name=%r  abn=%r  address=%r  commodity=%r",
        parsed.get("name"), parsed.get("abn"),
        parsed.get("address"), parsed.get("commodity"))

    return parsed, cleaned


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


# ── Address post-processing & validation ─────────────────────────────────────

_AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}
_STATE_POSTCODE_RE = re.compile(
    r"(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})\b", re.IGNORECASE)
_PO_BOX_RE         = re.compile(r"\bP\.?\s*O\.?\s*Box\b", re.IGNORECASE)
_BUYER_LABEL_RE    = re.compile(
    r"^(bill\s+to|ship\s+to|deliver\s+to|delivery\s+address|remittance|customer|attention|attn)",
    re.IGNORECASE)
_LEADING_NUMBER_RE = re.compile(r"^\d+[A-Za-z]?[\s,/\\-]+")
_UNIT_PREFIX_RE    = re.compile(
    r"^(unit|u|suite|ste|level|lvl|floor|fl|apt|apartment|lot)\s+[\w/]+[\s,]+",
    re.IGNORECASE)


def _strip_number_and_unit(address: str) -> str:
    cleaned = _UNIT_PREFIX_RE.sub("", address.strip()).strip()
    return _LEADING_NUMBER_RE.sub("", cleaned).strip()


def _validate_address(address: str, existing_warnings: list[str]) -> tuple[str, list[str], float]:
    warnings = list(existing_warnings)
    if not address:
        return address, warnings, 0.0

    cleaned = re.sub(r",?\s*Australia\s*$", "", address, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r",?\s*AU\s*$",        "", cleaned,  flags=re.IGNORECASE).strip()
    cleaned = _strip_number_and_unit(cleaned)

    if _BUYER_LABEL_RE.match(cleaned):
        warnings.append("Address may belong to buyer, not supplier — verify manually.")
    if _PO_BOX_RE.search(cleaned):
        warnings.append("Address is a PO Box — no physical street name found.")

    state_match = _STATE_POSTCODE_RE.search(cleaned)
    if not state_match:
        warnings.append("Address missing AU state abbreviation and/or 4-digit postcode.")
        return cleaned, warnings, 0.3

    state_found = state_match.group(1).upper()
    if state_found not in _AU_STATES:
        warnings.append(f"Address state '{state_found}' not recognised.")

    has_street = bool(cleaned[: state_match.start()].strip().rstrip(","))
    return cleaned, warnings, 0.9 if has_street else 0.7


# ── Endpoint ──────────────────────────────────────────────────────────────────

ALLOWED_TYPES = {
    "application/pdf", "image/png", "image/jpeg",
    "image/jpg", "image/webp", "image/tiff",
}


@router.post("/extract", response_model=ExtractResult)
async def extract(
    file: UploadFile = File(..., description="PDF or image of a supplier document"),
) -> ExtractResult:
    ct = (file.content_type or "").lower()
    if file.filename and file.filename.lower().endswith(".pdf"):
        ct = "application/pdf"
    if ct not in ALLOWED_TYPES and not ct.startswith("image/"):
        raise HTTPException(status_code=415,
            detail=f"Unsupported file type '{ct}'. Upload a PDF or image.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    # ── Step 1: Tesseract OCR ───────────────────────────────────────────────
    ocr_text = run_ocr(file_bytes, ct)
    logger.info("[extract] OCR: %d chars for '%s'", len(ocr_text), file.filename)
    logger.info("[extract] OCR full text:\n%s", ocr_text[:2000])

    if not ocr_text.strip():
        return ExtractResult(
            warnings=["OCR returned no text. Document may be blank or low-resolution."],
            ocr_text=ocr_text,
        )

    # ── Step 2: Ollama LLM ───────────────────────────────────────────────────
    raw_dict, llm_raw_str = await run_llm(ocr_text)

    conf_raw  = raw_dict.get("confidence", {})
    warnings  = list(raw_dict.get("warnings", []))
    abn_value = str(raw_dict.get("abn",       "")).strip()
    llm_addr  = str(raw_dict.get("address",   "")).strip()
    name_val  = str(raw_dict.get("name",      "")).strip()
    comm_val  = str(raw_dict.get("commodity", "")).strip()

    # ── Step 3: Regex fallback for any blank LLM fields ───────────────────────
    blanks = [f for f, v in [("name", name_val), ("abn", abn_value),
                              ("address", llm_addr), ("commodity", comm_val)] if not v]
    if blanks:
        logger.info("[extract] LLM returned empty for: %s — running regex fallback", blanks)
        raw_dict, warnings = _regex_fallback(ocr_text, raw_dict, warnings)
        abn_value = str(raw_dict.get("abn",       "")).strip()
        llm_addr  = str(raw_dict.get("address",   "")).strip()
        name_val  = str(raw_dict.get("name",      "")).strip()
        comm_val  = str(raw_dict.get("commodity", "")).strip()

    # ── Step 4: ABN checksum ───────────────────────────────────────────────────
    if abn_value:
        warnings.extend(_validate_abn(abn_value))

    # ── Step 5: Address sanitisation ────────────────────────────────────────────
    llm_addr_conf = float(conf_raw.get("address", 0))
    cleaned_addr, warnings, addr_conf_floor = _validate_address(llm_addr, warnings)
    final_addr_conf = max(llm_addr_conf, addr_conf_floor) if cleaned_addr else 0.0

    result = ExtractResult(
        name      = name_val,
        abn       = abn_value,
        address   = cleaned_addr,
        commodity = comm_val,
        confidence = FieldConfidence(
            name      = float(conf_raw.get("name",      0)),
            abn       = float(conf_raw.get("abn",       0)),
            address   = round(final_addr_conf, 2),
            commodity = float(conf_raw.get("commodity", 0)),
        ),
        warnings  = warnings,
        ocr_text  = ocr_text,
        llm_raw   = llm_raw_str,
    )

    logger.info(
        "[extract] FINAL  file=%s  name=%r  abn=%r  address=%r  commodity=%r  warnings=%d",
        file.filename, result.name, result.abn,
        result.address, result.commodity, len(warnings),
    )
    return result
