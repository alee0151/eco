import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="hf-inference",
    api_key=os.environ["HF_TOKEN"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Supply Chain Biodiversity Risk – Context
# This context is derived from the ECO platform's domain: Australian ASX
# company supply chains and their exposure to biodiversity/environmental risk.
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

# ─────────────────────────────────────────────────────────────────────────────
# Tailored questions for the supply chain biodiversity risk domain
# ─────────────────────────────────────────────────────────────────────────────
QUESTIONS = [
    "Which sectors carry the highest biodiversity risk scores?",
    "What datasets are used to map supplier locations?",
    "How is the risk score calculated for each company?",
    "What are suppliers located near flagged as?",
    "What can investors use the risk dashboard for?",
]


def run_qa(question: str, context: str = SUPPLY_CHAIN_CONTEXT) -> dict:
    """Run extractive QA using deepset/roberta-base-squad2."""
    answer = client.question_answering(
        question=question,
        context=context,
        model="deepset/roberta-base-squad2",
    )
    return {
        "question": question,
        "answer": answer.answer,
        "score": round(answer.score, 4),
        "start": answer.start,
        "end": answer.end,
    }


if __name__ == "__main__":
    print("=== Supply Chain Biodiversity Risk – QA Demo ===\n")
    for q in QUESTIONS:
        result = run_qa(q)
        print(f"Q: {result['question']}")
        print(f"A: {result['answer']}  (confidence: {result['score']})")
        print("-" * 60)
