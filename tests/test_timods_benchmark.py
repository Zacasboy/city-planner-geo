"""Testes do modelo do benchmark TimoDS contra soluções analíticas (molas muito rígidas)."""

import csv
from pathlib import Path

import numpy as np
import pytest

from backend.app.services.timods_benchmark import (
    LOAD_CASES,
    STATIONS,
    BenchmarkBeam,
    normalised_error,
    solve_benchmark_beam,
    solve_timoshenko_beam,
)
from backend.app.services.timods_data import (
    InstanceResult,
    run_benchmark,
    slenderness,
    summarise,
)

E = 210e6  # kN/m²
G = E / 2.6
L, A, IY, IZ, J = 4.2, 0.02, 1.0e-3, 2.0e-4, 1.0e-5
RIGID = 1e12
ENDS = "AB"
KEYS = ("k_x", "k_y", "k_z", "c_x", "c_y", "c_z")
MID = STATIONS.index(0.5)


def _springs(**stiffness: float) -> dict[str, float]:
    return {f"{k}_{e}": stiffness.get(k, 0.0) for k in KEYS for e in ENDS}


def _beam(load_case: int, a: float, springs: dict[str, float]) -> BenchmarkBeam:
    return BenchmarkBeam(L, A, IY, IZ, J, springs, load_case, a)


SIMPLY_SUPPORTED = _springs(k_x=RIGID, k_y=RIGID, k_z=RIGID, c_x=RIGID)


def test_strong_axis_force_on_simply_supported_beam() -> None:
    r = solve_benchmark_beam(_beam(3, 0.5, SIMPLY_SUPPORTED))
    assert r["uz"][MID] == pytest.approx(L**3 / (48 * E * IY), rel=1e-6)


def test_weak_axis_force_uses_the_other_inertia() -> None:
    r = solve_benchmark_beam(_beam(2, 0.5, SIMPLY_SUPPORTED))
    assert r["uy"][MID] == pytest.approx(L**3 / (48 * E * IZ), rel=1e-6)


def test_unit_moment_at_midspan_rotates_the_ends() -> None:
    r = solve_benchmark_beam(_beam(5, 0.5, SIMPLY_SUPPORTED))
    expected = L / (24 * E * IY)
    assert abs(r["ry"][0]) == pytest.approx(expected, rel=1e-6)
    assert abs(r["ry"][-1]) == pytest.approx(expected, rel=1e-6)
    assert r["uz"][MID] == pytest.approx(0.0, abs=1e-12)


def test_axial_force_on_bar_fixed_at_one_end() -> None:
    fixed_a = {f"{k}_A": RIGID for k in KEYS} | {f"{k}_B": 0.0 for k in KEYS}
    r = solve_benchmark_beam(_beam(1, 0.5, fixed_a))
    assert r["ux"][-1] == pytest.approx(0.5 * L / (E * A), rel=1e-6)


def test_torque_on_shaft_fixed_at_one_end() -> None:
    fixed_a = {f"{k}_A": RIGID for k in KEYS} | {f"{k}_B": 0.0 for k in KEYS}
    r = solve_benchmark_beam(_beam(4, 0.5, fixed_a))
    assert r["rx"][-1] == pytest.approx(0.5 * L / (G * J), rel=1e-6)


def test_cantilever_tip_force() -> None:
    fixed_a = {f"{k}_A": RIGID for k in KEYS} | {f"{k}_B": 0.0 for k in KEYS}
    r = solve_benchmark_beam(_beam(3, 1.0, fixed_a))
    assert r["uz"][-1] == pytest.approx(L**3 / (3 * E * IY), rel=1e-6)


def test_load_between_stations_is_supported() -> None:
    r = solve_benchmark_beam(_beam(3, 0.37, SIMPLY_SUPPORTED))
    a, x = 0.37 * L, 0.5 * L
    expected = a * (L - x) * (2 * L * x - x**2 - a**2) / (6 * E * IY * L)
    assert r["uz"][MID] == pytest.approx(expected, rel=1e-6)


SHEAR_AREA = 0.005
INFINITE_SHEAR_AREA = float("inf")


def _timoshenko_beam(
    case: int, a: float, springs: dict[str, float], shear_area: float
) -> BenchmarkBeam:
    return BenchmarkBeam(L, A, IY, IZ, J, springs, case, a, shear_area, shear_area)


def test_timoshenko_adds_the_shear_term_to_a_simply_supported_beam() -> None:
    r = solve_timoshenko_beam(_timoshenko_beam(3, 0.5, SIMPLY_SUPPORTED, SHEAR_AREA))
    expected = L**3 / (48 * E * IY) + L / (4 * G * SHEAR_AREA)
    assert r["uz"][MID] == pytest.approx(expected, rel=1e-6)


def test_timoshenko_adds_the_shear_term_to_a_cantilever() -> None:
    fixed_a = {f"{k}_A": RIGID for k in KEYS} | {f"{k}_B": 0.0 for k in KEYS}
    r = solve_timoshenko_beam(_timoshenko_beam(2, 1.0, fixed_a, SHEAR_AREA))
    assert r["uy"][-1] == pytest.approx(L**3 / (3 * E * IZ) + L / (G * SHEAR_AREA), rel=1e-6)


@pytest.mark.parametrize("case", [1, 2, 3, 4, 5, 6])
def test_timoshenko_without_shear_matches_pynite_for_elastic_supports(case: int) -> None:
    springs = {
        "k_x_A": 5e5, "k_x_B": 2e6, "k_y_A": 3e5, "k_y_B": 8e5, "k_z_A": 4e5, "k_z_B": 9e5,
        "c_x_A": 2e3, "c_x_B": 5e3, "c_y_A": 6e4, "c_y_B": 1e3, "c_z_A": 2e3, "c_z_B": 4e4,
    }  # fmt: skip
    pynite = solve_benchmark_beam(_beam(case, 0.35, springs))
    timoshenko = solve_timoshenko_beam(_timoshenko_beam(case, 0.35, springs, INFINITE_SHEAR_AREA))
    for quantity in LOAD_CASES[case][1]:
        assert normalised_error(timoshenko[quantity], pynite[quantity]) < 1e-6


def test_normalised_error() -> None:
    reference = np.array([0.0, 2.0, -4.0])
    assert normalised_error(reference, reference) == 0.0
    assert normalised_error(reference + 0.2, reference) == pytest.approx(0.05)
    assert normalised_error(np.zeros(3), np.zeros(3)) == 0.0
    assert normalised_error(np.ones(3), np.zeros(3)) == float("inf")


def test_slenderness_uses_the_bending_axis() -> None:
    strong = slenderness(_beam(3, 0.5, SIMPLY_SUPPORTED))
    weak = slenderness(_beam(2, 0.5, SIMPLY_SUPPORTED))
    assert strong == pytest.approx(L / np.sqrt(IY / A))
    assert weak > strong


def _write_csvs(tmp_path: Path) -> tuple[Path, Path]:
    """Cria CSV mínimos com o formato do TimoDS; os resultados vêm do nosso solver."""
    inputs = tmp_path / "input.csv"
    results = tmp_path / "results.csv"
    spring_cols = [f"{k}_{e}" for k in KEYS for e in ENDS]
    quantities = ("ux", "uy", "uz", "rx", "ry", "rz")
    result_cols = ["row_id", "S", "A_y", "A_z", "I_yy", "I_zz", "J_xx", *spring_cols] + [
        f"{q}{s:.2f}" for q in quantities for s in STATIONS
    ]
    with inputs.open("w", newline="") as fi, results.open("w", newline="") as fr:
        wi = csv.DictWriter(fi, ["ID", "Lcase", "L", "a", "SecName"])
        wr = csv.DictWriter(fr, result_cols)
        wi.writeheader()
        wr.writeheader()
        for i, case in enumerate((2, 3, 5)):
            springs = SIMPLY_SUPPORTED
            solved = solve_benchmark_beam(_beam(case, 0.5, springs))
            wi.writerow({"ID": i, "Lcase": case, "L": L, "a": 0.5, "SecName": "TEST"})
            row = {
                "row_id": i,
                "S": A,
                "A_y": A,
                "A_z": A,
                "I_yy": IY,
                "I_zz": IZ,
                "J_xx": J,
                **springs,
            }
            row.update(
                {
                    f"{q}{s:.2f}": v
                    for q, vals in solved.items()
                    for s, v in zip(STATIONS, vals, strict=True)
                }
            )
            wr.writerow(row)
    return inputs, results


def test_end_to_end_with_synthetic_csv(tmp_path: Path) -> None:
    inputs, results = _write_csvs(tmp_path)
    outcome = run_benchmark(inputs, results, sample_size=10)
    assert len(outcome) == 3
    assert all(max(r.errors["pynite"].values()) < 1e-9 for r in outcome)
    text = "\n".join(summarise(outcome, worst_per_case=1))
    assert "Piores instâncias" in text
    assert "caso 2" in text and "caso 3" in text and "caso 5" in text
    assert "todas" in text


def test_summary_flags_large_errors() -> None:
    bad = InstanceResult(1, 3, 15.0, {"pynite": {"uz": 0.2}, "timoshenko": {"uz": 0.2, "ry": 0.01}})
    good = InstanceResult(
        2, 3, 90.0, {"pynite": {"uz": 0.001}, "timoshenko": {"uz": 0.001, "ry": 0.002}}
    )
    lines = "\n".join(summarise([bad, good]))
    assert "0-20" in lines and ">80" in lines
    assert "50.0%" in lines  # metade das instâncias acima de 5 %
