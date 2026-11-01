"""Métricas de morfologia urbana calculadas a partir de uma lista de edifícios."""

import statistics
from typing import Any

Building = dict[str, Any]

M2_PER_KM2 = 1_000_000
PERCENTILES = (25, 50, 75, 90)
BUILDING_TYPES = ("residential", "commercial", "industrial")
DEFAULT_BUILDING_TYPE = "residential"


def _sum(buildings: list[Building], key: str) -> float:
    return float(sum(b.get(key, 0) for b in buildings))


def density_metrics(buildings: list[Building], area_m2: float) -> dict[str, float]:
    """Densidade de edifícios, índice de utilização (FAR) e índice de implantação (GSI)."""
    if not buildings or area_m2 <= 0:
        return dict.fromkeys(
            ("building_density_per_km2", "floor_area_ratio", "ground_space_index"), 0.0
        )
    return {
        "building_density_per_km2": round(len(buildings) / area_m2 * M2_PER_KM2, 2),
        "floor_area_ratio": round(_sum(buildings, "area_m2") / area_m2, 3),
        "ground_space_index": round(_sum(buildings, "footprint_m2") / area_m2, 3),
    }


def height_metrics(buildings: list[Building]) -> dict[str, float]:
    """Altura média, máxima, mínima, desvio-padrão (populacional) e pisos médios."""
    if not buildings:
        return dict.fromkeys(
            (
                "average_height_m",
                "max_height_m",
                "min_height_m",
                "height_std_dev",
                "average_floors",
            ),
            0.0,
        )
    heights = [b.get("height_m", 0) for b in buildings]
    floors = [b.get("floors", 0) for b in buildings]
    return {
        "average_height_m": round(statistics.fmean(heights), 2),
        "max_height_m": round(max(heights), 2),
        "min_height_m": round(min(heights), 2),
        "height_std_dev": round(statistics.pstdev(heights), 2),
        "average_floors": round(statistics.fmean(floors), 2),
    }


def _percentile(sorted_values: list[float], percent: float) -> float:
    """Percentil por interpolação linear (igual ao método por omissão do numpy)."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = percent / 100 * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def height_percentiles(buildings: list[Building]) -> dict[str, float]:
    """Percentis 25, 50, 75 e 90 da altura dos edifícios."""
    names = [f"height_{p}th_percentile" for p in PERCENTILES]
    if not buildings:
        return dict.fromkeys(names, 0.0)
    heights = sorted(b.get("height_m", 0) for b in buildings)
    return {
        name: round(_percentile(heights, percent), 2)
        for name, percent in zip(names, PERCENTILES, strict=True)
    }


def occupation_metrics(buildings: list[Building], area_m2: float) -> dict[str, float]:
    """Índice de implantação, taxa de ocupação do lote e percentagem edificada."""
    if not buildings or area_m2 <= 0:
        return dict.fromkeys(
            ("ground_space_index", "lot_coverage_ratio", "built_up_percentage"), 0.0
        )
    gsi = _sum(buildings, "footprint_m2") / area_m2
    return {
        "ground_space_index": round(gsi, 3),
        "lot_coverage_ratio": round(gsi, 3),
        "built_up_percentage": round(gsi * 100, 2),
    }


def building_type_metrics(buildings: list[Building]) -> dict[str, float]:
    """Percentagem de edifícios residenciais, comerciais e industriais."""
    names = [f"{t}_percentage" for t in BUILDING_TYPES]
    if not buildings:
        return dict.fromkeys(names, 0.0)
    counts = dict.fromkeys(BUILDING_TYPES, 0)
    for building in buildings:
        building_type = building.get("building_type", DEFAULT_BUILDING_TYPE)
        if building_type in counts:
            counts[building_type] += 1
    return {f"{t}_percentage": round(counts[t] / len(buildings) * 100, 2) for t in BUILDING_TYPES}
