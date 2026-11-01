"""Testes do cliente do painel ecológico."""

from unittest.mock import MagicMock, patch

import requests

from frontend.components.ecology_client import fetch_area_species

AREA = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]}


def test_success_returns_the_payload() -> None:
    response = MagicMock(status_code=200)
    response.json.return_value = {"species": []}
    with patch("requests.post", return_value=response):
        assert fetch_area_species(AREA) == ({"species": []}, "")


def test_backend_error_message_is_extracted() -> None:
    response = MagicMock(status_code=502)
    response.json.return_value = {"error": {"message": "GBIF down"}}
    with patch("requests.post", return_value=response):
        data, error = fetch_area_species(AREA)
    assert data is None
    assert error == "Backend error 502: GBIF down"


def test_unparseable_error_body_does_not_crash() -> None:
    response = MagicMock(status_code=500)
    response.json.side_effect = ValueError
    with patch("requests.post", return_value=response):
        assert fetch_area_species(AREA)[1] == "Backend error 500: unexpected response"


def test_network_failure_is_reported() -> None:
    with patch("requests.post", side_effect=requests.ConnectionError):
        data, error = fetch_area_species(AREA)
    assert data is None
    assert "Could not reach the backend" in error
