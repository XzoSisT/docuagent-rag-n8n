"""Tests for the document upload HTTP endpoint."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.api.documents import get_ingestion_service
from app.main import app
from app.services.embedding_service import EmbeddingServiceError
from app.services.rag_service import IngestionService
from app.services.vector_store import QdrantVectorStore, VectorStoreError
from tests.pdf_factory import build_text_pdf


class DeterministicEmbeddingService:
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(index + 1), 1.0, 0.0] for index, _text in enumerate(texts)]


class FailingIngestionService:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def index_pdf(self, source: object, filename: str) -> None:
        raise self._error


def test_upload_indexes_real_pdf_and_returns_chunk_count() -> None:
    qdrant_client = QdrantClient(location=":memory:")
    service = IngestionService(
        embedding_service=DeterministicEmbeddingService(),  # type: ignore[arg-type]
        vector_store=QdrantVectorStore(
            url="http://unused",
            collection_name="documents",
            client=qdrant_client,
        ),
        chunk_size=100,
        chunk_overlap=10,
    )

    with _client_using(service) as client:
        response = client.post(
            "/documents/upload",
            files={
                "file": (
                    "guide.pdf",
                    build_text_pdf(["First page", "Second page"]),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "guide.pdf",
        "chunks_created": 2,
        "status": "indexed",
    }
    assert qdrant_client.count("documents", exact=True).count == 2

    records, _ = qdrant_client.scroll(
        "documents",
        limit=10,
        with_payload=True,
    )
    payloads = sorted(
        (record.payload or {} for record in records), key=lambda p: p["page"]
    )
    assert [payload["page"] for payload in payloads] == [1, 2]
    assert [payload["source"] for payload in payloads] == ["guide.pdf", "guide.pdf"]


def test_upload_rejects_non_pdf_content_type() -> None:
    service = FailingIngestionService(AssertionError("service must not be called"))

    with _client_using(service) as client:
        response = client.post(
            "/documents/upload",
            files={"file": ("notes.txt", b"plain text", "text/plain")},
        )

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF files are supported"


def test_upload_without_filename_returns_validation_error() -> None:
    service = FailingIngestionService(AssertionError("service must not be called"))

    with _client_using(service) as client:
        response = client.post(
            "/documents/upload",
            files={"file": ("", build_text_pdf(["text"]), "application/pdf")},
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_rejects_invalid_pdf() -> None:
    service = _local_ingestion_service()

    with _client_using(service) as client:
        response = client.post(
            "/documents/upload",
            files={"file": ("broken.pdf", b"not a PDF", "application/pdf")},
        )

    assert response.status_code == 422
    assert "Could not read PDF" in response.json()["detail"]


def test_upload_rejects_pdf_without_text() -> None:
    service = _local_ingestion_service()

    with _client_using(service) as client:
        response = client.post(
            "/documents/upload",
            files={"file": ("empty.pdf", build_text_pdf([""]), "application/pdf")},
        )

    assert response.status_code == 422
    assert "no extractable text" in response.json()["detail"]


@pytest.mark.parametrize(
    ("error", "expected_detail"),
    [
        (EmbeddingServiceError("Ollama embedding request failed"), "Ollama"),
        (VectorStoreError("Could not connect to Qdrant"), "Qdrant"),
    ],
)
def test_upload_maps_service_failures_to_503(
    error: Exception,
    expected_detail: str,
) -> None:
    service = FailingIngestionService(error)

    with _client_using(service) as client:
        response = client.post(
            "/documents/upload",
            files={"file": ("guide.pdf", build_text_pdf(["text"]), "application/pdf")},
        )

    assert response.status_code == 503
    assert expected_detail in response.json()["detail"]


def _local_ingestion_service() -> IngestionService:
    return IngestionService(
        embedding_service=DeterministicEmbeddingService(),  # type: ignore[arg-type]
        vector_store=QdrantVectorStore(
            url="http://unused",
            collection_name="documents",
            client=QdrantClient(location=":memory:"),
        ),
    )


@contextmanager
def _client_using(service: object) -> Iterator[TestClient]:
    app.dependency_overrides[get_ingestion_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
