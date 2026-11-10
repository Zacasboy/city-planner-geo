"""Tipologia morfológica por regras, calculada com as métricas já existentes.

É uma heurística própria, não uma classificação científica validada: os limiares abaixo são
escolhas documentadas (``docs/data_sources.md``), pensadas para áreas urbanas de Portugal.
As regras são avaliadas por ordem e a primeira que se cumprir decide o tipo.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

PERCENT = 100
MIN_BUILT_UP_SHARE = 0.03
COMPACT_BUILT_UP_SHARE = 0.35
MEDIUM_BUILT_UP_SHARE = 0.15
LARGE_FOOTPRINT_M2 = 600.0
INDUSTRIAL_SHARE_PERCENT = 30.0
HIGH_RISE_FLOORS = 7.0
MID_RISE_FLOORS = 4.0
MIN_HEIGHT_COVERAGE_PERCENT = 50.0
NO_BUILDINGS = "no_buildings"
DISCLAIMER = (
    "Rule-based typology (own thresholds, not a validated classification). It describes the "
    "drawn area, so parks, roads and empty land inside it lower the built-up share."
)


@dataclass(frozen=True)
class _Inputs:
    built_up_share: float
    mean_footprint_m2: float
    industrial_percent: float
    average_floors: float | None


@dataclass(frozen=True)
class _Rule:
    key: str
    label: str
    applies: Callable[[_Inputs], bool]
    reason: Callable[[_Inputs], str]


def _floors(inputs: _Inputs) -> float:
    return inputs.average_floors or 0.0


_RULES = (
    _Rule(
        "large_footprint_industrial",
        "Large-footprint / industrial",
        lambda i: (
            i.built_up_share >= MIN_BUILT_UP_SHARE
            and (
                i.mean_footprint_m2 >= LARGE_FOOTPRINT_M2
                or i.industrial_percent >= INDUSTRIAL_SHARE_PERCENT
            )
        ),
        lambda i: (
            f"mean footprint {i.mean_footprint_m2:.0f} m² (limit {LARGE_FOOTPRINT_M2:.0f}) or "
            f"{i.industrial_percent:.0f} % industrial (limit {INDUSTRIAL_SHARE_PERCENT:.0f})"
        ),
    ),
    _Rule(
        "high_rise_blocks",
        "High-rise blocks",
        lambda i: i.average_floors is not None and _floors(i) >= HIGH_RISE_FLOORS,
        lambda i: f"average {_floors(i):.1f} floors (limit {HIGH_RISE_FLOORS:.0f})",
    ),
    _Rule(
        "compact_urban_fabric",
        "Compact urban fabric",
        lambda i: i.built_up_share >= COMPACT_BUILT_UP_SHARE,
        lambda i: (
            f"built-up share {i.built_up_share * PERCENT:.0f} % "
            f"(limit {COMPACT_BUILT_UP_SHARE * PERCENT:.0f} %)"
        ),
    ),
    _Rule(
        "medium_density_midrise",
        "Medium-density mid-rise",
        lambda i: i.built_up_share >= MEDIUM_BUILT_UP_SHARE and _floors(i) >= MID_RISE_FLOORS,
        lambda i: (
            f"built-up share {i.built_up_share * PERCENT:.0f} % and "
            f"average {_floors(i):.1f} floors (limit {MID_RISE_FLOORS:.0f})"
        ),
    ),
    _Rule(
        "medium_density_low_rise",
        "Medium-density low-rise",
        lambda i: i.built_up_share >= MEDIUM_BUILT_UP_SHARE,
        lambda i: (
            f"built-up share {i.built_up_share * PERCENT:.0f} % "
            f"(limit {MEDIUM_BUILT_UP_SHARE * PERCENT:.0f} %)"
        ),
    ),
    _Rule(
        "low_density_suburban",
        "Low-density / suburban",
        lambda i: i.built_up_share >= MIN_BUILT_UP_SHARE,
        lambda i: (
            f"built-up share {i.built_up_share * PERCENT:.0f} % "
            f"(limit {MIN_BUILT_UP_SHARE * PERCENT:.0f} %)"
        ),
    ),
)


def classify_typology(
    building_count: int,
    area_m2: float,
    occupation: dict[str, float],
    type_metrics: dict[str, float],
    height: dict[str, float],
    height_coverage_percent: float,
) -> dict[str, Any]:
    """Atribui um tipo morfológico a uma área.

    As regras de altura só contam se pelo menos metade dos edifícios tiver altura; caso
    contrário ficam de fora e isso é dito na resposta.

    Returns:
        ``type``, ``label``, ``reasons``, ``used_height`` e ``disclaimer``.
    """
    if building_count == 0 or area_m2 <= 0:
        return {
            "type": NO_BUILDINGS,
            "label": "No buildings",
            "reasons": ["no buildings found in the area"],
            "used_height": False,
            "disclaimer": DISCLAIMER,
        }
    use_height = height_coverage_percent >= MIN_HEIGHT_COVERAGE_PERCENT
    share = occupation["ground_space_index"]
    inputs = _Inputs(
        built_up_share=share,
        mean_footprint_m2=share * area_m2 / building_count,
        industrial_percent=type_metrics.get("industrial_percentage", 0.0),
        average_floors=height["average_floors"] if use_height else None,
    )
    for rule in _RULES:
        if rule.applies(inputs):
            reasons = [rule.reason(inputs)]
            break
    else:
        rule = _Rule("sparse_or_rural", "Sparse / rural", lambda _: True, lambda _: "")
        reasons = [f"built-up share below {MIN_BUILT_UP_SHARE * PERCENT:.0f} %"]
    if not use_height:
        reasons.append(
            f"height rules skipped: fewer than {MIN_HEIGHT_COVERAGE_PERCENT:.0f} % of buildings "
            "have a height"
        )
    return {
        "type": rule.key,
        "label": rule.label,
        "reasons": reasons,
        "used_height": use_height,
        "disclaimer": DISCLAIMER,
    }
