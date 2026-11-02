"""Pedidos POST ao backend com o token da sessão e mensagens de erro uniformes."""

from typing import Any

import requests

from frontend.components.settings import REQUEST_TIMEOUT_S, auth_headers, backend_url

HTTP_OK = 200
HTTP_UNAUTHORIZED = 401


def _error_message(response: requests.Response) -> str:
    if response.status_code == HTTP_UNAUTHORIZED:
        return "Session expired or not logged in. Please log in again."
    try:
        detail = response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        detail = "unexpected response"
    return f"Backend error {response.status_code}: {detail}"


def post_json(path: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Envia um pedido autenticado ao backend.

    Args:
        path: Caminho da rota, por exemplo `/forest/overlap`.
        payload: Corpo JSON do pedido.

    Returns:
        Um par (resposta, mensagem_de_erro); a mensagem é vazia se o pedido tiver sucesso.
    """
    try:
        response = requests.post(
            f"{backend_url()}{path}",
            json=payload,
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT_S,
        )
    except requests.RequestException:
        return None, "Could not reach the backend. Please try again later."
    if response.status_code != HTTP_OK:
        return None, _error_message(response)
    result: dict[str, Any] = response.json()
    return result, ""
