"""Tests for overlapping text chunking and document metadata."""

import pytest

from app.schemas.document import DocumentPage
from app.services.text_splitter import chunk_pages, split_text


def test_split_text_creates_expected_overlap() -> None:
    chunks = split_text("abcdefghij", chunk_size=4, chunk_overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_split_text_returns_empty_list_for_blank_text() -> None:
    assert split_text("  \n\t  ", chunk_size=10, chunk_overlap=2) == []


def test_chunk_pages_preserves_metadata_and_global_indexes() -> None:
    pages = [
        DocumentPage(text="abcdef", source="guide.pdf", page=1),
        DocumentPage(text="uvwxyz", source="guide.pdf", page=2),
    ]

    chunks = chunk_pages(pages, chunk_size=4, chunk_overlap=1)

    assert [chunk.text for chunk in chunks] == ["abcd", "def", "uvwx", "xyz"]
    assert [chunk.source for chunk in chunks] == ["guide.pdf"] * 4
    assert [chunk.page for chunk in chunks] == [1, 1, 2, 2]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2, 3]


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_split_text_rejects_invalid_settings(
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    with pytest.raises(ValueError):
        split_text("content", chunk_size, chunk_overlap)
