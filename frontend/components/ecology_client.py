"""Cliente do backend para o painel ecológico (`POST /ecology/area-species`)."""

from typing import Any

import requests

from frontend.components.settings import REQUEST_TIMEOUT_S, auth_headers, backend_url

AREA_SPECIES_PATH = "/ecology/area-species"
MAX_SPECIES = 100
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


def fetch_area_species(geometry: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Pede ao backend as espécies registadas numa área (só licenças CC0 / CC BY).

    Args:
        geometry: Polígono GeoJSON em EPSG:4326.

    Returns:
        Um par (resposta, mensagem_de_erro); a mensagem é vazia se o pedido tiver sucesso.
    """
    try:
        response = requests.post(
            f"{backend_url()}{AREA_SPECIES_PATH}",
            json={"geojson": geometry, "limit": MAX_SPECIES},
            headers=auth_headers(),
            timeout=REQUEST_TIMEOUT_S,
        )
    except requests.RequestException:
        return None, "Could not reach the backend. Please try again later."
    if response.status_code != HTTP_OK:
        return None, _error_message(response)
    result: dict[str, Any] = response.json()
    return result, ""
