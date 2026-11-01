"""Comparação do motor FEM com o benchmark sintético TimoDS (Zenodo 10.5281/zenodo.19324945).

O TimoDS tem vigas de Timoshenko com molas elásticas nos dois extremos e 6 casos de carga
unitários (1: Fx, 2: Fy, 3: Fz, 4: Mx, 5: My, 6: Mz) na posição `a·L`. Unidades: kN, m.
Os eixos locais do TimoDS coincidem com os globais do PyNite (viga ao longo de X).
O PyNite é Euler-Bernoulli, por isso as diferenças em vigas curtas medem o efeito do esforço
transverso, que o TimoDS inclui e este motor não.
"""

from dataclasses import dataclass

import numpy as np
from Pynite import FEModel3D

YOUNGS_MODULUS_KN_M2 = 210e6
POISSON_RATIO = 0.3
STATIONS = [round(i * 0.05, 2) for i in range(21)]
LOAD_COMBO = "Combo 1"
POSITION_TOLERANCE = 1e-9
SPRING_DOFS = ("DX", "DY", "DZ", "RX", "RY", "RZ")
SPRING_KEYS = {
    "DX": "k_x",
    "DY": "k_y",
    "DZ": "k_z",
    "RX": "c_x",
    "RY": "c_y",
    "RZ": "c_z",
}
# Caso de carga -> (direção da carga unitária, grandezas a comparar com o TimoDS)
LOAD_CASES: dict[int, tuple[str, tuple[str, ...]]] = {
    1: ("FX", ("ux",)),
    2: ("FY", ("uy", "rz")),
    3: ("FZ", ("uz", "ry")),
    4: ("MX", ("rx",)),
    5: ("MY", ("uz", "ry")),
    6: ("MZ", ("uy", "rz")),
}
NODE_ATTRIBUTE = {"ux": "DX", "uy": "DY", "uz": "DZ", "rx": "RX", "ry": "RY", "rz": "RZ"}


@dataclass(frozen=True)
class BenchmarkBeam:
    """Uma instância do TimoDS: secção, comprimento, molas e caso de carga."""

    length_m: float
    area_m2: float
    inertia_y_m4: float
    inertia_z_m4: float
    torsion_j_m4: float
    springs: dict[str, float]  # chaves como `k_x_A`, `c_z_B` (kN/m ou kN·m/rad)
    load_case: int
    load_position: float  # fração do comprimento


def _node_positions(load_position: float) -> list[float]:
    positions = sorted({*STATIONS, load_position})
    merged: list[float] = []
    for x in positions:
        if not merged or x - merged[-1] > POSITION_TOLERANCE:
            merged.append(x)
    return merged


def _build_model(beam: BenchmarkBeam, fractions: list[float]) -> FEModel3D:
    shear_modulus = YOUNGS_MODULUS_KN_M2 / (2 * (1 + POISSON_RATIO))
    model = FEModel3D()
    model.add_material("steel", YOUNGS_MODULUS_KN_M2, shear_modulus, POISSON_RATIO, 0.0)
    model.add_section(
        "section", beam.area_m2, beam.inertia_y_m4, beam.inertia_z_m4, beam.torsion_j_m4
    )
    for i, fraction in enumerate(fractions):
        model.add_node(f"N{i}", fraction * beam.length_m, 0, 0)
    for i in range(len(fractions) - 1):
        model.add_member(f"M{i}", f"N{i}", f"N{i + 1}", "steel", "section")
    last = f"N{len(fractions) - 1}"
    for dof in SPRING_DOFS:
        for end, node in (("A", "N0"), ("B", last)):
            stiffness = beam.springs[f"{SPRING_KEYS[dof]}_{end}"]
            model.def_support_spring(node, dof, stiffness)
    return model


def solve_benchmark_beam(beam: BenchmarkBeam) -> dict[str, np.ndarray]:
    """Resolve uma instância e devolve as 6 grandezas nas 21 posições do TimoDS.

    Args:
        beam: Instância do benchmark.

    Returns:
        Dicionário `ux`, `uy`, `uz`, `rx`, `ry`, `rz` com 21 valores cada (m ou rad).
    """
    fractions = _node_positions(beam.load_position)
    model = _build_model(beam, fractions)
    direction, _ = LOAD_CASES[beam.load_case]
    load_node = (
        f"N{min(range(len(fractions)), key=lambda i: abs(fractions[i] - beam.load_position))}"
    )
    model.add_node_load(load_node, direction, 1.0)
    model.analyze(check_statics=False)

    index = {f: i for i, f in enumerate(fractions)}
    return {
        quantity: np.array(
            [
                getattr(model.nodes[f"N{index[min(index, key=lambda f: abs(f - s))]}"], attribute)[
                    LOAD_COMBO
                ]
                for s in STATIONS
            ]
        )
        for quantity, attribute in NODE_ATTRIBUTE.items()
    }


def normalised_error(computed: np.ndarray, reference: np.ndarray) -> float:
    """Maior diferença absoluta dividida pelo maior valor absoluto de referência."""
    peak = float(np.max(np.abs(reference)))
    if peak == 0.0:
        return 0.0 if float(np.max(np.abs(computed))) == 0.0 else float("inf")
    return float(np.max(np.abs(computed - reference)) / peak)
