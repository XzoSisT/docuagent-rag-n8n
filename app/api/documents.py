"""PDF upload and indexing endpoint."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.document import DocumentUploadResponse
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@lru_cache
def get_ingestion_service() -> IngestionService:
    """Build and reuse the ingestion dependencies for the API process."""

    settings = get_settings()
    try:
        embedding_service = create_embedding_service(settings)
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection,
    )
    return IngestionService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    file: Annotated[UploadFile, File(description="PDF document to index")],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> DocumentUploadResponse:
    """Extract, chunk, embed, and index one uploaded PDF."""

    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    try:
        result = ingestion_service.index_pdf(file.file, filename=file.filename or "")
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except (EmptyPDFError, InvalidPDFError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except EmbeddingServiceError as exc:
        logger.exception("Embedding generation failed for %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except VectorStoreError as exc:
        logger.exception("Qdrant indexing failed for %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return DocumentUploadResponse(
        filename=result.filename,
        chunks_created=result.chunks_created,
        status="indexed",
    )
