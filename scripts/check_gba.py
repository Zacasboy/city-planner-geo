"""Verifica o acesso real ao GlobalBuildingAtlas (alturas estimadas) a partir da sua máquina.

Uso:
    PYTHONPATH=. poetry run python scripts/check_gba.py
Lê os edifícios de um quarteirão de Lisboa (OpenBuildingMap), completa as alturas em falta com o
GlobalBuildingAtlas e imprime tempos, colunas do tile e a cobertura de alturas antes e depois.
Não usa chaves. Dados GBA: CC BY-NC 4.0 (uso não comercial).
"""

import logging
import sys
import time

import pyarrow.dataset as ds
import pyarrow.fs as pafs
from shapely.geometry import box

from backend.app.services import gba_source
from backend.app.services.geo_utils import polygon_wgs84_to_tm06
from backend.app.services.obm_source import S3_REGION, BuildingSourceError

LISBON_BLOCK = (-9.145, 38.715, -9.135, 38.725)  # oeste, sul, este, norte (WGS84)

logging.basicConfig(level=logging.INFO)


def _say(text: object) -> None:
    sys.stdout.write(f"{text}\n")


def _schema(tile: str) -> None:
    filesystem = pafs.S3FileSystem(anonymous=True, region=S3_REGION)
    path = f"{gba_source.DATASET_PATH}/{tile}.parquet"
    _say(f"Esquema de {tile}:\n{ds.dataset(path, filesystem=filesystem).schema}")


def main() -> int:
    """Corre a verificação e devolve 0 se correu bem."""
    polygon = box(*LISBON_BLOCK)
    tiles = gba_source.tiles_for_bbox(*LISBON_BLOCK)
    _say(f"Tiles GBA: {tiles}")
    try:
        _schema(tiles[0])
        started = time.perf_counter()
        buildings, missing = gba_source.fetch_buildings_with_heights(
            polygon, polygon_wgs84_to_tm06(polygon)
        )
    except (BuildingSourceError, OSError) as exc:
        _say(f"FALHOU: {exc} ({exc.__cause__!r})")
        return 1
    elapsed = time.perf_counter() - started
    total = len(buildings)
    measured = sum(b["height_source"] == gba_source.HEIGHT_SOURCE_OBM for b in buildings)
    estimated = sum(b["height_source"] == gba_source.HEIGHT_SOURCE_GBA for b in buildings)
    _say(f"{total} edifícios em {elapsed:.1f} s; tiles em falta: {missing}")
    if total:
        _say(f"Altura OBM: {measured} ({measured / total:.0%})")
        _say(f"Altura estimada GBA: {estimated} ({estimated / total:.0%})")
        _say(f"Sem altura: {total - measured - estimated}")
    return 0 if total and not missing and estimated else 1


if __name__ == "__main__":
    sys.exit(main())
