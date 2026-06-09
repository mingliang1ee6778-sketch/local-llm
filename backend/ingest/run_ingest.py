import argparse
import hashlib

from backend.config import get_settings
from backend.ingest.chunker import chunk_documents
from backend.ingest.loaders import load_documents
from backend.rag.embedder import Embedder
from backend.rag.vectorstore import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["applet", "cos", "usim"], default="applet")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--source-filter",
        action="append",
        default=[],
        help="Only ingest chunks whose metadata source contains this text. Can be repeated.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Maximum chunks to ingest.")
    args = parser.parse_args()

    settings = get_settings()
    source_root = settings.raw_data_path / args.mode
    documents = load_documents(source_root, args.mode, args.source_filter)
    chunks = chunk_documents(documents)
    if args.limit:
        chunks = chunks[: args.limit]
    embedder = Embedder(settings.embedding_model, settings.embedding_backend)
    store = VectorStore(settings.vectordb_path)

    for start in range(0, len(chunks), args.batch_size):
        batch = chunks[start : start + args.batch_size]
        texts = [chunk.content for chunk in batch]
        embeddings = embedder.embed(texts)
        ids = [_chunk_id(chunk.metadata, chunk.content) for chunk in batch]
        metadatas = [chunk.metadata for chunk in batch]
        store.add(args.mode, ids, texts, embeddings, metadatas)
        print(f"ingested {min(start + args.batch_size, len(chunks))}/{len(chunks)}")


def _chunk_id(metadata: dict, content: str) -> str:
    digest = hashlib.sha256()
    digest.update(str(metadata).encode("utf-8", errors="ignore"))
    digest.update(content[:500].encode("utf-8", errors="ignore"))
    return digest.hexdigest()


if __name__ == "__main__":
    main()
