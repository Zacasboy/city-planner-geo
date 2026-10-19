"""
Forest Service - InterGeoPT Integration
T1.5: Serviço Florestal (InterGeoPT) — POST /forest/overlap
"""
import logging
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.app.config import settings

# Create router
router = APIRouter()

# Configure logging
logger = logging.getLogger(__name__)


class OverlapRequest(BaseModel):
    """Request model for forest overlap check."""
    geojson: dict
    # Additional fields can be added as needed


class OverlapResponse(BaseModel):
    """Response model for forest overlap result."""
    overlap_area_km2: float
    percentage_covered: float
    details: dict


class ForestService:
    """Service for InterGeoPT forest data integration."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self.http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = http_client is None
        self.api_base = self.settings.INTERGEOPT_API_BASE.rstrip("/")

    async def close(self):
        """Close the HTTP client if we own it."""
        if self._owns_client:
            await self.http_client.aclose()

    async def check_overlap(self, request: OverlapRequest) -> OverlapResponse:
        """
        Check overlap with forest areas using InterGeoPT API.

        Args:
            request: OverlapRequest containing geojson

        Returns:
            OverlapResponse with overlap area and coverage percentage

        Raises:
            HTTPException: If InterGeoPT API request fails
        """
        if not self.api_base:
            logger.error("InterGeoPT API base URL not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="InterGeoPT API not configured"
            )

        url = f"{self.api_base}/forest/overlap"
        logger.debug(f"Calling InterGeoPT API: {url}")

        try:
            # Send geojson as JSON payload
            response = await self.http_client.post(
                url,
                json=request.geojson,
                timeout=30.0
            )
            response.raise_for_status()

            # Parse response
            data = response.json()
            overlap_area = data.get("overlap_area_km2", 0.0)
            percentage = data.get("percentage_covered", 0.0)
            details = data.get("details", {})

            logger.info(
                f"Forest overlap check completed: {overlap_area} km², {percentage}% covered"
            )

            return OverlapResponse(
                overlap_area_km2=overlap_area,
                percentage_covered=percentage,
                details=details
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"InterGeoPT API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"InterGeoPT API error: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"InterGeoPT API request failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"InterGeoPT API request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Forest overlap check failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Forest overlap check failed: {str(e)}"
            )


# Create service instance
forest_service = ForestService()


# Convenience functions
async def check_overlap(request: OverlapRequest) -> OverlapResponse:
    """Check overlap with forest areas."""
    return await forest_service.check_overlap(request)


# API Routes
@router.post("/overlap", tags=["forest"])
async def forest_overlap_endpoint(request: OverlapRequest):
    """
    Check overlap with forest areas using InterGeoPT.

    Args:
        request: OverlapRequest containing geojson

    Returns:
        Overlap area and coverage percentage
    """
    try:
        return await check_overlap(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forest overlap check failed: {str(e)}"
        )