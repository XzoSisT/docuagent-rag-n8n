"""Semantic document search endpoint for the n8n HTTP tool."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.schemas.search import SearchRequest, SearchResponse
from app.services.embedding_service import (
    EmbeddingServiceError,
    create_embedding_service,
)
from app.services.rag_service import RetrievalService, extract_requested_pdf
from app.services.vector_store import QdrantVectorStore, VectorStoreError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Build and reuse retrieval dependencies for the API process."""

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
    return RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        default_top_k=settings.top_k,
        min_relevance_score=settings.min_relevance_score,
    )


@router.post("/search", response_model=SearchResponse)
def search_documents(
    request: SearchRequest,
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> SearchResponse:
    """Return relevant chunks; final answer generation remains in n8n."""

    try:
        results = retrieval_service.search(request.query, request.top_k)
    except EmbeddingServiceError as exc:
        logger.exception("Embedding generation failed for search query")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except VectorStoreError as exc:
        logger.exception("Qdrant search failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    requested_source = extract_requested_pdf(request.query)
    if results:
        reason = "context_found"
    elif requested_source:
        reason = "requested_source_not_found_or_irrelevant"
    else:
        reason = "no_relevant_context"

    return SearchResponse(
        query=request.query,
        answerable=bool(results),
        reason=reason,
        requested_source=requested_source,
        results=results,
    )
