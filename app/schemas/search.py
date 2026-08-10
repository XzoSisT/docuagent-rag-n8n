"""Request and response models for semantic document retrieval."""

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """A semantic query with an optional result-count override."""

    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, gt=0, le=100)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, query: str) -> str:
        """Reject whitespace-only input and keep the returned query clean."""

        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query must not be blank")
        return clean_query


class SearchResult(BaseModel):
    """One relevant document chunk returned by Qdrant."""

    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    page: int = Field(gt=0)
    score: float


class SearchResponse(BaseModel):
    """Ranked document context returned to the n8n search tool."""

    query: str
    results: list[SearchResult]
