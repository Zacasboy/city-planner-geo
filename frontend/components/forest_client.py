"""Cliente do backend para o painel florestal (`POST /forest/overlap`)."""

from typing import Any

from frontend.components.backend_client import post_json

OVERLAP_PATH = "/forest/overlap"


def fetch_forest_overlap(geometry: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Pede ao backend a sobreposição de uma área com o regime florestal da DGT.

    Args:
        geometry: Polígono GeoJSON em EPSG:4326.

    Returns:
        Um par (resposta, mensagem_de_erro); a mensagem é vazia se o pedido tiver sucesso.
    """
    return post_json(OVERLAP_PATH, {"geojson": geometry})
