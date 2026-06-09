import re
from dataclasses import replace

from backend.ingest.loaders import Document


HEADING_RE = re.compile(r"^(?:\d+(?:\.\d+)*\s+|#{1,6}\s+).{4,120}$")
JAVA_BOUNDARY_RE = re.compile(
    r"^\s*(?:public|protected|private|static|final|abstract|\s)+"
    r"(?:class|interface|enum|void|byte|short|int|boolean|[\w<>[\]]+)\b"
)


def chunk_documents(
    documents: list[Document],
    chunk_size: int = 1800,
    overlap: int = 180,
) -> list[Document]:
    chunks: list[Document] = []
    for doc in documents:
        if doc.metadata.get("file_type") in {"java", "c", "h", "js"}:
            chunks.extend(_chunk_code(doc, chunk_size))
        else:
            chunks.extend(_chunk_text(doc, chunk_size, overlap))
    return chunks


def _chunk_code(doc: Document, chunk_size: int) -> list[Document]:
    lines = doc.content.splitlines()
    blocks: list[tuple[str | None, list[str]]] = []
    current: list[str] = []
    heading: str | None = None
    for line in lines:
        if current and JAVA_BOUNDARY_RE.match(line) and sum(len(x) for x in current) > 300:
            blocks.append((heading, current))
            current = []
            heading = line.strip()[:120]
        elif not heading and JAVA_BOUNDARY_RE.match(line):
            heading = line.strip()[:120]
        current.append(line)
        if sum(len(x) + 1 for x in current) >= chunk_size:
            blocks.append((heading, current))
            current = []
            heading = None
    if current:
        blocks.append((heading, current))
    return [_with_heading(doc, "\n".join(block), heading) for heading, block in blocks]


def _chunk_text(doc: Document, chunk_size: int, overlap: int) -> list[Document]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", doc.content)]
    chunks: list[Document] = []
    current = ""
    heading = None
    for paragraph in paragraphs:
        if not paragraph:
            continue
        first_line = paragraph.splitlines()[0].strip()
        if HEADING_RE.match(first_line):
            heading = first_line[:120]
        if len(current) + len(paragraph) + 2 > chunk_size and current:
            chunks.append(_with_heading(doc, current, heading))
            current = current[-overlap:] if overlap else ""
        current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(_with_heading(doc, current, heading))
    return chunks


def _with_heading(doc: Document, content: str, heading: str | None) -> Document:
    metadata = dict(doc.metadata)
    if heading:
        metadata["heading"] = heading
    return replace(doc, content=content.strip(), metadata=metadata)
