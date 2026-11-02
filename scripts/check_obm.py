"""Verifica o acesso real ao OpenBuildingMap (T2.1) a partir da sua máquina.

Uso:
    poetry run python scripts/check_obm.py
Lê edifícios de um quarteirão de Lisboa no S3 público do Source Cooperative e imprime o
tempo, o número de edifícios, a cobertura de alturas e as projeções detetadas. Não usa chaves.
Se falhar com 'tile not found', o nome dos ficheiros ou a pasta mudaram: ver docs/data_sources.md.
"""

import logging
import sys
import time

from shapely.geometry import box

from backend.app.services.geo_utils import polygon_wgs84_to_tm06
from backend.app.services.obm_source import (
    BuildingSourceError,
    fetch_buildings,
    quadkeys_for_bbox,
)

LISBON_BLOCK = (-9.145, 38.715, -9.135, 38.725)  # oeste, sul, este, norte (WGS84)
SAMPLE_SIZE = 3

logging.basicConfig(level=logging.INFO)


def _say(text: object) -> None:
    sys.stdout.write(f"{text}\n")


def main() -> int:
    """Corre a verificação e devolve 0 se correu bem."""
    polygon = box(*LISBON_BLOCK)
    _say(f"Tiles: {quadkeys_for_bbox(*LISBON_BLOCK)}")
    started = time.perf_counter()
    try:
        buildings, missing = fetch_buildings(polygon, polygon_wgs84_to_tm06(polygon))
    except BuildingSourceError as exc:
        _say(f"FALHOU: {exc} ({exc.__cause__!r})")
        return 1
    elapsed = time.perf_counter() - started
    with_height = [b for b in buildings if b["height_m"] is not None]
    _say(f"{len(buildings)} edifícios em {elapsed:.1f} s; tiles em falta: {missing}")
    if buildings:
        _say(f"Com altura: {len(with_height)} ({len(with_height) / len(buildings):.0%})")
        for sample in buildings[:SAMPLE_SIZE]:
            _say(sample)
    return 0 if buildings and not missing else 1


if __name__ == "__main__":
    sys.exit(main())
