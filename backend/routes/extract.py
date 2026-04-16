"""
POST /api/extract

Accepts a multipart upload of a PDF or image file.

Pipeline
--------
  1. Validate file type & size.
  2. Run Tesseract OCR  →  raw text  (runs 100% locally).
  3. Use the OCR text as context for deepset/roberta-base-squad2
     via HuggingFace InferenceClient.question_answering().
     Four targeted questions are asked, one per field:
       - Supplier / company name
       - ABN (Australian Business Number)
       - Business address
       - Commodity / product supplied
  4. Validate ABN checksum (ATO algorithm).
  5. Sanitise address  →  "suburb state postcode" only.
  6. Return ExtractResult.

Model  : deepset/roberta-base-squad2
  - Extractive span model (SQuAD 2.0 fine-tuned RoBERTa)
  - Returns the exact span from the OCR text — no hallucination
  - Free on HuggingFace Inference API

Environment variables
---------------------
HF_TOKEN   Required. HuggingFace token (read access is sufficient).
           Free tier: https://huggingface.co/settings/tokens
"""

import io
import logging
import os
import re

from fastapi import APIRouter, HTTPException, UploadFile, File
from huggingface_hub import InferenceClient
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

QA_MODEL = "deepset/roberta-base-squad2"


# ─────────────────────────────────────────────────────────────────────────────
# Questions asked to the model — OCR text is the context for every question.
# Phrased to maximise extractive accuracy on Australian supplier documents
# (invoices, delivery dockets, ABR exports, purchase orders).
# ─────────────────────────────────────────────────────────────────────────────
QUESTIONS = {
    "name":      "What is the name of the supplier or company?",
    "abn":       "What is the ABN or Australian Business Number?",
    "address":   "What is the supplier address including suburb state and postcode?",
    "commodity": "What product or commodity is being supplied?",
}


# ── Response schema ───────────────────────────────────────────────────────────

class FieldConfidence(BaseModel):
    name:      float = 0.0
    abn:       float = 0.0
    address:   float = 0.0
    commodity: float = 0.0


class ExtractResult(BaseModel):
    name:      str = ""
    abn:       str = ""
    address:   str = ""   # "suburb state postcode" e.g. "Dubbo NSW 2830"
    commodity: str = ""
    confidence: FieldConfidence = FieldConfidence()
    warnings:  list[str] = []
    ocr_text:  str = ""   # raw OCR output — useful for debugging


# ── OCR — Tesseract ────────────────────────────────────────────────────────────

def run_ocr(file_bytes: bytes, content_type: str) -> str:
    """Extract raw text from a PDF or image using Tesseract."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"pytesseract or Pillow not installed: {exc}",
        )

    if "pdf" in content_type:
        try:
            from pdf2image import convert_from_bytes
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"pdf2image not installed: {exc}",
            )
        pages = convert_from_bytes(file_bytes, dpi=200)
        return "\n".join(pytesseract.image_to_string(p) for p in pages[:2])
    else:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img)


# ── HuggingFace QA — deepset/roberta-base-squad2 ───────────────────────────────

def _get_client() -> InferenceClient:
    api_key = os.getenv("HF_TOKEN", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "HF_TOKEN is not set. "
                "Add HF_TOKEN=hf_... to backend/.env. "
                "Free token: https://huggingface.co/settings/tokens"
            ),
        )
    return InferenceClient(provider="hf-inference", api_key=api_key)


def run_qa(client: InferenceClient, question: str, context: str) -> tuple[str, float]:
    """
    Ask one question against the OCR text context.
    Mirrors the exact pattern from the HuggingFace example:

        answer = client.question_answering(
            question="What is my name?",
            context="My name is Clara and I live in Berkeley.",
            model="deepset/roberta-base-squad2",
        )

    Returns (answer_text, confidence_score).
    """
    try:
        result = client.question_answering(
            question=question,
            context=context[:4000],   # roberta max context ~ 512 tokens
            model=QA_MODEL,
        )
        return (result.answer or ""), round(result.score, 4)
    except Exception as exc:
        logger.warning("[roberta-qa] question=%r error=%s", question, exc)
        return "", 0.0


def extract_fields(ocr_text: str) -> dict:
    """
    Run all four QA questions against the OCR text.
    The OCR text is used directly as the context for every question.

    Returns a dict:
      {
        "name":      (answer: str, score: float),
        "abn":       (answer: str, score: float),
        "address":   (answer: str, score: float),
        "commodity": (answer: str, score: float),
      }
    """
    client  = _get_client()
    results = {}
    for field, question in QUESTIONS.items():
        logger.info("[roberta-qa] field='%s'  question=%r", field, question)
        answer, score = run_qa(client, question, ocr_text)
        results[field] = {"answer": answer, "score": score}
        logger.info("[roberta-qa] field='%s'  answer=%r  score=%.4f", field, answer, score)
    return results


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


# ── Address sanitisation ───────────────────────────────────────────────────────

_AU_STATES           = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"}
_STATE_POSTCODE_RE   = re.compile(r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+(\d{4})\b", re.IGNORECASE)
_PO_BOX_RE           = re.compile(r"\bP\.?\s*O\.?\s*Box\b", re.IGNORECASE)
_STREET_POLLUTION_RE = re.compile(
    r"(^\d+[A-Za-z]?\s)|(\b(street|st|road|rd|avenue|ave|drive|dr"
    r"|place|pl|lane|ln|boulevard|blvd|way|court|ct"
    r"|crescent|cres|terrace|tce|close|cl|parade|pde"
    r"|highway|hwy|circuit|cct)\b)",
    re.IGNORECASE,
)


def _sanitise_address(address: str, existing_warnings: list[str]) -> tuple[str, list[str], float]:
    """Strip street details, country, commas. Return (cleaned, warnings, confidence)."""
    warnings = list(existing_warnings)
    if not address:
        return "", warnings, 0.0

    cleaned = re.sub(r",?\s*\bAustralia\b", "", address, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r",?\s*\bAU\b",        "", cleaned,  flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace(",", " ")
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(
        r"^(unit|u|suite|ste|level|lvl|floor|fl|apt|apartment|lot|p\.?o\.?\s*box)\s+[\w/]+\s*",
        "", cleaned, flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"^\d+[A-Za-z]?[\s,/\\-]+", "", cleaned).strip()

    if _PO_BOX_RE.search(address):
        warnings.append("Address is a PO Box — used suburb/state/postcode only.")
    if _STREET_POLLUTION_RE.search(cleaned):
        warnings.append("Address may contain a street name or number — verify manually.")

    state_match = _STATE_POSTCODE_RE.search(cleaned)
    if not state_match:
        warnings.append("Address missing Australian state abbreviation and/or postcode.")
        return cleaned, warnings, 0.3

    has_suburb = bool(cleaned[: state_match.start()].strip())
    if not has_suburb:
        warnings.append("Address missing suburb.")

    return cleaned, warnings, 1.0 if has_suburb else 0.5


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
    Extraction pipeline:

      Step 1 — Tesseract OCR
        Converts the uploaded PDF/image into raw text.

      Step 2 — deepset/roberta-base-squad2 (HuggingFace InferenceClient)
        The OCR text is passed as `context` to client.question_answering().
        Four questions are asked, one per field:

          client.question_answering(
              question="What is the name of the supplier or company?",
              context=<ocr_text>,
              model="deepset/roberta-base-squad2",
          )

        Fields extracted: name, abn, address, commodity.

      Step 3 — ABN checksum validation (ATO algorithm)
      Step 4 — Address sanitisation  →  "suburb state postcode"
      Step 5 — Return ExtractResult JSON
    """
    # ── Validate upload ───────────────────────────────────────────────────────────
    ct = (file.content_type or "").lower()
    if file.filename and file.filename.lower().endswith(".pdf"):
        ct = "application/pdf"
    if ct not in ALLOWED_TYPES and not ct.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ct}'. Upload a PDF or image.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit.")

    # ── Step 1: Tesseract OCR → raw text ───────────────────────────────────────
    ocr_text = run_ocr(file_bytes, ct)
    logger.info("[extract] OCR produced %d chars for '%s'", len(ocr_text), file.filename)

    if not ocr_text.strip():
        return ExtractResult(
            warnings=[
                "OCR returned no text. The document may be blank, "
                "encrypted, or a scanned image with very low resolution."
            ],
            ocr_text=ocr_text,
        )

    # ── Step 2: deepset/roberta-base-squad2 → extract all four fields ──────────
    #
    # Pattern (identical to the HuggingFace example):
    #
    #   client = InferenceClient(provider="hf-inference", api_key=os.environ["HF_TOKEN"])
    #
    #   answer = client.question_answering(
    #       question="What is the name of the supplier or company?",
    #       context=ocr_text,
    #       model="deepset/roberta-base-squad2",
    #   )
    #
    fields   = extract_fields(ocr_text)
    warnings: list[str] = []

    name_val      = fields["name"]["answer"]
    abn_val       = fields["abn"]["answer"]
    address_val   = fields["address"]["answer"]
    commodity_val = fields["commodity"]["answer"]

    name_conf      = fields["name"]["score"]
    abn_conf       = fields["abn"]["score"]
    address_conf   = fields["address"]["score"]
    commodity_conf = fields["commodity"]["score"]

    # ── Step 3: ABN checksum validation ────────────────────────────────────────
    if abn_val:
        warnings.extend(_validate_abn(abn_val))

    # ── Step 4: Address sanitisation ──────────────────────────────────────────
    address_val, warnings, addr_conf_floor = _sanitise_address(address_val, warnings)
    final_addr_conf = max(address_conf, addr_conf_floor) if address_val else 0.0

    result = ExtractResult(
        name      = name_val,
        abn       = abn_val,
        address   = address_val,
        commodity = commodity_val,
        confidence = FieldConfidence(
            name      = name_conf,
            abn       = abn_conf,
            address   = round(final_addr_conf, 4),
            commodity = commodity_conf,
        ),
        warnings = warnings,
        ocr_text = ocr_text,
    )

    logger.info(
        "[extract] file=%s  name=%r  abn=%r  address=%r  commodity=%r  warnings=%d",
        file.filename, result.name, result.abn,
        result.address, result.commodity, len(warnings),
    )
    return result
