"""Tests for semantic retrieval and the POST /search endpoint."""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.api.search import get_retrieval_service
from app.main import app
from app.schemas.document import DocumentChunk
from app.services.embedding_service import EmbeddingServiceError
from app.services.rag_service import RetrievalService
from app.services.vector_store import QdrantVectorStore, VectorStoreError


class KeywordEmbeddingService:
    """Return predictable vectors without calling an external provider."""

    def embed_query(self, query: str) -> list[float]:
        return [1.0, 0.0] if "deadline" in query.lower() else [0.0, 1.0]


class FailingRetrievalService:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def search(self, query: str, top_k: int | None = None) -> None:
        raise self._error


def test_search_returns_ranked_context_with_source_and_page() -> None:
    service = _indexed_retrieval_service(default_top_k=1)

    with _client_using(service) as client:
        response = client.post("/search", json={"query": "  submission deadline  "})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "submission deadline"
    assert body["answerable"] is True
    assert body["reason"] == "context_found"
    assert body["requested_source"] is None
    assert len(body["results"]) == 1
    assert body["results"][0]["text"] == "The submission deadline is Friday."
    assert body["results"][0]["source"] == "student-guide.pdf"
    assert body["results"][0]["page"] == 4
    assert body["results"][0]["score"] == pytest.approx(1.0)


def test_search_top_k_overrides_service_default() -> None:
    service = _indexed_retrieval_service(
        default_top_k=1,
        min_relevance_score=-1.0,
    )

    with _client_using(service) as client:
        response = client.post(
            "/search",
            json={"query": "submission deadline", "top_k": 2},
        )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 2


def test_search_returns_empty_results_before_any_document_is_indexed() -> None:
    service = RetrievalService(
        embedding_service=KeywordEmbeddingService(),  # type: ignore[arg-type]
        vector_store=QdrantVectorStore(
            url="http://unused",
            collection_name="documents",
            client=QdrantClient(location=":memory:"),
        ),
    )

    with _client_using(service) as client:
        response = client.post("/search", json={"query": "submission deadline"})

    assert response.status_code == 200
    assert response.json() == {
        "query": "submission deadline",
        "answerable": False,
        "reason": "no_relevant_context",
        "requested_source": None,
        "results": [],
    }


def test_search_rejects_an_explicit_filename_not_in_the_index() -> None:
    service = _indexed_retrieval_service(default_top_k=2)

    with _client_using(service) as client:
        response = client.post(
            "/search",
            json={"query": "What does employee-handbook.pdf say about deadlines?"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "query": "What does employee-handbook.pdf say about deadlines?",
        "answerable": False,
        "reason": "requested_source_not_found_or_irrelevant",
        "requested_source": "employee-handbook.pdf",
        "results": [],
    }


def test_search_filters_results_below_the_relevance_threshold() -> None:
    vector_store = QdrantVectorStore(
        url="http://unused",
        collection_name="documents",
        client=QdrantClient(location=":memory:"),
    )
    vector_store.upsert_chunks(
        [
            DocumentChunk(
                text="Only weakly related content.",
                source="guide.pdf",
                page=1,
                chunk_index=0,
            )
        ],
        [[0.8, 0.6]],
    )
    service = RetrievalService(
        embedding_service=KeywordEmbeddingService(),  # type: ignore[arg-type]
        vector_store=vector_store,
        min_relevance_score=0.9,
    )

    with _client_using(service) as client:
        response = client.post("/search", json={"query": "submission deadline"})

    assert response.status_code == 200
    assert response.json()["answerable"] is False
    assert response.json()["results"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "   "},
        {"query": "valid", "top_k": 0},
        {"query": "valid", "top_k": 101},
    ],
)
def test_search_rejects_invalid_requests(payload: dict[str, object]) -> None:
    service = FailingRetrievalService(AssertionError("service must not be called"))

    with _client_using(service) as client:
        response = client.post("/search", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error", "expected_detail"),
    [
        (EmbeddingServiceError("Ollama embedding request failed"), "Ollama"),
        (VectorStoreError("Could not search vectors in Qdrant"), "Qdrant"),
    ],
)
def test_search_maps_service_failures_to_503(
    error: Exception,
    expected_detail: str,
) -> None:
    service = FailingRetrievalService(error)

    with _client_using(service) as client:
        response = client.post("/search", json={"query": "valid query"})

    assert response.status_code == 503
    assert expected_detail in response.json()["detail"]


def test_vector_store_rejects_empty_query_vector() -> None:
    store = QdrantVectorStore(
        url="http://unused",
        collection_name="documents",
        client=QdrantClient(location=":memory:"),
    )

    with pytest.raises(ValueError, match="must not be empty"):
        store.search([], top_k=4)


def _indexed_retrieval_service(
    default_top_k: int,
    min_relevance_score: float = 0.42,
) -> RetrievalService:
    vector_store = QdrantVectorStore(
        url="http://unused",
        collection_name="documents",
        client=QdrantClient(location=":memory:"),
    )
    chunks = [
        DocumentChunk(
            text="The submission deadline is Friday.",
            source="student-guide.pdf",
            page=4,
            chunk_index=0,
        ),
        DocumentChunk(
            text="The course introduces data engineering.",
            source="student-guide.pdf",
            page=1,
            chunk_index=1,
        ),
    ]
    vector_store.upsert_chunks(chunks, [[1.0, 0.0], [0.0, 1.0]])
    return RetrievalService(
        embedding_service=KeywordEmbeddingService(),  # type: ignore[arg-type]
        vector_store=vector_store,
        default_top_k=default_top_k,
        min_relevance_score=min_relevance_score,
    )


@contextmanager
def _client_using(service: object) -> Iterator[TestClient]:
    app.dependency_overrides[get_retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
