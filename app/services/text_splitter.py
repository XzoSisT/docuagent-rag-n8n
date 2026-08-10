"""Simple character-based text chunking with overlap."""

from collections.abc import Iterable

from app.schemas.document import DocumentChunk, DocumentPage


def split_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    """Split text into fixed-size overlapping character chunks."""

    _validate_chunk_settings(chunk_size, chunk_overlap)
    clean_text = text.strip()
    if not clean_text:
        return []

    chunks: list[str] = []
    step = chunk_size - chunk_overlap

    for start in range(0, len(clean_text), step):
        end = start + chunk_size
        chunks.append(clean_text[start:end])
        if end >= len(clean_text):
            break

    return chunks


def chunk_pages(
    pages: Iterable[DocumentPage],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[DocumentChunk]:
    """Chunk each page independently while preserving page metadata."""

    _validate_chunk_settings(chunk_size, chunk_overlap)
    chunks: list[DocumentChunk] = []

    # Chunks never span pages so every chunk keeps an unambiguous page number.
    for page in pages:
        for text in split_text(page.text, chunk_size, chunk_overlap):
            chunks.append(
                DocumentChunk(
                    text=text,
                    source=page.source,
                    page=page.page,
                    chunk_index=len(chunks),
                )
            )

    return chunks


def _validate_chunk_settings(chunk_size: int, chunk_overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
