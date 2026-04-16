"""
POST /api/extract

Accepts a multipart upload of a PDF or image file.

Pipeline
--------
  1. Validate file type & size.
  2. Run Tesseract OCR  →  raw text.
  3. PRIMARY:  Send OCR text to HuggingFace Inference Router (generative LLM)
               Model: Qwen/Qwen2.5-7B-Instruct  (or HF_MODEL env override)
               Produces structured JSON with name, abn, address, commodity.
  4. FALLBACK: For any field that the LLM returns as empty or with confidence < 0.5,
               run extractive QA using deepset/roberta-base-squad2.
               This model extracts exact text spans — no hallucination.
  5. Validate ABN checksum (ATO algorithm).
  6. Sanitise address  →  "suburb state postcode" only.
  7. Return ExtractResult.

OCR  : Tesseract (pytesseract) — runs 100% locally.
LLM  : HuggingFace Inference Router — free tier.
        Set HF_TOKEN in backend/.env  (https://huggingface.co/settings/tokens)
        Set HF_MODEL  in backend/.env  (default: Qwen/Qwen2.5-7B-Instruct)
QA   : deepset/roberta-base-squad2 via huggingface_hub InferenceClient.
        Same HF_TOKEN is reused — no extra credentials needed.

Address extraction scope
------------------------
Only suburb, state abbreviation, and postcode are extracted.
Format: "<suburb> <state> <postcode>"  e.g. "Keperra QLD 4054"

Environment variables
---------------------
HF_TOKEN   Required.
HF_MODEL   Generative model repo (default: Qwen/Qwen2.5-7B-Instruct)
"""

import io
import json
import logging
import os
import re

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from hf_supply_chain_qa import extract_supplier_entities

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_MODEL  = "Qwen/Qwen2.5-7B-Instruct"
HF_ROUTER_BASE = "https://router.huggingface.co/hf-inference/models"

# Confidence threshold below which roberta fallback is triggered
ROBERTA_FALLBACK_THRESHOLD = 0.5


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
    extraction_method: dict = {}   # records which model filled each field


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
  RULE 2:  Do NOT include the street name.
  RULE 3:  Do NOT include the street number.
  RULE 4:  Do NOT include unit, suite, level, floor, or lot numbers.
  RULE 5:  Do NOT include the country name.
  RULE 6:  Do NOT include a comma anywhere in the address field.
  RULE 7:  State MUST be a standard abbreviation: NSW VIC QLD WA SA TAS ACT NT
  RULE 8:  Postcode MUST be exactly 4 digits.
  RULE 9:  If only state + postcode are visible, return "<state> <postcode>".
  RULE 10: If nothing identifiable is found, return empty string "".

════════════════════════════════════════════════════════
FIELD 4 — commodity
════════════════════════════════════════════════════════
The primary product or service supplied.
Use a short noun phrase of 1–4 words.
Examples: "Timber", "Seafood", "Grain", "Steel", "Electrical Components".

HARD RULES:
  ✗ Do NOT describe the document type.
  ✗ Do NOT return vague terms like "Goods" or "Services" unless no better term exists.

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
  name/commodity  1.0 = clearly labelled  |  0.5 = inferred  |  0.0 = not found
  abn             1.0 = 11 digits near supplier  |  0.5 = uncertain  |  0.0 = not found
  address         1.0 = suburb+state+postcode  |  0.5 = state+postcode  |  0.0 = not found

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

OCR TEXT:
---
{ocr_text}
---
"""


# ── LLM call — HuggingFace Inference Router ────────────────────────────────────

def run_llm(ocr_text: str) -> dict:
    """
    Send OCR text to the HuggingFace Inference Router and return parsed JSON.
    Model must be a generative/instruction-tuned LLM (not extractive QA like roberta).
    """
    api_key = os.getenv("HF_TOKEN", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "HF_TOKEN is not configured. "
                "Create a free token at https://huggingface.co/settings/tokens "
                "and add HF_TOKEN=hf_... to backend/.env"
            ),
        )

    model   = os.getenv("HF_MODEL", DEFAULT_MODEL)
    url     = f"{HF_ROUTER_BASE}/{model}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": EXTRACT_PROMPT.format(ocr_text=ocr_text[:8000])}],
        "temperature": 0.0,
        "max_tokens":  1024,
    }

    logger.info("[extract] HF router model: %s  url: %s", model, url)

    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=60)
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail=f"Cannot reach HuggingFace router: {exc}")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="HuggingFace authentication failed — check HF_TOKEN.")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Model '{model}' not found on HF router.")
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail="HuggingFace free tier rate limit — retry in a moment.")
    if resp.status_code == 503:
        raise HTTPException(status_code=503, detail=f"Model '{model}' is loading (cold start) — retry in 20–60s.")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"HuggingFace router error {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
        raw  = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected HuggingFace response shape: {exc}")

    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$",       "", raw).strip()
    json_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(1)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("HF non-JSON response: %s", raw[:500])
        raise HTTPException(status_code=502, detail=f"HuggingFace model returned unparseable JSON: {exc}")


# ── Roberta QA fallback ───────────────────────────────────────────────────────

def apply_roberta_fallback(
    llm_result: dict,
    conf_raw: dict,
    ocr_text: str,
    extraction_method: dict,
) -> tuple[dict, dict, dict]:
    """
    For any field that the LLM left empty or returned with confidence < threshold,
    run deepset/roberta-base-squad2 on the raw OCR text and fill the gap.

    Returns updated (llm_result, conf_raw, extraction_method).
    """
    fields_to_check = ["name", "abn", "address", "commodity"]
    needs_fallback  = [
        f for f in fields_to_check
        if not str(llm_result.get(f, "")).strip()
        or float(conf_raw.get(f, 0)) < ROBERTA_FALLBACK_THRESHOLD
    ]

    if not needs_fallback:
        for f in fields_to_check:
            extraction_method[f] = "llm"
        return llm_result, conf_raw, extraction_method

    logger.info(
        "[extract] roberta fallback triggered for fields: %s",
        needs_fallback,
    )

    roberta_results = extract_supplier_entities(ocr_text)

    for field in fields_to_check:
        if field in needs_fallback:
            rb = roberta_results.get(field, {})
            rb_answer = str(rb.get("answer", "")).strip()
            rb_score  = float(rb.get("score",  0.0))

            current_val  = str(llm_result.get(field, "")).strip()
            current_conf = float(conf_raw.get(field, 0.0))

            # Use roberta answer if it has a higher score or the LLM returned nothing
            if rb_answer and (not current_val or rb_score > current_conf):
                llm_result[field] = rb_answer
                conf_raw[field]   = rb_score
                extraction_method[field] = "roberta-base-squad2"
                logger.info(
                    "[extract] roberta filled field='%s' answer=%r score=%.3f",
                    field, rb_answer, rb_score,
                )
            else:
                extraction_method[field] = "llm"
        else:
            extraction_method[field] = "llm"

    return llm_result, conf_raw, extraction_method


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


# ── Address post-processing ───────────────────────────────────────────────────

_AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}

_STATE_POSTCODE_RE = re.compile(
    r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})\b", re.IGNORECASE
)
_PO_BOX_RE       = re.compile(r"\bP\.?\s*O\.?\s*Box\b", re.IGNORECASE)
_BUYER_LABEL_RE  = re.compile(
    r"^(bill\s+to|ship\s+to|deliver\s+to|delivery\s+address"
    r"|remittance|customer|attention|attn|consignee)",
    re.IGNORECASE,
)
_STREET_POLLUTION_RE = re.compile(
    r"(^\d+[A-Za-z]?\s)"
    r"|(\b(street|st|road|rd|avenue|ave|drive|dr"
    r"|place|pl|lane|ln|boulevard|blvd|way|court"
    r"|ct|crescent|cres|terrace|tce|close|cl"
    r"|parade|pde|highway|hwy|circuit|cct)\b)",
    re.IGNORECASE,
)


def _sanitise_address(address: str, existing_warnings: list[str]) -> tuple[str, list[str], float]:
    warnings = list(existing_warnings)
    if not address:
        return "", warnings, 0.0

    cleaned = re.sub(r",?\s*\bAustralia\b", "", address, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r",?\s*\bAU\b",        "", cleaned,  flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace(",", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(
        r"^(unit|u|suite|ste|level|lvl|floor|fl|apt|apartment|lot|p\.?o\.?\s*box)\s+[\w/]+\s*",
        "", cleaned, flags=re.IGNORECASE
    ).strip()
    cleaned = re.sub(r"^\d+[A-Za-z]?[\s,/\\-]+", "", cleaned).strip()

    if _BUYER_LABEL_RE.match(cleaned):
        warnings.append("Address may belong to buyer, not supplier — verify manually.")
    if _PO_BOX_RE.search(address):
        warnings.append("Address is a PO Box — used suburb/state/postcode only.")
    if _STREET_POLLUTION_RE.search(cleaned):
        warnings.append(
            "Address appears to contain a street name or number — "
            "only suburb/state/postcode expected."
        )

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
    Full extraction pipeline:
      1. Validate file type & size.
      2. Run Tesseract OCR  →  raw text.
      3. PRIMARY:  Qwen2.5-7B-Instruct (generative)  →  structured JSON.
      4. FALLBACK: deepset/roberta-base-squad2 (extractive QA) fills any
                   empty or low-confidence fields from the LLM.
      5. Validate ABN checksum.
      6. Sanitise address  →  suburb state postcode.
      7. Return ExtractResult (includes extraction_method per field).
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

    # ── Step 1: OCR ────────────────────────────────────────────────────────────
    ocr_text = run_ocr(file_bytes, ct)
    logger.debug("OCR produced %d chars for '%s'", len(ocr_text), file.filename)

    if not ocr_text.strip():
        return ExtractResult(
            warnings=[
                "OCR returned no text. The document may be blank, "
                "encrypted, or a scanned image with very low resolution."
            ]
        )

    # ── Step 2: Primary LLM extraction ────────────────────────────────────────
    raw      = run_llm(ocr_text)
    conf_raw = dict(raw.get("confidence", {}))
    warnings = list(raw.get("warnings",   []))
    extraction_method: dict = {}

    # ── Step 3: Roberta fallback for empty / low-confidence fields ─────────────
    raw, conf_raw, extraction_method = apply_roberta_fallback(
        raw, conf_raw, ocr_text, extraction_method
    )

    # ── Step 4: ABN validation ─────────────────────────────────────────────────
    abn_value = str(raw.get("abn", "")).strip()
    if abn_value:
        warnings.extend(_validate_abn(abn_value))

    # ── Step 5: Address sanitisation ──────────────────────────────────────────
    llm_addr      = str(raw.get("address", "")).strip()
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
        warnings          = warnings,
        extraction_method = extraction_method,
    )

    logger.info(
        "extract: file=%s name=%r abn=%r address=%r addr_conf=%.2f method=%s warnings=%d",
        file.filename, result.name, result.abn,
        result.address, result.confidence.address,
        extraction_method, len(warnings),
    )
    return result
