"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="Document retrieval backend for the DocuAgent n8n workflow.",
    version="0.1.0",
)
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(search_router)
