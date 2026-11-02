"""Testes do motor estrutural contra soluções analíticas fechadas (Rules: engenharia)."""

import math

import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.services.structural_fem import GRAVITY_MS2, solve_beam
from backend.app.services.structural_models import BeamRequest
from backend.app.services.structural_service import StructuralService

E = 210e9
B, H, L = 0.2, 0.4, 6.0
INERTIA = B * H**3 / 12
AREA = B * H
EI = E * INERTIA
REL = 1e-5
PIN_ROLLER = [{"position": 0.0, "type": "pin"}, {"position": L, "type": "roller"}]


def _beam(**overrides: object) -> BeamRequest:
    data: dict[str, object] = {
        "length": L,
        "width": B,
        "height": H,
        "youngs_modulus": E,
        "density": 7850,
        "yield_stress": 275e6,
        "supports": PIN_ROLLER,
        "include_self_weight": False,
        "include_shear_deformation": False,
    }
    data.update(overrides)
    return BeamRequest.model_validate(data)


def test_simply_supported_midspan_point_load() -> None:
    load = 20_000.0
    r = solve_beam(_beam(point_loads=[{"position": L / 2, "magnitude": load}]))
    assert r.max_deflection_m == pytest.approx(load * L**3 / (48 * EI), rel=REL)
    assert r.max_moment_nm == pytest.approx(load * L / 4, rel=REL)
    assert r.max_shear_n == pytest.approx(load / 2, rel=REL)
    assert r.reactions_n[0.0] == pytest.approx(load / 2, rel=REL)
    assert r.reactions_n[L] == pytest.approx(load / 2, rel=REL)


def test_simply_supported_off_centre_point_load() -> None:
    load, a = 30_000.0, 2.0
    b = L - a
    r = solve_beam(_beam(point_loads=[{"position": a, "magnitude": load}]))

    x = np.linspace(0, L, 200_001)
    left = load * b * x * (L**2 - b**2 - x**2) / (6 * EI * L)
    right = load * a * (L - x) * (2 * L * x - x**2 - a**2) / (6 * EI * L)
    reference_deflection = np.where(x <= a, left, right).max()

    assert r.max_deflection_m == pytest.approx(reference_deflection, rel=1e-3)
    assert r.max_moment_nm == pytest.approx(load * a * b / L, rel=REL)
    assert r.reactions_n[0.0] == pytest.approx(load * b / L, rel=REL)
    assert r.reactions_n[L] == pytest.approx(load * a / L, rel=REL)


def test_simply_supported_uniform_load() -> None:
    w = 12_000.0
    r = solve_beam(_beam(uniform_load=w))
    assert r.max_deflection_m == pytest.approx(5 * w * L**4 / (384 * EI), rel=REL)
    assert r.max_moment_nm == pytest.approx(w * L**2 / 8, rel=REL)
    assert r.max_shear_n == pytest.approx(w * L / 2, rel=REL)


def test_self_weight_equals_the_equivalent_uniform_load() -> None:
    w = 7850 * GRAVITY_MS2 * AREA
    with_self_weight = solve_beam(_beam(include_self_weight=True))
    equivalent = solve_beam(_beam(uniform_load=w))
    assert with_self_weight.self_weight_n_per_m == pytest.approx(w)
    assert with_self_weight.max_deflection_m == pytest.approx(equivalent.max_deflection_m)
    assert with_self_weight.max_moment_nm == pytest.approx(w * L**2 / 8, rel=REL)


def test_cantilever_tip_load() -> None:
    load = 15_000.0
    r = solve_beam(
        _beam(
            supports=[{"position": 0.0, "type": "fixed"}],
            point_loads=[{"position": L, "magnitude": load}],
        )
    )
    assert r.max_deflection_m == pytest.approx(load * L**3 / (3 * EI), rel=REL)
    assert r.max_moment_nm == pytest.approx(load * L, rel=REL)
    assert r.reactions_n[0.0] == pytest.approx(load, rel=REL)


def test_overhanging_beam_uniform_load_matches_statics() -> None:
    w, span = 10_000.0, 4.0
    r = solve_beam(
        _beam(
            supports=[{"position": 0.0, "type": "pin"}, {"position": span, "type": "roller"}],
            uniform_load=w,
        )
    )
    reaction_right = w * L**2 / (2 * span)
    assert r.reactions_n[span] == pytest.approx(reaction_right, rel=REL)
    assert r.reactions_n[0.0] == pytest.approx(w * L - reaction_right, rel=REL)
    overhang = L - span
    assert r.max_moment_nm == pytest.approx(w * overhang**2 / 2, rel=REL)


def test_two_symmetric_point_loads_superpose() -> None:
    load, a = 10_000.0, 1.5
    r = solve_beam(
        _beam(
            point_loads=[
                {"position": a, "magnitude": load},
                {"position": L - a, "magnitude": load},
            ]
        )
    )
    assert r.max_moment_nm == pytest.approx(load * a, rel=REL)
    assert r.max_deflection_m == pytest.approx(
        load * a * (3 * L**2 - 4 * a**2) / (24 * EI), rel=REL
    )


def test_results_scale_linearly_with_the_load() -> None:
    one = solve_beam(_beam(point_loads=[{"position": 2.0, "magnitude": 1_000.0}]))
    two = solve_beam(_beam(point_loads=[{"position": 2.0, "magnitude": 2_000.0}]))
    assert two.max_deflection_m == pytest.approx(2 * one.max_deflection_m, rel=REL)
    assert two.max_moment_nm == pytest.approx(2 * one.max_moment_nm, rel=REL)


@pytest.mark.asyncio
async def test_service_reports_stress_and_utilisation() -> None:
    load = 20_000.0
    response = await StructuralService().analyze_beam(
        _beam(point_loads=[{"position": L / 2, "magnitude": load}])
    )
    stress = (load * L / 4) * (H / 2) / INERTIA
    assert response.max_stress == pytest.approx(stress, rel=REL)
    assert response.utilization_ratio == pytest.approx(stress / 275e6, rel=REL)
    assert response.details["analysis_method"].startswith("FEM")
    assert "does not replace" in response.details["note"]
    assert math.isclose(response.details["total_load_n"], load)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"point_loads": [{"position": L + 1, "magnitude": 1.0}]}, "outside the beam"),
        ({"supports": [{"position": 0.0, "type": "pin"}]}, "unstable"),
        (
            {"supports": [{"position": 0.0, "type": "roller"}, {"position": L, "type": "roller"}]},
            "unstable",
        ),
        (
            {"supports": [{"position": 1.0, "type": "pin"}, {"position": 1.0, "type": "roller"}]},
            "same position",
        ),
        ({"supports": []}, "at least 1"),
        ({"supports": [{"position": 0.0, "type": "spring"}]}, "Input should be"),
    ],
)
def test_invalid_beams_are_rejected(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _beam(**overrides)


SHEAR_MODULUS = E / (2 * 1.3)
SHEAR_AREA = 10 * 1.3 / (12 + 11 * 0.3) * AREA  # Cowper, retângulo, nu = 0.3


def test_timoshenko_midspan_point_load_adds_the_shear_term() -> None:
    load = 20_000.0
    r = solve_beam(
        _beam(include_shear_deformation=True, point_loads=[{"position": L / 2, "magnitude": load}])
    )
    expected = load * L**3 / (48 * EI) + load * L / (4 * SHEAR_MODULUS * SHEAR_AREA)
    assert r.max_deflection_m == pytest.approx(expected, rel=1e-6)
    assert r.max_moment_nm == pytest.approx(load * L / 4, rel=REL)


def test_timoshenko_cantilever_uniform_load_adds_the_shear_term() -> None:
    w = 9_000.0
    r = solve_beam(
        _beam(
            include_shear_deformation=True,
            uniform_load=w,
            supports=[{"position": 0.0, "type": "fixed"}],
        )
    )
    expected = w * L**4 / (8 * EI) + w * L**2 / (2 * SHEAR_MODULUS * SHEAR_AREA)
    assert r.max_deflection_m == pytest.approx(expected, rel=1e-4)
    assert r.max_moment_nm == pytest.approx(w * L**2 / 2, rel=REL)


def test_shear_deformation_matters_more_for_deep_short_beams() -> None:
    def ratio(length: float) -> float:
        loads = [{"position": length / 2, "magnitude": 10_000.0}]
        supports = [{"position": 0.0, "type": "pin"}, {"position": length, "type": "roller"}]
        kwargs = {"length": length, "point_loads": loads, "supports": supports}
        shear = solve_beam(_beam(include_shear_deformation=True, **kwargs))
        bending = solve_beam(_beam(**kwargs))
        return shear.max_deflection_m / bending.max_deflection_m

    assert ratio(1.0) > 1.2 > ratio(12.0) > 1.0


def test_explicit_section_drives_stiffness_stress_and_shear_area() -> None:
    area, inertia, depth = 0.005, 8e-5, 0.3
    shear_area = 0.002
    request = BeamRequest.model_validate(
        {
            "length": 2.0,
            "section": {
                "area": area,
                "moment_of_inertia": inertia,
                "height": depth,
                "shear_area": shear_area,
            },
            "youngs_modulus": E,
            "density": 7850,
            "yield_stress": 275e6,
            "include_self_weight": False,
            "supports": PIN_ROLLER[:1] + [{"position": 2.0, "type": "roller"}],
            "point_loads": [{"position": 1.0, "magnitude": 50_000.0}],
        }
    )
    r = solve_beam(request)
    expected = 50_000.0 * 8 / (48 * E * inertia) + 50_000.0 * 2 / (4 * SHEAR_MODULUS * shear_area)
    assert r.max_deflection_m == pytest.approx(expected, rel=1e-6)
    assert request.depth == depth
    assert request.shear_area == shear_area


def test_section_without_shear_area_uses_half_of_the_area() -> None:
    request = _beam(
        width=None,
        height=None,
        section={"area": 0.01, "moment_of_inertia": 1e-4, "height": 0.2},
    )
    assert request.shear_area == pytest.approx(0.005)


@pytest.mark.parametrize(
    "overrides",
    [
        {"width": None},
        {"section": {"area": 0.01, "moment_of_inertia": 1e-4, "height": 0.2}},
    ],
)
def test_section_must_be_rectangle_or_explicit(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="either width and height, or a section"):
        _beam(**overrides)


def test_moment_peak_between_nodes_is_found_on_a_coarse_mesh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.app.services.structural_fem.MESH_DIVISIONS", 3)
    w = 12_000.0
    r = solve_beam(_beam(uniform_load=w))
    assert r.max_moment_nm == pytest.approx(w * L**2 / 8, rel=REL)
