"""Testes da configuração, do CORS e do arranque da aplicação."""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.config import DEFAULT_CORS_ORIGINS, Settings
from backend.app.main import app

REQUIRED = {
    "SUPABASE_URL": "http://fake",
    "SUPABASE_PUBLISHABLE_KEY": "fake",
    "SUPABASE_SECRET_KEY": "fake",
    "SECRET_KEY": "fake",
}


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove do ambiente todas as variáveis lidas por `Settings`."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **(REQUIRED | overrides))


@pytest.mark.usefixtures("clean_env")
def test_default_cors_is_not_wildcard() -> None:
    assert _settings().BACKEND_CORS_ORIGINS == DEFAULT_CORS_ORIGINS


@pytest.mark.usefixtures("clean_env")
def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError, match="BACKEND_CORS_ORIGINS"):
        _settings(BACKEND_CORS_ORIGINS=["*"])


@pytest.mark.usefixtures("clean_env")
def test_default_host_is_local_only() -> None:
    assert _settings().HOST == "127.0.0.1"


@pytest.mark.usefixtures("clean_env")
def test_env_file_with_unknown_keys_is_ignored(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(f"{k}={v}" for k, v in REQUIRED.items()) + "\nHF_TOKEN=abc\nAPP_ENV=development\n"
    )
    assert Settings(_env_file=env_file).SECRET_KEY == "fake"


@pytest.mark.usefixtures("clean_env")
def test_missing_required_setting_fails() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SUPABASE_URL="http://fake")


def test_health_returns_request_id() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.headers["X-Request-ID"]


def test_cors_allows_configured_origin_only() -> None:
    client = TestClient(app)
    ok = client.options(
        "/health",
        headers={"Origin": DEFAULT_CORS_ORIGINS[0], "Access-Control-Request-Method": "GET"},
    )
    blocked = client.options(
        "/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == DEFAULT_CORS_ORIGINS[0]
    assert "access-control-allow-origin" not in blocked.headers


def test_lifespan_logs_startup_and_shutdown(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="backend.app.main"), TestClient(app):
        pass
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "Starting" in messages
    assert "Shutting down" in messages
