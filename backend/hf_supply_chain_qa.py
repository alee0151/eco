import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="hf-inference",
    api_key=os.environ["HF_TOKEN"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Supply Chain Biodiversity Risk – Static Context (for domain QA)
# ─────────────────────────────────────────────────────────────────────────────
SUPPLY_CHAIN_CONTEXT = (
    "The ECO platform assesses biodiversity risks for ASX-listed companies by "
    "analysing their supply chain exposure to ecologically sensitive areas in "
    "Australia. Suppliers located within or adjacent to IBRA bioregions or CAPAD "
    "protected areas are flagged as high-risk. The platform uses GIS overlays to "
    "map supplier locations against biodiversity datasets including threatened "
    "species habitats, deforestation hotspots, and water stress zones. A risk "
    "score is calculated for each company based on the proportion of its suppliers "
    "that intersect with critical biodiversity areas. Companies in the agriculture, "
    "mining, and forestry sectors typically carry the highest biodiversity risk "
    "scores. Investors can use the platform's risk dashboard to compare portfolio "
    "exposure and identify suppliers that require urgent environmental due diligence."
)

DOMAIN_QUESTIONS = [
    "Which sectors carry the highest biodiversity risk scores?",
    "What datasets are used to map supplier locations?",
    "How is the risk score calculated for each company?",
    "What are suppliers located near flagged as?",
    "What can investors use the risk dashboard for?",
]


# ─────────────────────────────────────────────────────────────────────────────
# OCR Entity Extraction
# Pass raw OCR text as `context`; the model extracts the four key fields
# needed for the supply chain risk pipeline:
#   - Supplier / company name
#   - ABN (Australian Business Number)
#   - Business address
#   - Commodity / product supplied
# ─────────────────────────────────────────────────────────────────────────────

# These questions are phrased to maximise extractive accuracy for
# Australian supplier documents (invoices, ABR exports, delivery dockets).
OCR_EXTRACTION_QUESTIONS = {
    "supplier_name": "What is the name of the company or supplier?",
    "abn":          "What is the ABN or Australian Business Number?",
    "address":      "What is the business address or registered address?",
    "commodity":    "What product, commodity, or goods are being supplied?",
}

# Sample OCR text – replace this with real OCR output at runtime.
# Represents a typical Australian supplier invoice / delivery docket.
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


def run_qa(question: str, context: str) -> dict:
    """Run a single extractive QA call using deepset/roberta-base-squad2."""
    answer = client.question_answering(
        question=question,
        context=context,
        model="deepset/roberta-base-squad2",
    )
    return {
        "answer": answer.answer,
        "score": round(answer.score, 4),
        "start": answer.start,
        "end": answer.end,
    }


def extract_supplier_entities(ocr_text: str) -> dict:
    """
    Extract key supply chain entities from raw OCR text.

    Args:
        ocr_text: Raw text extracted from a supplier document via OCR.

    Returns:
        dict with keys: supplier_name, abn, address, commodity
        Each value contains the extracted answer and confidence score.
    """
    results = {}
    for field, question in OCR_EXTRACTION_QUESTIONS.items():
        results[field] = run_qa(question, ocr_text)
    return results


if __name__ == "__main__":
    print("=" * 60)
    print(" Supply Chain OCR Entity Extraction")
    print(" Model: deepset/roberta-base-squad2")
    print("=" * 60)
    print()

    entities = extract_supplier_entities(SAMPLE_OCR_TEXT)

    labels = {
        "supplier_name": "Supplier Name",
        "abn":           "ABN",
        "address":       "Address",
        "commodity":     "Commodity",
    }

    for field, label in labels.items():
        info = entities[field]
        print(f"{label:<16}: {info['answer']}")
        print(f"{'Confidence':<16}: {info['score']}")
        print("-" * 60)

    print()
    print("=" * 60)
    print(" Domain Risk QA (static context)")
    print("=" * 60)
    print()
    for q in DOMAIN_QUESTIONS:
        result = run_qa(q, SUPPLY_CHAIN_CONTEXT)
        print(f"Q: {q}")
        print(f"A: {result['answer']}  (confidence: {result['score']})")
        print("-" * 60)
