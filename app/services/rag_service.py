"""Orchestrate document ingestion and semantic retrieval."""

import re
from typing import BinaryIO

from app.schemas.document import DocumentIndexResult
from app.schemas.search import SearchResult
from app.services.document_loader import load_pdf
from app.services.embedding_service import EmbeddingService
from app.services.text_splitter import chunk_pages
from app.services.vector_store import QdrantVectorStore


class IngestionService:
    """Run the explicit PDF-to-Qdrant ingestion pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def index_pdf(
        self,
        source: BinaryIO,
        filename: str,
    ) -> DocumentIndexResult:
        """Extract and index one PDF, preserving source and page metadata."""

        pages = load_pdf(source, filename=filename)
        chunks = chunk_pages(
            pages,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        embeddings = self._embedding_service.embed_texts(
            [chunk.text for chunk in chunks]
        )
        chunks_created = self._vector_store.upsert_chunks(chunks, embeddings)
        return DocumentIndexResult(
            filename=pages[0].source,
            chunks_created=chunks_created,
        )


class RetrievalService:
    """Embed a query and retrieve relevant document context from Qdrant."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
        default_top_k: int = 4,
        min_relevance_score: float = 0.42,
    ) -> None:
        if default_top_k <= 0:
            raise ValueError("default_top_k must be greater than 0")

        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._default_top_k = default_top_k
        self._min_relevance_score = min_relevance_score

    def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Return relevant chunks without asking an LLM to generate an answer."""

        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query must not be blank")

        result_limit = self._default_top_k if top_k is None else top_k
        if result_limit <= 0:
            raise ValueError("top_k must be greater than 0")

        query_vector = self._embedding_service.embed_query(clean_query)
        return self._vector_store.search(
            query_vector,
            result_limit,
            score_threshold=self._min_relevance_score,
            source_filter=extract_requested_pdf(clean_query),
        )


_PDF_FILENAME_PATTERN = re.compile(r"(?i)(?<![\w.-])([\w][\w.-]*\.pdf)\b")


def extract_requested_pdf(query: str) -> str | None:
    """Return an explicitly mentioned PDF filename, if the query contains one."""

    match = _PDF_FILENAME_PATTERN.search(query)
    return match.group(1) if match else None
