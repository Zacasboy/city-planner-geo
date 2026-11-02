"""Testes da leitura do OpenBuildingMap com um Parquet sintético (sem rede)."""

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import pyarrow.parquet as pq
import pytest
import shapely
from pyproj import Transformer
from shapely.geometry import Polygon, box

from backend.app.services import obm_source
from backend.app.services.geo_utils import polygon_wgs84_to_tm06
from backend.app.services.obm_attributes import building_type, parse_height

LISBON_QUADKEY = "033110"
WEST, SOUTH = -9.140, 38.720
STEP = 0.0005
SIZE = 0.0002


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("H:2", (6.0, 2)),
        ("HHT:99.95", (99.95, 33)),
        ("HHT:1", (1.0, 1)),
        ("HBET:3,5", (12.0, 4)),
        ("HBET:2-4", (9.0, 3)),
        ("HAPP:4", (12.0, 4)),
        ("H:3+HBEX:1", (9.0, 3)),
        ("HHT:10+H:2", (10.0, 3)),
        (None, None),
        ("", None),
        ("H:0", None),
        ("H:abc", None),
        ("HBEX:1", None),
        ("HBET:3", (9.0, 3)),
        ("HBET:x,5", None),
    ],
)
def test_parse_height(code: str | None, expected: tuple[float, int] | None) -> None:
    assert parse_height(code) == expected


@pytest.mark.parametrize(
    ("occupancy", "expected"),
    [
        ("RES3", "residential"),
        ("res", "residential"),
        ("COM2", "commercial"),
        ("IND", "industrial"),
        ("UNK", "other_or_unknown"),
        ("EDU", "other_or_unknown"),
        (None, "other_or_unknown"),
    ],
)
def test_building_type(occupancy: str | None, expected: str) -> None:
    assert building_type(occupancy) == expected


def test_quadkeys_cover_lisbon_and_portugal() -> None:
    assert obm_source.quadkeys_for_bbox(-9.14, 38.72, -9.13, 38.73) == [LISBON_QUADKEY]
    assert set(obm_source.quadkeys_for_bbox(-9.5, 36.9, -6.1, 42.2)) == {"031332", LISBON_QUADKEY}


def _rows(count: int) -> list[dict[str, object]]:
    rows = []
    for i in range(count):
        x = WEST + i * STEP
        footprint = box(x, SOUTH, x + SIZE, SOUTH + SIZE)
        rows.append(
            {
                "id": i,
                "geometry": shapely.to_wkb(footprint),
                "bbox": {"xmin": x, "ymin": SOUTH, "xmax": x + SIZE, "ymax": SOUTH + SIZE},
                "height": "H:2" if i % 2 == 0 else None,
                "occupancy": "RES1" if i % 3 == 0 else "UNK",
                "source": "OSM",
            }
        )
    return rows


def _write(folder: Path, rows: list[dict[str, object]], scale: float = 1.0) -> None:
    if scale != 1.0:
        rows = [
            r | {"bbox": {k: v * scale for k, v in r["bbox"].items()}}  # type: ignore[attr-defined]
            for r in rows
        ]
    pq.write_table(
        pa.Table.from_pylist(rows),
        folder / f"building.{LISBON_QUADKEY}.parquet",
        row_group_size=10,
    )


def _area(west: float, east: float) -> tuple[Polygon, Polygon]:
    polygon = box(west, SOUTH - 0.0005, east, SOUTH + 0.0005)
    return polygon, polygon_wgs84_to_tm06(polygon)


def _fetch(folder: Path, west: float, east: float) -> tuple[list[dict[str, object]], list[str]]:
    wgs84, metric = _area(west, east)
    return obm_source.fetch_buildings(
        wgs84, metric, pafs.LocalFileSystem(), dataset_path=str(folder)
    )


def test_reads_only_buildings_inside_the_area(tmp_path: Path) -> None:
    _write(tmp_path, _rows(100))
    buildings, missing = _fetch(tmp_path, WEST + 0.0004, WEST + 5 * STEP)
    assert missing == []
    assert sorted(b["id"] for b in buildings) == ["1", "2", "3", "4"]
    one = next(b for b in buildings if b["id"] == "2")
    assert one["height_m"] == 6.0
    assert one["floors"] == 2
    assert one["footprint_m2"] == pytest.approx(SIZE * 111_000 * SIZE * 111_000 * 0.78, rel=0.1)
    assert one["area_m2"] == pytest.approx(2 * one["footprint_m2"])  # type: ignore[operator]
    unknown = next(b for b in buildings if b["id"] == "1")
    assert unknown["height_m"] is None
    assert unknown["area_m2"] == unknown["footprint_m2"]


def test_web_mercator_files_give_the_same_buildings(tmp_path: Path) -> None:
    to_mercator = Transformer.from_crs(4326, 3857, always_xy=True)
    rows = []
    for row in _rows(20):
        geometry = shapely.from_wkb(row["geometry"])  # type: ignore[arg-type]
        mercator = shapely.transform(
            geometry, lambda c: np.column_stack(to_mercator.transform(c[:, 0], c[:, 1]))
        )
        xmin, ymin, xmax, ymax = mercator.bounds
        rows.append(
            row
            | {
                "geometry": shapely.to_wkb(mercator),
                "bbox": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
            }
        )
    _write(tmp_path, rows)
    buildings, _ = _fetch(tmp_path, WEST + 0.0004, WEST + 5 * STEP)
    assert sorted(b["id"] for b in buildings) == ["1", "2", "3", "4"]


def test_missing_tile_is_reported_not_hidden(tmp_path: Path) -> None:
    buildings, missing = _fetch(tmp_path, WEST, WEST + STEP)
    assert buildings == []
    assert missing == [LISBON_QUADKEY]


def test_unreadable_tile_raises(tmp_path: Path) -> None:
    (tmp_path / f"building.{LISBON_QUADKEY}.parquet").write_bytes(b"not a parquet file")
    with pytest.raises(obm_source.BuildingSourceError):
        _fetch(tmp_path, WEST, WEST + STEP)


def test_bbox_filter_skips_row_groups(tmp_path: Path) -> None:
    _write(tmp_path, _rows(100))
    path = tmp_path / f"building.{LISBON_QUADKEY}.parquet"
    fragment = next(iter(ds.dataset(str(path), format="parquet").get_fragments()))
    selected = fragment.split_by_row_group(
        obm_source._bbox_filter(WEST, SOUTH, WEST + 3 * STEP, SOUTH + SIZE)
    )
    assert 0 < len(selected) < 10
