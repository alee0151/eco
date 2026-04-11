# eco — Backend

FastAPI backend for the eco supply-chain risk platform.  
All components are **free and run 100 % locally** — no API keys required.

---

## Stack

| Layer | Tool | Cost |
|-------|------|------|
| Web framework | FastAPI + Uvicorn | Free |
| OCR | Tesseract (pytesseract) | Free |
| LLM | Ollama (llama3.2 / mistral) | Free |
| ABN enrichment | ABR public JSON API | Free |
| Geocoding | Nominatim (OpenStreetMap) | Free |

---

## Prerequisites

### 1 — Python 3.11+
```bash
python --version   # must be 3.11 or higher
```

### 2 — System dependencies for Tesseract
```bash
# macOS
brew install tesseract poppler

# Ubuntu / Debian
sudo apt update && sudo apt install tesseract-ocr poppler-utils -y
```

### 3 — Ollama (local LLM server)
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull the default model (~2 GB)
ollama pull llama3.2

# Or a lighter model for slower machines
ollama pull mistral
```

---

## Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Copy the env template (no keys needed!)
cp .env.example .env
```

---

## Run

```bash
# Terminal 1 — start Ollama
ollama serve

# Terminal 2 — start FastAPI
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |

---

## API Endpoints

### `POST /api/extract`
Upload a PDF or image. Returns extracted supplier fields.

**Request:** `multipart/form-data` — field `file`  
**Response:**
```json
{
  "name":       "Acme Timber Pty Ltd",
  "abn":        "12 345 678 901",
  "address":    "42 Forest Rd, Brisbane QLD 4000",
  "commodity":  "Timber",
  "confidence": { "name": 0.95, "abn": 0.99, "address": 0.88, "commodity": 0.91 },
  "warnings":   []
}
```

**Supported file types:** PDF, PNG, JPEG, WEBP, TIFF  
**Size limit:** 10 MB

---

## Changing the LLM model

Edit `.env`:
```bash
OLLAMA_MODEL=mistral        # faster on CPU-only machines
OLLAMA_MODEL=llama3.1:8b   # larger, more accurate
OLLAMA_MODEL=phi3           # Microsoft Phi-3, very lightweight
```

Then restart Uvicorn. No code changes needed.
