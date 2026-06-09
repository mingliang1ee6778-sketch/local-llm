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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed chunks even when their generated ids already exist.",
    )
    args = parser.parse_args()

    settings = get_settings()
    source_root = settings.raw_data_path / args.mode
    print(f"loading documents from {source_root}", flush=True)
    documents = load_documents(source_root, args.mode, args.source_filter)
    print(f"loaded {len(documents)} documents/pages/files", flush=True)
    chunks = chunk_documents(documents)
    if args.limit:
        chunks = chunks[: args.limit]
    print(f"created {len(chunks)} chunks", flush=True)
    embedder = Embedder(settings.embedding_model, settings.embedding_backend)
    store = VectorStore(settings.vectordb_path)
    ids = [_chunk_id(chunk.metadata, chunk.content) for chunk in chunks]

    if not args.force:
        existing_ids = _existing_ids(store, args.mode, ids)
        if existing_ids:
            chunks_and_ids = [
                (chunk, chunk_id)
                for chunk, chunk_id in zip(chunks, ids)
                if chunk_id not in existing_ids
            ]
            chunks = [chunk for chunk, _ in chunks_and_ids]
            ids = [chunk_id for _, chunk_id in chunks_and_ids]
            print(f"skipped {len(existing_ids)} existing chunks", flush=True)
            print(f"remaining {len(chunks)} chunks", flush=True)

    for start in range(0, len(chunks), args.batch_size):
        batch = chunks[start : start + args.batch_size]
        batch_ids = ids[start : start + args.batch_size]
        texts = [chunk.content for chunk in batch]
        embeddings = embedder.embed(texts)
        metadatas = [chunk.metadata for chunk in batch]
        store.add(args.mode, batch_ids, texts, embeddings, metadatas)
        print(f"ingested {min(start + args.batch_size, len(chunks))}/{len(chunks)}", flush=True)


def _chunk_id(metadata: dict, content: str) -> str:
    digest = hashlib.sha256()
    digest.update(str(metadata).encode("utf-8", errors="ignore"))
    digest.update(content[:500].encode("utf-8", errors="ignore"))
    return digest.hexdigest()


def _existing_ids(store: VectorStore, mode: str, ids: list[str]) -> set[str]:
    if not ids:
        return set()
    existing: set[str] = set()
    collection = store.collection(mode)
    for start in range(0, len(ids), 1000):
        result = collection.get(ids=ids[start : start + 1000])
        existing.update(result.get("ids") or [])
    return existing


if __name__ == "__main__":
    main()
