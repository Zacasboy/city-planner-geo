"""Tests for the forest service with a mocked DGT ArcGIS FeatureServer."""

import json
import os
from urllib.parse import parse_qs

os.environ.setdefault("SUPABASE_URL", "http://fake")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "fake")
os.environ.setdefault("SUPABASE_SECRET_KEY", "fake")
os.environ.setdefault("SECRET_KEY", "fakesecret")

import httpx
import pytest
from fastapi import HTTPException

from backend.app.config import Settings
from backend.app.services import forest_service as fs
from backend.app.services import http_retry
from backend.app.services.forest_service import ForestService, OverlapRequest

# ~1.2 km x 1.1 km square near Sintra (Portugal), EPSG:4326
QUERY = {
    "type": "Polygon",
    "coordinates": [
        [[-9.40, 38.80], [-9.39, 38.80], [-9.39, 38.81], [-9.40, 38.81], [-9.40, 38.80]]
    ],
}
# Forest-regime polygon covering the west half of QUERY
HALF = {
    "type": "Polygon",
    "coordinates": [
        [[-9.41, 38.79], [-9.395, 38.79], [-9.395, 38.82], [-9.41, 38.82], [-9.41, 38.79]]
    ],
}


def _feature(geometry: dict, codigo: str = "RF001") -> dict:
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "codigo": codigo,
            "nome": "Mata Teste",
            "tipologia": "Perímetro",
            "regime": "Total",
        },
    }


def _service(handler, layer_url: str = "https://dgt.test/FeatureServer/1562") -> ForestService:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = ForestService(http_client=client)
    service.layer_url = layer_url
    return service


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    fs._overlap_cache.clear()

    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(http_retry, "_sleep", no_sleep)


def test_default_url_is_dgt_layer_1562_not_intergeopt():
    url = Settings().DGT_REGIME_FLORESTAL_URL
    assert "dgterritorio.gov.pt" in url and url.endswith("/FeatureServer/1562")
    assert not hasattr(Settings(), "INTERGEOPT_API_BASE")


@pytest.mark.asyncio
async def test_overlap_half_and_request_parameters():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["form"] = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        return httpx.Response(200, json={"type": "FeatureCollection", "features": [_feature(HALF)]})

    service = _service(handler)
    response = await service.check_overlap(OverlapRequest(geojson=QUERY))

    assert seen["url"] == "https://dgt.test/FeatureServer/1562/query"
    form = seen["form"]
    assert form["inSR"] == "4326" and form["outSR"] == "4326" and form["f"] == "geojson"
    assert form["geometryType"] == "esriGeometryPolygon"
    rings = json.loads(form["geometry"])["rings"][0]
    xs, ys = [p[0] for p in rings], [p[1] for p in rings]
    signed = sum(xs[i] * ys[i + 1] - xs[i + 1] * ys[i] for i in range(len(xs) - 1))
    assert signed < 0  # Esri outer rings are clockwise
    assert response.percentage_covered == pytest.approx(50.0, abs=1.0)
    assert 0.4 < response.overlap_area_km2 < 0.6
    assert response.details["license_status"] == "unconfirmed"
    assert response.details["features"][0]["codigo"] == "RF001"
    assert any("Licença" in w for w in response.details["warnings"])
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_no_overlap_returns_zero_with_scope_warning():
    service = _service(
        lambda r: httpx.Response(200, json={"type": "FeatureCollection", "features": []})
    )
    response = await service.check_overlap(OverlapRequest(geojson=QUERY))
    assert response.overlap_area_km2 == 0.0 and response.percentage_covered == 0.0
    assert any("apenas Portugal" in w for w in response.details["warnings"])
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_pagination_follows_exceeded_transfer_limit():
    pages: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = parse_qs(request.content.decode())["resultOffset"][0]
        pages.append(offset)
        if offset == "0":
            return httpx.Response(
                200, json={"features": [_feature(HALF, "A")], "exceededTransferLimit": True}
            )
        return httpx.Response(200, json={"features": [_feature(HALF, "B")]})

    service = _service(handler)
    response = await service.check_overlap(OverlapRequest(geojson=QUERY))
    assert pages == ["0", "2000"]
    assert response.details["features_count"] == 2
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_result_is_cached_for_same_area():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"features": []})

    service = _service(handler)
    await service.check_overlap(OverlapRequest(geojson=QUERY))
    await service.check_overlap(OverlapRequest(geojson=QUERY))
    assert calls["n"] == 1
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_arcgis_error_in_http_200_becomes_502():
    service = _service(
        lambda r: httpx.Response(200, json={"error": {"code": 400, "message": "bad"}})
    )
    with pytest.raises(HTTPException) as exc:
        await service.check_overlap(OverlapRequest(geojson=QUERY))
    assert exc.value.status_code == 502
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_http_error_retries_then_502():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, text="Unavailable")

    service = _service(handler)
    with pytest.raises(HTTPException) as exc:
        await service.check_overlap(OverlapRequest(geojson=QUERY))
    assert exc.value.status_code == 502 and "503" in exc.value.detail
    assert calls["n"] == http_retry.MAX_ATTEMPTS
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_network_error_becomes_503():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    service = _service(handler)
    with pytest.raises(HTTPException) as exc:
        await service.check_overlap(OverlapRequest(geojson=QUERY))
    assert exc.value.status_code == 503
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_non_polygon_is_422():
    service = _service(lambda r: httpx.Response(200, json={"features": []}))
    with pytest.raises(HTTPException) as exc:
        await service.check_overlap(
            OverlapRequest(geojson={"type": "Point", "coordinates": [0, 0]})
        )
    assert exc.value.status_code == 422
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_missing_url_is_503():
    service = _service(lambda r: httpx.Response(200, json={}), layer_url="")
    with pytest.raises(HTTPException) as exc:
        await service.check_overlap(OverlapRequest(geojson=QUERY))
    assert exc.value.status_code == 503 and "not configured" in exc.value.detail
    await service.http_client.aclose()


@pytest.mark.asyncio
async def test_service_close_closes_owned_client():
    service = ForestService()
    assert service._owns_client is True
    await service.close()
