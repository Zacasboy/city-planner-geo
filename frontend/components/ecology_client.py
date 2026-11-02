"""Cliente do backend para o painel ecológico (`POST /ecology/area-species`)."""

from typing import Any

from frontend.components.backend_client import post_json

AREA_SPECIES_PATH = "/ecology/area-species"
MAX_SPECIES = 100


def fetch_area_species(geometry: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Pede ao backend as espécies registadas numa área (só licenças CC0 / CC BY).

    Args:
        geometry: Polígono GeoJSON em EPSG:4326.

    Returns:
        Um par (resposta, mensagem_de_erro); a mensagem é vazia se o pedido tiver sucesso.
    """
    return post_json(AREA_SPECIES_PATH, {"geojson": geometry, "limit": MAX_SPECIES})
