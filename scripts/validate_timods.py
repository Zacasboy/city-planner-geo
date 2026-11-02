"""Compara o motor FEM com o benchmark TimoDS (T1.6, objetivo O3).

Uso, a partir da raiz do repositório:
    poetry run python scripts/validate_timods.py \
        --inputs ~/Downloads/TimoDS_input_data.csv \
        --results ~/Downloads/TimoDS_beam_results.csv --sample 2000
Os CSV não fazem parte do repositório (ver docs/data_sources.md, secção 4).
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.timods_data import run_benchmark, summarise  # noqa: E402

DEFAULT_SAMPLE = 2000


def main() -> None:
    """Corre a comparação e escreve o resumo no ecrã."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--worst", type=int, default=2, help="piores instâncias por caso")
    args = parser.parse_args()
    results = run_benchmark(
        args.inputs.expanduser(), args.results.expanduser(), args.sample, args.seed
    )
    sys.stdout.write("\n".join(summarise(results, args.worst)) + "\n")


if __name__ == "__main__":
    main()
