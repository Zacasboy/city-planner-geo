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

from backend.app.services import timoshenko

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
    shear_area_y_m2: float = float("inf")  # só o solver de Timoshenko usa as áreas de corte
    shear_area_z_m2: float = float("inf")


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


def _stations_from_nodes(fractions: list[float], values: np.ndarray) -> np.ndarray:
    """Valores nodais nas 21 posições do TimoDS (os nós incluem todas essas posições)."""
    return np.array(
        [values[min(range(len(fractions)), key=lambda i: abs(fractions[i] - s))] for s in STATIONS]
    )


def solve_timoshenko_beam(beam: BenchmarkBeam) -> dict[str, np.ndarray]:
    """Resolve uma instância com vigas de Timoshenko (inclui o esforço transverso).

    Args:
        beam: Instância do benchmark, com as áreas de corte preenchidas.

    Returns:
        As grandezas do caso de carga nas 21 posições; as restantes ficam a zero.
    """
    fractions = _node_positions(beam.load_position)
    xs = [f * beam.length_m for f in fractions]
    lengths = [b - a for a, b in zip(xs, xs[1:], strict=False)]
    load_node = min(range(len(fractions)), key=lambda i: abs(fractions[i] - beam.load_position))
    last = len(fractions) - 1
    e, g = YOUNGS_MODULUS_KN_M2, YOUNGS_MODULUS_KN_M2 / (2 * (1 + POISSON_RATIO))
    out = {q: np.zeros(len(STATIONS)) for q in NODE_ATTRIBUTE}
    case = beam.load_case

    def springs(key: str, dof: int) -> list[timoshenko.Spring]:
        return [(0, dof, beam.springs[f"{key}_A"]), (last, dof, beam.springs[f"{key}_B"])]

    if case in (1, 4):
        stiffness = e * beam.area_m2 if case == 1 else g * beam.torsion_j_m4
        key, name = ("k_x", "ux") if case == 1 else ("c_x", "rx")
        elements = [timoshenko.axial_element(stiffness, h) for h in lengths]
        u = timoshenko.solve_chain(xs, elements, 1, springs(key, 0), [(load_node, 0, 1.0)])
        out[name] = _stations_from_nodes(fractions, u[:, 0])
        return out

    plane_y = case in (2, 6)
    inertia = beam.inertia_z_m4 if plane_y else beam.inertia_y_m4
    shear_area = beam.shear_area_y_m2 if plane_y else beam.shear_area_z_m2
    elements = [timoshenko.timoshenko_element(e, inertia, g, shear_area, h) for h in lengths]
    k_key, c_key = ("k_y", "c_z") if plane_y else ("k_z", "c_y")
    node_springs = springs(k_key, 0) + springs(c_key, 1)
    # ry = -theta, por isso o momento My entra com sinal trocado
    load = {2: (0, 1.0), 3: (0, 1.0), 6: (1, 1.0), 5: (1, -1.0)}[case]
    u = timoshenko.solve_chain(xs, elements, 2, node_springs, [(load_node, load[0], load[1])])
    displacement = _stations_from_nodes(fractions, u[:, 0])
    rotation = _stations_from_nodes(fractions, u[:, 1])
    if plane_y:
        out["uy"], out["rz"] = displacement, rotation
    else:
        out["uz"], out["ry"] = displacement, -rotation
    return out
