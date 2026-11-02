"""Solver 1D de vigas de Timoshenko com molas nos extremos (elementos de 2 nós, SI ou kN-m).

Quatro problemas independentes ao longo da viga: axial, torção e flexão em dois planos. Cada nó
tem 1 grau de liberdade (axial, torção) ou 2 (flexão: deslocamento transversal `w` e rotação da
secção `theta`). Serve de referência para o benchmark TimoDS, que inclui o esforço transverso.
"""

import numpy as np

Spring = tuple[int, int, float]  # (nó, grau de liberdade local, rigidez)
Load = tuple[int, int, float]  # (nó, grau de liberdade local, valor)


def axial_element(stiffness_per_length: float, length: float) -> np.ndarray:
    """Matriz de uma barra axial ou de torção (`EA` ou `GJ` a dividir pelo comprimento)."""
    k = stiffness_per_length / length
    return np.array([[k, -k], [-k, k]])


def timoshenko_element(
    youngs_modulus: float, inertia: float, shear_modulus: float, shear_area: float, length: float
) -> np.ndarray:
    """Matriz de rigidez de um elemento de flexão de Timoshenko (w1, theta1, w2, theta2).

    Args:
        youngs_modulus: Módulo de elasticidade.
        inertia: Inércia no plano de flexão.
        shear_modulus: Módulo de distorção.
        shear_area: Área de corte efetiva; infinita recupera Euler-Bernoulli.
        length: Comprimento do elemento.

    Returns:
        Matriz 4x4.
    """
    ei = youngs_modulus * inertia
    phi = 12 * ei / (shear_modulus * shear_area * length**2) if np.isfinite(shear_area) else 0.0
    ll = length
    factor = ei / ((1 + phi) * ll**3)
    return factor * np.array(
        [
            [12, 6 * ll, -12, 6 * ll],
            [6 * ll, (4 + phi) * ll**2, -6 * ll, (2 - phi) * ll**2],
            [-12, -6 * ll, 12, -6 * ll],
            [6 * ll, (2 - phi) * ll**2, -6 * ll, (4 + phi) * ll**2],
        ]
    )


def solve_chain(
    positions: list[float],
    element_matrices: list[np.ndarray],
    dofs_per_node: int,
    springs: list[Spring],
    loads: list[Load],
) -> np.ndarray:
    """Monta e resolve a cadeia de elementos.

    Args:
        positions: Coordenadas dos nós (crescentes).
        element_matrices: Uma matriz por elemento entre nós consecutivos.
        dofs_per_node: 1 (axial, torção) ou 2 (flexão).
        springs: Molas de apoio.
        loads: Cargas nodais.

    Returns:
        Deslocamentos com forma (n_nós, dofs_per_node).
    """
    n_nodes = len(positions)
    size = n_nodes * dofs_per_node
    stiffness = np.zeros((size, size))
    width = 2 * dofs_per_node
    for i, matrix in enumerate(element_matrices):
        start = i * dofs_per_node
        stiffness[start : start + width, start : start + width] += matrix
    for node, dof, value in springs:
        stiffness[node * dofs_per_node + dof, node * dofs_per_node + dof] += value
    force = np.zeros(size)
    for node, dof, value in loads:
        force[node * dofs_per_node + dof] += value
    return np.linalg.solve(stiffness, force).reshape(n_nodes, dofs_per_node)
