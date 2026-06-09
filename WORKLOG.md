# Work Log

## 2026-06-09

### 16:29 KST - Resume
- User asked to continue and leave a record for each step.
- Current state before continuing:
  - Repository is at `D:\github\local-llm`.
  - Python `.venv` exists and dependencies are installed.
  - Backend imports and compiles successfully.
  - Ollama is installed.
  - `deepseek-coder-v2:16b-lite-instruct` tag does not exist in Ollama.
  - `deepseek-coder-v2:16b` pull was interrupted before completion.
  - Installed local Ollama models include `gemma4:latest`, `gemma3:4b`, `qwen3:4b`, `qwen2.5:3b`, and `nomic-embed-text:latest`.

### 16:31 KST - Local model fallback configuration
- Read `backend/rag/embedder.py`, `backend/config.py`, and `.env`.
- Added `EMBEDDING_BACKEND` setting.
- Updated the embedder to support both:
  - `sentence-transformers` for the planned `BAAI/bge-m3` path.
  - `ollama` for local `/api/embeddings`.
- Updated local `.env` to use already installed models:
  - Chat model: `qwen3:4b`
  - Embedding model: `nomic-embed-text:latest`
- Kept `.env.example` on the planned bge-m3 default, with the new backend setting documented.

### 16:33 KST - Fallback configuration verified
- Ran `.venv\Scripts\python.exe -m compileall backend`.
  - Result: success.
- Ran settings check.
  - Result: `MODEL_NAME=qwen3:4b`, `EMBEDDING_BACKEND=ollama`, `EMBEDDING_MODEL=nomic-embed-text:latest`.
- Ran an embedding smoke test through Ollama.
  - Result: success, embedding dimension `768`.

### 16:38 KST - Ingest size checked
- Ran a dry count for `data/raw/applet`.
  - Documents/pages/files loaded: `8056`.
  - Chunks generated: `13790`.
  - First chunks came from PBOC2013 PDF material.
- Conclusion: full ingest with local Ollama embeddings will be slow.
- Added ingest controls:
  - `--source-filter`, repeatable, to ingest only paths containing selected text.
  - `--limit`, to cap chunk count for smoke tests.

### 16:43 KST - Interrupted ingest diagnosed
- User interrupted the first filtered ingest attempt.
- Checked running processes and found two `python.exe` processes still running `backend.ingest.run_ingest`.
- Stopped the leftover ingest processes.
- Found the performance issue: filtering happened after `load_documents`, so PDFs were still being parsed before filtering.
- Updated `load_documents` so `source_filters` apply before reading files.

### 16:45 KST - Source-only ingest size checked
- Ran compile check for `backend\ingest`.
  - Result: success.
- Counted `src/com/konai/pboc` only after path prefiltering.
  - Documents loaded: `10`.
  - Chunks generated: `960`.
  - Sources are the 10 PBOC Java files under `src/com/konai/pboc`.
- Decision: ingest first `80` chunks as an end-to-end smoke database, then expand after validation.

### 16:50 KST - Smoke ingest completed
- Ran:
  - `.venv\Scripts\python.exe -m backend.ingest.run_ingest --mode applet --source-filter src/com/konai/pboc --limit 80 --batch-size 8`
- Result:
  - Completed `80/80`.
- Checked Chroma applet collection count.
  - Result: `144` records.
  - Note: count is greater than `80` because the interrupted previous ingest had already persisted some records.
- Ran retriever smoke test with query `How does PBOC handle SELECT APDU?`.
  - Result: `3` retrieved chunks from `EMVUtil.java`.
  - Retrieval path works with Ollama `nomic-embed-text:latest`.

### 16:56 KST - First API test
- Started FastAPI on `127.0.0.1:8000`.
- Tested `GET /health`.
  - Result: success, `{"status":"ok"}`.
- Tested `POST /chat` with `qwen3:4b`.
  - Result: client timed out after `180` seconds.
- Checked Ollama runtime.
  - Models were running on CPU; `qwen3:4b` was active and slow.
- Updated runtime config:
  - `MODEL_NAME=qwen2.5:3b`
  - `MAX_OUTPUT_TOKENS=256`
- Added `max_output_tokens` setting and passed it to the OpenAI-compatible chat call.

### 17:00 KST - API smoke test passed
- Restarted FastAPI on `127.0.0.1:8000`.
- Tested `GET /health`.
  - Result: success, `{"status":"ok"}`.
- Tested `POST /chat` with:
  - Model: `qwen2.5:3b`
  - Query: `In one paragraph, what does EMVUtil.checkIncoming validate?`
  - `top_k=1`
- Result:
  - Request completed in about `22` seconds.
  - Response included `1` source from `EMVUtil.java`.
- Follow-up improvement:
  - Changed `LLMClient.complete` to send separate `system` and `user` messages.
  - Tightened the user prompt so the model is told to answer only from retrieved snippets and avoid plausible but unsupported details.

### 17:03 KST - Second API smoke test passed
- Restarted FastAPI after prompt/LLM client changes.
- Tested `GET /health`.
  - Result: success.
- Tested `POST /chat` with:
  - Model: `qwen2.5:3b`
  - Query: `What fields does EMVUtil.checkIncoming validate? Answer only from the retrieved code.`
  - `top_k=3`
- Result:
  - Completed in about `16` seconds.
  - Answer: `EMVUtil.checkIncoming validates CHECK_RECEIVE, CHECK_P1, CHECK_P2, CHECK_LC, and CHECK_CLA fields.`
  - Sources: `EMVUtil.java`, `Constants.java`, `EMVUtil.java`.
- Improved Ollama embedding code to use batch `/api/embed` instead of one `/api/embeddings` call per text.

### 17:05 KST - Batch embedding verified
- Ran compile check for `backend\rag\embedder.py`.
  - Result: success.
- Ran batch embedding smoke test with two inputs through Ollama `/api/embed`.
  - Result: `2` embeddings returned.
  - Dimensions: `768`, `768`.

### 17:07 KST - Expanded source smoke database
- Ran:
  - `.venv\Scripts\python.exe -m backend.ingest.run_ingest --mode applet --source-filter src/com/konai/pboc --limit 300 --batch-size 32`
- Result:
  - Completed `300/300` in about `72` seconds.
- Checked Chroma applet collection count.
  - Result: `300` records.
- Tested `/chat` immediately after external ingest.
  - Result: HTTP `500`.
  - Server traceback: Chroma `InternalError: Error finding id`.
- Verified retriever in a fresh Python process.
  - Result: success, retrieved `4` chunks from `PBOC.java`.
- Diagnosis:
  - FastAPI process held an old Chroma client while another process rewrote/upserted the collection.
  - Need to restart FastAPI after external ingest during this prototype stage.

### 17:10 KST - Business query verified after restart
- Restarted FastAPI after the expanded ingest.
- Tested `GET /health`.
  - Result: success.
- Retested `POST /chat` with query:
  - `According to retrieved PBOC applet code, what does processGPO do?`
- Result:
  - Completed in about `20` seconds.
  - Response correctly said the retrieved context does not contain a method named `processGPO`.
  - Sources: `4` chunks from `PBOC.java`.
- Ran `rg` over PBOC Java sources for `processGPO|GPO`.
  - Result: no `processGPO` method name; only GPO-related comments/handling references in `PBOC.java`.

### 17:15 KST - Full Java source ingest completed
- Ran:
  - `.venv\Scripts\python.exe -m backend.ingest.run_ingest --mode applet --source-filter src/com/konai/pboc --batch-size 64`
- Result:
  - Completed `960/960` chunks in about `190` seconds.
- Checked Chroma applet collection count.
  - Result: `960` records.
- Restarted FastAPI after ingest.
- Tested `GET /health`.
  - Result: HTTP `200`, `{"status":"ok"}`.
- Tested `POST /chat` with query:
  - `According to the retrieved code, how does the applet route APDU processing for PSE, PPSE, and normal PBOC instances?`
- Result:
  - Completed in about `28` seconds.
  - Answer correctly described routing by `TypeOfAppletInstance`:
    - `APPTYPE_PSE` -> `pse.process(apdu)`
    - `APPTYPE_PPSE` -> `ppse.process(apdu)`
    - Otherwise normal PBOC path checks APDU protocol/contactless flag.
  - Sources returned: `5`, from `PSE.java` and `PBOC.java`.
- Current service:
  - FastAPI is running on `http://127.0.0.1:8000`.
- Current vector DB:
  - `data/vectordb/chroma.sqlite3`
  - Size observed: about `6.9 MB`.

### 17:17 KST - README updated
- Updated `README.md` with:
  - Current local fallback model commands for `qwen2.5:3b` and `nomic-embed-text`.
  - Faster source-only smoke ingest command.
  - Current verified local setup and backend URL.

### 17:12 KST - Chat UI requested
- User asked to make it possible to chat interactively.
- Added `frontend/index.html`, a local browser chat UI.
- Updated `backend/main.py`:
  - `GET /` now serves the chat UI.
  - `/static` mounts the frontend directory.

### 17:14 KST - Chat UI verified
- Ran `.venv\Scripts\python.exe -m compileall backend`.
  - Result: success.
- Restarted FastAPI on `127.0.0.1:8000`.
- Tested `GET /health`.
  - Result: HTTP `200`, `{"status":"ok"}`.
- Tested `GET /`.
  - Result: HTTP `200`, `text/html; charset=utf-8`.
  - Response begins with the chat UI HTML.
- Tested `POST /chat` from a Python client with query:
  - `What Java files are mentioned in the retrieved context?`
- Result:
  - Completed in about `13` seconds.
  - Answer mentioned `PBOC.java` and `RecordFile.java`.
  - Sources returned: `2`.
- User can now open `http://127.0.0.1:8000/` in a browser and chat.

### 17:25 KST - Fixed non-RAG clarification replies
- User reported the browser answer was off-topic for `你在说什么。`.
- Root cause:
  - `/chat` always routed every message through vector retrieval.
  - A normal clarification message was treated like a PBOC source question, so unrelated Java snippets were returned as sources.
- Updated `backend/agents/base.py`:
  - Added a small general-chat detector for clarification/meta messages such as `你在说什么`, `什么意思`, `答非所问`, `你是谁`, and `hello`.
  - These messages now return a direct answer with `sources=[]`.
  - Project terms such as `APDU`, `PBOC`, `Java Card`, `源码`, and `规范` still force normal RAG behavior.
- Updated `backend/main.py`:
  - Added a small `lru_cache` wrapper so mode agents are reused instead of rebuilt on every request.
- Updated `frontend/index.html`:
  - Changed default retrieval from `top 5` to `top 3`.
  - Reworded the initial assistant message to describe the app as local PBOC source Q&A.
- Verification:
  - Ran `.venv\Scripts\python.exe -m compileall backend`.
    - Result: success.
  - Restarted FastAPI and verified `GET /health`.
    - Result: `{"status":"ok"}`.
  - Tested `POST /chat` with `你在说什么。` using a UTF-8 Python client.
    - Result: direct Chinese clarification answer.
    - Sources returned: `0`.
  - Tested `POST /chat` with `APDU 处理是怎么分发到 PSE、PPSE 和普通 PBOC 实例的？`.
    - Result: normal RAG answer.
    - Sources returned: `3`, first source `PSE.java`.

### 17:30 KST - Added agent routing tests
- User asked to add a test method for the agent behavior and let the agent decide where to place it.
- Added:
  - `tests/__init__.py`
  - `tests/test_base_agent.py`
- Test location decision:
  - Put tests under project-level `tests/` so backend unit tests and later API tests can live outside the app package.
- Test method:
  - Uses Python standard-library `unittest`, so no extra network download or pytest dependency is needed.
  - Uses fake retriever and fake LLM objects, so tests do not start Ollama, FastAPI, or Chroma.
- Coverage:
  - `你在说什么。` returns a direct general-chat answer and `sources=[]`.
  - `你刚才答非所问。` returns a direct general-chat answer and `sources=[]`.
  - `APDU ... PSE ... PPSE ... PBOC ...` uses retriever and LLM.
  - A message containing both a general trigger and project term, such as `你在说什么，APDU 的 GPO 是什么？`, still routes to RAG.
- Verification:
  - Ran `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
    - Result: `Ran 4 tests`, `OK`.
  - Ran `py -3.11 -m compileall backend tests`.
    - Result: success.
- Added the test command and routing contract to `README.md`.

### 17:33 KST - Version control moved to GitHub fork
- User asked to record this modification and use version control without updating the originally downloaded repository.
- Confirmed original remote:
  - `origin` fetch/push: `https://github.com/bright6778/local-llm`
- Created GitHub fork under the authenticated account:
  - `https://github.com/mingliang1ee6778-sketch/local-llm`
- Added local remote:
  - `fork`: `https://github.com/mingliang1ee6778-sketch/local-llm.git`
- Created local commit:
  - `8c4da75 feat: add local Java Card LLM agent`
- Did not push to `origin`.
- Tried pushing to `fork/main`, but GitHub rejected it because `fork/main` already contained remote commits not present locally.
- To avoid overwriting fork history, pushed the current local work to a separate fork branch instead:
  - `local-agent-worklog-tests`
  - PR URL offered by GitHub: `https://github.com/mingliang1ee6778-sketch/local-llm/pull/new/local-agent-worklog-tests`

### 17:43 KST - Added real web/RAG/Ollama integration test
- User pointed out that only using fake retriever and fake LLM does not prove the real webpage, Ollama, and RAG chain works.
- Added:
  - `tests/test_web_integration.py`
- Test behavior:
  - Default `unittest discover` skips the integration test unless explicitly enabled.
  - Enable with `LOCAL_LLM_RUN_INTEGRATION=1`.
  - Targets `http://127.0.0.1:8000` by default.
  - Optional override: `LOCAL_LLM_BASE_URL`.
- Coverage:
  - `GET /` verifies the real chat page is served.
  - `POST /chat` with `你在说什么。` verifies general chat returns no sources.
  - `POST /chat` with an APDU/PBOC routing question verifies the real RAG + Ollama path returns an answer and sources.
- Verification:
  - Ran normal tests:
    - `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
    - Result: `Ran 7 tests`, `OK (skipped=3)`.
  - Ran real integration tests:
    - `$env:LOCAL_LLM_RUN_INTEGRATION='1'; .\.venv\Scripts\python.exe -m unittest tests.test_web_integration -v`
    - Result: `Ran 3 tests in 34.440s`, `OK`.
  - Ran `py -3.11 -m compileall backend tests`.
    - Result: success.
- Updated `README.md` with both fast unit test and real integration test commands.

### 17:48 KST - Replaced external integration test with real agent chat verification
- User clarified that the desired verification is not another `unittest` file hitting the API, but testing inside the real running agent behavior.
- Removed:
  - `tests/test_web_integration.py`
  - README instructions for `LOCAL_LLM_RUN_INTEGRATION`.
- Kept:
  - `tests/test_base_agent.py` as a fast routing regression test only.
- Real agent verification performed against the running backend:
  - Target: `http://127.0.0.1:8000/chat`
  - Runtime path: FastAPI -> cached AppletAgent -> Chroma retriever / direct general-chat branch -> Ollama when RAG is needed.
- Important test harness note:
  - A first PowerShell here-string attempt corrupted Chinese input into `????`, which incorrectly forced RAG.
  - Re-ran with Python Unicode escapes to guarantee the request payload contained real UTF-8 Chinese.
- Real agent results:
  - Query: `\u4f60\u5728\u8bf4\u4ec0\u4e48\u3002`
    - Elapsed: about `0.01s`.
    - Sources: `0`.
    - Result: direct clarification answer, no RAG.
  - Query: `APDU \u5904\u7406\u662f\u600e\u4e48\u5206\u53d1\u5230 PSE\u3001PPSE \u548c\u666e\u901a PBOC \u5b9e\u4f8b\u7684\uff1f`
    - Elapsed: about `22.24s`.
    - Sources: `3`.
    - Source files included `PSE.java` and `PBOC.java`.
    - Result: real RAG + Ollama answer returned.

### 17:57-19:17 KST - Vectorized PBOC specification PDFs
- User asked whether `data/raw/applet/PBOC/spec` had been fully vectorized.
- Verified current Chroma first:
  - Before spec ingest: `total=960`, `code=960`, `spec=0`.
  - Root cause: earlier ingest used `--source-filter src/com/konai/pboc`, so only the 10 Java source files were embedded.
- Counted spec inventory:
  - `86` PDF files.
  - `1` RAR archive.
  - Loader supports PDFs; the RAR archive was not unpacked or vectorized.
- Dry count:
  - Loaded PDF pages/documents: `5803`.
  - Chunks created: `6242`.
- Started full spec ingest with:
  - `.\.venv\Scripts\python.exe -m backend.ingest.run_ingest --mode applet --source-filter PBOC/spec --batch-size 64`
- Because CPU-only Ollama embedding was slow, stopped the first run after partial progress and improved `backend/ingest/run_ingest.py`:
  - Added default skip-existing behavior using generated chunk IDs.
  - Added `--force` for intentional full re-embedding.
  - Added flushed progress logs for document loading, chunking, skipping, and batch ingest.
- Resumed the same command.
  - It skipped `384` existing chunks and embedded the remaining `5858`.
- Final Chroma metadata count:
  - `total=7202`
  - `code=960`
  - `spec=6242`
- Vector DB file:
  - `data/vectordb/chroma.sqlite3`
  - Size observed: about `79.7 MB`.
- Restarted FastAPI after external Chroma writes.
  - Health check result: `{"status":"ok"}`.
- Verified direct retriever:
  - Spec queries now return `PBOC/spec` sources from CN/EN/KR PDFs with page metadata.
- Verified real `/chat` after restart:
  - Query: `UICS 2017 debit credit application overview specification 主要说明什么？请根据规范回答。`
  - Result: `sources=5`, including `PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf`.
  - Caveat: the current small local chat model returned a weak answer despite relevant spec sources. Retrieval/vectorization is fixed; answer quality still needs prompt/model/reranking improvement.
- Added documentation:
  - `docs/pboc-spec-vectorization.md`
