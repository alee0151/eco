"""
POST /api/extract

Accepts a multipart upload of a PDF or image file.

OCR  : Tesseract (pytesseract) — free, runs 100 % locally.
LLM  : Ollama — free, runs 100 % locally.
        Install Ollama from https://ollama.com and pull a model:
          ollama pull llama3.2          # default
          ollama pull mistral            # lighter alternative

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


# ── OCR — Tesseract only ──────────────────────────────────────────────────────

def run_ocr(file_bytes: bytes, content_type: str) -> str:
    """
    Run Tesseract OCR locally.
    Requires:
      pip install pytesseract Pillow pdf2image
      macOS  : brew install tesseract poppler
      Ubuntu : sudo apt install tesseract-ocr poppler-utils
    """
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
                detail=(
                    "pdf2image is not installed. "
                    f"Run: pip install pdf2image  ({exc})"
                ),
            )
        pages = convert_from_bytes(file_bytes, dpi=200)
        # OCR first two pages to cover cover-sheets that put ABN on page 2
        texts = [pytesseract.image_to_string(p) for p in pages[:2]]
        return "\n".join(texts)
    else:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img)


# ── LLM — Ollama only (free) ──────────────────────────────────────────────────

EXTRACT_PROMPT = """\
You are a data-extraction assistant for an Australian supply-chain risk platform.

From the raw OCR text below, extract EXACTLY these four fields:
  - name       : The supplier / company name
  - abn        : The Australian Business Number (11 digits, spaces allowed)
  - address    : The full street address including suburb, state and postcode
  - commodity  : The primary product or commodity supplied (e.g. Timber, Seafood, Grain)

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


def run_llm(ocr_text: str) -> dict:
    """
    Call Ollama's local REST API to extract structured fields from OCR text.
    Ollama must be running:  ollama serve
    Model must be pulled:    ollama pull llama3.2
    """
    model    = os.getenv("OLLAMA_MODEL",    "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url      = f"{base_url}/api/generate"

    payload = {
        "model":  model,
        "prompt": EXTRACT_PROMPT.format(ocr_text=ocr_text[:8000]),
        "stream": False,
        "format": "json",   # Ollama native JSON mode — guarantees JSON output
    }

    try:
        resp = httpx.post(url, json=payload, timeout=120)
        resp.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot reach Ollama at {url}. "
                "Make sure Ollama is running: ollama serve"
            ),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:300]}",
        )

    raw = resp.json().get("response", "{}")

    # Strip markdown fences if the model ignores format=json
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
    """Apply the ATO's 11-digit weighted-sum algorithm. Returns warning strings."""
    warnings: list[str] = []
    digits = re.sub(r"\D", "", abn)
    if not digits:
        return warnings  # empty field — handled elsewhere
    if len(digits) != 11:
        warnings.append(f"ABN '{abn}' does not have 11 digits.")
        return warnings

    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    d = [int(c) for c in digits]
    d[0] -= 1  # subtract 1 from the first digit per ATO spec
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
) -> ExtractResult:
    """
    Pipeline:
      1. Validate file type & size.
      2. Run Tesseract OCR  →  raw text.
      3. Send raw text to Ollama  →  structured JSON.
      4. Validate ABN checksum.
      5. Return ExtractResult.
    """
    # ── Content-type guard ──────────────────────────────────────────────────
    ct = (file.content_type or "").lower()
    if file.filename and file.filename.lower().endswith(".pdf"):
        ct = "application/pdf"  # browsers sometimes mislabel PDFs
    if ct not in ALLOWED_TYPES and not ct.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ct}'. Please upload a PDF or image.",
        )

    # ── Size guard ──────────────────────────────────────────────────────────
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB hard cap
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit.")

    # ── OCR ─────────────────────────────────────────────────────────────────
    ocr_text = run_ocr(file_bytes, ct)
    logger.debug("OCR produced %d chars for '%s'", len(ocr_text), file.filename)

    if not ocr_text.strip():
        return ExtractResult(
            warnings=[
                "OCR returned no text. The document may be blank, "
                "encrypted, or a scanned image with very low resolution."
            ]
        )

    # ── LLM extraction ──────────────────────────────────────────────────────
    raw = run_llm(ocr_text)

    # ── Assemble result ─────────────────────────────────────────────────────
    conf_raw  = raw.get("confidence", {})
    warnings  = list(raw.get("warnings", []))
    abn_value = str(raw.get("abn", "")).strip()

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
