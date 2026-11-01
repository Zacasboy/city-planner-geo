"""Testes da validação de JWT do Supabase (segredo partilhado e JWKS)."""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable, Iterator
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app import auth
from backend.app.auth import verify_supabase_jwt
from backend.app.config import settings
from backend.app.main import app

ONE_HOUR_S = 3600
KEY_ID = "key-1"
MakeToken = Callable[..., str]


def _status_of(token: str) -> int:
    with pytest.raises(HTTPException) as info:
        verify_supabase_jwt(token)
    return info.value.status_code


# ---------- segredo partilhado (HS256) ----------


def test_valid_token_returns_claims(make_token: MakeToken) -> None:
    assert verify_supabase_jwt(make_token("user-1"))["sub"] == "user-1"


def test_expired_token_is_401(make_token: MakeToken) -> None:
    with pytest.raises(HTTPException) as info:
        verify_supabase_jwt(make_token(exp=time.time() - ONE_HOUR_S))
    assert info.value.status_code == 401
    assert info.value.detail == "Token has expired"


def test_wrong_signature_is_401_with_bearer_header(make_token: MakeToken) -> None:
    forged = make_token(secret="outra-chave-qualquer-com-32-bytes-ou-mais")
    with pytest.raises(HTTPException) as info:
        verify_supabase_jwt(forged)
    assert info.value.status_code == 401
    assert info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_malformed_token_is_401() -> None:
    assert _status_of("isto-nao-e-um-jwt") == 401


@pytest.mark.parametrize("missing", ["sub", "exp", "aud", "iss"])
def test_token_without_required_claim_is_401(make_token: MakeToken, missing: str) -> None:
    assert _status_of(make_token(**{missing: None})) == 401


def test_wrong_audience_is_401(make_token: MakeToken) -> None:
    assert _status_of(make_token(aud="anon")) == 401


def test_wrong_issuer_is_401(make_token: MakeToken) -> None:
    assert _status_of(make_token(iss="https://outro-projeto.supabase.co/auth/v1")) == 401


def test_secret_not_configured_rejects_hs256(
    make_token: MakeToken, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = make_token()
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    assert _status_of(token) == 401


def test_unsigned_token_is_rejected(make_token: MakeToken) -> None:
    def part(data: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    claims = jwt.decode(make_token(), options={"verify_signature": False})
    assert _status_of(f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(claims)}.") == 401


def test_custom_issuer_setting(make_token: MakeToken, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SUPABASE_JWT_ISSUER", "https://auth.exemplo.pt/auth/v1")
    assert verify_supabase_jwt(make_token(iss="https://auth.exemplo.pt/auth/v1"))["sub"]


# ---------- JWKS (ES256) ----------


class _FakeJwksClient(jwt.PyJWKClient):
    """PyJWKClient real (procura por `kid`), mas sem rede."""

    def __init__(self, keys: list[dict[str, Any]], error: Exception | None = None) -> None:
        super().__init__("http://fake/jwks")
        self._keys = keys
        self._error = error

    def fetch_data(self) -> Any:
        if self._error:
            raise self._error
        return {"keys": self._keys}


def _jwk(private_key: ec.EllipticCurvePrivateKey, kid: str = KEY_ID) -> dict[str, Any]:
    jwk: dict[str, Any] = jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    return jwk | {"kid": kid, "alg": "ES256", "use": "sig"}


def _es256_token(
    private_key: ec.EllipticCurvePrivateKey, kid: str = KEY_ID, **overrides: Any
) -> str:
    claims: dict[str, Any] = {
        "sub": "user-1",
        "aud": settings.SUPABASE_JWT_AUDIENCE,
        "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
        "exp": time.time() + ONE_HOUR_S,
    } | overrides
    claims = {key: value for key, value in claims.items() if value is not None}
    return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": kid})


@pytest.fixture
def signing_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def jwks(
    signing_key: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    client = _FakeJwksClient([_jwk(signing_key)])
    monkeypatch.setattr(auth, "_jwks_client", lambda: client)
    yield


@pytest.mark.usefixtures("jwks")
def test_es256_token_is_accepted(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assert verify_supabase_jwt(_es256_token(signing_key))["sub"] == "user-1"


@pytest.mark.usefixtures("jwks")
def test_es256_without_jwt_secret_configured(
    signing_key: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    assert verify_supabase_jwt(_es256_token(signing_key))["sub"] == "user-1"


@pytest.mark.usefixtures("jwks")
def test_es256_signed_by_another_key_is_401() -> None:
    attacker = ec.generate_private_key(ec.SECP256R1())
    assert _status_of(_es256_token(attacker)) == 401


@pytest.mark.usefixtures("jwks")
def test_es256_unknown_kid_is_401(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assert _status_of(_es256_token(signing_key, kid="desconhecida")) == 401


@pytest.mark.usefixtures("jwks")
@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "anon"},
        {"iss": "https://outro.supabase.co/auth/v1"},
        {"exp": time.time() - ONE_HOUR_S},
        {"sub": None},
    ],
)
def test_es256_claims_are_checked(
    signing_key: ec.EllipticCurvePrivateKey, overrides: dict[str, Any]
) -> None:
    assert _status_of(_es256_token(signing_key, **overrides)) == 401


def _hs256_token_by_hand(secret: bytes, claims: dict[str, Any], kid: str) -> str:
    """Assina com HMAC à mão: o PyJWT recusa chaves públicas como segredo, um atacante não."""

    def part(data: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    signing_input = f"{part({'alg': 'HS256', 'typ': 'JWT', 'kid': kid})}.{part(claims)}"
    signature = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


@pytest.mark.usefixtures("jwks")
def test_hs256_token_signed_with_the_public_key_is_rejected(
    signing_key: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Confusão de algoritmo: o atacante usa a chave pública como segredo HS256."""
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    public_pem = signing_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    claims = {
        "sub": "admin",
        "aud": settings.SUPABASE_JWT_AUDIENCE,
        "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
        "exp": time.time() + ONE_HOUR_S,
    }
    assert _status_of(_hs256_token_by_hand(public_pem, claims, KEY_ID)) == 401


@pytest.mark.usefixtures("jwks")
def test_hs256_token_signed_with_the_public_key_is_rejected_even_with_secret_set(
    signing_key: ec.EllipticCurvePrivateKey,
) -> None:
    public_pem = signing_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    claims = {
        "sub": "admin",
        "aud": settings.SUPABASE_JWT_AUDIENCE,
        "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
        "exp": time.time() + ONE_HOUR_S,
    }
    assert _status_of(_hs256_token_by_hand(public_pem, claims, KEY_ID)) == 401


def test_jwks_unreachable_is_503(
    signing_key: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _FakeJwksClient([], error=jwt.PyJWKClientConnectionError("sem rede"))
    monkeypatch.setattr(auth, "_jwks_client", lambda: client)
    assert _status_of(_es256_token(signing_key)) == 503


def test_jwks_url_comes_from_supabase_url() -> None:
    auth._jwks_client.cache_clear()
    assert auth._jwks_client().uri == f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    auth._jwks_client.cache_clear()


# ---------- rotas ----------


def test_protected_route_accepts_valid_token(make_token: MakeToken) -> None:
    client = TestClient(app)
    response = client.get("/protected", headers={"Authorization": f"Bearer {make_token()}"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user-1"


def test_protected_route_rejects_forged_token(make_token: MakeToken) -> None:
    forged = make_token(secret="outra-chave-qualquer-com-32-bytes-ou-mais")
    response = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == 401


def test_protected_route_without_credentials_is_rejected() -> None:
    assert TestClient(app).get("/protected").status_code in (401, 403)
