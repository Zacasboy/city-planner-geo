"""
Ecological Service - GBIF Integration
T1.4: Serviço Ecológico (GBIF) com cache e testes mock — POST /ecology/species
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any
import httpx
from cachetools import TTLCache

from fastapi import HTTPException, status, APIRouter
from pydantic import BaseModel

# Create router
router = APIRouter()


# Cache configuration
# Cache species data for 1 hour (3600 seconds) with max 1000 entries
species_cache = TTLCache(maxsize=1000, ttl=3600)

# GBIF API configuration
GBIF_API_BASE = "https://api.gbif.org/v1"
GBIF_SPECIES_ENDPOINT = f"{GBIF_API_BASE}/species/match"
GBIF_OCCURRENCE_ENDPOINT = f"{GBIF_API_BASE}/occurrence/search"


class SpeciesRequest(BaseModel):
    """Request model for species lookup."""
    scientific_name: str
    kingdom: Optional[str] = None
    phylum: Optional[str] = None
    class_: Optional[str] = None  # Using class_ to avoid conflict with Python keyword
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None


class SpeciesResponse(BaseModel):
    """Response model for species data."""
    usage_key: Optional[int] = None
    scientific_name: Optional[str] = None
    canonical_name: Optional[str] = None
    rank: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[float] = None
    match_type: Optional[str] = None
    kingdom: Optional[str] = None
    phylum: Optional[str] = None
    class_: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None
    # Additional GBIF fields
    kingdom_key: Optional[int] = None
    phylum_key: Optional[int] = None
    class_key: Optional[int] = None
    order_key: Optional[int] = None
    family_key: Optional[int] = None
    genus_key: Optional[int] = None
    species_key: Optional[int] = None


class EcologyService:
    """Service for GBIF ecological data integration with caching."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    def _get_cache_key(self, scientific_name: str, **kwargs) -> str:
        """Generate a cache key for species lookup."""
        # Create a deterministic key based on all parameters
        key_data = {
            "scientific_name": scientific_name.lower().strip(),
            "kingdom": kwargs.get("kingdom", "").lower().strip() if kwargs.get("kingdom") else "",
            "phylum": kwargs.get("phylum", "").lower().strip() if kwargs.get("phylum") else "",
            "class": kwargs.get("class_", "").lower().strip() if kwargs.get("class_") else "",
            "order": kwargs.get("order", "").lower().strip() if kwargs.get("order") else "",
            "family": kwargs.get("family", "").lower().strip() if kwargs.get("family") else "",
            "genus": kwargs.get("genus", "").lower().strip() if kwargs.get("genus") else ""
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def lookup_species(self, request: SpeciesRequest) -> SpeciesResponse:
        """
        Look up species information from GBIF with caching.

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
            genus=request.genus
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
                "strict": False  # Allow fuzzy matching
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            response = await self.http_client.get(GBIF_SPECIES_ENDPOINT, params=params)
            response.raise_for_status()

            gbif_data = response.json()

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
                "species_key": gbif_data.get("speciesKey")
            }

            # Cache the result
            species_cache[cache_key] = species_data

            return SpeciesResponse(**species_data)

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GBIF API error: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"GBIF API request failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Species lookup failed: {str(e)}"
            )

    async def get_species_occurrences(
        self,
        species_key: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get occurrence data for a species from GBIF.

        Args:
            species_key: GBIF species key
            limit: Maximum number of occurrences to return

        Returns:
            Dictionary with occurrence data
        """
        try:
            params = {
                "taxonKey": species_key,
                "limit": limit
            }

            response = await self.http_client.get(GBIF_OCCURRENCE_ENDPOINT, params=params)
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GBIF occurrence API error: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"GBIF occurrence API request failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Species occurrence lookup failed: {str(e)}"
            )


# Create service instance
ecology_service = EcologyService()


# Convenience functions
async def lookup_species(request: SpeciesRequest) -> SpeciesResponse:
    """Look up species information from GBIF with caching."""
    return await ecology_service.lookup_species(request)


async def get_species_occurrences(species_key: int, limit: int = 100) -> Dict[str, Any]:
    """Get occurrence data for a species from GBIF."""
    return await ecology_service.get_species_occurrences(species_key, limit)


# API Routes
@router.post("/species", tags=["ecology"])
async def lookup_species_endpoint(request: SpeciesRequest):
    """
    Look up species information from GBIF.

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
            detail=f"Species lookup failed: {str(e)}"
        )


@router.get("/species/{species_key}/occurrences", tags=["ecology"])
async def get_species_occurrences_endpoint(species_key: int, limit: int = 100):
    """
    Get occurrence data for a species from GBIF.

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
            detail=f"Failed to get species occurrences: {str(e)}"
        )


@router.get("/cache/stats", tags=["ecology"])
async def get_cache_stats():
    """
    Get cache statistics for debugging/monitoring.

    Returns:
        Dictionary with cache statistics
    """
    return {
        "cache_size": len(species_cache),
        "cache_maxsize": species_cache.maxsize,
        "cache_ttl": species_cache.ttl
    }


@router.delete("/cache", tags=["ecology"])
async def clear_cache():
    """
    Clear the species cache.

    Returns:
        Confirmation message
    """
    species_cache.clear()
    return {"message": "Species cache cleared"}