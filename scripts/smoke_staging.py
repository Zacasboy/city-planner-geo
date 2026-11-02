"""Verifica um backend publicado (T1.13): saúde, rotas protegidas e um cálculo conhecido.

Uso:
    poetry run python scripts/smoke_staging.py https://<serviço>.onrender.com
    SMOKE_TOKEN=<JWT de um utilizador de teste> poetry run python scripts/smoke_staging.py URL
Sem `SMOKE_TOKEN` só se confirma que as rotas protegidas recusam pedidos anónimos. O token vem
do ambiente para não ficar no histórico do terminal; nunca o escreva no código nem no chat.
O primeiro pedido pode demorar (o plano gratuito do Render adormece sem tráfego).
"""

import os
import sys

import requests

COLD_START_TIMEOUT_S = 90
TIMEOUT_S = 30
UNAUTHORISED = (401, 403)
LOAD_N, LENGTH_M, WIDTH_M, HEIGHT_M, E_PA = 10_000.0, 5.0, 0.3, 0.5, 200e9
BEAM = {
    "length": LENGTH_M,
    "width": WIDTH_M,
    "height": HEIGHT_M,
    "youngs_modulus": E_PA,
    "density": 7850,
    "yield_stress": 250e6,
    "include_self_weight": False,
    "include_shear_deformation": False,
    "point_loads": [{"position": LENGTH_M / 2, "magnitude": LOAD_N}],
    "supports": [{"position": 0.0, "type": "pin"}, {"position": LENGTH_M, "type": "roller"}],
}
EXPECTED_DEFLECTION_M = LOAD_N * LENGTH_M**3 / (48 * E_PA * WIDTH_M * HEIGHT_M**3 / 12)
REL_TOLERANCE = 1e-4
PROTECTED = ("/structural/beam", "/geo/validate", "/ecology/area-species", "/reports/structural")


def _check(label: str, ok: bool, detail: str = "") -> bool:
    sys.stdout.write(f"{'OK  ' if ok else 'FAIL'} {label} {detail}\n")
    return ok


def run(base_url: str, token: str | None) -> bool:
    """Corre as verificações e devolve `True` se todas passarem."""
    base = base_url.rstrip("/")
    health = requests.get(f"{base}/health", timeout=COLD_START_TIMEOUT_S)
    results = [
        _check("GET /health", health.status_code == requests.codes.ok, str(health.status_code))
    ]
    for path in PROTECTED:
        code = requests.post(f"{base}{path}", json={}, timeout=TIMEOUT_S).status_code
        results.append(_check(f"anónimo recusado em {path}", code in UNAUTHORISED, str(code)))
    if token:
        response = requests.post(
            f"{base}/structural/beam",
            json=BEAM,
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_S,
        )
        deflection = (
            response.json().get("max_deflection", 0.0)
            if response.status_code == requests.codes.ok
            else 0.0
        )
        close = abs(deflection - EXPECTED_DEFLECTION_M) <= REL_TOLERANCE * EXPECTED_DEFLECTION_M
        results.append(_check("viga: flecha igual à solução fechada", close, f"{deflection:.6e} m"))
    return all(results)


def main() -> None:
    """Lê o URL e o token e termina com código 1 se alguma verificação falhar."""
    if len(sys.argv) != 2:  # noqa: PLR2004
        sys.stderr.write(__doc__ or "")
        sys.exit(2)
    sys.exit(0 if run(sys.argv[1], os.environ.get("SMOKE_TOKEN")) else 1)


if __name__ == "__main__":
    main()
