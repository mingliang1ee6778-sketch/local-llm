from functools import lru_cache

import numpy as np
import httpx
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str, backend: str = "sentence-transformers") -> None:
        self.model_name = model_name
        self.backend = backend
        self.model = None
        if backend == "sentence-transformers":
            self.model = _load_model(model_name)
        elif backend != "ollama":
            raise ValueError(f"Unsupported embedding backend: {backend}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.backend == "ollama":
            return _embed_with_ollama(self.model_name, texts)
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if isinstance(vectors, np.ndarray):
            return vectors.astype(float).tolist()
        return [vector.astype(float).tolist() for vector in vectors]


@lru_cache
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def _embed_with_ollama(model_name: str, texts: list[str]) -> list[list[float]]:
    response = httpx.post(
        "http://localhost:11434/api/embed",
        json={"model": model_name, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    if "embeddings" in data:
        return data["embeddings"]
    return [data["embedding"]]
