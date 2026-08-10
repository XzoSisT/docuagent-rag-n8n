"""Tests for the OpenAI embedding adapter without network calls."""

from types import SimpleNamespace

import pytest
from openai import OpenAIError

from app.core.config import Settings
from app.services.embedding_service import (
    EmbeddingServiceError,
    MissingOpenAIAPIKeyError,
    OllamaEmbeddingService,
    OpenAIEmbeddingService,
    create_embedding_service,
)


class FakeEmbeddingsResource:
    def __init__(self) -> None:
        self.last_request: dict[str, object] = {}

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.last_request = kwargs
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.0, 1.0, 0.0]),
                SimpleNamespace(index=0, embedding=[1.0, 0.0, 0.0]),
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddingsResource()


def test_embed_texts_uses_configured_model_and_preserves_order() -> None:
    client = FakeOpenAIClient()
    service = OpenAIEmbeddingService(
        api_key="",
        model="text-embedding-3-small",
        client=client,
    )

    embeddings = service.embed_texts(["first", "second"])

    assert embeddings == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert client.embeddings.last_request == {
        "model": "text-embedding-3-small",
        "input": ["first", "second"],
        "encoding_format": "float",
    }


def test_embed_query_returns_one_vector() -> None:
    item = SimpleNamespace(index=0, embedding=[0.1, 0.2])
    client = SimpleNamespace(
        embeddings=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(data=[item]))
    )
    service = OpenAIEmbeddingService(api_key="", client=client)

    assert service.embed_query("assignment requirements") == [0.1, 0.2]


def test_embedding_service_requires_key_for_real_client() -> None:
    with pytest.raises(MissingOpenAIAPIKeyError, match="OPENAI_API_KEY"):
        OpenAIEmbeddingService(api_key="")


def test_embedding_service_rejects_blank_input() -> None:
    service = OpenAIEmbeddingService(api_key="", client=FakeOpenAIClient())

    with pytest.raises(ValueError, match="blank text"):
        service.embed_texts(["valid", "  "])


def test_embedding_service_wraps_openai_errors() -> None:
    def fail(**kwargs: object) -> None:
        raise OpenAIError("temporary failure")

    client = SimpleNamespace(embeddings=SimpleNamespace(create=fail))
    service = OpenAIEmbeddingService(api_key="", client=client)

    with pytest.raises(EmbeddingServiceError, match="request failed"):
        service.embed_texts(["content"])


def test_ollama_service_uses_local_model_with_compatible_request() -> None:
    client = FakeOpenAIClient()
    service = OllamaEmbeddingService(
        model="embeddinggemma",
        client=client,
    )

    service.embed_texts(["ภาษาไทย", "English"])

    assert service.provider_name == "Ollama"
    assert client.embeddings.last_request["model"] == "embeddinggemma"
    assert client.embeddings.last_request["input"] == ["ภาษาไทย", "English"]


def test_factory_uses_ollama_by_default() -> None:
    settings = Settings(_env_file=None)

    service = create_embedding_service(settings)

    assert isinstance(service, OllamaEmbeddingService)
    assert service.model == "embeddinggemma"


def test_factory_can_switch_to_openai() -> None:
    settings = Settings(
        _env_file=None,
        embedding_provider="openai",
        openai_api_key="test-key",
    )

    service = create_embedding_service(settings)

    assert isinstance(service, OpenAIEmbeddingService)
    assert service.model == "text-embedding-3-small"
