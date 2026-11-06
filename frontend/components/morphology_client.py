"""Cliente do backend para a página de morfologia (`POST /morphology/analyze`)."""

from typing import Any

from frontend.components.backend_client import post_json

ANALYZE_PATH = "/morphology/analyze"


def fetch_morphology(geometry: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Pede ao backend a análise de morfologia de uma área.

    Args:
        geometry: Polígono GeoJSON (geometria) em EPSG:4326.

    Returns:
        Um par (resposta, mensagem_de_erro); a mensagem é vazia se o pedido tiver sucesso.
    """
    feature = {"type": "Feature", "geometry": geometry, "properties": {}}
    return post_json(ANALYZE_PATH, {"geojson": feature, "include_detailed_metrics": False})
