"""Tests for basic API availability and public route registration."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_contains_version_one_endpoints() -> None:
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert {"/health", "/documents/upload", "/search"} <= set(paths)
