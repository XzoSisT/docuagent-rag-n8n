"""Tests for local PDF path discovery used by the batch ingestion script."""

from pathlib import Path

import pytest

from scripts.ingest_documents import resolve_pdf_paths


def test_resolve_pdf_paths_discovers_sorted_default_documents(tmp_path: Path) -> None:
    second = tmp_path / "second.pdf"
    first = tmp_path / "first.pdf"
    second.write_bytes(b"pdf")
    first.write_bytes(b"pdf")

    paths = resolve_pdf_paths([], default_directory=tmp_path)

    assert paths == [first, second]


def test_resolve_pdf_paths_rejects_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pdf"

    with pytest.raises(ValueError, match="PDF file not found"):
        resolve_pdf_paths([str(missing)])


def test_resolve_pdf_paths_rejects_non_pdf(tmp_path: Path) -> None:
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a PDF", encoding="utf-8")

    with pytest.raises(ValueError, match="Only PDF files"):
        resolve_pdf_paths([str(text_file)])
