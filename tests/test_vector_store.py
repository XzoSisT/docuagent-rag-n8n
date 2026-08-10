"""Tests for Qdrant collection creation and document indexing."""

from types import SimpleNamespace

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.schemas.document import DocumentChunk
from app.services.embedding_service import OpenAIEmbeddingService
from app.services.vector_store import (
    QdrantVectorStore,
    VectorDimensionError,
)


def test_upsert_chunks_creates_cosine_collection_and_indexes_metadata() -> None:
    client = QdrantClient(location=":memory:")
    store = QdrantVectorStore(
        url="http://unused",
        collection_name="documents",
        client=client,
    )
    chunks = [
        DocumentChunk(
            text="Assignment requirements",
            source="guide.pdf",
            page=1,
            chunk_index=0,
        ),
        DocumentChunk(
            text="Submission deadline",
            source="guide.pdf",
            page=2,
            chunk_index=1,
        ),
    ]
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    indexed_count = store.upsert_chunks(chunks, embeddings)

    collection = client.get_collection("documents")
    vectors_config = collection.config.params.vectors
    assert isinstance(vectors_config, models.VectorParams)
    assert vectors_config.size == 3
    assert vectors_config.distance == models.Distance.COSINE
    assert indexed_count == 2
    assert client.count("documents", exact=True).count == 2

    records, _ = client.scroll(
        collection_name="documents",
        limit=10,
        with_payload=True,
        with_vectors=True,
    )
    payloads = sorted(
        (record.payload or {} for record in records), key=lambda p: p["page"]
    )
    assert payloads == [
        {
            "text": "Assignment requirements",
            "source": "guide.pdf",
            "page": 1,
            "chunk_index": 0,
        },
        {
            "text": "Submission deadline",
            "source": "guide.pdf",
            "page": 2,
            "chunk_index": 1,
        },
    ]


def test_upsert_is_idempotent_for_the_same_chunks() -> None:
    client = QdrantClient(location=":memory:")
    store = QdrantVectorStore("http://unused", "documents", client=client)
    chunk = DocumentChunk(
        text="Stable content",
        source="guide.pdf",
        page=1,
        chunk_index=0,
    )

    store.upsert_chunks([chunk], [[1.0, 0.0]])
    store.upsert_chunks([chunk], [[1.0, 0.0]])

    assert client.count("documents", exact=True).count == 1


def test_embedding_output_can_be_indexed_in_qdrant() -> None:
    embedding_items = [
        SimpleNamespace(index=0, embedding=[1.0, 0.0]),
        SimpleNamespace(index=1, embedding=[0.0, 1.0]),
    ]
    openai_client = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(data=embedding_items)
        )
    )
    embedding_service = OpenAIEmbeddingService(api_key="", client=openai_client)
    qdrant_client = QdrantClient(location=":memory:")
    vector_store = QdrantVectorStore(
        "http://unused",
        "documents",
        client=qdrant_client,
    )
    chunks = [
        DocumentChunk(text="alpha", source="guide.pdf", page=1, chunk_index=0),
        DocumentChunk(text="beta", source="guide.pdf", page=1, chunk_index=1),
    ]

    embeddings = embedding_service.embed_texts([chunk.text for chunk in chunks])
    indexed_count = vector_store.upsert_chunks(chunks, embeddings)

    assert indexed_count == 2
    assert qdrant_client.count("documents", exact=True).count == 2


def test_existing_collection_must_match_embedding_dimension() -> None:
    client = QdrantClient(location=":memory:")
    client.create_collection(
        collection_name="documents",
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    store = QdrantVectorStore("http://unused", "documents", client=client)

    with pytest.raises(VectorDimensionError, match="collection=2, embedding=3"):
        store.ensure_collection(vector_size=3)


def test_upsert_rejects_mismatched_chunk_and_embedding_counts() -> None:
    client = QdrantClient(location=":memory:")
    store = QdrantVectorStore("http://unused", "documents", client=client)
    chunk = DocumentChunk(text="content", source="guide.pdf", page=1, chunk_index=0)

    with pytest.raises(ValueError, match="same length"):
        store.upsert_chunks([chunk], [])
