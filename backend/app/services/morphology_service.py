"""Análise de morfologia urbana.

T2.1: edifícios do OpenBuildingMap (ODbL), alturas em falta estimadas pelo GlobalBuildingAtlas
(CC BY-NC 4.0, uso não comercial) e métricas (densidade, altura, ocupação).
"""

import asyncio
import hashlib
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from cachetools import TTLCache
from fastapi import HTTPException, status
from shapely.geometry import Polygon

from backend.app.services import gba_source
from backend.app.services import morphology_metrics as metrics
from backend.app.services.geo_utils import point_tm06_to_wgs84, polygon_wgs84_to_tm06
from backend.app.services.morphology_data import (
    Building,
    extract_polygon,
    generate_mock_buildings,
    is_valid_geojson,
)
from backend.app.services.morphology_models import MorphologyRequest, MorphologyResponse
from backend.app.services.obm_source import ATTRIBUTION, BuildingSourceError

__all__ = ["MorphologyRequest", "MorphologyResponse", "MorphologyService"]

logger = logging.getLogger(__name__)

MOCK_DATA_SOURCE = "mock/sample"
MOCK_ANALYSIS_METHOD = "Simulated buildings on a grid (development only, not real data)"
OBM_DATA_SOURCE = "OpenBuildingMap"
OBM_ANALYSIS_METHOD = "Building footprints from OpenBuildingMap; metrics computed in EPSG:3763"
OBM_LICENSE = "ODbL-1.0"
GBA_LICENSE = "CC-BY-NC-4.0"
GBA_DATA_SOURCE = "OpenBuildingMap + GlobalBuildingAtlas (estimated heights)"
GBA_HEIGHT_RMSE_M = 5.5
SAMPLE_BUILDINGS = 5
MOCK_SOURCE_REQUEST = "mock"
MAX_REAL_AREA_M2 = 5_000_000
FETCH_TIMEOUT_S = 60
CACHE_TTL_SECONDS = 24 * 3600
CACHE_MAX_ENTRIES = 200
PERCENT = 100
FLOOR_AREA_NOTE = (
    "floor_area_ratio is a lower bound: buildings without a known height count as one floor."
)

BuildingFetcher = Callable[[Any, Any], tuple[list[Building], list[str]]]
_cache: TTLCache[str, tuple[list[Building], list[str]]] = TTLCache(
    maxsize=CACHE_MAX_ENTRIES, ttl=CACHE_TTL_SECONDS
)


def _cache_key(polygon_m: Polygon) -> str:
    return hashlib.sha256(polygon_m.normalize().wkb).hexdigest()


def _data_source_label(is_mock: bool, estimated: int) -> str:
    if is_mock:
        return MOCK_DATA_SOURCE
    return GBA_DATA_SOURCE if estimated else OBM_DATA_SOURCE


def _estimated_height_details(
    estimated: int, total: int, details: dict[str, Any]
) -> dict[str, Any]:
    """Campos extra quando parte das alturas vem de estimativas do GlobalBuildingAtlas."""
    share = round(estimated / total * PERCENT, 1)
    return {
        "buildings_with_estimated_height": estimated,
        "estimated_height_percent": share,
        "attribution": f"{details['attribution']}; {gba_source.ATTRIBUTION}",
        "license": f"{OBM_LICENSE}; heights: {GBA_LICENSE}",
        "notes": [
            *details["notes"],
            f"{share:.0f} % of the buildings have a model-estimated height "
            f"(GlobalBuildingAtlas, global RMSE about {GBA_HEIGHT_RMSE_M} m); "
            "treat height-based figures as indicative. Non-commercial use only.",
        ],
    }


class MorphologyService:
    """Análise de morfologia com edifícios reais do OpenBuildingMap (ou simulados, em dev)."""

    def __init__(self, fetcher: BuildingFetcher = gba_source.fetch_buildings_with_heights) -> None:  # noqa: D107
        self._fetcher = fetcher

    async def close(self) -> None:
        """Fecha o serviço (não faz nada por agora)."""

    async def analyze_morphology(self, request: MorphologyRequest) -> MorphologyResponse:
        """Calcula as métricas de morfologia de uma área.

        Args:
            request: Pedido com o GeoJSON da área e os parâmetros da análise.

        Returns:
            Métricas de densidade, altura, ocupação e tipologia.

        Raises:
            HTTPException: 400 se o GeoJSON for inválido, 500 se a análise falhar.
        """
        try:
            if not is_valid_geojson(request.geojson):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid GeoJSON provided"
                )
            polygon = extract_polygon(request.geojson)
            if polygon is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not extract valid polygon from GeoJSON",
                )
            try:
                polygon_m = polygon_wgs84_to_tm06(polygon)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                ) from exc
            return await self._analyze_polygon(polygon, polygon_m, request)
        except HTTPException:
            raise
        except BuildingSourceError as e:
            logger.error("Building source failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Building data source unavailable",
            ) from e
        except TimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Building data source timed out",
            ) from e
        except Exception as e:
            logger.error("Morphology analysis failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Morphology analysis failed: {e}",
            ) from e

    async def _load_buildings(
        self, polygon: Polygon, polygon_m: Polygon, request: MorphologyRequest
    ) -> tuple[list[Building], list[str]]:
        """Obtém os edifícios (simulados só se pedido) e converte os centroides para WGS84."""
        if request.data_source == MOCK_SOURCE_REQUEST:
            return generate_mock_buildings(polygon_m), []
        if polygon_m.area > MAX_REAL_AREA_M2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Area too large: the limit is {MAX_REAL_AREA_M2} m²",
            )
        key = _cache_key(polygon_m)
        if key not in _cache:
            _cache[key] = await asyncio.wait_for(
                asyncio.to_thread(self._fetcher, polygon, polygon_m), FETCH_TIMEOUT_S
            )
        buildings, missing = _cache[key]
        return [dict(b) for b in buildings], missing

    async def _analyze_polygon(
        self, polygon: Polygon, polygon_m: Polygon, request: MorphologyRequest
    ) -> MorphologyResponse:
        """Analisa uma área; a API devolve coordenadas em WGS84 e áreas em m²."""
        area_m2 = polygon_m.area
        buildings, missing_tiles = await self._load_buildings(polygon, polygon_m, request)
        for building in buildings:
            building["centroid"] = list(point_tm06_to_wgs84(*building["centroid"]))
        is_mock = request.data_source == MOCK_SOURCE_REQUEST
        gba_missing = [t for t in missing_tiles if t.startswith(gba_source.MISSING_PREFIX)]
        missing_tiles = [t for t in missing_tiles if t not in gba_missing]
        estimated = sum(b.get("height_source") == gba_source.HEIGHT_SOURCE_GBA for b in buildings)
        with_height = [b for b in buildings if b.get("height_m") is not None]

        details: dict[str, Any] = {
            "analysis_area_m2": area_m2,
            "building_count": len(buildings),
            "buildings_with_height": len(with_height),
            "height_coverage_percent": (
                round(len(with_height) / len(buildings) * PERCENT, 1) if buildings else 0.0
            ),
            "include_detailed_metrics": request.include_detailed_metrics,
            "timestamp": datetime.now().isoformat(),
        }
        if not is_mock:
            details |= {
                "attribution": ATTRIBUTION,
                "license": OBM_LICENSE,
                "tiles_missing": missing_tiles,
                "notes": [
                    FLOOR_AREA_NOTE,
                    "Height metrics use only buildings with a known height.",
                ],
            }
            if estimated:
                details |= _estimated_height_details(estimated, len(buildings), details)
            if gba_missing:
                details["gba_tiles_missing"] = gba_missing
        if request.include_detailed_metrics and buildings:
            details["building_samples"] = buildings[:SAMPLE_BUILDINGS]

        return MorphologyResponse(
            analysis_area_m2=area_m2,
            building_count=len(buildings),
            density_metrics=metrics.density_metrics(buildings, area_m2),
            height_metrics=metrics.height_metrics(with_height),
            height_percentiles=metrics.height_percentiles(with_height),
            occupation_metrics=metrics.occupation_metrics(buildings, area_m2),
            building_type_metrics=metrics.building_type_metrics(buildings),
            data_source_used=_data_source_label(is_mock, estimated),
            analysis_method=MOCK_ANALYSIS_METHOD if is_mock else OBM_ANALYSIS_METHOD,
            details=details,
        )
