"""Motor de elementos finitos de vigas (PyNite, Euler-Bernoulli, regime linear elástico).

A viga fica no eixo X e carrega-se no eixo Y; a flexão é em torno de Z. Unidades SI.
"""

import math
from dataclasses import dataclass

from Pynite import FEModel3D

from backend.app.services.structural_models import BeamRequest

GRAVITY_MS2 = 9.80665
LOAD_COMBO = "Combo 1"
MERGE_TOLERANCE_M = 1e-9
EQUILIBRIUM_TOLERANCE = 1e-6
# O PyNite avalia os extremos em pontos discretos de cada barra: malha fina evita subestimá-los
MESH_DIVISIONS = 40

# DX, DY, DZ, RX, RY, RZ impedidos em cada tipo de apoio (RX e DZ evitam mecanismos fora do plano)
SUPPORT_RESTRAINTS: dict[str, tuple[bool, bool, bool, bool, bool, bool]] = {
    "pin": (True, True, True, True, False, False),
    "roller": (False, True, True, True, False, False),
    "fixed": (True, True, True, True, True, True),
}


@dataclass(frozen=True)
class BeamResults:
    """Resultados do cálculo, em unidades SI."""

    max_deflection_m: float
    max_moment_nm: float
    max_shear_n: float
    reactions_n: dict[float, float]
    self_weight_n_per_m: float
    total_load_n: float


def _node_positions(request: BeamRequest) -> list[float]:
    """Posições dos nós: extremos, apoios e cargas pontuais (sem duplicados)."""
    raw = sorted(
        [0.0, request.length]
        + [s.position for s in request.supports]
        + [p.position for p in request.point_loads]
    )
    merged: list[float] = []
    for x in raw:
        if not merged or x - merged[-1] > MERGE_TOLERANCE_M:
            merged.append(x)
    return _refine(merged, request.length / MESH_DIVISIONS)


def _refine(positions: list[float], max_element_m: float) -> list[float]:
    """Divide cada troço em barras com no máximo `max_element_m`."""
    refined = [positions[0]]
    for start, end in zip(positions, positions[1:], strict=False):
        parts = max(1, math.ceil((end - start) / max_element_m - MERGE_TOLERANCE_M))
        refined.extend(start + (end - start) * k / parts for k in range(1, parts + 1))
    return refined


def _node_at(nodes: list[float], position: float) -> str:
    return f"N{min(range(len(nodes)), key=lambda i: abs(nodes[i] - position))}"


def _build_model(
    request: BeamRequest, nodes: list[float], uniform_down_n_per_m: float
) -> FEModel3D:
    area = request.width * request.height
    inertia_z = request.width * request.height**3 / 12
    inertia_y = request.height * request.width**3 / 12
    shear_modulus = request.youngs_modulus / (2 * (1 + request.poisson_ratio))
    model = FEModel3D()
    model.add_material(
        "steel", request.youngs_modulus, shear_modulus, request.poisson_ratio, request.density
    )
    model.add_section("section", area, inertia_y, inertia_z, inertia_y + inertia_z)
    for i, x in enumerate(nodes):
        model.add_node(f"N{i}", x, 0, 0)
    for i in range(len(nodes) - 1):
        model.add_member(f"M{i}", f"N{i}", f"N{i + 1}", "steel", "section")
        if uniform_down_n_per_m:
            model.add_member_dist_load(f"M{i}", "Fy", -uniform_down_n_per_m, -uniform_down_n_per_m)
    for support in request.supports:
        model.def_support(_node_at(nodes, support.position), *SUPPORT_RESTRAINTS[support.type])
    for load in request.point_loads:
        model.add_node_load(_node_at(nodes, load.position), "FY", -load.magnitude)
    return model


def _peak(model: FEModel3D, n_members: int, quantity: str, direction: str) -> float:
    """Maior valor absoluto de uma grandeza (`deflection`, `moment` ou `shear`) ao longo da viga."""
    values: list[float] = []
    for i in range(n_members):
        member = model.members[f"M{i}"]
        for extreme in ("max", "min"):
            getter = getattr(member, f"{extreme}_{quantity}")
            values.append(abs(float(getter(direction, LOAD_COMBO))))
    return max(values)


def solve_beam(request: BeamRequest) -> BeamResults:
    """Resolve a viga por elementos finitos.

    Args:
        request: Geometria, material, cargas e apoios (já validados).

    Returns:
        Flecha, momento e esforço transverso máximos e as reações nos apoios.

    Raises:
        ValueError: Se as reações não equilibrarem as cargas (modelo mal condicionado).
    """
    area = request.width * request.height
    self_weight = request.density * GRAVITY_MS2 * area if request.include_self_weight else 0.0
    nodes = _node_positions(request)
    model = _build_model(request, nodes, self_weight + request.uniform_load)
    model.analyze(check_statics=False)

    n_members = len(nodes) - 1
    reactions = {
        support.position: float(model.nodes[_node_at(nodes, support.position)].RxnFY[LOAD_COMBO])
        for support in request.supports
    }
    total_load = (
        sum(p.magnitude for p in request.point_loads)
        + (self_weight + request.uniform_load) * request.length
    )
    if abs(sum(reactions.values()) - total_load) > EQUILIBRIUM_TOLERANCE * max(
        abs(total_load), 1.0
    ):
        raise ValueError("Reactions do not balance the applied loads")
    return BeamResults(
        max_deflection_m=_peak(model, n_members, "deflection", "dy"),
        max_moment_nm=_peak(model, n_members, "moment", "Mz"),
        max_shear_n=_peak(model, n_members, "shear", "Fy"),
        reactions_n=reactions,
        self_weight_n_per_m=self_weight,
        total_load_n=total_load,
    )
