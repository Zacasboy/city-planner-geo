"""Leitura dos CSV do TimoDS e comparação com o motor FEM (ver `timods_benchmark`)."""

import csv
import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.app.services.timods_benchmark import (
    LOAD_CASES,
    SPRING_KEYS,
    STATIONS,
    BenchmarkBeam,
    normalised_error,
    solve_benchmark_beam,
    solve_timoshenko_beam,
)

ERROR_LIMIT = 0.05  # objetivo O3: diferença < 5 %
SLENDERNESS_BINS = (20.0, 40.0, 80.0)
STRONG_AXIS_CASES = {1, 3, 4, 5}  # os restantes fletem em torno de z
Row = dict[str, str]


@dataclass(frozen=True)
class InstanceResult:
    """Erro normalizado de uma instância, por grandeza comparada."""

    instance_id: int
    load_case: int
    slenderness: float
    errors: dict[str, dict[str, float]]  # motor -> grandeza -> erro normalizado
    detail: str = ""


def _station_key(quantity: str, station: float) -> str:
    return f"{quantity}{station:.2f}"


def read_input_rows(path: Path) -> list[Row]:
    """Lê `TimoDS_input_data.csv` inteiro (cerca de 15 MB)."""
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_result_rows(path: Path, wanted_ids: set[int]) -> dict[int, Row]:
    """Lê só as linhas pedidas de `TimoDS_beam_results.csv` (cerca de 150 MB, em fluxo)."""
    rows: dict[int, Row] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            row_id = int(row["row_id"])
            if row_id in wanted_ids:
                rows[row_id] = row
                if len(rows) == len(wanted_ids):
                    break
    return rows


def build_beam(inputs: Row, results: Row) -> BenchmarkBeam:
    """Junta uma linha de entrada e a de resultados numa instância do benchmark."""
    springs = {
        f"{key}_{end}": float(results[f"{key}_{end}"])
        for key in SPRING_KEYS.values()
        for end in ("A", "B")
    }
    return BenchmarkBeam(
        length_m=float(inputs["L"]),
        area_m2=float(results["S"]),
        inertia_y_m4=float(results["I_yy"]),
        inertia_z_m4=float(results["I_zz"]),
        torsion_j_m4=float(results["J_xx"]),
        springs=springs,
        load_case=int(inputs["Lcase"]),
        load_position=float(inputs["a"]),
        shear_area_y_m2=float(results["A_y"]),
        shear_area_z_m2=float(results["A_z"]),
    )


def reference_values(results: Row, quantity: str) -> np.ndarray:
    """As 21 posições de uma grandeza no TimoDS."""
    return np.array([float(results[_station_key(quantity, s)]) for s in STATIONS])


def slenderness(beam: BenchmarkBeam) -> float:
    """Esbelteza L / raio de giração no eixo de flexão do caso de carga."""
    inertia = beam.inertia_y_m4 if beam.load_case in STRONG_AXIS_CASES else beam.inertia_z_m4
    return beam.length_m / math.sqrt(inertia / beam.area_m2)


ENGINES = {"pynite": solve_benchmark_beam, "timoshenko": solve_timoshenko_beam}


def _describe(instance_id: int, inputs: Row, beam: BenchmarkBeam, results: Row) -> str:
    """Texto com os parâmetros e três posições, para diagnosticar uma instância."""
    quantity = LOAD_CASES[beam.load_case][1][0]
    reference = reference_values(results, quantity)
    computed = {name: solver(beam)[quantity] for name, solver in ENGINES.items()}
    marks = [0, len(STATIONS) // 2, len(STATIONS) - 1]
    values = "  ".join(
        f"x={STATIONS[i]:.2f}: TimoDS={reference[i]:.4e} "
        + " ".join(f"{n}={c[i]:.4e}" for n, c in computed.items())
        for i in marks
    )
    return (
        f"id={instance_id} caso={beam.load_case} {inputs['SecName']} L={beam.length_m} "
        f"a={beam.load_position} J={beam.torsion_j_m4:.3e} springs="
        + ",".join(f"{k}={v:.3g}" for k, v in beam.springs.items())
        + f"\n    {quantity}: {values}"
    )


def compare_instance(instance_id: int, inputs: Row, results: Row) -> InstanceResult:
    """Resolve uma instância com os dois motores e compara-a com o TimoDS."""
    beam = build_beam(inputs, results)
    quantities = LOAD_CASES[beam.load_case][1]
    errors: dict[str, dict[str, float]] = {}
    for name, solver in ENGINES.items():
        computed = solver(beam)
        errors[name] = {
            q: normalised_error(computed[q], reference_values(results, q)) for q in quantities
        }
    return InstanceResult(
        instance_id,
        beam.load_case,
        slenderness(beam),
        errors,
        _describe(instance_id, inputs, beam, results),
    )


def run_benchmark(
    input_path: Path, results_path: Path, sample_size: int, seed: int = 0
) -> list[InstanceResult]:
    """Compara uma amostra aleatória (semente fixa) de instâncias.

    Args:
        input_path: `TimoDS_input_data.csv`.
        results_path: `TimoDS_beam_results.csv`.
        sample_size: Número de instâncias a comparar.
        seed: Semente da amostragem.

    Returns:
        Um resultado por instância.
    """
    inputs = read_input_rows(input_path)
    sampler = random.Random(seed)  # noqa: S311 - amostragem reprodutível, não é criptografia
    chosen = sampler.sample(range(len(inputs)), min(sample_size, len(inputs)))
    results = read_result_rows(results_path, set(chosen))
    return [compare_instance(i, inputs[i], results[i]) for i in sorted(chosen)]


def _worst_error(result: InstanceResult, engine: str) -> float:
    return max(result.errors[engine].values())


def _bin_label(value: float) -> str:
    previous = 0.0
    for upper in SLENDERNESS_BINS:
        if value <= upper:
            return f"{previous:g}-{upper:g}"
        previous = upper
    return f">{previous:g}"


def _stats_line(label: str, values: list[float]) -> str:
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    over = sum(v > ERROR_LIMIT for v in values) / len(values)
    return (
        f"{label:<12} n={len(values):<5} mediana={statistics.median(values):8.3%} "
        f"p95={p95:8.3%} max={ordered[-1]:9.3%} acima de {ERROR_LIMIT:.0%}: {over:6.1%}"
    )


def _engine_summary(results: list[InstanceResult], engine: str) -> list[str]:
    by_case: dict[int, list[float]] = defaultdict(list)
    by_slenderness: dict[str, list[float]] = defaultdict(list)
    for result in results:
        by_case[result.load_case].append(_worst_error(result, engine))
        by_slenderness[_bin_label(result.slenderness)].append(_worst_error(result, engine))
    lines = ["Por caso de carga"]
    lines += [_stats_line(f"caso {case}", by_case[case]) for case in sorted(by_case)]
    lines += ["", "Por esbelteza L/i (eixo de flexão)"]
    lines += [_stats_line(label, values) for label, values in sorted(by_slenderness.items())]
    lines += ["", _stats_line("todas", [_worst_error(r, engine) for r in results])]
    return lines


def summarise(results: list[InstanceResult], worst_per_case: int = 0) -> list[str]:
    """Linhas de texto com o erro por motor, caso de carga e esbelteza.

    Args:
        results: Resultados da comparação.
        worst_per_case: Se > 0, acrescenta as piores instâncias do solver de Timoshenko
            em cada caso de carga, com valores, para diagnóstico.

    Returns:
        Linhas de texto.
    """
    lines = ["Erro normalizado (maior diferença / maior valor do TimoDS)"]
    for engine, title in (("pynite", "PyNite (Euler-Bernoulli)"), ("timoshenko", "Timoshenko")):
        lines += ["", f"=== {title} ===", *_engine_summary(results, engine)]
    if worst_per_case:
        lines += ["", "=== Piores instâncias (Timoshenko) ==="]
        for case in sorted({r.load_case for r in results}):
            worst = sorted(
                (r for r in results if r.load_case == case),
                key=lambda r: _worst_error(r, "timoshenko"),
                reverse=True,
            )
            lines += [
                f"erro={_worst_error(r, 'timoshenko'):.3%} {r.detail}"
                for r in worst[:worst_per_case]
            ]
    return lines
