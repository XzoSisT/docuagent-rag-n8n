"""Extract text and page metadata from PDF documents."""

from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.schemas.document import DocumentPage


class UnsupportedFileTypeError(ValueError):
    """Raised when a document is not a PDF."""


class EmptyPDFError(ValueError):
    """Raised when a PDF contains no extractable text."""


class InvalidPDFError(ValueError):
    """Raised when pypdf cannot read a PDF document."""


def load_pdf(
    source: str | Path | BinaryIO,
    filename: str | None = None,
) -> list[DocumentPage]:
    """Extract text page-by-page from a PDF path or binary stream."""

    if isinstance(source, (str, Path)):
        path = Path(source)
        source_name = _validate_pdf_filename(filename or path.name)
        if not path.is_file():
            raise FileNotFoundError(f"PDF file not found: {path}")

        with path.open("rb") as pdf_file:
            return _read_pages(pdf_file, source_name)

    source_name = _validate_pdf_filename(filename or _stream_name(source))
    try:
        source.seek(0)
    except (AttributeError, OSError) as exc:
        raise InvalidPDFError("PDF stream must be seekable") from exc

    return _read_pages(source, source_name)


def _read_pages(pdf_file: BinaryIO, source_name: str) -> list[DocumentPage]:
    try:
        reader = PdfReader(pdf_file)
        pages = [
            DocumentPage(
                text=(pdf_page.extract_text() or "").strip(),
                source=source_name,
                page=page_number,
            )
            for page_number, pdf_page in enumerate(reader.pages, start=1)
        ]
    except (PdfReadError, OSError) as exc:
        raise InvalidPDFError(f"Could not read PDF: {source_name}") from exc

    if not any(page.text for page in pages):
        raise EmptyPDFError(f"PDF contains no extractable text: {source_name}")

    return pages


def _validate_pdf_filename(filename: str) -> str:
    # Normalize both separator styles because upload names may come from any OS.
    source_name = Path(str(filename).replace("\\", "/")).name
    if not source_name:
        raise ValueError("A PDF filename is required")
    if Path(source_name).suffix.lower() != ".pdf":
        raise UnsupportedFileTypeError("Only PDF files are supported")
    return source_name


def _stream_name(source: BinaryIO) -> str:
    stream_name = getattr(source, "name", "")
    return Path(str(stream_name)).name if stream_name else ""
