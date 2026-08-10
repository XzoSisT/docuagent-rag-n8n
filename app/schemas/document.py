"""Internal document models shared by ingestion services."""

from typing import Literal

from pydantic import BaseModel, Field


class DocumentPage(BaseModel):
    """Text extracted from one PDF page."""

    text: str
    source: str = Field(min_length=1)
    page: int = Field(gt=0)


class DocumentChunk(DocumentPage):
    """A searchable text chunk with its original page metadata."""

    chunk_index: int = Field(ge=0)


class DocumentIndexResult(BaseModel):
    """Result produced after storing all chunks from one document."""

    filename: str = Field(min_length=1)
    chunks_created: int = Field(ge=0)


class DocumentUploadResponse(DocumentIndexResult):
    """Public response returned by the document upload endpoint."""

    status: Literal["indexed"]
