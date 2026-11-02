"""Motor de elementos finitos de vigas de Timoshenko, regime linear elástico, flexão num plano.

A viga fica no eixo X e carrega-se na vertical. Cada nó tem o deslocamento vertical `w` (positivo
para cima) e a rotação da secção `theta`. Com `include_shear_deformation=False` o elemento reduz-se
ao de Euler-Bernoulli. O motor foi comparado com o benchmark TimoDS (ver `timods_benchmark`).
Unidades SI.
"""

import math
from dataclasses import dataclass

import numpy as np

from backend.app.services.structural_models import BeamRequest
from backend.app.services.timoshenko import timoshenko_element

GRAVITY_MS2 = 9.80665
MERGE_TOLERANCE_M = 1e-9
EQUILIBRIUM_TOLERANCE = 1e-6
# Malha fina para os extremos entre nós ficarem bem representados
MESH_DIVISIONS = 40
DOFS_PER_NODE = 2


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
    """Posições dos nós: extremos, apoios e cargas pontuais (sem duplicados), com malha fina."""
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


def _node_index(nodes: list[float], position: float) -> int:
    return min(range(len(nodes)), key=lambda i: abs(nodes[i] - position))


def _element_matrices(request: BeamRequest, nodes: list[float]) -> list[np.ndarray]:
    shear_modulus = request.youngs_modulus / (2 * (1 + request.poisson_ratio))
    shear_area = request.shear_area if request.include_shear_deformation else math.inf
    return [
        timoshenko_element(
            request.youngs_modulus, request.inertia, shear_modulus, shear_area, end - start
        )
        for start, end in zip(nodes, nodes[1:], strict=False)
    ]


def _udl_nodal_loads(length: float, down_n_per_m: float) -> np.ndarray:
    """Cargas nodais equivalentes a uma carga uniforme descendente num elemento."""
    qq = down_n_per_m
    return np.array([-qq * length / 2, -qq * length**2 / 12, -qq * length / 2, qq * length**2 / 12])


def _assemble(
    request: BeamRequest, nodes: list[float], matrices: list[np.ndarray], down_n_per_m: float
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    """Matriz global, vetor de cargas e as cargas equivalentes de cada elemento."""
    size = len(nodes) * DOFS_PER_NODE
    stiffness = np.zeros((size, size))
    force = np.zeros(size)
    element_loads = []
    for i, matrix in enumerate(matrices):
        start = i * DOFS_PER_NODE
        stiffness[start : start + 4, start : start + 4] += matrix
        load = _udl_nodal_loads(nodes[i + 1] - nodes[i], down_n_per_m)
        force[start : start + 4] += load
        element_loads.append(load)
    for point in request.point_loads:
        force[_node_index(nodes, point.position) * DOFS_PER_NODE] -= point.magnitude
    return stiffness, force, element_loads


def _fixed_dofs(request: BeamRequest, nodes: list[float]) -> list[int]:
    fixed: set[int] = set()
    for support in request.supports:
        base = _node_index(nodes, support.position) * DOFS_PER_NODE
        fixed.add(base)
        if support.type == "fixed":
            fixed.add(base + 1)
    return sorted(fixed)


def _interior_peak(start_moment: float, start_shear: float, load: float, length: float) -> float:
    """Momento no ponto de esforço transverso nulo dentro do elemento (0 se estiver fora)."""
    if load == 0:
        return 0.0
    x = start_shear / load
    if 0 < x < length:
        return abs(start_moment + start_shear * x - load * x**2 / 2)
    return 0.0


def _peaks(
    displacement: np.ndarray,
    nodes: list[float],
    matrices: list[np.ndarray],
    element_loads: list[np.ndarray],
    down_n_per_m: float,
) -> tuple[float, float, float]:
    """Flecha, momento e esforço transverso máximos (valores absolutos)."""
    deflection = float(np.max(np.abs(displacement[::DOFS_PER_NODE])))
    moment = shear = 0.0
    for i, (matrix, load) in enumerate(zip(matrices, element_loads, strict=True)):
        length = nodes[i + 1] - nodes[i]
        local = displacement[i * DOFS_PER_NODE : i * DOFS_PER_NODE + 4]
        ends = matrix @ local - load
        w1, th1, w2, th2 = local
        deflection = max(deflection, abs((w1 + w2) / 2 + length * (th1 - th2) / 8))
        shear = max(shear, abs(ends[0]), abs(ends[2]))
        moment = max(
            moment,
            abs(ends[1]),
            abs(ends[3]),
            _interior_peak(-ends[1], ends[0], down_n_per_m, length),
        )
    return deflection, moment, shear


def solve_beam(request: BeamRequest) -> BeamResults:
    """Resolve a viga por elementos finitos de Timoshenko.

    Args:
        request: Geometria, material, cargas e apoios (já validados).

    Returns:
        Flecha, momento e esforço transverso máximos e as reações nos apoios.

    Raises:
        ValueError: Se as reações não equilibrarem as cargas (modelo mal condicionado).
    """
    self_weight = request.density * GRAVITY_MS2 * request.area if request.include_self_weight else 0
    down_n_per_m = self_weight + request.uniform_load
    nodes = _node_positions(request)
    matrices = _element_matrices(request, nodes)
    stiffness, force, element_loads = _assemble(request, nodes, matrices, down_n_per_m)

    fixed = _fixed_dofs(request, nodes)
    free = [d for d in range(len(force)) if d not in set(fixed)]
    displacement = np.zeros(len(force))
    displacement[free] = np.linalg.solve(stiffness[np.ix_(free, free)], force[free])
    residual = stiffness @ displacement - force

    reactions = {
        support.position: float(residual[_node_index(nodes, support.position) * DOFS_PER_NODE])
        for support in request.supports
    }
    total_load = sum(p.magnitude for p in request.point_loads) + down_n_per_m * request.length
    if abs(sum(reactions.values()) - total_load) > EQUILIBRIUM_TOLERANCE * max(
        abs(total_load), 1.0
    ):
        raise ValueError("Reactions do not balance the applied loads")
    deflection, moment, shear = _peaks(displacement, nodes, matrices, element_loads, down_n_per_m)
    return BeamResults(
        max_deflection_m=deflection,
        max_moment_nm=moment,
        max_shear_n=shear,
        reactions_n=reactions,
        self_weight_n_per_m=self_weight,
        total_load_n=total_load,
    )
