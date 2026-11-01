"""Configuração comum dos testes.

Define as variáveis obrigatórias de `Settings` antes de qualquer import da aplicação,
para os testes correrem sem `.env` (por exemplo no CI).
"""

import os

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "fake")
os.environ.setdefault("SUPABASE_SECRET_KEY", "fake")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-with-at-least-32-bytes!")


import time
from collections.abc import Callable
from typing import Any

import jwt
import pytest

from backend.app.config import settings

ONE_HOUR_S = 3600


@pytest.fixture
def make_token() -> Callable[..., str]:
    """Cria um JWT HS256 como o Supabase (com `aud`, `iss`, `sub` e `exp`)."""

    def make(user_id: str = "user-1", secret: str | None = None, **overrides: Any) -> str:
        claims: dict[str, Any] = {
            "sub": user_id,
            "aud": settings.SUPABASE_JWT_AUDIENCE,
            "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
            "exp": time.time() + ONE_HOUR_S,
        } | overrides
        claims = {key: value for key, value in claims.items() if value is not None}
        return jwt.encode(claims, secret or settings.SUPABASE_JWT_SECRET, algorithm="HS256")

    return make


@pytest.fixture
def auth_headers(make_token: Callable[..., str]) -> Callable[[str], dict[str, str]]:
    """Devolve uma função que cria o cabeçalho Authorization de um utilizador."""

    def make(user_id: str = "user-1") -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(user_id)}"}

    return make
