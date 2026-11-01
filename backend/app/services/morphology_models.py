"""Modelos de pedido e resposta da análise de morfologia urbana."""

from typing import Any

from pydantic import BaseModel, Field


class MorphologyRequest(BaseModel):
    """Pedido de análise de morfologia."""

    geojson: dict[str, Any] = Field(..., description="GeoJSON polygon defining the analysis area")
    data_source: str = Field(default="auto", description="Data source: 'opendata', 'dbsm', 'auto'")
    include_detailed_metrics: bool = Field(
        default=True, description="Include detailed morphological metrics"
    )


class MorphologyResponse(BaseModel):
    """Resultado da análise de morfologia."""

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
