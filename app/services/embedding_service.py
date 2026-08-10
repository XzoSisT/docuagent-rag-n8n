"""Generate vector embeddings with the OpenAI Python SDK."""

from collections.abc import Sequence
from typing import Any

from openai import OpenAI, OpenAIError

from app.core.config import Settings


class EmbeddingServiceError(RuntimeError):
    """Raised when embedding generation fails."""


class MissingOpenAIAPIKeyError(EmbeddingServiceError):
    """Raised when no API key is available for a real OpenAI client."""


class EmbeddingService:
    """Shared embedding behavior for OpenAI-compatible clients."""

    def __init__(
        self,
        model: str,
        client: Any,
        provider_name: str,
    ) -> None:
        if not model.strip():
            raise ValueError("Embedding model must not be empty")

        self.model = model
        self.provider_name = provider_name
        self._client = client

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple texts in one API request."""

        inputs = list(texts)
        if not inputs:
            return []
        if any(not text.strip() for text in inputs):
            raise ValueError("Embedding input must not contain blank text")

        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=inputs,
                encoding_format="float",
            )
        except OpenAIError as exc:
            raise EmbeddingServiceError(
                f"{self.provider_name} embedding request failed"
            ) from exc

        ordered_items = sorted(response.data, key=lambda item: item.index)
        embeddings = [list(item.embedding) for item in ordered_items]
        _validate_embedding_response(
            embeddings,
            expected_count=len(inputs),
            provider_name=self.provider_name,
        )
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        """Embed one search query using the configured model."""

        return self.embed_texts([query])[0]


class OpenAIEmbeddingService(EmbeddingService):
    """Generate embeddings through the hosted OpenAI API."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        client: Any | None = None,
    ) -> None:
        if client is None and not api_key.strip():
            raise MissingOpenAIAPIKeyError("OPENAI_API_KEY is not configured")

        super().__init__(
            model=model,
            client=client or OpenAI(api_key=api_key),
            provider_name="OpenAI",
        )


class OllamaEmbeddingService(EmbeddingService):
    """Generate free local embeddings through Ollama's compatible API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "embeddinggemma",
        client: Any | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("OLLAMA_BASE_URL must not be empty")

        openai_compatible_url = f"{base_url.rstrip('/')}/v1"
        super().__init__(
            model=model,
            client=client
            or OpenAI(
                base_url=openai_compatible_url,
                api_key="ollama",
            ),
            provider_name="Ollama",
        )


def create_embedding_service(settings: Settings) -> EmbeddingService:
    """Create the embedding provider selected through environment settings."""

    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingService(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
        )
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingService(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )

    # Settings validates this value, but this guard keeps the factory safe in isolation.
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")


def _validate_embedding_response(
    embeddings: Sequence[Sequence[float]],
    expected_count: int,
    provider_name: str,
) -> None:
    if len(embeddings) != expected_count:
        raise EmbeddingServiceError(
            f"{provider_name} returned a different number of embeddings than requested"
        )
    if not embeddings or not embeddings[0]:
        raise EmbeddingServiceError(f"{provider_name} returned an empty embedding")

    vector_size = len(embeddings[0])
    if any(len(embedding) != vector_size for embedding in embeddings):
        raise EmbeddingServiceError(
            f"{provider_name} returned inconsistent embedding dimensions"
        )
