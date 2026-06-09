from backend.rag.embedder import Embedder
from backend.rag.vectorstore import VectorStore


class Retriever:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.embedder = Embedder(settings.embedding_model, settings.embedding_backend)
        self.store = VectorStore(settings.vectordb_path)

    def retrieve(self, query: str, mode: str, top_k: int | None = None) -> list[dict]:
        embedding = self.embedder.embed([query])[0]
        domain_filter = {"domain_tag": mode}
        return self.store.query(
            mode=mode,
            embedding=embedding,
            top_k=top_k or self.settings.retrieval_top_k,
            where=domain_filter,
        )
