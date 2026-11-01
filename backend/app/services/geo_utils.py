"""Shared geometry helpers for services that receive GeoJSON areas."""

from functools import lru_cache
from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

SUPPORTED_AREA_TYPES = ("Polygon", "MultiPolygon")
WGS84_EPSG = 4326
TM06_EPSG = 3763


@lru_cache(maxsize=2)
def _transformer(source_epsg: int, target_epsg: int) -> Transformer:
    return Transformer.from_crs(source_epsg, target_epsg, always_xy=True)


def _within_tm06_validity(polygon: Polygon) -> bool:
    west, south, east, north = CRS.from_epsg(TM06_EPSG).area_of_use.bounds  # type: ignore[union-attr]
    minx, miny, maxx, maxy = polygon.bounds
    return minx >= west and maxx <= east and miny >= south and maxy <= north


def polygon_wgs84_to_tm06(polygon: Polygon) -> Polygon:
    """Projeta um polígono de WGS84 (lon, lat) para PT-TM06 (metros).

    Args:
        polygon: Polígono em EPSG:4326, com coordenadas (longitude, latitude).

    Returns:
        O polígono válido em EPSG:3763; se a correção da geometria der várias partes,
        devolve a de maior área.

    Raises:
        ValueError: Se o polígono estiver fora da área de validade do EPSG:3763
            (Portugal continental).
    """
    if not _within_tm06_validity(polygon):
        raise ValueError(
            "A área está fora da zona de validade do EPSG:3763 (Portugal continental)."
        )
    xs, ys = polygon.exterior.xy
    easting, northing = _transformer(WGS84_EPSG, TM06_EPSG).transform(list(xs), list(ys))
    projected = Polygon(zip(easting, northing, strict=True))
    fixed = make_valid(projected)
    parts = [g for g in getattr(fixed, "geoms", [fixed]) if isinstance(g, Polygon)]
    if not parts:
        raise ValueError("A área não contém nenhum polígono válido.")
    return max(parts, key=lambda g: g.area)


def point_tm06_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Converte um ponto de PT-TM06 para WGS84 (longitude, latitude)."""
    lng, lat = _transformer(TM06_EPSG, WGS84_EPSG).transform(easting, northing)
    return float(lng), float(lat)


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
