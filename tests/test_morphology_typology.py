"""Testes da tipologia morfológica por regras."""

import pytest

from backend.app.services.morphology_typology import classify_typology

AREA_M2 = 100_000.0


def _classify(
    share: float,
    count: int = 100,
    floors: float = 3.0,
    coverage: float = 100.0,
    industrial: float = 0.0,
) -> dict:
    return classify_typology(
        count,
        AREA_M2,
        {"ground_space_index": share},
        {"industrial_percentage": industrial},
        {"average_floors": floors},
        coverage,
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"share": 0.01}, "sparse_or_rural"),
        ({"share": 0.05}, "low_density_suburban"),
        ({"share": 0.20, "floors": 2.0}, "medium_density_low_rise"),
        ({"share": 0.20, "floors": 5.0}, "medium_density_midrise"),
        ({"share": 0.40, "floors": 3.0}, "compact_urban_fabric"),
        ({"share": 0.40, "floors": 8.0}, "high_rise_blocks"),
        ({"share": 0.20, "count": 20}, "large_footprint_industrial"),
        ({"share": 0.10, "industrial": 40.0}, "large_footprint_industrial"),
    ],
)
def test_rules_pick_the_expected_type(kwargs: dict, expected: str) -> None:
    result = _classify(**kwargs)
    assert result["type"] == expected
    assert result["used_height"] is True
    assert result["reasons"]
    assert "not a validated classification" in result["disclaimer"]


def test_height_rules_are_skipped_with_low_height_coverage() -> None:
    result = _classify(share=0.40, floors=9.0, coverage=30.0)
    assert result["type"] == "compact_urban_fabric"
    assert result["used_height"] is False
    assert any("height rules skipped" in reason for reason in result["reasons"])


def test_empty_area_has_no_buildings() -> None:
    result = classify_typology(0, AREA_M2, {"ground_space_index": 0.0}, {}, {}, 0.0)
    assert result["type"] == "no_buildings"
    assert result["used_height"] is False


def test_large_footprints_need_a_minimum_built_up_share() -> None:
    assert _classify(share=0.01, count=5)["type"] == "sparse_or_rural"
