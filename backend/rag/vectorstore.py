from pathlib import Path

import chromadb


VALID_MODES = {"applet", "cos", "usim"}


class VectorStore:
    def __init__(self, persist_path: Path) -> None:
        self.client = chromadb.PersistentClient(path=str(persist_path))

    def collection(self, mode: str):
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode: {mode}")
        return self.client.get_or_create_collection(name=mode)

    def add(
        self,
        mode: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        self.collection(mode).upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        mode: str,
        embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[dict]:
        result = self.collection(mode).query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            {
                "content": document,
                "metadata": metadata,
                "score": None if distance is None else 1.0 - float(distance),
            }
            for document, metadata, distance in zip(documents, metadatas, distances)
        ]
