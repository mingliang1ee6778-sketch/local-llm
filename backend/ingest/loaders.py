from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


TEXT_SUFFIXES = {".txt", ".md", ".java", ".c", ".h", ".js", ".json", ".xml"}
PDF_SUFFIXES = {".pdf"}


@dataclass(frozen=True)
class Document:
    content: str
    metadata: dict


def load_documents(root: Path, mode: str, source_filters: list[str] | None = None) -> list[Document]:
    if not root.exists():
        return []
    source_filters = source_filters or []
    documents: list[Document] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        source = str(path.relative_to(root)).replace("\\", "/")
        if source_filters and not any(filter_text in source for filter_text in source_filters):
            continue
        suffix = path.suffix.lower()
        if suffix in TEXT_SUFFIXES:
            documents.append(_load_text(path, root, mode))
        elif suffix in PDF_SUFFIXES:
            documents.extend(_load_pdf(path, root, mode))
    return [doc for doc in documents if doc.content.strip()]


def _load_text(path: Path, root: Path, mode: str) -> Document:
    content = path.read_text(encoding="utf-8", errors="ignore")
    return Document(content=content, metadata=_base_metadata(path, root, mode))


def _load_pdf(path: Path, root: Path, mode: str) -> list[Document]:
    reader = PdfReader(str(path))
    docs: list[Document] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        metadata = _base_metadata(path, root, mode)
        metadata["page"] = page_index
        docs.append(Document(content=text, metadata=metadata))
    return docs


def _base_metadata(path: Path, root: Path, mode: str) -> dict:
    return {
        "source": str(path.relative_to(root)).replace("\\", "/"),
        "domain_tag": mode,
        "file_type": path.suffix.lower().lstrip(".") or "unknown",
    }
