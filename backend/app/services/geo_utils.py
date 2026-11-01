"""Shared geometry helpers for services that receive GeoJSON areas."""

from typing import Any

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

SUPPORTED_AREA_TYPES = ("Polygon", "MultiPolygon")


def parse_area(geojson: dict[str, Any]) -> BaseGeometry:
    """Parse a GeoJSON Polygon/MultiPolygon (or Feature of one) in EPSG:4326.

    Args:
        geojson: GeoJSON geometry or Feature.

    Returns:
        A valid, non-empty shapely geometry.

    Raises:
        ValueError: If the input is not a usable polygonal area.
    """
    geometry = geojson.get("geometry") if geojson.get("type") == "Feature" else geojson
    if not isinstance(geometry, dict) or geometry.get("type") not in SUPPORTED_AREA_TYPES:
        raise ValueError("A área deve ser um Polygon ou MultiPolygon GeoJSON.")
    try:
        area = make_valid(shape(geometry))
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"GeoJSON inválido: {exc}") from exc
    polygons = [g for g in getattr(area, "geoms", [area]) if g.geom_type in SUPPORTED_AREA_TYPES]
    if area.is_empty or not polygons:
        raise ValueError("A área não contém nenhum polígono válido.")
    return area
