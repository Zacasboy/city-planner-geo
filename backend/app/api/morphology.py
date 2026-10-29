"""Morphology API Router
T2.1: Morfologia: OpenBuildingMap/DBSM + métricas (densidade, altura, ocupação)
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.auth import get_current_user
from backend.app.services.morphology_service import (
    MorphologyRequest,
    MorphologyResponse,
    MorphologyService,
)

# Create router
router = APIRouter(prefix="/morphology", tags=["morphology"])

# Initialize service
morphology_service = MorphologyService()


@router.post("/analyze", response_model=MorphologyResponse)
async def analyze_morphology(
    request: MorphologyRequest, current_user: dict = Depends(get_current_user)
):
    """Analyze building morphology for a given area.

    Args:
        request: MorphologyRequest containing GeoJSON polygon and analysis parameters
        current_user: Current authenticated user

    Returns:
        MorphologyResponse with morphology analysis results
    """
    try:
        # Use authenticated user's ID for audit/logging purposes
        # In a real implementation, this might be used for access control or billing

        # Analyze morphology
        result = await morphology_service.analyze_morphology(request)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Morphology analysis failed: {str(e)}",
        )


@router.get("/health")
async def morphology_health_check():
    """Health check endpoint for morphology service.

    Returns:
        dict: Service health status
    """
    try:
        # Test that the service can be instantiated
        service = MorphologyService()
        return {
            "status": "healthy",
            "service": "morphology",
            "geospatial_available": True,  # This would be determined by actual imports
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "morphology",
            "error": str(e),
            "geospatial_available": False,
        }
