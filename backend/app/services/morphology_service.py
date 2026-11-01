"""Análise de morfologia urbana.

T2.1: OpenBuildingMap/DBSM e métricas (densidade, altura, ocupação).
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from shapely.geometry import Polygon

from backend.app.services import morphology_metrics as metrics
from backend.app.services.geo_utils import point_tm06_to_wgs84, polygon_wgs84_to_tm06
from backend.app.services.morphology_data import (
    Building,
    extract_polygon,
    generate_mock_buildings,
    is_valid_geojson,
)
from backend.app.services.morphology_models import MorphologyRequest, MorphologyResponse

__all__ = ["MorphologyRequest", "MorphologyResponse", "MorphologyService"]

logger = logging.getLogger(__name__)

MOCK_DATA_SOURCE = "mock/sample"
ANALYSIS_METHOD = "Enhanced Mock Analysis with Realistic Building Distribution"
SAMPLE_BUILDINGS = 5


class MorphologyService:
    """Análise de morfologia com dados simulados (OpenBuildingMap/DBSM ainda não integrados)."""

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
            return self._analyze_polygon(polygon_m, request)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Morphology analysis failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Morphology analysis failed: {e}",
            ) from e

    def _analyze_polygon(
        self, polygon_m: Polygon, request: MorphologyRequest
    ) -> MorphologyResponse:
        """Analisa um polígono já projetado em EPSG:3763 (metros); a API devolve WGS84."""
        area_m2 = polygon_m.area
        buildings: list[Building] = generate_mock_buildings(polygon_m)
        for building in buildings:
            building["centroid"] = list(point_tm06_to_wgs84(*building["centroid"]))

        details: dict[str, Any] = {
            "analysis_area_m2": area_m2,
            "building_count": len(buildings),
            "data_source_attempted": request.data_source,
            "include_detailed_metrics": request.include_detailed_metrics,
            "timestamp": datetime.now().isoformat(),
        }
        if request.include_detailed_metrics and buildings:
            details["building_samples"] = buildings[:SAMPLE_BUILDINGS]

        return MorphologyResponse(
            analysis_area_m2=area_m2,
            building_count=len(buildings),
            density_metrics=metrics.density_metrics(buildings, area_m2),
            height_metrics=metrics.height_metrics(buildings),
            height_percentiles=metrics.height_percentiles(buildings),
            occupation_metrics=metrics.occupation_metrics(buildings, area_m2),
            building_type_metrics=metrics.building_type_metrics(buildings),
            data_source_used=self._data_source_used(request.data_source),
            analysis_method=ANALYSIS_METHOD,
            details=details,
        )

    @staticmethod
    def _data_source_used(requested_source: str) -> str:
        """Devolve a fonte efetivamente usada; em modo auto só há dados simulados."""
        return MOCK_DATA_SOURCE if requested_source == "auto" else requested_source
