"""Tests for page-by-page PDF text extraction."""

from io import BytesIO
from pathlib import Path

import pytest

from app.services.document_loader import (
    EmptyPDFError,
    UnsupportedFileTypeError,
    load_pdf,
)
from tests.pdf_factory import build_text_pdf


def test_load_pdf_extracts_each_page_with_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "guide.pdf"
    _write_text_pdf(pdf_path, ["First page", "Second page"])

    pages = load_pdf(pdf_path)

    assert [page.text for page in pages] == ["First page", "Second page"]
    assert [page.source for page in pages] == ["guide.pdf", "guide.pdf"]
    assert [page.page for page in pages] == [1, 2]


def test_load_pdf_accepts_binary_stream(tmp_path: Path) -> None:
    pdf_path = tmp_path / "stream-source.pdf"
    _write_text_pdf(pdf_path, ["Stream content"])

    pages = load_pdf(BytesIO(pdf_path.read_bytes()), filename="uploaded.pdf")

    assert pages[0].text == "Stream content"
    assert pages[0].source == "uploaded.pdf"


def test_load_pdf_rejects_document_without_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    _write_text_pdf(pdf_path, [""])

    with pytest.raises(EmptyPDFError, match="no extractable text"):
        load_pdf(pdf_path)


def test_load_pdf_rejects_non_pdf_extension(tmp_path: Path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("not a PDF", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError, match="Only PDF"):
        load_pdf(text_path)


def _write_text_pdf(path: Path, page_texts: list[str]) -> None:
    """Create a tiny valid PDF fixture without adding a PDF generator dependency."""
    path.write_bytes(build_text_pdf(page_texts))
