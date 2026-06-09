from typing import Literal

from pydantic import BaseModel, Field


Mode = Literal["applet", "cos", "usim"]


class ChatRequest(BaseModel):
    mode: Mode = "applet"
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    content: str
    metadata: dict
    score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
