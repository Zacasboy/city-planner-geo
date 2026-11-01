"""Geo validation and coordinate conversion service.

T1.3: Serviço Geo: POST /geo/validate, conversões 4326↔3763, testes
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError

# Create router
router = APIRouter()


class GeoService:
    """Service for geo validation and coordinate conversion."""

    def __init__(self) -> None:
        """Create the WGS84 and PT-TM06 coordinate systems and their transformers."""
        # Define coordinate reference systems
        self.wgs84 = CRS.from_epsg(4326)  # WGS 84 (latitude/longitude)
        self.ptm06 = CRS.from_epsg(3763)  # PT-TM06 / ETRS89 (Portugal TM06)

        # Create transformers
        self._to_tm06 = Transformer.from_crs(self.wgs84, self.ptm06, always_xy=True)
        self._to_wgs84 = Transformer.from_crs(self.ptm06, self.wgs84, always_xy=True)

    def validate_coordinates(self, lng: float, lat: float) -> bool:
        """Validate if coordinates are within reasonable bounds.

        Args:
            lng: Longitude coordinate
            lat: Latitude coordinate

        Returns:
            bool: True if coordinates are valid, False otherwise
        """
        # Basic validation for WGS84 coordinates
        if not (-180 <= lng <= 180):
            return False
        if not (-90 <= lat <= 90):
            return False

        # Additional validation for Portugal region (approximate)
        # Portugal mainland: roughly -9.5 to -6.2 longitude, 36.9 to 42.2 latitude
        # This is just a basic check - can be made more specific
        if not (-10.0 <= lng <= -6.0):
            return False
        if not (36.0 <= lat <= 43.0):
            return False

        return True

    def convert_coordinates(
        self, lng: float, lat: float, source_epsg: int, target_epsg: int
    ) -> tuple[float, float]:
        """Convert coordinates between different EPSG systems.

        Args:
            lng: Longitude/X coordinate
            lat: Latitude/Y coordinate
            source_epsg: Source EPSG code
            target_epsg: Target EPSG code

        Returns:
            Tuple of (converted_lng, converted_lat)

        Raises:
            HTTPException: If conversion fails
        """
        try:
            source_crs = CRS.from_epsg(source_epsg)
            target_crs = CRS.from_epsg(target_epsg)

            transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
            x, y = transformer.transform(lng, lat)

            return (x, y)

        except CRSError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid coordinate reference system: {str(e)}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Coordinate conversion failed: {str(e)}",
            ) from e

    def wgs84_to_tm06(self, lng: float, lat: float) -> tuple[float, float]:
        """Convert coordinates from WGS84 (EPSG:4326) to PT-TM06 (EPSG:3763).

        Args:
            lng: Longitude in WGS84
            lat: Latitude in WGS84

        Returns:
            Tuple of (easting, northing) in PT-TM06
        """
        try:
            easting, northing = self._to_tm06.transform(lng, lat)
            return (easting, northing)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"WGS84 to TM06 conversion failed: {str(e)}",
            ) from e

    def tm06_to_wgs84(self, easting: float, northing: float) -> tuple[float, float]:
        """Convert coordinates from PT-TM06 (EPSG:3763) to WGS84 (EPSG:4326).

        Args:
            easting: Easting in PT-TM06
            northing: Northing in PT-TM06

        Returns:
            Tuple of (longitude, latitude) in WGS84
        """
        try:
            lng, lat = self._to_wgs84.transform(easting, northing)
            return (lng, lat)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"TM06 to WGS84 conversion failed: {str(e)}",
            ) from e


# Create service instance
geo_service = GeoService()


def validate_geo_point(lng: float, lat: float) -> dict[str, Any]:
    """Validate a geographical point and return validation result.

    Args:
        lng: Longitude coordinate
        lat: Latitude coordinate

    Returns:
        Dict with validation result and metadata
    """
    is_valid = validate_coordinates(lng, lat)

    result = {
        "valid": is_valid,
        "coordinates": {"lng": lng, "lat": lat},
        "message": "Coordinates are valid" if is_valid else "Coordinates are invalid",
    }

    if is_valid:
        # Also provide converted coordinates
        try:
            easting, northing = wgs84_to_tm06(lng, lat)
            result["converted_coordinates"] = {
                "easting": easting,
                "northing": northing,
                "source_epsg": 4326,
                "target_epsg": 3763,
            }
        except Exception as e:
            result["conversion_error"] = str(e)

    return result


# Convenience functions for direct use
def validate_coordinates(lng: float, lat: float) -> bool:
    """Validate if coordinates are within reasonable bounds."""
    return geo_service.validate_coordinates(lng, lat)


def convert_coordinates(
    lng: float, lat: float, source_epsg: int, target_epsg: int
) -> tuple[float, float]:
    """Convert coordinates between different EPSG systems."""
    return geo_service.convert_coordinates(lng, lat, source_epsg, target_epsg)


def wgs84_to_tm06(lng: float, lat: float) -> tuple[float, float]:
    """Convert coordinates from WGS84 to PT-TM06."""
    return geo_service.wgs84_to_tm06(lng, lat)


def tm06_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert coordinates from PT-TM06 to WGS84."""
    return geo_service.tm06_to_wgs84(easting, northing)


# API Routes
@router.post("/validate", tags=["geo"])
async def validate_geo_point_endpoint(lng: float, lat: float) -> dict[str, Any]:
    """Validate a geographical point.

    Args:
        lng: Longitude coordinate
        lat: Latitude coordinate

    Returns:
        Validation result with coordinates and optional converted coordinates
    """
    return validate_geo_point(lng, lat)


@router.post("/convert", tags=["geo"])
async def convert_coordinates_endpoint(
    lng: float, lat: float, source_epsg: int, target_epsg: int
) -> dict[str, Any]:
    """Convert coordinates between different EPSG systems.

    Args:
        lng: Longitude/X coordinate
        lat: Latitude/Y coordinate
        source_epsg: Source EPSG code
        target_epsg: Target EPSG code

    Returns:
        Converted coordinates
    """
    try:
        converted_lng, converted_lat = convert_coordinates(lng, lat, source_epsg, target_epsg)
        return {
            "input": {"lng": lng, "lat": lat, "source_epsg": source_epsg},
            "output": {"lng": converted_lng, "lat": converted_lat, "target_epsg": target_epsg},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coordinate conversion failed: {str(e)}",
        ) from e


@router.get("/wgs84-to-tm06/{lng}/{lat}", tags=["geo"])
async def wgs84_to_tm06_endpoint(lng: float, lat: float) -> dict[str, Any]:
    """Convert coordinates from WGS84 (EPSG:4326) to PT-TM06 (EPSG:3763).

    Args:
        lng: Longitude in WGS84
        lat: Latitude in WGS84

    Returns:
        Converted coordinates in PT-TM06
    """
    try:
        easting, northing = wgs84_to_tm06(lng, lat)
        return {
            "input": {"lng": lng, "lat": lat, "source_epsg": 4326},
            "output": {"easting": easting, "northing": northing, "target_epsg": 3763},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"WGS84 to TM06 conversion failed: {str(e)}",
        ) from e


@router.get("/tm06-to-wgs84/{easting}/{northing}", tags=["geo"])
async def tm06_to_wgs84_endpoint(easting: float, northing: float) -> dict[str, Any]:
    """Convert coordinates from PT-TM06 (EPSG:3763) to WGS84 (EPSG:4326).

    Args:
        easting: Easting in PT-TM06
        northing: Northing in PT-TM06

    Returns:
        Converted coordinates in WGS84
    """
    try:
        lng, lat = tm06_to_wgs84(easting, northing)
        return {
            "input": {"easting": easting, "northing": northing, "source_epsg": 3763},
            "output": {"lng": lng, "lat": lat, "target_epsg": 4326},
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"TM06 to WGS84 conversion failed: {str(e)}",
        ) from e
