# eco – Backend API

FastAPI service that powers the `UploadExtractPage` OCR + AI extraction flow.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# System deps for Tesseract OCR (macOS):
brew install tesseract poppler
# Ubuntu / Debian:
# sudo apt install tesseract-ocr poppler-utils

cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or switch to LLM_PROVIDER=ollama)

uvicorn main:app --reload --port 8000
```

Health check: http://localhost:8000/api/health

Swagger UI: http://localhost:8000/docs

## Endpoints

| Method | Path          | Description                          |
|--------|---------------|--------------------------------------|
| GET    | /api/health   | Liveness check                       |
| POST   | /api/extract  | Upload PDF/image → extracted fields  |

## Configuration

All config is via environment variables (see `.env.example`).

| Variable            | Default        | Description                              |
|---------------------|----------------|------------------------------------------|
| `OCR_PROVIDER`      | `tesseract`    | `tesseract` \| `textract` \| `vision`   |
| `LLM_PROVIDER`      | `openai`       | `openai` \| `ollama`                    |
| `OPENAI_API_KEY`    | —              | Required when `LLM_PROVIDER=openai`     |
| `OPENAI_MODEL`      | `gpt-4o-mini`  | Any OpenAI chat model                   |
| `OLLAMA_MODEL`      | `llama3.2`     | Model name served by local Ollama       |
| `OLLAMA_BASE_URL`   | `http://localhost:11434` | Ollama server URL           |

## Swapping OCR providers

- **Tesseract** (default): Free, runs locally. Best for clean PDFs/images.
- **AWS Textract**: Higher accuracy on complex layouts. Requires `boto3` + AWS creds.
- **Google Vision**: Excellent handwriting support. Requires `google-cloud-vision` + service account key.

Set `OCR_PROVIDER=textract` or `OCR_PROVIDER=vision` in `.env` and install the corresponding
package from `requirements.txt`.

## Swapping LLM providers

- **OpenAI** (default): Uses `gpt-4o-mini` — fast and cheap. Needs `OPENAI_API_KEY`.
- **Ollama**: Runs LLaMA 3.2 locally — completely free, no API key needed.
  Install Ollama from https://ollama.ai then run `ollama pull llama3.2`.
