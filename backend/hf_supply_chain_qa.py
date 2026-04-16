"""
hf_supply_chain_qa.py

Extractive QA helper using deepset/roberta-base-squad2 via HuggingFace Inference API.

Used by routes/extract.py to extract supplier name, ABN, address, and commodity
from raw OCR text when the primary generative LLM returns empty or low-confidence fields.

Model: deepset/roberta-base-squad2
  - Extractive span-extraction model (SQuAD 2.0 fine-tuned)
  - Returns the exact span of text from the context that answers the question
  - Does NOT generate or hallucinate — only extracts what is present
  - Free on HuggingFace Inference API (HF_TOKEN required)

Environment variables
---------------------
HF_TOKEN   Required.  HuggingFace token (read access is sufficient).
           Free tier: https://huggingface.co/settings/tokens
"""

import os
import logging
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

QA_MODEL = "deepset/roberta-base-squad2"

# ─────────────────────────────────────────────────────────────────────────────
# Questions tailored for Australian supplier documents
# (invoices, delivery dockets, ABR exports, purchase orders)
# ─────────────────────────────────────────────────────────────────────────────
OCR_EXTRACTION_QUESTIONS = {
    "name": (
        "What is the name of the supplier, company, or business?"
    ),
    "abn": (
        "What is the ABN or Australian Business Number?"
    ),
    "address": (
        "What is the supplier business address or registered address including suburb state and postcode?"
    ),
    "commodity": (
        "What product, commodity, or goods are being supplied or sold?"
    ),
}


def _get_client() -> InferenceClient:
    api_key = os.getenv("HF_TOKEN", "").strip()
    if not api_key:
        raise RuntimeError(
            "HF_TOKEN is not set. Add HF_TOKEN=hf_... to backend/.env. "
            "Free token: https://huggingface.co/settings/tokens"
        )
    return InferenceClient(provider="hf-inference", api_key=api_key)


def run_qa(question: str, context: str) -> dict:
    """
    Run a single extractive QA call against the OCR text.

    Args:
        question: The extraction question (e.g. "What is the ABN?")
        context:  Raw OCR text used as the document context.

    Returns:
        dict with keys: answer (str), score (float), start (int), end (int)
        Returns empty answer with score 0.0 on any error.
    """
    try:
        client = _get_client()
        result = client.question_answering(
            question=question,
            context=context[:4000],   # roberta context window ~ 512 tokens
            model=QA_MODEL,
        )
        return {
            "answer": result.answer or "",
            "score":  round(result.score, 4),
            "start":  result.start,
            "end":    result.end,
        }
    except Exception as exc:
        logger.warning("[roberta-qa] field extraction failed: %s", exc)
        return {"answer": "", "score": 0.0, "start": 0, "end": 0}


def extract_supplier_entities(ocr_text: str) -> dict:
    """
    Extract the four key supply chain fields from raw OCR text using
    deepset/roberta-base-squad2.

    Args:
        ocr_text: Raw text string produced by Tesseract OCR from a supplier document.

    Returns:
        dict with keys matching ExtractResult fields:
        {
            "name":      {"answer": str, "score": float},
            "abn":       {"answer": str, "score": float},
            "address":   {"answer": str, "score": float},
            "commodity": {"answer": str, "score": float},
        }
    """
    results = {}
    for field, question in OCR_EXTRACTION_QUESTIONS.items():
        logger.debug("[roberta-qa] extracting field='%s'", field)
        results[field] = run_qa(question, ocr_text)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo — run directly:  python hf_supply_chain_qa.py
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_OCR_TEXT = """
TAX INVOICE

Supplier:   GreenHarvest Pty Ltd
ABN:        51 824 753 196
Address:    14 Farmland Drive, Dubbo NSW 2830, Australia
Date:       12 April 2026
Invoice #:  INV-20260412-009

Description                     Qty     Unit Price   Total
---------------------------------------------------------------
Organic Wheat Grain (bulk)      80 t    $310.00      $24,800.00
Sunflower Seeds (export grade)  20 t    $520.00      $10,400.00
---------------------------------------------------------------
Subtotal:                                            $35,200.00
GST (10%):                                           $3,520.00
Total Due:                                           $38,720.00

Payment due within 30 days. ABN verified via Australian Business Register.
"""

if __name__ == "__main__":
    print("=" * 60)
    print(" Supply Chain OCR Entity Extraction")
    print(f" Model: {QA_MODEL}")
    print("=" * 60)
    print()

    entities = extract_supplier_entities(SAMPLE_OCR_TEXT)

    labels = {
        "name":      "Supplier Name",
        "abn":       "ABN",
        "address":   "Address",
        "commodity": "Commodity",
    }
    for field, label in labels.items():
        info = entities[field]
        print(f"{label:<16}: {info['answer']}")
        print(f"{'Confidence':<16}: {info['score']}")
        print("-" * 60)
