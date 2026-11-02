"""Diagnóstico da torção no TimoDS (caso de carga 4, binário unitário a `a·L`).

Num troço sem carga a rotação `rx` é linear, por isso as 21 estações dão o binário interno
`GJ·rx'` em cada extremo. As molas equivalentes que daí resultam, `c_A = GJ·rx'(0)/rx(0)` e
`c_B = -GJ·rx'(1)/rx(1)`, comparam-se com as colunas `c_x_A` e `c_x_B`; o equilíbrio exige ainda
que `GJ·(rx'(0) - rx'(1))` seja 1 kN·m.
"""

import random
import statistics
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from backend.app.services.timods_benchmark import STATIONS
from backend.app.services.timods_data import (
    Row,
    build_beam,
    read_input_rows,
    read_result_rows,
    reference_values,
)

SHEAR_MODULUS_KN_M2 = 210e6 / 2.6
TORSION_CASE = 4
STATION_STEP = STATIONS[1] - STATIONS[0]
LOAD_MARGIN = 2 * STATION_STEP  # a carga tem de estar longe dos extremos para o troço ser linear
MIN_ROTATION_RAD = 1e-12
LSQ_COLUMNS = ("c_x_B", "GJ/L", "1")


@dataclass(frozen=True)
class TorsionEnds:
    """Rigidezes e equilíbrio inferidos de uma instância do caso 4."""

    instance_id: int
    torsion_gj: float
    length_m: float
    load_position: float
    input_spring_a: float
    input_spring_b: float
    implied_spring_a: float
    implied_spring_b: float
    applied_torque: float
    springs: dict[str, float]
    rotations: list[float]


def implied_torsion_ends(instance_id: int, inputs: Row, results: Row) -> TorsionEnds | None:
    """Infere as molas de torção; `None` se a carga estiver perto de um extremo."""
    beam = build_beam(inputs, results)
    if not LOAD_MARGIN < beam.load_position < 1 - LOAD_MARGIN:
        return None
    rotation = reference_values(results, "rx")
    if abs(rotation[0]) < MIN_ROTATION_RAD or abs(rotation[-1]) < MIN_ROTATION_RAD:
        return None
    gj = SHEAR_MODULUS_KN_M2 * beam.torsion_j_m4
    step = STATION_STEP * beam.length_m
    slope_a = (rotation[1] - rotation[0]) / step
    slope_b = (rotation[-1] - rotation[-2]) / step
    return TorsionEnds(
        instance_id,
        gj,
        beam.length_m,
        beam.load_position,
        beam.springs["c_x_A"],
        beam.springs["c_x_B"],
        gj * slope_a / rotation[0],
        -gj * slope_b / rotation[-1],
        gj * (slope_a - slope_b),
        dict(beam.springs),
        [float(r) for r in rotation],
    )


def run_torsion_diagnostic(
    input_path: Path, results_path: Path, sample_size: int, seed: int = 0
) -> list[TorsionEnds]:
    """Analisa uma amostra aleatória (semente fixa) das instâncias do caso 4."""
    inputs = read_input_rows(input_path)
    candidates = [i for i, row in enumerate(inputs) if int(row["Lcase"]) == TORSION_CASE]
    sampler = random.Random(seed)  # noqa: S311 - amostragem reprodutível, não é criptografia
    chosen = sampler.sample(candidates, min(sample_size, len(candidates)))
    results = read_result_rows(results_path, set(chosen))
    found = (implied_torsion_ends(i, inputs[i], results[i]) for i in sorted(chosen))
    return [item for item in found if item is not None]


def _ratio_line(label: str, values: list[float]) -> str:
    ordered = sorted(values)
    low, high = ordered[len(ordered) // 20], ordered[-1 - len(ordered) // 20]
    return (
        f"{label:<28} mediana={statistics.median(values):10.4g}  p5={low:10.4g}  p95={high:10.4g}"
    )


def _fit_spring_b(items: list[TorsionEnds]) -> str:
    """Ajuste por mínimos quadrados `mola_B_implícita ≈ α·c_x_B + β·GJ/L + γ`."""
    design = np.array([[t.input_spring_b, t.torsion_gj / t.length_m, 1.0] for t in items])
    target = np.array([t.implied_spring_b for t in items])
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    residual = float(np.max(np.abs(design @ coefficients - target) / (np.abs(target) + 1e-12)))
    terms = "  ".join(f"{n}: {c:.4g}" for n, c in zip(LSQ_COLUMNS, coefficients, strict=True))
    return f"ajuste c_B_implícita = α·c_x_B + β·GJ/L + γ -> {terms}  (erro máx {residual:.3g})"


def _ranks(values: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(values)).astype(float)


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return 0.0
    return float(np.corrcoef(_ranks(x), _ranks(y))[0, 1])


def _features(item: TorsionEnds) -> dict[str, float]:
    features = {
        "a": item.load_position,
        "L": item.length_m,
        "GJ": item.torsion_gj,
        "GJ/L": item.torsion_gj / item.length_m,
    }
    return features | item.springs


def correlation_lines(items: list[TorsionEnds], top: int = 8) -> list[str]:
    """Correlação de Spearman da mola de B implícita (valor e sinal) com cada parâmetro."""
    names = list(_features(items[0]))
    columns = {n: np.array([_features(t)[n] for t in items]) for n in names}
    implied = np.array([t.implied_spring_b for t in items])
    targets = {"c_B implícita": implied, "sinal de c_B implícita": np.sign(implied)}
    lines = []
    for label, target in targets.items():
        ranked = sorted(names, key=lambda n: -abs(_spearman(columns[n], target)))[:top]
        body = "  ".join(f"{n}={_spearman(columns[n], target):+.2f}" for n in ranked)
        lines.append(f"Spearman de {label}: {body}")
    return lines


def rotation_lines(items: list[TorsionEnds], count: int = 3) -> list[str]:
    """As 21 rotações de algumas instâncias, para ver a forma completa."""
    return [
        f"rx id={t.instance_id} a={t.load_position}: " + " ".join(f"{r:.4e}" for r in t.rotations)
        for t in items[:count]
    ]


def summarise_torsion(items: list[TorsionEnds], examples: int = 8) -> list[str]:
    """Linhas de texto com as razões, o equilíbrio e alguns exemplos."""
    if not items:
        return ["Sem instâncias do caso 4 utilizáveis"]
    lines = [
        f"Caso 4: {len(items)} instâncias com a carga longe dos extremos",
        _ratio_line(
            "c_A implícita / c_x_A", [t.implied_spring_a / t.input_spring_a for t in items]
        ),
        _ratio_line(
            "c_B implícita / c_x_B", [t.implied_spring_b / t.input_spring_b for t in items]
        ),
        _ratio_line("binário aplicado (kN·m)", [t.applied_torque for t in items]),
        _fit_spring_b(items),
        *correlation_lines(items),
        "",
        "exemplos: id, a, L, GJ/L, c_x_A, c_x_B, c_A implícita, c_B implícita",
    ]
    lines += [
        f"{t.instance_id:>6} a={t.load_position:<5} L={t.length_m:<6}"
        f" GJ/L={t.torsion_gj / t.length_m:<9.4g}"
        f" c_x_A={t.input_spring_a:<10.4g} c_x_B={t.input_spring_b:<10.4g}"
        f" cA*={t.implied_spring_a:<10.4g} cB*={t.implied_spring_b:<10.4g}"
        for t in items[:examples]
    ]
    return lines + ["", *rotation_lines(items)]
