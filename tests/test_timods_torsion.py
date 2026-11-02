"""Testes do diagnóstico de torção do TimoDS com dados sintéticos do nosso solver."""

import csv
from pathlib import Path

import pytest

from backend.app.services.timods_benchmark import STATIONS, BenchmarkBeam, solve_benchmark_beam
from backend.app.services.timods_torsion import (
    SHEAR_MODULUS_KN_M2,
    implied_torsion_ends,
    run_torsion_diagnostic,
    summarise_torsion,
)

L, A, INERTIA, J = 3.0, 0.01, 1e-4, 2e-6
KEYS = ("k_x", "k_y", "k_z", "c_x", "c_y", "c_z")
ENDS = "AB"
GJ = SHEAR_MODULUS_KN_M2 * J
COLUMNS = ["row_id", "S", "A_y", "A_z", "I_yy", "I_zz", "J_xx"] + [
    f"{k}_{e}" for k in KEYS for e in ENDS
]
INPUT_COLUMNS = ["ID", "Lcase", "L", "a", "SecName"]


def _row(c_a: float, c_b: float, position: float, row_id: int = 0) -> tuple[dict, dict]:
    springs = {f"{k}_{e}": 0.0 for k in KEYS for e in ENDS}
    springs.update({"c_x_A": c_a, "c_x_B": c_b, "k_x_A": 1e9, "k_y_A": 1e9, "k_z_A": 1e9})
    beam = BenchmarkBeam(L, A, INERTIA, INERTIA, J, springs, 4, position)
    rotation = solve_benchmark_beam(beam)["rx"]
    inputs = {"ID": row_id, "Lcase": 4, "L": L, "a": position, "SecName": "T"}
    results = {
        "row_id": row_id,
        "S": A,
        "A_y": A,
        "A_z": A,
        "I_yy": INERTIA,
        "I_zz": INERTIA,
        "J_xx": J,
    }
    results.update(springs)
    results.update({f"rx{s:.2f}": v for s, v in zip(STATIONS, rotation, strict=True)})
    return {k: str(v) for k, v in inputs.items()}, {k: str(v) for k, v in results.items()}


def test_a_physical_spring_is_recovered_with_unit_torque() -> None:
    inputs, results = _row(c_a=40.0, c_b=15.0, position=0.4)
    ends = implied_torsion_ends(0, inputs, results)
    assert ends is not None
    assert ends.implied_spring_a == pytest.approx(40.0, rel=1e-6)
    assert ends.implied_spring_b == pytest.approx(15.0, rel=1e-6)
    assert ends.applied_torque == pytest.approx(1.0, rel=1e-6)
    assert ends.torsion_gj == pytest.approx(GJ)


def test_load_near_an_end_is_skipped() -> None:
    inputs, results = _row(c_a=40.0, c_b=15.0, position=0.05)
    assert implied_torsion_ends(0, inputs, results) is None


def test_summary_and_run_on_a_csv(tmp_path: Path) -> None:
    rows = [_row(40.0 + 5 * i, 10.0 + 3 * i, 0.3 + 0.05 * i, i) for i in range(6)]
    result_columns = COLUMNS + [f"rx{s:.2f}" for s in STATIONS]
    inputs_path, results_path = tmp_path / "in.csv", tmp_path / "res.csv"
    with inputs_path.open("w", newline="") as fi, results_path.open("w", newline="") as fr:
        wi = csv.DictWriter(fi, INPUT_COLUMNS)
        wr = csv.DictWriter(fr, result_columns)
        wi.writeheader()
        wr.writeheader()
        for inp, res in rows:
            wi.writerow(inp)
            wr.writerow(res)
    items = run_torsion_diagnostic(inputs_path, results_path, sample_size=10)
    assert len(items) == 6
    text = "\n".join(summarise_torsion(items, examples=2))
    assert "c_B implícita / c_x_B" in text
    assert "ajuste" in text
    assert "Spearman de c_B implícita" in text
    assert "rx id=0" in text
    assert summarise_torsion([]) == ["Sem instâncias do caso 4 utilizáveis"]
