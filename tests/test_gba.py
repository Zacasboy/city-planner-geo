"""Testes das alturas do GlobalBuildingAtlas com Parquet sintético (sem rede)."""

from pathlib import Path

import pyarrow as pa
import pyarrow.fs as pafs
import pyarrow.parquet as pq
import pytest
import shapely
from shapely.geometry import box

from backend.app.services import gba_source
from backend.app.services.geo_utils import point_tm06_to_wgs84, polygon_wgs84_to_tm06
from backend.app.services.obm_source import BuildingSourceError

TILE = "w010_n40_w005_n35"
WEST, SOUTH = -9.140, 38.720
STEP = 0.0005
SIZE = 0.0002


@pytest.mark.parametrize(
    ("bounds", "expected"),
    [
        ((-9.14, 38.72, -9.13, 38.73), ["w010_n40_w005_n35"]),
        ((-9.5, 36.9, -6.1, 42.2), None),
        ((4.0, 6.0, 4.5, 6.5), ["e000_n10_e005_n05"]),
        ((-0.5, 41.0, 0.5, 41.5), None),
    ],
)
def test_tiles_for_bbox(bounds: tuple[float, ...], expected: list[str] | None) -> None:
    tiles = gba_source.tiles_for_bbox(*bounds)
    if expected is not None:
        assert tiles == expected
    elif bounds[0] < 0 < bounds[2]:
        assert tiles == ["w005_n45_e000_n40", "e000_n45_e005_n40"]
    else:
        assert "w010_n45_w005_n40" in tiles
        assert "w010_n40_w005_n35" in tiles
        assert len(tiles) == 2


def _gba_rows(heights: list[float | None]) -> list[dict[str, object]]:
    rows = []
    for i, height in enumerate(heights):
        x = WEST + i * STEP
        footprint = box(x, SOUTH, x + SIZE, SOUTH + SIZE)
        rows.append(
            {
                "geometry": shapely.to_wkb(footprint),
                "height": height,
                "bbox": {"xmin": x, "ymin": SOUTH, "xmax": x + SIZE, "ymax": SOUTH + SIZE},
            }
        )
    return rows


def _write(folder: Path, rows: list[dict[str, object]]) -> None:
    pq.write_table(pa.Table.from_pylist(rows), folder / f"{TILE}.parquet", row_group_size=5)


def _obm_building(index: int, height_m: float | None) -> dict[str, object]:
    x = WEST + index * STEP + SIZE / 2
    centroid = polygon_wgs84_to_tm06(box(x, SOUTH + SIZE / 2, x + 1e-6, SOUTH + SIZE / 2 + 1e-6))
    return {
        "id": str(index),
        "centroid": [centroid.centroid.x, centroid.centroid.y],
        "footprint_m2": 100.0,
        "area_m2": 100.0 if height_m is None else 100.0 * round(height_m / 3),
        "height_m": height_m,
        "floors": None if height_m is None else round(height_m / 3),
        "building_type": "other_or_unknown",
    }


def test_missing_heights_are_filled_and_marked_as_estimates(tmp_path: Path) -> None:
    _write(tmp_path, _gba_rows([9.0, 12.0, -999.0, 7.4, None]))
    table = gba_source.read_tile(
        TILE,
        (WEST - 0.001, SOUTH - 0.001, WEST + 0.01, SOUTH + 0.001),
        pafs.LocalFileSystem(),
        str(tmp_path),
    )
    buildings = [
        _obm_building(0, None),
        _obm_building(1, 6.0),
        _obm_building(2, None),
        _obm_building(3, None),
        _obm_building(4, None),
        _obm_building(20, None),
    ]
    assert table is not None
    assert gba_source.apply_gba_heights(buildings, [table]) == 2

    filled, kept, no_data, rounded, null_height, outside = buildings
    assert (filled["height_m"], filled["floors"], filled["height_source"]) == (
        9.0,
        3,
        "gba_estimate",
    )
    assert filled["area_m2"] == 300.0
    assert (kept["height_m"], kept["height_source"]) == (6.0, "obm")
    assert no_data["height_m"] is None
    assert no_data["height_source"] is None
    assert (rounded["height_m"], rounded["floors"]) == (7.4, 2)
    assert null_height["height_m"] is None
    assert outside["height_m"] is None


def test_low_buildings_have_at_least_one_floor() -> None:
    table = pa.Table.from_pylist(_gba_rows([1.2]))
    buildings = [_obm_building(0, None)]
    gba_source.apply_gba_heights(buildings, [table])
    assert buildings[0]["floors"] == 1
    assert buildings[0]["area_m2"] == 100.0


def test_nothing_to_fill_skips_the_gba_lookup() -> None:
    buildings = [_obm_building(0, 6.0)]
    assert gba_source.apply_gba_heights(buildings, []) == 0
    assert buildings[0]["height_source"] == "obm"


def test_read_tile_prunes_rows_outside_the_area(tmp_path: Path) -> None:
    _write(tmp_path, _gba_rows([5.0] * 40))
    table = gba_source.read_tile(
        TILE,
        (WEST + 0.0004, SOUTH, WEST + 4.5 * STEP, SOUTH + SIZE),
        pafs.LocalFileSystem(),
        str(tmp_path),
    )
    assert table is not None
    assert table.num_rows == 4


def test_read_tile_returns_none_for_a_missing_tile(tmp_path: Path) -> None:
    assert gba_source.read_tile(TILE, (0, 0, 1, 1), pafs.LocalFileSystem(), str(tmp_path)) is None


def test_read_tile_rejects_projected_coordinates(tmp_path: Path) -> None:
    rows = _gba_rows([5.0])
    rows[0]["bbox"] = {
        "xmin": -1_017_000.0,
        "ymin": 4_680_000.0,
        "xmax": -1_016_900.0,
        "ymax": 4_680_100.0,
    }
    _write(tmp_path, rows)
    with pytest.raises(BuildingSourceError):
        gba_source.read_tile(TILE, (-2e6, 0.0, 0.0, 5e6), pafs.LocalFileSystem(), str(tmp_path))


def test_read_tile_wraps_unreadable_files(tmp_path: Path) -> None:
    (tmp_path / f"{TILE}.parquet").write_bytes(b"not parquet")
    with pytest.raises(BuildingSourceError):
        gba_source.read_tile(TILE, (-10, 35, -5, 40), pafs.LocalFileSystem(), str(tmp_path))


def _fake_obm(buildings: list[dict[str, object]]):
    return lambda *_: (buildings, [])


def test_fetch_combines_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path, _gba_rows([9.0, 12.0]))
    monkeypatch.setattr(
        gba_source, "fetch_buildings", _fake_obm([_obm_building(0, None), _obm_building(1, 3.0)])
    )
    polygon = box(WEST - 0.001, SOUTH - 0.001, WEST + 0.01, SOUTH + 0.001)
    buildings, missing = gba_source.fetch_buildings_with_heights(
        polygon, polygon_wgs84_to_tm06(polygon), pafs.LocalFileSystem(), str(tmp_path)
    )
    assert missing == []
    assert [b["height_m"] for b in buildings] == [9.0, 3.0]
    assert [b["height_source"] for b in buildings] == ["gba_estimate", "obm"]
    lon, lat = point_tm06_to_wgs84(*buildings[0]["centroid"])
    assert (round(lon, 3), round(lat, 3)) == (-9.14, 38.72)


def test_fetch_reports_missing_gba_tile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gba_source, "fetch_buildings", _fake_obm([_obm_building(0, None)]))
    polygon = box(WEST, SOUTH, WEST + 0.001, SOUTH + 0.001)
    buildings, missing = gba_source.fetch_buildings_with_heights(
        polygon, polygon_wgs84_to_tm06(polygon), pafs.LocalFileSystem(), str(tmp_path)
    )
    assert missing == [f"gba:{TILE}"]
    assert buildings[0]["height_m"] is None


def test_gba_failure_does_not_fail_the_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / f"{TILE}.parquet").write_bytes(b"not parquet")
    monkeypatch.setattr(gba_source, "fetch_buildings", _fake_obm([_obm_building(0, 6.0)]))
    polygon = box(WEST, SOUTH, WEST + 0.001, SOUTH + 0.001)
    buildings, missing = gba_source.fetch_buildings_with_heights(
        polygon, polygon_wgs84_to_tm06(polygon), pafs.LocalFileSystem(), str(tmp_path)
    )
    assert missing == ["gba:unavailable"]
    assert buildings[0]["height_m"] == 6.0


def test_obm_failure_still_propagates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(*_args: object) -> None:
        raise BuildingSourceError("obm down")

    monkeypatch.setattr(gba_source, "fetch_buildings", failing)
    polygon = box(WEST, SOUTH, WEST + 0.001, SOUTH + 0.001)
    with pytest.raises(BuildingSourceError):
        gba_source.fetch_buildings_with_heights(
            polygon, polygon_wgs84_to_tm06(polygon), pafs.LocalFileSystem(), str(tmp_path)
        )
