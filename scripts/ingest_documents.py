"""Index one or more local PDF files with the configured services."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from app.core.config import get_settings
from app.services.document_loader import (
    EmptyPDFError,
    InvalidPDFError,
    UnsupportedFileTypeError,
)
from app.services.embedding_service import (
    EmbeddingServiceError,
    create_embedding_service,
)
from app.services.rag_service import IngestionService
from app.services.vector_store import QdrantVectorStore, VectorStoreError


def resolve_pdf_paths(
    values: Sequence[str],
    default_directory: Path = Path("data/documents"),
) -> list[Path]:
    """Resolve explicit files or every PDF in the default document directory."""

    paths = [Path(value) for value in values]
    if not paths:
        paths = sorted(default_directory.glob("*.pdf"))
    if not paths:
        raise ValueError("No PDF files were found to index")

    for path in paths:
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Only PDF files are supported: {path}")
        if not path.is_file():
            raise ValueError(f"PDF file not found: {path}")
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    """Run batch ingestion and return a process exit code."""

    parser = argparse.ArgumentParser(
        description="Index PDFs into the configured DocuAgent Qdrant collection."
    )
    parser.add_argument(
        "pdfs",
        nargs="*",
        help="PDF paths; defaults to every PDF in data/documents",
    )
    arguments = parser.parse_args(argv)

    try:
        pdf_paths = resolve_pdf_paths(arguments.pdfs)
        settings = get_settings()
        embedding_service = create_embedding_service(settings)
        vector_store = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection,
        )
        ingestion_service = IngestionService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        for pdf_path in pdf_paths:
            with pdf_path.open("rb") as pdf_file:
                result = ingestion_service.index_pdf(pdf_file, filename=pdf_path.name)
            print(f"Indexed {result.filename}: {result.chunks_created} chunks")
    except (
        OSError,
        ValueError,
        EmptyPDFError,
        InvalidPDFError,
        UnsupportedFileTypeError,
        EmbeddingServiceError,
        VectorStoreError,
    ) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
