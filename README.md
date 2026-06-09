# Java Card Local LLM Agent

Offline-oriented local LLM agent for Java Card development. The first target is a
PBOC applet agent backed by RAG over `data/raw/applet/PBOC`.

## Quick Start

1. Install Ollama and pull the inference model.

   ```powershell
   ollama pull deepseek-coder-v2:16b-lite-instruct
   ```

   Current local smoke-test fallback:

   ```powershell
   ollama pull qwen2.5:3b
   ollama pull nomic-embed-text
   ```

2. Create Python environment and install dependencies.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. Build the applet vector database.

   ```powershell
   python -m backend.ingest.run_ingest --mode applet
   ```

   Faster source-only smoke ingest:

   ```powershell
   python -m backend.ingest.run_ingest --mode applet --source-filter src/com/konai/pboc --batch-size 64
   ```

4. Start the backend.

   ```powershell
   uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

5. Ask a question.

   ```powershell
   curl.exe -X POST http://127.0.0.1:8000/chat `
     -H "Content-Type: application/json" `
     -d "{\"mode\":\"applet\",\"query\":\"How does the PBOC applet handle GPO?\"}"
   ```

## Tests

Run the local agent routing tests without starting Ollama or FastAPI:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

These tests cover the current routing contract:

- General follow-up messages such as `你在说什么。` return a direct answer with no RAG sources.
- Complaints such as `你刚才答非所问。` return a direct answer with no RAG sources.
- Project questions mentioning `APDU`, `PBOC`, or `GPO` use the retriever and LLM path.

Run the real web/RAG/Ollama integration smoke test against a running backend:

```powershell
$env:LOCAL_LLM_RUN_INTEGRATION='1'
.\.venv\Scripts\python.exe -m unittest tests.test_web_integration -v
```

This test calls the real local web app at `http://127.0.0.1:8000` by default:

- `GET /` verifies the chat page is served.
- `POST /chat` with `你在说什么。` verifies general chat returns no RAG sources.
- `POST /chat` with an APDU/PBOC question verifies the real RAG + Ollama path returns an answer and sources.

Use `LOCAL_LLM_BASE_URL` to target a different backend URL.

## Current Shape

- One backend, three modes: `applet`, `cos`, `usim`.
- One local model service through an OpenAI-compatible client.
- One Chroma persistence directory, separated by collection and `domain_tag`.
- PBOC applet data is ready under `data/raw/applet/PBOC`.

COS and USIM collections are scaffolded but need raw materials under
`data/raw/cos` and `data/raw/usim`.

## Current Verified Local Setup

This workspace has been verified with:

- `MODEL_NAME=qwen2.5:3b`
- `EMBEDDING_BACKEND=ollama`
- `EMBEDDING_MODEL=nomic-embed-text:latest`
- Applet source ingest count: `960` chunks
- Backend URL: `http://127.0.0.1:8000`

See `WORKLOG.md` for the step-by-step execution record.
