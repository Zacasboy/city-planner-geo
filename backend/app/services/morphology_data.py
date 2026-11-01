"""Obtenção da área (GeoJSON) e dos edifícios para a análise de morfologia.

Os edifícios são simulados: a integração com OpenBuildingMap/DBSM ainda não existe.
"""

import logging
import random
from typing import Any

from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)

MOCK_SEED = 42
MOCK_GRID_SPACING = 20  # unidades de coordenada entre edifícios
MOCK_WIDTH_RANGE = (8, 20)
MOCK_LENGTH_RANGE = (8, 25)
MOCK_HEIGHT_RANGE = (5, 25)
METERS_PER_FLOOR = 3

Building = dict[str, Any]


def is_valid_geojson(geojson: object) -> bool:
    """Indica se o GeoJSON tem a estrutura mínima aceite (Feature ou FeatureCollection)."""
    return isinstance(geojson, dict) and geojson.get("type") in ("Feature", "FeatureCollection")


def _exterior_ring(feature: dict[str, Any]) -> list[Any] | None:
    coords = (feature.get("geometry") or {}).get("coordinates")
    if coords and coords[0]:
        ring: list[Any] = coords[0]
        return ring
    return None


def extract_polygon(geojson: dict[str, Any]) -> Polygon | None:
    """Extrai o anel exterior do primeiro polígono de um Feature ou FeatureCollection.

    Args:
        geojson: GeoJSON do tipo Feature ou FeatureCollection.

    Returns:
        O polígono, ou None se não for possível extraí-lo.
    """
    try:
        feature = geojson
        if geojson.get("type") == "FeatureCollection":
            features = geojson.get("features") or []
            if not features:
                return None
            feature = features[0]
        ring = _exterior_ring(feature)
        return Polygon(ring) if ring else None
    except (TypeError, ValueError, AttributeError) as exc:
        logger.warning("Failed to extract polygon from GeoJSON: %s", exc)
        return None


def generate_mock_buildings(polygon: Polygon) -> list[Building]:
    """Gera edifícios simulados numa grelha dentro do polígono (determinístico).

    Args:
        polygon: Área de análise.

    Returns:
        Lista de edifícios com área, altura e pisos.
    """
    rng = random.Random(MOCK_SEED)  # noqa: S311 - dados simulados, não é criptografia
    minx, miny, maxx, maxy = polygon.bounds
    cols = max(1, int((maxx - minx) / MOCK_GRID_SPACING))
    rows = max(1, int((maxy - miny) / MOCK_GRID_SPACING))
    cell_width = (maxx - minx) / cols
    cell_height = (maxy - miny) / rows

    buildings: list[Building] = []
    for i in range(cols):
        for j in range(rows):
            x = minx + i * cell_width + cell_width / 2
            y = miny + j * cell_height + cell_height / 2
            if not polygon.contains(Point(x, y)):
                continue
            footprint_m2 = rng.uniform(*MOCK_WIDTH_RANGE) * rng.uniform(*MOCK_LENGTH_RANGE)
            height_m = rng.uniform(*MOCK_HEIGHT_RANGE)
            buildings.append(
                {
                    "id": f"building_{i}_{j}",
                    "centroid": [x, y],
                    "area_m2": footprint_m2,
                    "footprint_m2": footprint_m2,
                    "height_m": height_m,
                    "floors": max(1, int(height_m / METERS_PER_FLOOR)),
                }
            )
    return buildings
