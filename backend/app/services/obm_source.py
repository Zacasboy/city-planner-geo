"""Leitura de edifícios do OpenBuildingMap (Parquet por tile, em acesso público).

Dados: OpenBuildingMap (Oostwegel et al., 2025), licença ODbL v1.0 — citar sempre a fonte.
Não há API de consulta: cada ficheiro ``building.<quadkey>.parquet`` cobre um tile de nível 6
e é lido com filtro por ``bbox``, aproveitando a ordenação espacial do ficheiro.
"""

import logging
import math
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import pyarrow.parquet as pq
import shapely
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from backend.app.services.geo_utils import TM06_EPSG, WGS84_EPSG
from backend.app.services.obm_attributes import building_type, parse_height

logger = logging.getLogger(__name__)

TILE_LEVEL = 6
S3_REGION = "us-west-2"
DATASET_PATH = "us-west-2.opendata.source.coop/tge-labs/openbuildingmap"
COLUMNS = ["id", "geometry", "height", "occupancy", "source", "bbox"]
WEB_MERCATOR_EPSG = 3857
MAX_LONGITUDE_DEGREES = 180.0
MAX_MERCATOR_LATITUDE = 85.05112878
SUPPORTED_GEOMETRIES = ("Polygon", "MultiPolygon")
ATTRIBUTION = "OpenBuildingMap (Oostwegel et al., 2025), ODbL v1.0"

Building = dict[str, Any]


class BuildingSourceError(RuntimeError):
    """A fonte de edifícios não pôde ser lida (rede, formato ou tile inesperado)."""


def _tile_xy(longitude: float, latitude: float, level: int) -> tuple[int, int]:
    latitude = max(-MAX_MERCATOR_LATITUDE, min(MAX_MERCATOR_LATITUDE, latitude))
    tiles = 2**level
    x = int((longitude + 180.0) / 360.0 * tiles)
    lat_rad = math.radians(latitude)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * tiles)
    return min(max(x, 0), tiles - 1), min(max(y, 0), tiles - 1)


def _quadkey(x: int, y: int, level: int) -> str:
    digits = []
    for bit in range(level, 0, -1):
        mask = 1 << (bit - 1)
        digits.append(str((1 if x & mask else 0) + (2 if y & mask else 0)))
    return "".join(digits)


def quadkeys_for_bbox(west: float, south: float, east: float, north: float) -> list[str]:
    """Quadkeys dos tiles de nível 6 que cobrem uma caixa em WGS84 (lon/lat)."""
    x_min, y_max = _tile_xy(west, south, TILE_LEVEL)
    x_max, y_min = _tile_xy(east, north, TILE_LEVEL)
    return [
        _quadkey(x, y, TILE_LEVEL) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)
    ]


def _is_web_mercator(parquet: pq.ParquetFile) -> bool:
    """Deteta a projeção pelas estatísticas da caixa: graus nunca passam de 180."""
    names = [parquet.schema.column(i).path for i in range(parquet.metadata.num_columns)]
    column = names.index("bbox.xmin")
    for group in range(parquet.metadata.num_row_groups):
        stats = parquet.metadata.row_group(group).column(column).statistics
        if stats is not None and stats.has_min_max and abs(stats.min) > MAX_LONGITUDE_DEGREES:
            return True
    return False


def _bbox_filter(west: float, south: float, east: float, north: float) -> Any:
    return (
        (pc.field("bbox", "xmin") <= east)
        & (pc.field("bbox", "xmax") >= west)
        & (pc.field("bbox", "ymin") <= north)
        & (pc.field("bbox", "ymax") >= south)
    )


def read_tile(
    quadkey: str,
    bounds: tuple[float, float, float, float],
    filesystem: Any = None,
    dataset_path: str = DATASET_PATH,
) -> tuple[pa.Table, bool] | None:
    """Lê os edifícios de um tile cuja caixa interseta ``bounds`` (lon/lat).

    Returns:
        ``(tabela, em_web_mercator)``, ou None se o tile não existir.

    Raises:
        BuildingSourceError: Se o ficheiro existir mas não puder ser lido.
    """
    filesystem = filesystem or pafs.S3FileSystem(anonymous=True, region=S3_REGION)
    path = f"{dataset_path}/building.{quadkey}.parquet"
    try:
        with filesystem.open_input_file(path) as handle:
            mercator = _is_web_mercator(pq.ParquetFile(handle))
        query = bounds
        if mercator:
            to_mercator = Transformer.from_crs(WGS84_EPSG, WEB_MERCATOR_EPSG, always_xy=True)
            query = (*to_mercator.transform(*bounds[:2]), *to_mercator.transform(*bounds[2:]))
        dataset = ds.dataset(path, filesystem=filesystem, format="parquet")
        table = dataset.to_table(columns=COLUMNS, filter=_bbox_filter(*query))
    except FileNotFoundError:
        return None
    except (OSError, pa.ArrowException, KeyError, ValueError) as exc:
        raise BuildingSourceError(f"Could not read OpenBuildingMap tile {quadkey}") from exc
    return table, mercator


def _row_to_building(
    row: dict[str, Any], geometry: BaseGeometry, polygon_m: Polygon, to_m: Transformer
) -> Building | None:
    geometry_m = shapely.transform(
        geometry, lambda coords: np.column_stack(to_m.transform(coords[:, 0], coords[:, 1]))
    )
    centroid = geometry_m.centroid
    if not polygon_m.contains(centroid):
        return None
    footprint_m2 = geometry_m.area
    parsed = parse_height(row.get("height"))
    height_m, floors = parsed if parsed else (None, None)
    return {
        "id": str(row["id"]),
        "centroid": [centroid.x, centroid.y],
        "footprint_m2": footprint_m2,
        "area_m2": footprint_m2 * (floors or 1),
        "height_m": height_m,
        "floors": floors,
        "building_type": building_type(row.get("occupancy")),
        "source": row.get("source"),
    }


def table_to_buildings(table: pa.Table, mercator: bool, polygon_m: Polygon) -> list[Building]:
    """Converte uma tabela do OBM em edifícios cujo centroide está dentro de ``polygon_m``."""
    to_m = Transformer.from_crs(
        WEB_MERCATOR_EPSG if mercator else WGS84_EPSG, TM06_EPSG, always_xy=True
    )
    geometries = shapely.from_wkb(table["geometry"].to_pylist())
    columns = {name: table[name].to_pylist() for name in ("id", "height", "occupancy", "source")}
    buildings: list[Building] = []
    for index, geometry in enumerate(geometries):
        if geometry is None or geometry.is_empty or geometry.geom_type not in SUPPORTED_GEOMETRIES:
            continue
        row = {name: values[index] for name, values in columns.items()}
        building = _row_to_building(row, geometry, polygon_m, to_m)
        if building is not None:
            buildings.append(building)
    return buildings


def fetch_buildings(
    polygon_wgs84: Polygon,
    polygon_m: Polygon,
    filesystem: Any = None,
    dataset_path: str = DATASET_PATH,
) -> tuple[list[Building], list[str]]:
    """Lê os edifícios dentro de uma área, juntando os tiles que a cobrem.

    Args:
        polygon_wgs84: Área em EPSG:4326 (lon, lat), usada para escolher tiles e filtrar.
        polygon_m: A mesma área em EPSG:3763 (metros), usada para áreas e contenção.
        filesystem: Sistema de ficheiros do pyarrow (por omissão, S3 anónimo).
        dataset_path: Pasta com os ficheiros ``building.<quadkey>.parquet``.

    Returns:
        ``(edifícios, quadkeys dos tiles inexistentes)``.

    Raises:
        BuildingSourceError: Se algum tile existente não puder ser lido.
    """
    bounds = polygon_wgs84.bounds
    buildings: dict[str, Building] = {}
    missing: list[str] = []
    for quadkey in quadkeys_for_bbox(*bounds):
        result = read_tile(quadkey, bounds, filesystem, dataset_path)
        if result is None:
            missing.append(quadkey)
            continue
        table, mercator = result
        for building in table_to_buildings(table, mercator, polygon_m):
            buildings[building["id"]] = building
    return list(buildings.values()), missing
