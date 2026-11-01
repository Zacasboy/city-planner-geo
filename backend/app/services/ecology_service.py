"""Ecological service backed by GBIF.

T1.4: Serviço Ecológico (GBIF) com cache e testes mock — POST /ecology/species

P4: occurrence data is only used when its license is on ``ALLOWED_LICENSES``
(CC0 and CC BY 4.0). Records under CC BY-NC, UNSPECIFIED or UNSUPPORTED are excluded
because the platform is commercial.
"""

import asyncio
import hashlib
import json
from typing import Any

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

from backend.app.config import settings
from backend.app.services.geo_utils import parse_area
from backend.app.services.http_retry import request_with_retry

# Create router
router = APIRouter()


# Cache configuration
# Rules R2: GBIF cache TTL must be at least 24 h
CACHE_TTL_SECONDS = 24 * 3600
species_cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=1000, ttl=CACHE_TTL_SECONDS)
area_cache: TTLCache[str, Any] = TTLCache(maxsize=500, ttl=CACHE_TTL_SECONDS)

# GBIF API configuration
GBIF_API_BASE = "https://api.gbif.org/v1"
GBIF_SPECIES_ENDPOINT = f"{GBIF_API_BASE}/species/match"
GBIF_OCCURRENCE_ENDPOINT = f"{GBIF_API_BASE}/occurrence/search"

# GBIF license enumeration: CC0_1_0, CC_BY_4_0, CC_BY_NC_4_0, UNSPECIFIED, UNSUPPORTED
ALLOWED_LICENSES = ("CC0_1_0", "CC_BY_4_0")
GBIF_MAX_LIMIT = 300  # occurrence/search page size limit
DEFAULT_FACET_LIMIT = 20
MAX_FACET_LIMIT = 100
MAX_WKT_VERTICES = 1000  # keeps the GET URL within server limits
SIMPLIFY_ABOVE_VERTICES = 300
SIMPLIFY_TOLERANCE_DEG = 0.0001
EFFORT_NOTE = (
    "As contagens medem esforço de observação (registos), não abundância. "
    "Em Angola a cobertura GBIF é esparsa e de baixa resolução."
)
ATTRIBUTION_NOTE = (
    "Dados GBIF sob CC0 ou CC BY 4.0; a atribuição ao fornecedor de cada registo é obrigatória."
)


class SpeciesRequest(BaseModel):
    """Request model for species lookup."""

    scientific_name: str
    kingdom: str | None = None
    phylum: str | None = None
    class_: str | None = None  # Using class_ to avoid conflict with Python keyword
    order: str | None = None
    family: str | None = None
    genus: str | None = None


class SpeciesResponse(BaseModel):
    """Response model for species data."""

    usage_key: int | None = None
    scientific_name: str | None = None
    canonical_name: str | None = None
    rank: str | None = None
    status: str | None = None
    confidence: float | None = None
    match_type: str | None = None
    kingdom: str | None = None
    phylum: str | None = None
    class_: str | None = None
    order: str | None = None
    family: str | None = None
    genus: str | None = None
    species: str | None = None
    # Additional GBIF fields
    kingdom_key: int | None = None
    phylum_key: int | None = None
    class_key: int | None = None
    order_key: int | None = None
    family_key: int | None = None
    genus_key: int | None = None
    species_key: int | None = None


class AreaSpeciesRequest(BaseModel):
    """Request model for species observed inside an area."""

    geojson: dict[str, Any]
    limit: int = Field(default=DEFAULT_FACET_LIMIT, ge=1, le=MAX_FACET_LIMIT)


class AreaSpeciesItem(BaseModel):
    """One species and its number of allowed-license records in the area."""

    species_key: int
    scientific_name: str | None = None
    records: int


class AreaSpeciesResponse(BaseModel):
    """Species observed in an area, using only allowed-license records."""

    total_records: int
    records_excluded_by_license: int
    allowed_licenses: list[str]
    species: list[AreaSpeciesItem]
    notes: list[str]


def _polygons(area: BaseGeometry) -> list[Polygon]:
    """Flatten any polygonal geometry into its Polygon parts."""
    if isinstance(area, Polygon):
        return [area]
    return [p for part in getattr(area, "geoms", []) for p in _polygons(part)]


def _vertex_count(polygons: list[Polygon]) -> int:
    return sum(len(p.exterior.coords) for p in polygons)


def _polygon_to_wkt(geojson: dict[str, Any]) -> str:
    """Convert a GeoJSON area to anti-clockwise WKT, as GBIF requires."""
    area = parse_area(geojson)
    if _vertex_count(_polygons(area)) > SIMPLIFY_ABOVE_VERTICES:
        area = area.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
    polygons = _polygons(area)
    if not polygons:
        raise ValueError("A área não contém nenhum polígono válido.")
    if _vertex_count(polygons) > MAX_WKT_VERTICES:
        raise ValueError("A área tem demasiados vértices; simplifique o polígono.")
    oriented = [orient(p, sign=1.0) for p in polygons]
    wkt: str = (oriented[0] if len(oriented) == 1 else MultiPolygon(oriented)).wkt
    return wkt


class EcologyService:
    """Service for GBIF ecological data integration with caching."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        """Use the given HTTP client, or create and own one."""
        self.http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = http_client is None

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            await self.http_client.aclose()

    @property
    def _headers(self) -> dict[str, str]:
        return {"User-Agent": settings.GBIF_USER_AGENT}

    async def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        response = await request_with_retry(
            self.http_client, "GET", url, params=params, headers=self._headers
        )
        return response.json()

    def _get_cache_key(self, scientific_name: str, **kwargs: Any) -> str:
        """Generate a cache key for species lookup."""
        # Create a deterministic key based on all parameters
        key_data = {
            "scientific_name": scientific_name.lower().strip(),
            "kingdom": kwargs.get("kingdom", "").lower().strip() if kwargs.get("kingdom") else "",
            "phylum": kwargs.get("phylum", "").lower().strip() if kwargs.get("phylum") else "",
            "class": kwargs.get("class_", "").lower().strip() if kwargs.get("class_") else "",
            "order": kwargs.get("order", "").lower().strip() if kwargs.get("order") else "",
            "family": kwargs.get("family", "").lower().strip() if kwargs.get("family") else "",
            "genus": kwargs.get("genus", "").lower().strip() if kwargs.get("genus") else "",
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def lookup_species(self, request: SpeciesRequest) -> SpeciesResponse:
        """Look up species information from GBIF with caching.

        Args:
            request: SpeciesRequest containing search parameters

        Returns:
            SpeciesResponse with species information from GBIF

        Raises:
            HTTPException: If GBIF API request fails
        """
        # Check cache first
        cache_key = self._get_cache_key(
            request.scientific_name,
            kingdom=request.kingdom,
            phylum=request.phylum,
            class_=request.class_,
            order=request.order,
            family=request.family,
            genus=request.genus,
        )

        if cache_key in species_cache:
            cached_data = species_cache[cache_key]
            # Return cached data with cache hit indicator
            return SpeciesResponse(**cached_data)

        # If not in cache, make API request to GBIF
        try:
            params = {
                "name": request.scientific_name,
                "kingdom": request.kingdom,
                "phylum": request.phylum,
                "class": request.class_,
                "order": request.order,
                "family": request.family,
                "genus": request.genus,
                "strict": False,  # Allow fuzzy matching
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            gbif_data = await self._get_json(GBIF_SPECIES_ENDPOINT, params)

            # Convert GBIF response to our response model
            species_data = {
                "usage_key": gbif_data.get("usageKey"),
                "scientific_name": gbif_data.get("scientificName"),
                "canonical_name": gbif_data.get("canonicalName"),
                "rank": gbif_data.get("rank"),
                "status": gbif_data.get("status"),
                "confidence": gbif_data.get("confidence"),
                "match_type": gbif_data.get("matchType"),
                "kingdom": gbif_data.get("kingdom"),
                "phylum": gbif_data.get("phylum"),
                "class_": gbif_data.get("class"),
                "order": gbif_data.get("order"),
                "family": gbif_data.get("family"),
                "genus": gbif_data.get("genus"),
                "species": gbif_data.get("species"),
                "kingdom_key": gbif_data.get("kingdomKey"),
                "phylum_key": gbif_data.get("phylumKey"),
                "class_key": gbif_data.get("classKey"),
                "order_key": gbif_data.get("orderKey"),
                "family_key": gbif_data.get("familyKey"),
                "genus_key": gbif_data.get("genusKey"),
                "species_key": gbif_data.get("speciesKey"),
            }

            # Cache the result
            species_cache[cache_key] = species_data

            return SpeciesResponse(**species_data)

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GBIF API error: {e.response.status_code} - {e.response.text}",
            ) from e
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"GBIF API request failed: {str(e)}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Species lookup failed: {str(e)}",
            ) from e

    async def get_species_occurrences(self, species_key: int, limit: int = 100) -> dict[str, Any]:
        """Get occurrence data for a species from GBIF, restricted to allowed licenses.

        Args:
            species_key: GBIF species key
            limit: Maximum number of occurrences to return (capped at 300)

        Returns:
            Dictionary with occurrence data
        """
        try:
            params = {
                "taxonKey": species_key,
                "limit": max(0, min(limit, GBIF_MAX_LIMIT)),
                "license": list(ALLOWED_LICENSES),
            }
            occurrences: dict[str, Any] = await self._get_json(GBIF_OCCURRENCE_ENDPOINT, params)
            return occurrences

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GBIF occurrence API error: {e.response.status_code} - {e.response.text}",
            ) from e
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"GBIF occurrence API request failed: {str(e)}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Species occurrence lookup failed: {str(e)}",
            ) from e

    async def _species_name(self, species_key: int) -> str | None:
        cache_key = f"name:{species_key}"
        if cache_key not in area_cache:
            data = await self._get_json(f"{GBIF_API_BASE}/species/{species_key}", {})
            area_cache[cache_key] = data.get("canonicalName") or data.get("scientificName")
        name: str | None = area_cache[cache_key]
        return name

    async def get_area_species(self, request: AreaSpeciesRequest) -> AreaSpeciesResponse:
        """List the most recorded species inside an area, using allowed licenses only.

        Uses one faceted request (``limit=0``) instead of paging through occurrences,
        plus one count request without the license filter to report what was excluded.

        Raises:
            HTTPException: 422 invalid area, 502 upstream error, 503 unavailable.
        """
        try:
            wkt = _polygon_to_wkt(request.geojson)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc

        cache_key = hashlib.sha256(f"{wkt}|{request.limit}".encode()).hexdigest()
        if cache_key in area_cache:
            return AreaSpeciesResponse(**area_cache[cache_key])

        base = {"geometry": wkt, "hasCoordinate": "true", "hasGeospatialIssue": "false", "limit": 0}
        try:
            allowed, everything = await asyncio.gather(
                self._get_json(
                    GBIF_OCCURRENCE_ENDPOINT,
                    {
                        **base,
                        "license": list(ALLOWED_LICENSES),
                        "facet": "speciesKey",
                        "facetLimit": request.limit,
                    },
                ),
                self._get_json(GBIF_OCCURRENCE_ENDPOINT, base),
            )
            counts: list[dict[str, Any]] = next(
                (f["counts"] for f in allowed.get("facets", []) if f["field"] == "SPECIES_KEY"), []
            )
            names = await asyncio.gather(*(self._species_name(int(c["name"])) for c in counts))
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GBIF API error: {e.response.status_code} - {e.response.text}",
            ) from e
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"GBIF API request failed: {str(e)}",
            ) from e

        total = int(allowed.get("count", 0))
        result = {
            "total_records": total,
            "records_excluded_by_license": max(int(everything.get("count", 0)) - total, 0),
            "allowed_licenses": list(ALLOWED_LICENSES),
            "species": [
                {"species_key": int(c["name"]), "scientific_name": n, "records": int(c["count"])}
                for c, n in zip(counts, names, strict=True)
            ],
            "notes": [EFFORT_NOTE, ATTRIBUTION_NOTE],
        }
        area_cache[cache_key] = result
        return AreaSpeciesResponse.model_validate(result)


# Create service instance
ecology_service = EcologyService()


# Convenience functions
async def lookup_species(request: SpeciesRequest) -> SpeciesResponse:
    """Look up species information from GBIF with caching."""
    return await ecology_service.lookup_species(request)


async def get_species_occurrences(species_key: int, limit: int = 100) -> dict[str, Any]:
    """Get occurrence data for a species from GBIF."""
    return await ecology_service.get_species_occurrences(species_key, limit)


async def get_area_species(request: AreaSpeciesRequest) -> AreaSpeciesResponse:
    """List species recorded in an area (allowed licenses only)."""
    return await ecology_service.get_area_species(request)


# API Routes
@router.post("/area-species", tags=["ecology"])
async def area_species_endpoint(request: AreaSpeciesRequest) -> AreaSpeciesResponse:
    """Species recorded in a polygon (GeoJSON, EPSG:4326), using only CC0 / CC BY 4.0 records.

    Counts are observation effort, not abundance.
    """
    return await get_area_species(request)


@router.post("/species", tags=["ecology"])
async def lookup_species_endpoint(request: SpeciesRequest) -> SpeciesResponse:
    """Look up species information from GBIF.

    Args:
        request: SpeciesRequest containing search parameters

    Returns:
        Species information from GBIF
    """
    try:
        return await lookup_species(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Species lookup failed: {str(e)}",
        ) from e


@router.get("/species/{species_key}/occurrences", tags=["ecology"])
async def get_species_occurrences_endpoint(species_key: int, limit: int = 100) -> dict[str, Any]:
    """Get occurrence data for a species from GBIF.

    Args:
        species_key: GBIF species key
        limit: Maximum number of occurrences to return (default: 100)

    Returns:
        Occurrence data for the species
    """
    try:
        return await get_species_occurrences(species_key, limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get species occurrences: {str(e)}",
        ) from e


@router.get("/cache/stats", tags=["ecology"])
async def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics for debugging/monitoring.

    Returns:
        Dictionary with cache statistics
    """
    return {
        "cache_size": len(species_cache) + len(area_cache),
        "cache_maxsize": species_cache.maxsize,
        "cache_ttl": species_cache.ttl,
    }


@router.delete("/cache", tags=["ecology"])
async def clear_cache() -> dict[str, str]:
    """Clear the species cache.

    Returns:
        Confirmation message
    """
    species_cache.clear()
    area_cache.clear()
    return {"message": "Species cache cleared"}
