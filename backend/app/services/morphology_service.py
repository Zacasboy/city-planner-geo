"""Morphology Service - Building Morphology Analysis
T2.1: Morfologia: OpenBuildingMap/DBSM + métricas (densidade, altura, ocupação)
"""

import logging
import math
import random
from typing import Any

try:
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union

    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False
    # We'll fall back to simplified calculations or mock data
    Polygon = None  # Define as None for type checking when not available

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# Create router
router = APIRouter()

# Configure logging
logger = logging.getLogger(__name__)


class MorphologyRequest(BaseModel):
    """Request model for morphology analysis."""

    geojson: dict[str, Any] = Field(..., description="GeoJSON polygon defining the analysis area")
    data_source: str = Field(default="auto", description="Data source: 'opendata', 'dbsm', 'auto'")
    include_detailed_metrics: bool = Field(
        default=True, description="Include detailed morphological metrics"
    )


class MorphologyResponse(BaseModel):
    """Response model for morphology analysis results."""

    analysis_area_m2: float = Field(..., description="Analysis area in square meters")
    building_count: int = Field(..., description="Number of buildings in the area")
    density_metrics: dict[str, float] = Field(..., description="Density-related metrics")
    height_metrics: dict[str, float] = Field(..., description="Height-related metrics")
    height_percentiles: dict[str, float] = Field(..., description="Height distribution percentiles")
    occupation_metrics: dict[str, float] = Field(..., description="Occupation-related metrics")
    building_type_metrics: dict[str, float] = Field(
        ..., description="Building type distribution metrics"
    )
    data_source_used: str = Field(..., description="Actual data source used for analysis")
    analysis_method: str = Field(..., description="Method used for analysis")
    details: dict[str, Any] = Field(..., description="Additional analysis details")


class MorphologyService:
    """Service for building morphology analysis using OpenBuildingMap, DBSM, or fallback methods."""

    def __init__(self):
        # No external dependencies to initialize for now
        pass

    async def close(self):
        """Close the service (does nothing)."""
        pass

    async def analyze_morphology(self, request: MorphologyRequest) -> MorphologyResponse:
        """Analyze building morphology for a given area.

        Args:
            request: MorphologyRequest containing GeoJSON polygon and analysis parameters

        Returns:
            MorphologyResponse with morphology analysis results

        Raises:
            HTTPException: If analysis fails
        """
        try:
            # Extract parameters
            geojson = request.geojson
            data_source = request.data_source
            include_detailed = request.include_detailed_metrics

            # Validate GeoJSON
            if not self._is_valid_geojson(geojson):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid GeoJSON provided"
                )

            # Extract polygon from GeoJSON
            polygon = self._extract_polygon_from_geojson(geojson)
            if polygon is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not extract valid polygon from GeoJSON",
                )

            # Calculate analysis area
            analysis_area_m2 = polygon.area

            # For now, we'll use mock/simplified data since we don't have actual OpenBuildingMap/DBSM integration
            # In a real implementation, this would query actual building databases
            building_data = await self._get_building_data_for_area(polygon, data_source)

            # Calculate morphology metrics
            density_metrics = self._calculate_density_metrics(building_data, analysis_area_m2)
            height_metrics = self._calculate_height_metrics(building_data)
            height_percentiles = self._calculate_height_percentiles(building_data)
            occupation_metrics = self._calculate_occupation_metrics(building_data, analysis_area_m2)
            building_type_metrics = self._calculate_building_type_metrics(building_data)

            # Determine actual data source used
            data_source_used = await self._determine_actual_data_source(polygon, data_source)

            # Prepare details
            details = {
                "analysis_area_m2": analysis_area_m2,
                "building_count": len(building_data) if building_data else 0,
                "data_source_attempted": data_source,
                "include_detailed_metrics": include_detailed,
                "timestamp": self._get_timestamp(),
            }

            if include_detailed and building_data:
                details["building_samples"] = (
                    building_data[: min(5, len(building_data))] if building_data else []
                )

            return MorphologyResponse(
                analysis_area_m2=analysis_area_m2,
                building_count=len(building_data) if building_data else 0,
                density_metrics=density_metrics,
                height_metrics=height_metrics,
                height_percentiles=height_percentiles,
                occupation_metrics=occupation_metrics,
                building_type_metrics=building_type_metrics,
                data_source_used=data_source_used,
                analysis_method="Enhanced Mock Analysis with Realistic Building Distribution",
                details=details,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Morphology analysis failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Morphology analysis failed: {str(e)}",
            )

    def _is_valid_geojson(self, geojson: dict[str, Any]) -> bool:
        """Validate GeoJSON structure."""
        try:
            if not isinstance(geojson, dict):
                return False
            if geojson.get("type") not in ["Feature", "FeatureCollection"]:
                return False
            # Basic validation - in production, use a proper GeoJSON validator
            return True
        except Exception:
            return False

    def _extract_polygon_from_geojson(self, geojson: dict[str, Any]) -> Polygon | None:
        """Extract Polygon from GeoJSON."""
        if not GEOSPATIAL_AVAILABLE:
            return None

        try:
            if geojson.get("type") == "Feature":
                coords = geojson.get("geometry", {}).get("coordinates")
                if coords and len(coords) > 0 and coords[0] and len(coords[0]) > 0:
                    return Polygon(coords[0])  # Exterior ring of first polygon
            elif geojson.get("type") == "FeatureCollection":
                features = geojson.get("features", [])
                if features:
                    # Take the first feature's geometry
                    first_feature = features[0]
                    coords = first_feature.get("geometry", {}).get("coordinates")
                    if coords and len(coords) > 0 and coords[0] and len(coords[0]) > 0:
                        return Polygon(coords[0])  # Exterior ring of first polygon
            return None
        except Exception as e:
            logger.warning(f"Failed to extract polygon from GeoJSON: {e}")
            return None

    async def _get_building_data_for_area(
        self, polygon: Polygon, data_source: str
    ) -> list[dict[str, Any]]:
        """Get building data for the analysis area from the specified data source.
        For now, returns mock data since actual OpenBuildingMap/DBSM integration is pending.
        """
        try:
            # In a real implementation, this would:
            # 1. Query OpenBuildingMap API or DBSM database for buildings intersecting the polygon
            # 2. Return building footprints with height attributes
            # 3. Process the data into a standardized format

            # For now, generate mock building data based on the polygon area
            if not GEOSPATIAL_AVAILABLE:
                logger.warning("Geospatial libraries not available, returning empty building data")
                return []

            # Create a mock building grid within the polygon bounds
            minx, miny, maxx, maxy = polygon.bounds
            width = maxx - minx
            height = maxy - miny

            # Generate a grid of mock buildings
            building_data = []
            cols = max(1, int(width / 20))  # Buildings every ~20m
            rows = max(1, int(height / 20))  # Buildings every ~20m

            if cols > 0 and rows > 0:
                cell_width = width / cols
                cell_height = height / rows

                for i in range(cols):
                    for j in range(rows):
                        # Calculate building position
                        building_x = minx + (i * cell_width) + (cell_width / 2)
                        building_y = miny + (j * cell_height) + (cell_height / 2)
                        building_point = Point(building_x, building_y)

                        # Check if point is within polygon
                        if polygon.contains(building_point):
                            # Generate mock building properties
                            building_width = random.uniform(8, 20)  # 8-20m width
                            building_length = random.uniform(8, 25)  # 8-25m length
                            building_height = random.uniform(5, 25)  # 5-25m height
                            building_floors = max(1, int(building_height / 3))  # ~3m per floor

                            building_data.append(
                                {
                                    "id": f"building_{i}_{j}",
                                    "footprint": Point(
                                        building_x, building_y
                                    ),  # Simplified as point
                                    "area_m2": building_width * building_length,
                                    "height_m": building_height,
                                    "floors": building_floors,
                                    "footprint_m2": building_width * building_length,
                                }
                            )

            return building_data

        except Exception as e:
            logger.error(f"Failed to get building data: {e}")
            return []

    def _calculate_density_metrics(
        self, building_data: list[dict[str, Any]], analysis_area_m2: float
    ) -> dict[str, float]:
        """Calculate density-related metrics."""
        if not building_data or analysis_area_m2 <= 0:
            return {
                "building_density_per_km2": 0.0,
                "floor_area_ratio": 0.0,
                "ground_space_index": 0.0,
            }

        try:
            total_building_area = sum(b.get("area_m2", 0) for b in building_data)
            total_footprint_area = sum(b.get("footprint_m2", 0) for b in building_data)
            building_count = len(building_data)

            # Building density (buildings per km2)
            building_density_per_km2 = (
                (building_count / analysis_area_m2) * 1_000_000 if analysis_area_m2 > 0 else 0
            )

            # Floor Area Ratio (FAR) = total floor area / land area
            # Assuming single floor for simplicity in mock data
            floor_area_ratio = total_building_area / analysis_area_m2 if analysis_area_m2 > 0 else 0

            # Ground Space Index (GSI) = total footprint area / land area
            ground_space_index = (
                total_footprint_area / analysis_area_m2 if analysis_area_m2 > 0 else 0
            )

            return {
                "building_density_per_km2": round(building_density_per_km2, 2),
                "floor_area_ratio": round(floor_area_ratio, 3),
                "ground_space_index": round(ground_space_index, 3),
            }
        except Exception as e:
            logger.warning(f"Error calculating density metrics: {e}")
            return {
                "building_density_per_km2": 0.0,
                "floor_area_ratio": 0.0,
                "ground_space_index": 0.0,
            }

    def _calculate_height_metrics(self, building_data: list[dict[str, Any]]) -> dict[str, float]:
        """Calculate height-related metrics."""
        if not building_data:
            return {
                "average_height_m": 0.0,
                "max_height_m": 0.0,
                "min_height_m": 0.0,
                "height_std_dev": 0.0,
                "average_floors": 0.0,
            }

        try:
            heights = [b.get("height_m", 0) for b in building_data]
            floors = [b.get("floors", 0) for b in building_data]

            if not heights:
                return {
                    "average_height_m": 0.0,
                    "max_height_m": 0.0,
                    "min_height_m": 0.0,
                    "height_std_dev": 0.0,
                    "average_floors": 0.0,
                }

            avg_height = sum(heights) / len(heights)
            max_height = max(heights)
            min_height = min(heights)
            # Calculate standard deviation without numpy
            if len(heights) > 1:
                avg_height = sum(heights) / len(heights)
                variance = sum((h - avg_height) ** 2 for h in heights) / len(heights)
                height_std_dev = math.sqrt(variance) if variance >= 0 else 0
            elif len(heights) == 1:
                height_std_dev = 0.0
            else:
                height_std_dev = 0.0
            avg_floors = sum(floors) / len(floors) if floors else 0

            return {
                "average_height_m": round(avg_height, 2),
                "max_height_m": round(max_height, 2),
                "min_height_m": round(min_height, 2),
                "height_std_dev": round(height_std_dev, 2),
                "average_floors": round(avg_floors, 2),
            }
        except Exception as e:
            logger.warning(f"Error calculating height metrics: {e}")
            return {
                "average_height_m": 0.0,
                "max_height_m": 0.0,
                "min_height_m": 0.0,
                "height_std_dev": 0.0,
                "average_floors": 0.0,
            }

    def _calculate_height_percentiles(
        self, building_data: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Calculate height distribution percentiles."""
        if not building_data:
            return {
                "height_25th_percentile": 0.0,
                "height_50th_percentile": 0.0,
                "height_75th_percentile": 0.0,
                "height_90th_percentile": 0.0,
            }

        try:
            heights = [b.get("height_m", 0) for b in building_data]
            if not heights:
                return {
                    "height_25th_percentile": 0.0,
                    "height_50th_percentile": 0.0,
                    "height_75th_percentile": 0.0,
                    "height_90th_percentile": 0.0,
                }

            # Sort heights for percentile calculation
            sorted_heights = sorted(heights)
            n = len(sorted_heights)

            # Calculate percentiles using linear interpolation method
            def get_percentile(p):
                """Get percentile value using linear interpolation."""
                if n == 0:
                    return 0.0
                if n == 1:
                    return sorted_heights[0]

                # Calculate index (0-based)
                index = (p / 100) * (n - 1)
                lower = int(index)
                upper = min(lower + 1, n - 1)
                weight = index - lower

                if lower == upper:
                    return sorted_heights[lower]
                else:
                    return sorted_heights[lower] * (1 - weight) + sorted_heights[upper] * weight

            return {
                "height_25th_percentile": round(get_percentile(25), 2),
                "height_50th_percentile": round(get_percentile(50), 2),
                "height_75th_percentile": round(get_percentile(75), 2),
                "height_90th_percentile": round(get_percentile(90), 2),
            }
        except Exception as e:
            logger.warning(f"Error calculating height percentiles: {e}")
            return {
                "height_25th_percentile": 0.0,
                "height_50th_percentile": 0.0,
                "height_75th_percentile": 0.0,
                "height_90th_percentile": 0.0,
            }

    def _calculate_occupation_metrics(
        self, building_data: list[dict[str, Any]], analysis_area_m2: float
    ) -> dict[str, float]:
        """Calculate occupation-related metrics."""
        if not building_data or analysis_area_m2 <= 0:
            return {
                "ground_space_index": 0.0,
                "lot_coverage_ratio": 0.0,
                "built_up_percentage": 0.0,
            }

        try:
            total_footprint_area = sum(b.get("footprint_m2", 0) for b in building_data)

            # Ground Space Index (GSI) - already calculated in density metrics
            gsi = total_footprint_area / analysis_area_m2 if analysis_area_m2 > 0 else 0

            # Lot Coverage Ratio (same as GSI for single layer)
            lot_coverage_ratio = gsi

            # Built-up Percentage
            built_up_percentage = gsi * 100

            return {
                "ground_space_index": round(gsi, 3),
                "lot_coverage_ratio": round(lot_coverage_ratio, 3),
                "built_up_percentage": round(built_up_percentage, 2),
            }
        except Exception as e:
            logger.warning(f"Error calculating occupation metrics: {e}")
            return {
                "ground_space_index": 0.0,
                "lot_coverage_ratio": 0.0,
                "built_up_percentage": 0.0,
            }

    def _calculate_building_type_metrics(
        self, building_data: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Calculate building type distribution metrics."""
        if not building_data:
            return {
                "residential_percentage": 0.0,
                "commercial_percentage": 0.0,
                "industrial_percentage": 0.0,
            }

        try:
            # Count buildings by type
            type_counts = {"residential": 0, "commercial": 0, "industrial": 0}
            for building in building_data:
                btype = building.get("building_type", "residential")  # Default to residential
                if btype in type_counts:
                    type_counts[btype] += 1

            total_buildings = len(building_data)
            if total_buildings > 0:
                return {
                    "residential_percentage": round(
                        (type_counts["residential"] / total_buildings) * 100, 2
                    ),
                    "commercial_percentage": round(
                        (type_counts["commercial"] / total_buildings) * 100, 2
                    ),
                    "industrial_percentage": round(
                        (type_counts["industrial"] / total_buildings) * 100, 2
                    ),
                }
            else:
                return {
                    "residential_percentage": 0.0,
                    "commercial_percentage": 0.0,
                    "industrial_percentage": 0.0,
                }
        except Exception as e:
            logger.warning(f"Error calculating building type metrics: {e}")
            return {
                "residential_percentage": 0.0,
                "commercial_percentage": 0.0,
                "industrial_percentage": 0.0,
            }

    async def _determine_actual_data_source(self, polygon: Polygon, requested_source: str) -> str:
        """Determine which data source was actually used."""
        if requested_source != "auto":
            return requested_source

        # In auto mode, we would try different sources in order of preference
        # For now, we'll return "mock" since we're using sample data
        return "mock/sample"

    def _get_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime

        return datetime.now().isoformat()
