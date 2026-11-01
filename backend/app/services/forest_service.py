"""Forest service backed by the DGT regime florestal.

T1.5: Serviço Florestal (DGT, regime florestal) — POST /forest/overlap

Source: Direção-Geral do Território, ArcGIS FeatureServer ``Regime_florestal`` (layer 1562).
The layer lists areas under forest regime (public/communal forest), NOT land cover or PROF.
Its license is not stated in the service metadata (see docs/data_sources.md).
"""

import hashlib
import json
import logging
from typing import Any

import httpx
import numpy as np
import shapely
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from pyproj import Transformer
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from backend.app.config import settings
from backend.app.services.geo_utils import parse_area
from backend.app.services.http_retry import request_with_retry

router = APIRouter()
logger = logging.getLogger(__name__)

SOURCE_NAME = "DGT - Regime Florestal"
LAYER_FIELDS = "codigo,nome,tipologia,regime"
PAGE_SIZE = 2000  # layer maxRecordCount
MAX_PAGES = 5
CACHE_TTL_SECONDS = 24 * 3600  # Rules R2: TTL >= 24 h
AREA_CRS = "EPSG:3763"  # Rules R1: local area calculations in PT-TM06
M2_PER_KM2 = 1_000_000
LICENSE_WARNING = (
    "Licença da camada DGT não confirmada: não redistribuir os dados em bruto "
    "até confirmação com a DGT/ICNF."
)
SCOPE_NOTE = (
    "A camada cobre apenas Portugal e apenas áreas sob regime florestal. "
    "Ausência de sobreposição não significa ausência de floresta nem de condicionantes (PROF)."
)

_overlap_cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=500, ttl=CACHE_TTL_SECONDS)
_to_area_crs = Transformer.from_crs("EPSG:4326", AREA_CRS, always_xy=True).transform


class OverlapRequest(BaseModel):
    """Request model for forest overlap check."""

    geojson: dict[str, Any]


class OverlapResponse(BaseModel):
    """Response model for forest overlap result."""

    overlap_area_km2: float
    percentage_covered: float
    details: dict[str, Any]


def _to_esri_polygon(area: BaseGeometry) -> dict[str, Any]:
    """Convert to Esri JSON rings (outer rings clockwise, holes counter-clockwise)."""
    rings: list[list[list[float]]] = []
    for polygon in getattr(area, "geoms", [area]):
        polygon = orient(polygon, sign=-1.0)
        rings.append([list(c) for c in polygon.exterior.coords])
        rings.extend([list(c) for c in hole.coords] for hole in polygon.interiors)
    return {"rings": rings, "spatialReference": {"wkid": 4326}}


def _area_m2(geometry: BaseGeometry) -> float:
    projected = shapely.transform(
        geometry, lambda xy: np.column_stack(_to_area_crs(xy[:, 0], xy[:, 1]))
    )
    return float(projected.area)


def _cache_key(area: BaseGeometry) -> str:
    return hashlib.sha256(area.wkb).hexdigest()


class ForestService:
    """Service for DGT forest-regime data integration."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        """Use the given HTTP client, or create and own one."""
        self.settings = settings
        self.http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = http_client is None
        self.layer_url = (self.settings.DGT_REGIME_FLORESTAL_URL or "").rstrip("/")

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            await self.http_client.aclose()

    async def _fetch_page(self, area: BaseGeometry, offset: int) -> dict[str, Any]:
        data = {
            "where": "1=1",
            "geometry": json.dumps(_to_esri_polygon(area)),
            "geometryType": "esriGeometryPolygon",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": LAYER_FIELDS,
            "returnGeometry": "true",
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE_SIZE),
            "f": "geojson",
        }
        response = await request_with_retry(
            self.http_client, "POST", f"{self.layer_url}/query", data=data
        )
        payload = response.json()
        if "error" in payload:  # ArcGIS reports errors with HTTP 200
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"DGT ArcGIS error: {payload['error']}",
            )
        return dict(payload)

    async def _fetch_features(self, area: BaseGeometry) -> list[dict[str, Any]]:
        features: list[dict[str, Any]] = []
        for page in range(MAX_PAGES):
            payload = await self._fetch_page(area, page * PAGE_SIZE)
            features.extend(payload.get("features", []))
            exceeded = payload.get("exceededTransferLimit") or payload.get("properties", {}).get(
                "exceededTransferLimit"
            )
            if not exceeded:
                return features
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="DGT devolveu mais resultados do que o limite de paginação.",
        )

    def _summarise(self, area: BaseGeometry, features: list[dict[str, Any]]) -> dict[str, Any]:
        query_m2 = _area_m2(area)
        items: list[dict[str, Any]] = []
        pieces: list[BaseGeometry] = []
        for feature in features:
            piece = area.intersection(shape(feature["geometry"]).buffer(0))
            if piece.is_empty:
                continue
            pieces.append(piece)
            props = feature.get("properties", {})
            items.append(
                {
                    "codigo": props.get("codigo"),
                    "nome": props.get("nome"),
                    "tipologia": props.get("tipologia"),
                    "regime": props.get("regime"),
                    "overlap_km2": round(_area_m2(piece) / M2_PER_KM2, 6),
                }
            )
        overlap_m2 = _area_m2(unary_union(pieces)) if pieces else 0.0
        return {
            "overlap_area_km2": round(overlap_m2 / M2_PER_KM2, 6),
            "percentage_covered": round(100 * overlap_m2 / query_m2, 4) if query_m2 else 0.0,
            "details": {
                "source": SOURCE_NAME,
                "features_count": len(items),
                "features": items,
                "license_status": "unconfirmed",
                "warnings": [LICENSE_WARNING, SCOPE_NOTE],
            },
        }

    async def check_overlap(self, request: OverlapRequest) -> OverlapResponse:
        """Compute the overlap between a polygon and DGT forest-regime areas.

        Raises:
            HTTPException: 422 invalid area, 502 upstream error, 503 unavailable/unconfigured.
        """
        if not self.layer_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DGT forest regime URL not configured",
            )
        try:
            area = parse_area(request.geojson)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc

        key = _cache_key(area)
        if key not in _overlap_cache:
            try:
                features = await self._fetch_features(area)
            except httpx.HTTPStatusError as exc:
                logger.error("DGT HTTP error: %s", exc.response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"DGT API error: {exc.response.status_code} - {exc.response.text}",
                ) from exc
            except httpx.RequestError as exc:
                logger.error("DGT request failed: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"DGT API request failed: {exc}",
                ) from exc
            _overlap_cache[key] = self._summarise(area, features)
        return OverlapResponse(**_overlap_cache[key])


forest_service = ForestService()


async def check_overlap(request: OverlapRequest) -> OverlapResponse:
    """Check overlap with forest-regime areas."""
    return await forest_service.check_overlap(request)


@router.post("/overlap", tags=["forest"])
async def forest_overlap_endpoint(request: OverlapRequest) -> OverlapResponse:
    """Check overlap of an area (GeoJSON, EPSG:4326) with DGT forest-regime areas."""
    return await check_overlap(request)
