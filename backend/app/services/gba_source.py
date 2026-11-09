"""Alturas estimadas do GlobalBuildingAtlas (GBA) para completar o OpenBuildingMap.

Dados: GlobalBuildingAtlas LoD1 (Zhu et al., TUM, 2025), licença CC BY-NC 4.0 — **uso não
comercial**. Distribuído em Parquet por tiles de 5°x5° (conversão do Source Cooperative), com
geometria, ``height`` em metros (-999 = sem dados) e ``bbox``. As alturas são estimativas de um
modelo de deep learning, não medições: ficam sempre identificadas como tal.

Cada edifício do OpenBuildingMap sem altura recebe a altura do polígono do GBA que contém o
seu centroide.
"""

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import shapely
from pyproj import Transformer
from shapely.geometry import Polygon

from backend.app.services.geo_utils import TM06_EPSG, WGS84_EPSG
from backend.app.services.obm_source import (
    MAX_LONGITUDE_DEGREES,
    S3_REGION,
    Building,
    BuildingSourceError,
    _bbox_filter,
    fetch_buildings,
)

logger = logging.getLogger(__name__)

DATASET_PATH = "us-west-2.opendata.source.coop/tge-labs/globalbuildingatlas-lod1"
TILE_DEGREES = 5
COLUMNS = ["geometry", "height", "bbox"]
NO_DATA_HEIGHT = -999.0
METERS_PER_FLOOR = 3.0
HEIGHT_SOURCE_OBM = "obm"
HEIGHT_SOURCE_GBA = "gba_estimate"
MISSING_PREFIX = "gba:"
ATTRIBUTION = "GlobalBuildingAtlas LoD1 (Zhu et al., 2025), CC BY-NC 4.0, non-commercial use only"
UNAVAILABLE = f"{MISSING_PREFIX}unavailable"


def _tile_label(west: int, north: int) -> str:
    east, south = west + TILE_DEGREES, north - TILE_DEGREES

    def lon(value: int) -> str:
        return f"{'e' if value >= 0 else 'w'}{abs(value):03d}"

    def lat(value: int) -> str:
        return f"{'n' if value >= 0 else 's'}{abs(value):02d}"

    return f"{lon(west)}_{lat(north)}_{lon(east)}_{lat(south)}"


def tiles_for_bbox(west: float, south: float, east: float, north: float) -> list[str]:
    """Nomes (sem extensão) dos tiles de 5°x5° que cobrem uma caixa em WGS84 (lon/lat)."""
    first_west = math.floor(west / TILE_DEGREES) * TILE_DEGREES
    last_west = math.floor(east / TILE_DEGREES) * TILE_DEGREES
    first_north = math.ceil(north / TILE_DEGREES) * TILE_DEGREES
    last_north = math.ceil(south / TILE_DEGREES) * TILE_DEGREES
    return [
        _tile_label(tile_west, tile_north)
        for tile_west in range(first_west, last_west + 1, TILE_DEGREES)
        for tile_north in range(first_north, last_north - 1, -TILE_DEGREES)
    ]


def read_tile(
    tile: str,
    bounds: tuple[float, float, float, float],
    filesystem: Any = None,
    dataset_path: str = DATASET_PATH,
) -> pa.Table | None:
    """Lê as linhas de um tile cuja caixa interseta ``bounds`` (lon/lat).

    Returns:
        A tabela com ``geometry``, ``height`` e ``bbox``, ou None se o tile não existir.

    Raises:
        BuildingSourceError: Se o ficheiro existir mas não puder ser lido ou tiver outra projeção.
    """
    filesystem = filesystem or pafs.S3FileSystem(anonymous=True, region=S3_REGION)
    path = f"{dataset_path}/{tile}.parquet"
    try:
        dataset = ds.dataset(path, filesystem=filesystem, format="parquet")
        table = dataset.to_table(columns=COLUMNS, filter=_bbox_filter(*bounds))
    except FileNotFoundError:
        return None
    except (OSError, pa.ArrowException, KeyError, ValueError) as exc:
        raise BuildingSourceError(f"Could not read GlobalBuildingAtlas tile {tile}") from exc
    if table.num_rows:
        longitudes = table["bbox"].combine_chunks().field("xmin").to_pylist()
        if max(abs(value) for value in longitudes) > MAX_LONGITUDE_DEGREES:
            raise BuildingSourceError(f"GlobalBuildingAtlas tile {tile} is not in WGS84 degrees")
    return table


def _valid_heights(table: pa.Table) -> tuple[list[Any], np.ndarray]:
    """Geometrias (WGS84) e alturas dos polígonos com altura válida."""
    geometries = shapely.from_wkb(table["geometry"].to_pylist())
    heights = np.array(table["height"].to_numpy(zero_copy_only=False), dtype=float)
    keep = (
        ~np.isnan(heights)
        & (heights > 0)
        & (heights != NO_DATA_HEIGHT)
        & ~shapely.is_empty(geometries)
        & ~shapely.is_missing(geometries)
    )
    return list(geometries[keep]), heights[keep]


def apply_gba_heights(buildings: list[Building], tables: list[pa.Table]) -> int:
    """Preenche a altura dos edifícios sem ela com a do polígono GBA que contém o centroide.

    As alturas do OpenBuildingMap nunca são substituídas. Altera ``buildings`` no local.

    Returns:
        O número de edifícios que ganharam uma altura estimada.
    """
    for building in buildings:
        building["height_source"] = HEIGHT_SOURCE_OBM if building["height_m"] is not None else None
    pending = [i for i, b in enumerate(buildings) if b["height_m"] is None]
    if not pending:
        return 0
    to_m = Transformer.from_crs(WGS84_EPSG, TM06_EPSG, always_xy=True)
    points = shapely.points([buildings[i]["centroid"] for i in pending])
    assigned: dict[int, float] = {}
    for table in tables:
        geometries, heights = _valid_heights(table)
        if not geometries:
            continue
        projected = shapely.transform(
            np.array(geometries, dtype=object),
            lambda coords: np.column_stack(to_m.transform(coords[:, 0], coords[:, 1])),
        )
        point_index, polygon_index = shapely.STRtree(projected).query(points, predicate="within")
        for position, polygon in zip(point_index, polygon_index, strict=True):
            assigned.setdefault(pending[int(position)], float(heights[polygon]))
    for index, height in assigned.items():
        building = buildings[index]
        floors = max(1, round(height / METERS_PER_FLOOR))
        building["height_m"] = height
        building["floors"] = floors
        building["area_m2"] = building["footprint_m2"] * floors
        building["height_source"] = HEIGHT_SOURCE_GBA
    return len(assigned)


def _read_tiles(
    polygon_wgs84: Polygon, filesystem: Any, dataset_path: str
) -> tuple[list[pa.Table], list[str]]:
    tables: list[pa.Table] = []
    missing: list[str] = []
    for tile in tiles_for_bbox(*polygon_wgs84.bounds):
        table = read_tile(tile, polygon_wgs84.bounds, filesystem, dataset_path)
        if table is None:
            missing.append(f"{MISSING_PREFIX}{tile}")
        else:
            tables.append(table)
    return tables, missing


def fetch_buildings_with_heights(
    polygon_wgs84: Polygon,
    polygon_m: Polygon,
    filesystem: Any = None,
    dataset_path: str = DATASET_PATH,
) -> tuple[list[Building], list[str]]:
    """Edifícios do OpenBuildingMap com as alturas em falta completadas pelo GBA.

    Os dois conjuntos são lidos em paralelo. Se o GBA falhar, devolve só o OpenBuildingMap e
    regista ``gba:unavailable`` na lista de tiles em falta: a análise não falha por isso.

    Returns:
        ``(edifícios, tiles em falta)``; os do GBA levam o prefixo ``gba:``.

    Raises:
        BuildingSourceError: Se o OpenBuildingMap não puder ser lido.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        obm = pool.submit(fetch_buildings, polygon_wgs84, polygon_m)
        gba = pool.submit(_read_tiles, polygon_wgs84, filesystem, dataset_path)
        buildings, missing = obm.result()
        try:
            tables, gba_missing = gba.result()
        except BuildingSourceError:
            logger.warning("GlobalBuildingAtlas unavailable; heights not completed", exc_info=True)
            tables, gba_missing = [], [UNAVAILABLE]
    apply_gba_heights(buildings, tables)
    return buildings, [*missing, *gba_missing]
