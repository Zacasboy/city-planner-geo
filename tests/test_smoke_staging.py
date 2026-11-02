"""Teste do script de verificação de staging contra a aplicação em memória."""

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import requests
from fastapi.testclient import TestClient

from backend.app.main import app

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "smoke_staging.py"
BASE = "http://testserver"


@pytest.fixture
def smoke(monkeypatch: pytest.MonkeyPatch) -> Any:
    spec = importlib.util.spec_from_file_location("smoke_staging", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = TestClient(app)

    def fake(method: str) -> Callable[..., Any]:
        def call(url: str, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            return getattr(client, method)(url.removeprefix(BASE), **kwargs)

        return call

    monkeypatch.setattr(requests, "get", fake("get"))
    monkeypatch.setattr(requests, "post", fake("post"))
    return module


def test_smoke_passes_with_a_valid_token(smoke: Any, make_token: Callable[..., str]) -> None:
    assert smoke.run(BASE, make_token("smoke")) is True


def test_smoke_without_token_only_checks_protection(smoke: Any, capsys: Any) -> None:
    assert smoke.run(BASE, None) is True
    assert "viga" not in capsys.readouterr().out


def test_smoke_fails_with_an_invalid_token(smoke: Any) -> None:
    assert smoke.run(BASE, "not-a-token") is False
