from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.agents import get_agent
from backend.config import get_settings
from backend.schemas import ChatRequest, ChatResponse


app = FastAPI(title="Java Card Local LLM Agent", version="0.1.0")

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    agent = get_cached_agent(request.mode)
    return agent.answer(request.query, top_k=request.top_k)


@lru_cache(maxsize=3)
def get_cached_agent(mode: str):
    settings = get_settings()
    return get_agent(mode, settings)
