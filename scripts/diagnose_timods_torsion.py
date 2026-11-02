"""Diagnostica a torção do TimoDS (T1.6b): molas de torção implícitas nos resultados.

Uso, a partir da raiz do repositório:
    poetry run python scripts/diagnose_timods_torsion.py \
        --inputs ~/Downloads/TimoDS_input_data.csv \
        --results ~/Downloads/TimoDS_beam_results.csv --sample 3000
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.timods_torsion import (  # noqa: E402
    run_torsion_diagnostic,
    summarise_torsion,
)

DEFAULT_SAMPLE = 3000


def main() -> None:
    """Corre o diagnóstico e escreve o resumo no ecrã."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    items = run_torsion_diagnostic(
        args.inputs.expanduser(), args.results.expanduser(), args.sample, args.seed
    )
    sys.stdout.write("\n".join(summarise_torsion(items)) + "\n")


if __name__ == "__main__":
    main()
