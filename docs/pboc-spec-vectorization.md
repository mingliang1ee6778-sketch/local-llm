# PBOC Spec Vectorization Notes

## Goal

Vectorize the PBOC standards under:

```text
data/raw/applet/PBOC/spec
```

The intent is to make the applet RAG collection cover both:

- PBOC Java Card source code under `data/raw/applet/PBOC/code`
- PBOC / UICS / UnionPay specification PDFs under `data/raw/applet/PBOC/spec`

## Source Inventory

The `spec` directory currently contains:

- `86` PDF files
- `1` RAR archive

The current ingestion loader supports PDF and text-like files. The RAR archive is not automatically unpacked or vectorized.

## Ingestion Method

The spec ingestion uses the existing applet collection:

```text
data/vectordb
collection: applet
```

The command is:

```powershell
.\.venv\Scripts\python.exe -m backend.ingest.run_ingest `
  --mode applet `
  --source-filter PBOC/spec `
  --batch-size 64
```

The source filter is applied before file parsing, so only paths containing `PBOC/spec` are loaded.

## Resume Behavior

The ingestion command now skips chunks whose generated IDs already exist in Chroma, unless `--force` is passed.

This matters because the full spec ingestion is slow on CPU-only Ollama embeddings. If the process is interrupted, rerunning the same command resumes by embedding only missing chunks.

Use `--force` only when intentionally re-embedding all matching chunks:

```powershell
.\.venv\Scripts\python.exe -m backend.ingest.run_ingest `
  --mode applet `
  --source-filter PBOC/spec `
  --batch-size 64 `
  --force
```

## Current Runtime Characteristics

The current local embedding setup is:

```text
EMBEDDING_BACKEND=ollama
EMBEDDING_MODEL=nomic-embed-text:latest
```

Ollama is running the embedding model on CPU in this environment, so the spec vectorization is much slower than Java source ingestion.

## Verification Method

After ingestion, verify Chroma metadata directly:

```powershell
@'
from backend.config import get_settings
from backend.rag.vectorstore import VectorStore

settings = get_settings()
collection = VectorStore(settings.vectordb_path).collection("applet")
count = collection.count()
page = collection.get(limit=count, include=["metadatas"])
sources = [m.get("source", "") for m in page.get("metadatas") or []]
spec = sum(1 for s in sources if "PBOC/spec" in s.replace("\\", "/"))
code = sum(1 for s in sources if "PBOC/code" in s.replace("\\", "/"))

print(f"total={count}")
print(f"code={code}")
print(f"spec={spec}")
'@ | .\.venv\Scripts\python.exe -
```

Then restart FastAPI before testing `/chat`, because external Chroma writes can leave the running server with a stale Chroma client during this prototype stage.

## Final Result

Completed on 2026-06-09.

Final Chroma metadata count:

```text
total=7202
code=960
spec=6242
```

The `spec` chunks came from the 86 readable PDF files under `PBOC/spec`.
The 1 RAR archive was not vectorized because the current loader does not unpack archives.

Observed vector database file:

```text
data/vectordb/chroma.sqlite3
size: about 79.7 MB
```

FastAPI was restarted after ingestion so the running app uses a fresh Chroma client.

## Retrieval Verification

Direct retriever checks returned `PBOC/spec` sources for specification-oriented queries.

Example query:

```text
PBOC 规范 借记贷记应用 卡片规范 AFL AIP GPO
```

Example sources:

```text
PBOC/spec/UICS2017-CN/.../基础规范 第2部分：借记贷记应用卡片规范.pdf page=25
PBOC/spec/UICS2017-CN/.../基础规范 第1部分：借记贷记应用规范.pdf page=18
PBOC/spec/UICS2017-CN/.../基础规范 第5部分：非接触式IC卡支付规范.pdf page=57
```

Example query:

```text
UICS 2017 debit credit application overview specification
```

Example sources:

```text
PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf page=38
PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf page=49
PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf page=58
```

## Real Agent Verification

Real `/chat` was tested against the running backend after restart.

Request:

```text
UICS 2017 debit credit application overview specification 主要说明什么？请根据规范回答。
```

Observed result:

```text
elapsed=24.49s
sources=5
```

Returned sources included:

```text
PBOC/spec/UICS2017-EN/Implementation Guide for UICS Updates 2017.pdf page=27
PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf page=12
PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf page=49
PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf page=58
PBOC/spec/UICS2017-EN/Basic Specifications/Part I Debit Credit Application Overview.pdf page=74
```

Important caveat: retrieval is now hitting the standards, but the current small local chat model can still produce a weak answer. In the observed real-agent run, it returned relevant `Part I Debit Credit Application Overview.pdf` sources but still claimed the context did not contain the specific overview. This is a prompt/model/reranking quality issue, not a missing-vector issue.

## Next Improvements

- Add metadata such as `source_kind=code|spec` so code/spec filtering and source balancing are explicit.
- Improve the answer prompt so the model uses retrieved spec pages more directly.
- Consider reranking or hybrid retrieval for standards questions.
- Add archive extraction if the RAR file needs to be ingested.
