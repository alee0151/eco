"""
POST /api/extract

Accepts a multipart upload of a PDF or image file.
Runs OCR via pytesseract (or swaps in a cloud provider),
then uses an LLM prompt (OpenAI GPT-4o-mini by default, or a
local Ollama model) to extract the four supplier fields.

Environment variables
---------------------
OCR_PROVIDER          tesseract | textract | vision   (default: tesseract)
LLM_PROVIDER          openai | ollama                 (default: openai)
OPENAI_API_KEY        Required when LLM_PROVIDER=openai
OPENAI_MODEL          default: gpt-4o-mini
OLLAMA_MODEL          default: llama3.2
OLLAMA_BASE_URL       default: http://localhost:11434
"""

import io
import json
import logging
import os
import re
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Response schema ───────────────────────────────────────────────────────────

class FieldConfidence(BaseModel):
    name: float = 0.0
    abn: float = 0.0
    address: float = 0.0
    commodity: float = 0.0


class ExtractResult(BaseModel):
    name: str = ""
    abn: str = ""
    address: str = ""
    commodity: str = ""
    confidence: FieldConfidence = FieldConfidence()
    warnings: list[str] = []


# ── OCR helpers ───────────────────────────────────────────────────────────────

def _ocr_tesseract(file_bytes: bytes, content_type: str) -> str:
    """
    Run Tesseract OCR locally.
    Requires: pip install pytesseract Pillow pdf2image
    System dep: apt install tesseract-ocr poppler-utils  (or brew equivalent)
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"pytesseract / Pillow not installed: {e}",
        )

    if "pdf" in content_type:
        try:
            from pdf2image import convert_from_bytes
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"pdf2image not installed: {e}",
            )
        pages = convert_from_bytes(file_bytes, dpi=200)
        # OCR first page only for now; extend for multi-page if needed
        return pytesseract.image_to_string(pages[0])
    else:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img)


def _ocr_textract(file_bytes: bytes, content_type: str) -> str:
    """
    AWS Textract – DetectDocumentText (sync, single page).
    Requires: pip install boto3
    IAM permission: textract:DetectDocumentText
    """
    try:
        import boto3
    except ImportError as e:
        raise HTTPException(
            status_code=500, detail=f"boto3 not installed: {e}"
        )
    client = boto3.client("textract")
    response = client.detect_document_text(
        Document={"Bytes": file_bytes}
    )
    lines = [
        block["Text"]
        for block in response["Blocks"]
        if block["BlockType"] == "LINE"
    ]
    return "\n".join(lines)


def _ocr_vision(file_bytes: bytes, content_type: str) -> str:
    """
    Google Cloud Vision – document_text_detection.
    Requires: pip install google-cloud-vision
    Env var:  GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
    """
    try:
        from google.cloud import vision
    except ImportError as e:
        raise HTTPException(
            status_code=500, detail=f"google-cloud-vision not installed: {e}"
        )
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=file_bytes)
    response = client.document_text_detection(image=image)
    return response.full_text_annotation.text


OCR_PROVIDERS = {
    "tesseract": _ocr_tesseract,
    "textract":  _ocr_textract,
    "vision":    _ocr_vision,
}


def run_ocr(file_bytes: bytes, content_type: str) -> str:
    provider = os.getenv("OCR_PROVIDER", "tesseract")
    fn = OCR_PROVIDERS.get(provider)
    if fn is None:
        raise HTTPException(
            status_code=500,
            detail=f"Unknown OCR_PROVIDER '{provider}'. Choose: {list(OCR_PROVIDERS)}",
        )
    text = fn(file_bytes, content_type)
    logger.debug("OCR (%s) produced %d chars", provider, len(text))
    return text


# ── LLM helpers ───────────────────────────────────────────────────────────────

EXTRACT_PROMPT = """
You are a data-extraction assistant for an Australian supply-chain risk platform.

From the raw OCR text below, extract EXACTLY these four fields:
  - name       : The supplier / company name
  - abn        : The Australian Business Number (11 digits, spaces allowed)
  - address    : The full street address including suburb, state and postcode
  - commodity  : The primary product or commodity supplied (e.g. Timber, Seafood, Grain)

Return ONLY valid JSON in this exact shape (no prose, no markdown fences):
{
  "name":      "...",
  "abn":       "...",
  "address":   "...",
  "commodity": "...",
  "confidence": {
    "name":      0.0,
    "abn":       0.0,
    "address":   0.0,
    "commodity": 0.0
  },
  "warnings": []
}

Rules:
- If a field cannot be found, use an empty string "".
- confidence values are 0.0 – 1.0 reflecting how certain you are.
- Add human-readable strings to warnings[] for anything suspicious
  (e.g. "ABN digit count incorrect", "Address appears incomplete").
- Do NOT invent data that is not present in the text.

OCR TEXT:
---
{ocr_text}
---
"""


def _llm_openai(ocr_text: str) -> dict:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise HTTPException(
            status_code=500, detail=f"openai package not installed: {e}"
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set.",
        )

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a JSON-only data extraction assistant."},
            {"role": "user",   "content": EXTRACT_PROMPT.format(ocr_text=ocr_text[:12000])},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    return json.loads(raw)


def _llm_ollama(ocr_text: str) -> dict:
    model    = os.getenv("OLLAMA_MODEL",    "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    payload = {
        "model":  model,
        "prompt": EXTRACT_PROMPT.format(ocr_text=ocr_text[:8000]),
        "stream": False,
        "format": "json",
    }
    resp = httpx.post(f"{base_url}/api/generate", json=payload, timeout=120)
    resp.raise_for_status()
    raw = resp.json().get("response", "{}")
    # Ollama sometimes wraps in markdown fences — strip them
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
    raw = re.sub(r"\n?```$",       "", raw.strip())
    return json.loads(raw)


LLM_PROVIDERS = {
    "openai": _llm_openai,
    "ollama": _llm_ollama,
}


def run_llm(ocr_text: str) -> dict:
    provider = os.getenv("LLM_PROVIDER", "openai")
    fn = LLM_PROVIDERS.get(provider)
    if fn is None:
        raise HTTPException(
            status_code=500,
            detail=f"Unknown LLM_PROVIDER '{provider}'. Choose: {list(LLM_PROVIDERS)}",
        )
    return fn(ocr_text)


# ── Validation helpers ────────────────────────────────────────────────────────

def _validate_abn(abn: str) -> list[str]:
    """Apply the ATO's ABN checksum algorithm. Returns a list of warnings."""
    warnings = []
    digits = re.sub(r"\D", "", abn)
    if not digits:
        return warnings  # empty is handled upstream
    if len(digits) != 11:
        warnings.append(f"ABN '{abn}' does not have 11 digits.")
        return warnings

    # ATO weighting
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    d = [int(c) for c in digits]
    d[0] -= 1  # subtract 1 from first digit
    total = sum(w * v for w, v in zip(weights, d))
    if total % 89 != 0:
        warnings.append(f"ABN '{abn}' fails the ATO checksum — may be invalid.")
    return warnings


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
):
    """
    1. Read the uploaded file into memory.
    2. Run OCR to get raw text.
    3. Pass text to LLM to extract structured fields.
    4. Validate ABN checksum.
    5. Return ExtractResult.
    """
    # ── Content-type guard ──
    ct = (file.content_type or "").lower()
    # Allow missing content-type for .pdf uploads that browsers sometimes mislabel
    if file.filename and file.filename.lower().endswith(".pdf"):
        ct = "application/pdf"
    if ct not in ALLOWED_TYPES and not ct.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ct}'. Upload a PDF or image.",
        )

    # ── Read file ──
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    # ── OCR ──
    ocr_text = run_ocr(file_bytes, ct)
    if not ocr_text.strip():
        # Return empty result with a warning rather than a hard 422
        return ExtractResult(
            warnings=["OCR returned no text. The document may be blank, encrypted, or purely image-based with low resolution."]
        )

    # ── LLM extraction ──
    try:
        raw = run_llm(ocr_text)
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned unparseable JSON: {e}",
        )

    # ── Build result ──
    conf_raw  = raw.get("confidence", {})
    warnings  = list(raw.get("warnings", []))
    abn_value = str(raw.get("abn", "")).strip()

    # Server-side ABN validation
    if abn_value:
        warnings.extend(_validate_abn(abn_value))

    result = ExtractResult(
        name      = str(raw.get("name",      "")).strip(),
        abn       = abn_value,
        address   = str(raw.get("address",   "")).strip(),
        commodity = str(raw.get("commodity", "")).strip(),
        confidence=FieldConfidence(
            name      = float(conf_raw.get("name",      0)),
            abn       = float(conf_raw.get("abn",       0)),
            address   = float(conf_raw.get("address",   0)),
            commodity = float(conf_raw.get("commodity", 0)),
        ),
        warnings=warnings,
    )

    logger.info(
        "extract: file=%s name=%r abn=%r warnings=%d",
        file.filename, result.name, result.abn, len(warnings),
    )
    return result
