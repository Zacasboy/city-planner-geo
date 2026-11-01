"""Configuração comum dos testes.

Define as variáveis obrigatórias de `Settings` antes de qualquer import da aplicação,
para os testes correrem sem `.env` (por exemplo no CI).
"""

import os

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "fake")
os.environ.setdefault("SUPABASE_SECRET_KEY", "fake")
os.environ.setdefault("SECRET_KEY", "fakesecret")


import time
from collections.abc import Callable

import jwt
import pytest

from backend.app.config import settings

ONE_HOUR_S = 3600


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    """Devolve uma função que cria o cabeçalho Authorization de um utilizador."""

    def make(user_id: str = "user-1") -> dict[str, str]:
        token = jwt.encode(
            {"sub": user_id, "exp": time.time() + ONE_HOUR_S},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        return {"Authorization": f"Bearer {token}"}

    return make
