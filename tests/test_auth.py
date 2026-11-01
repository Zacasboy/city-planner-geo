"""Testes da validação de JWT e da rota protegida."""

import time
from typing import Any

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.auth import verify_supabase_jwt
from backend.app.config import settings
from backend.app.main import app

pytestmark = pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")

ONE_HOUR_S = 3600


def _token(claims: dict[str, Any], key: str | None = None) -> str:
    return jwt.encode(claims, key or settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _valid_claims() -> dict[str, Any]:
    return {"sub": "user-1", "email": "ana@exemplo.pt", "exp": time.time() + ONE_HOUR_S}


def test_valid_token_returns_claims() -> None:
    payload = verify_supabase_jwt(_token(_valid_claims()))
    assert payload["sub"] == "user-1"


def test_expired_token_is_401() -> None:
    claims = _valid_claims() | {"exp": time.time() - ONE_HOUR_S}
    with pytest.raises(HTTPException) as info:
        verify_supabase_jwt(_token(claims))
    assert info.value.status_code == 401
    assert info.value.detail == "Token has expired"


def test_wrong_signature_is_401_not_500() -> None:
    forged = _token(_valid_claims(), key="outra-chave-qualquer-com-32-bytes-ou-mais")
    with pytest.raises(HTTPException) as info:
        verify_supabase_jwt(forged)
    assert info.value.status_code == 401
    assert info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_malformed_token_is_401() -> None:
    with pytest.raises(HTTPException) as info:
        verify_supabase_jwt("isto-nao-e-um-jwt")
    assert info.value.status_code == 401


def test_token_without_subject_is_401() -> None:
    claims = {"exp": time.time() + ONE_HOUR_S}
    with pytest.raises(HTTPException) as info:
        verify_supabase_jwt(_token(claims))
    assert info.value.status_code == 401
    assert "subject" in str(info.value.detail)


def test_protected_route_accepts_valid_token() -> None:
    client = TestClient(app)
    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {_token(_valid_claims())}"}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"


def test_protected_route_rejects_forged_token() -> None:
    client = TestClient(app)
    forged = _token(_valid_claims(), key="outra-chave-qualquer-com-32-bytes-ou-mais")
    response = client.get("/protected", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == 401


def test_protected_route_without_credentials_is_rejected() -> None:
    client = TestClient(app)
    assert client.get("/protected").status_code in (401, 403)
