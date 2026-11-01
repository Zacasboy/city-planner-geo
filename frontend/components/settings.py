"""Leitura de configuração do frontend (variáveis de ambiente ou `st.secrets`)."""

import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

DEFAULT_BACKEND_URL = "http://localhost:8000"
REQUEST_TIMEOUT_S = 30


def get_setting(name: str, default: str = "") -> str:
    """Devolve uma definição: variável de ambiente, depois `st.secrets`, depois o valor por omissão.

    Args:
        name: Nome da definição (por exemplo `BACKEND_URL`).
        default: Valor se não existir em nenhuma das fontes.

    Returns:
        O valor encontrado.
    """
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets[name])
    except (KeyError, StreamlitSecretNotFoundError):
        return default


def backend_url() -> str:
    """URL base da API do backend."""
    return get_setting("BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def auth_headers() -> dict[str, str]:
    """Cabeçalho Authorization com o token da sessão, se o utilizador tiver iniciado sessão."""
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}
