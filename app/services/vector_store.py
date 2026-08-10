"""Store document chunk vectors and metadata in Qdrant."""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException

from app.schemas.document import DocumentChunk
from app.schemas.search import SearchResult


class VectorStoreError(RuntimeError):
    """Raised when a Qdrant operation fails."""


class VectorDimensionError(VectorStoreError):
    """Raised when embedding and collection dimensions do not match."""


class QdrantVectorStore:
    """Explicit Qdrant operations needed for indexing and retrieval."""

    def __init__(
        self,
        url: str,
        collection_name: str,
        api_key: str = "",
        client: QdrantClient | None = None,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("Qdrant collection name must not be empty")

        self.collection_name = collection_name
        self._client = client or QdrantClient(
            url=url,
            api_key=api_key or None,
        )

    def ensure_collection(self, vector_size: int) -> None:
        """Create a cosine collection or validate the existing collection."""

        if vector_size <= 0:
            raise ValueError("Vector size must be greater than 0")

        try:
            exists = self._client.collection_exists(self.collection_name)
            if not exists:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                return

            collection = self._client.get_collection(self.collection_name)
        except (ApiException, ResponseHandlingException, OSError) as exc:
            raise VectorStoreError("Could not connect to Qdrant") from exc

        vectors_config = collection.config.params.vectors
        if not isinstance(vectors_config, models.VectorParams):
            raise VectorStoreError(
                "Named Qdrant vectors are not supported in Version 1"
            )
        if vectors_config.size != vector_size:
            raise VectorDimensionError(
                "Qdrant collection vector size does not match the embedding model: "
                f"collection={vectors_config.size}, embedding={vector_size}"
            )
        if vectors_config.distance != models.Distance.COSINE:
            raise VectorStoreError("Qdrant collection must use cosine distance")

    def upsert_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        """Store chunks and vectors, returning the number of indexed chunks."""

        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings must have the same length")
        if not chunks:
            return 0

        vector_size = _validate_vectors(embeddings)
        self.ensure_collection(vector_size)
        points = [
            models.PointStruct(
                id=_point_id(chunk),
                vector=list(embedding),
                payload={
                    "text": chunk.text,
                    "source": chunk.source,
                    "page": chunk.page,
                    "chunk_index": chunk.chunk_index,
                },
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]

        try:
            self._client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
        except (ApiException, ResponseHandlingException, OSError) as exc:
            raise VectorStoreError("Could not store vectors in Qdrant") from exc

        return len(points)

    def search(
        self,
        query_vector: Sequence[float],
        top_k: int,
    ) -> list[SearchResult]:
        """Return the nearest document chunks ordered by cosine similarity."""

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0")

        vector = list(query_vector)
        if not vector:
            raise ValueError("Query vector must not be empty")

        try:
            # A missing collection means no documents have been indexed yet.
            if not self._client.collection_exists(self.collection_name):
                return []

            response = self._client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
        except (ApiException, ResponseHandlingException, OSError, ValueError) as exc:
            raise VectorStoreError("Could not search vectors in Qdrant") from exc

        results: list[SearchResult] = []
        for point in response.points:
            payload = point.payload or {}
            try:
                results.append(
                    SearchResult(
                        text=payload["text"],
                        source=payload["source"],
                        page=payload["page"],
                        score=point.score,
                    )
                )
            except (KeyError, TypeError, ValidationError) as exc:
                raise VectorStoreError(
                    "Qdrant search result contains invalid document metadata"
                ) from exc

        return results


def _validate_vectors(embeddings: Sequence[Sequence[float]]) -> int:
    vector_size = len(embeddings[0])
    if vector_size == 0:
        raise VectorDimensionError("Embedding vectors must not be empty")
    if any(len(embedding) != vector_size for embedding in embeddings):
        raise VectorDimensionError("All embedding vectors must have the same size")
    return vector_size


def _point_id(chunk: DocumentChunk) -> str:
    identity = "\x1f".join(
        [
            chunk.source,
            str(chunk.page),
            str(chunk.chunk_index),
            chunk.text,
        ]
    )
    return str(uuid5(NAMESPACE_URL, identity))
