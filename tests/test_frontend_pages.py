"""Testes das páginas Streamlit com o AppTest (sem navegador nem backend)."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES = REPO_ROOT / "frontend" / "pages"
# Teto, não duração típica: o primeiro import do folium em frio pode demorar.
SCRIPT_TIMEOUT_S = 120

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _page(name: str, user: object | None = None) -> AppTest:
    app = AppTest.from_file(str(PAGES / name), default_timeout=SCRIPT_TIMEOUT_S)
    app.session_state["user"] = user
    app.session_state["access_token"] = "token-de-teste" if user else None
    return app


LOGGED_IN = SimpleNamespace(email="ana@exemplo.pt")


def _without_supabase_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simula a falta de credenciais, mesmo que exista `.streamlit/secrets.toml`."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setattr("frontend.components.supabase_client.get_setting", lambda *_a, **_k: "")


@pytest.mark.parametrize(
    "name",
    [
        "home.py",
        "geo.py",
        "ecology.py",
        "forest.py",
        "morphology.py",
        "structural.py",
        "orchestration.py",
    ],
)
def test_page_runs_without_exception(name: str) -> None:
    app = _page(name, LOGGED_IN).run()
    assert not app.exception


def test_reports_page_runs_without_exception() -> None:
    app = _page("reports.py", LOGGED_IN).run()
    assert not app.exception
    assert app.title[0].value.endswith("Structural Analysis Reports")


def test_home_page_asks_for_login_when_anonymous() -> None:
    app = _page("home.py").run()
    assert not app.exception
    assert any("log in" in w.value for w in app.warning)


def test_login_without_credentials_stops_with_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _without_supabase_config(monkeypatch)
    app = _page("login.py").run()
    assert not app.exception
    assert any("credentials not configured" in w.value for w in app.warning)


def test_signup_without_credentials_stops_with_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _without_supabase_config(monkeypatch)
    app = _page("signup.py").run()
    assert not app.exception
    assert any("credentials not configured" in w.value for w in app.warning)


def test_login_stores_user_and_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://fake")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_fake")
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=LOGGED_IN, session=SimpleNamespace(access_token="acc", refresh_token="ref")
    )
    with patch("frontend.components.supabase_client.create_client", return_value=client):
        app = _page("login.py").run()
        app.text_input[0].set_value("ana@exemplo.pt")
        app.text_input[1].set_value("segredo")
        app.button[0].click().run()
    assert app.session_state["access_token"] == "acc"
    assert app.session_state["user"].email == "ana@exemplo.pt"


def test_login_without_session_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://fake")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_fake")
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(user=LOGGED_IN, session=None)
    with patch("frontend.components.supabase_client.create_client", return_value=client):
        app = _page("login.py").run()
        app.text_input[0].set_value("ana@exemplo.pt")
        app.text_input[1].set_value("segredo")
        app.button[0].click().run()
    assert not app.exception
    assert any("Login failed" in e.value for e in app.error)


def test_structural_page_shows_backend_results() -> None:
    result = {
        "max_deflection": 0.0417,
        "max_stress": 1.0e6,
        "utilization_ratio": 0.004,
        "details": {"analysis_method": "Analytical", "beam_length_m": 5.0},
    }
    response = MagicMock(status_code=200)
    response.json.return_value = result
    with patch("requests.post", return_value=response) as post:
        app = _page("structural.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert not app.exception
    assert post.call_args.kwargs["json"]["youngs_modulus"] == 200e9
    assert post.call_args.kwargs["json"]["include_self_weight"] is True
    assert [m.value for m in app.metric][0] == "41.70 mm"


AREA = {
    "type": "Polygon",
    "coordinates": [
        [[-9.14, 38.72], [-9.14, 38.73], [-9.13, 38.73], [-9.13, 38.72], [-9.14, 38.72]]
    ],
}
AREA_SPECIES = {
    "total_records": 12,
    "records_excluded_by_license": 3,
    "allowed_licenses": ["CC0_1_0", "CC_BY_4_0"],
    "species": [
        {"species_key": 1, "scientific_name": "Passer domesticus", "records": 8},
        {"species_key": 2, "scientific_name": "Turdus merula", "records": 4},
    ],
    "notes": ["Nota de teste."],
}


def test_ecology_page_asks_for_a_polygon_first() -> None:
    with patch("frontend.components.map_selector.render_map_selector", return_value=None):
        app = _page("ecology.py", LOGGED_IN).run()
    assert not app.exception
    assert any("draw a polygon" in i.value for i in app.info)
    assert not any(b.label.startswith("Query") for b in app.button)


def test_ecology_page_queries_backend_with_token_and_shows_results() -> None:
    response = MagicMock(status_code=200)
    response.json.return_value = AREA_SPECIES
    with (
        patch("frontend.components.map_selector.render_map_selector", return_value=AREA),
        patch("requests.post", return_value=response) as post,
    ):
        app = _page("ecology.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert not app.exception
    call = post.call_args
    assert call.args[0].endswith("/ecology/area-species")
    assert call.kwargs["json"]["geojson"] == AREA
    assert call.kwargs["headers"] == {"Authorization": "Bearer token-de-teste"}
    assert [m.value for m in app.metric] == ["2", "12", "3"]
    assert any("observation effort" in c.value for c in app.caption)
    assert len(app.dataframe) == 1


def test_ecology_page_shows_backend_errors() -> None:
    response = MagicMock(status_code=401)
    with (
        patch("frontend.components.map_selector.render_map_selector", return_value=AREA),
        patch("requests.post", return_value=response),
    ):
        app = _page("ecology.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert not app.exception
    assert any("log in" in e.value for e in app.error)
    assert len(app.metric) == 0


def test_ecology_page_rejects_invalid_polygon() -> None:
    with patch(
        "frontend.components.map_selector.render_map_selector",
        return_value={"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [2, 2], [3, 3]]]},
    ):
        app = _page("ecology.py", LOGGED_IN).run()
    assert any("Invalid polygon" in e.value for e in app.error)
    assert not any(b.label.startswith("Query") for b in app.button)


FOREST_OVERLAP = {
    "overlap_area_km2": 0.5,
    "percentage_covered": 42.5,
    "details": {
        "features_count": 1,
        "features": [
            {
                "codigo": "X1",
                "nome": "Mata Teste",
                "tipologia": "Perímetro",
                "regime": "Parcial",
                "overlap_km2": 0.5,
            }
        ],
        "warnings": ["Aviso de teste."],
    },
}


def test_forest_page_asks_for_a_polygon_first() -> None:
    with patch("frontend.components.map_selector.render_map_selector", return_value=None):
        app = _page("forest.py", LOGGED_IN).run()
    assert not app.exception
    assert any("draw a polygon" in i.value for i in app.info)
    assert not any(b.label.startswith("Check") for b in app.button)


def test_forest_page_queries_backend_and_shows_overlap() -> None:
    response = MagicMock(status_code=200)
    response.json.return_value = FOREST_OVERLAP
    with (
        patch("frontend.components.map_selector.render_map_selector", return_value=AREA),
        patch("requests.post", return_value=response) as post,
    ):
        app = _page("forest.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert not app.exception
    call = post.call_args
    assert call.args[0].endswith("/forest/overlap")
    assert call.kwargs["json"] == {"geojson": AREA}
    assert call.kwargs["headers"] == {"Authorization": "Bearer token-de-teste"}
    assert [m.value for m in app.metric] == ["50.00 ha", "42.5 %", "1"]
    assert any("Aviso de teste" in c.value for c in app.caption)
    assert len(app.dataframe) == 1


def test_forest_page_without_overlap_says_so() -> None:
    empty = FOREST_OVERLAP | {
        "overlap_area_km2": 0.0,
        "percentage_covered": 0.0,
        "details": FOREST_OVERLAP["details"] | {"features_count": 0, "features": []},  # type: ignore[dict-item]
    }
    response = MagicMock(status_code=200)
    response.json.return_value = empty
    with (
        patch("frontend.components.map_selector.render_map_selector", return_value=AREA),
        patch("requests.post", return_value=response),
    ):
        app = _page("forest.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert not app.exception
    assert any("No forest-regime area" in i.value for i in app.info)
    assert len(app.dataframe) == 0


def test_forest_page_shows_backend_errors() -> None:
    response = MagicMock(status_code=503)
    response.json.return_value = {"error": {"message": "DGT unavailable"}}
    with (
        patch("frontend.components.map_selector.render_map_selector", return_value=AREA),
        patch("requests.post", return_value=response),
    ):
        app = _page("forest.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert any("DGT unavailable" in e.value for e in app.error)
    assert len(app.metric) == 0


MORPHOLOGY = {
    "analysis_area_m2": 100000.0,
    "building_count": 40,
    "density_metrics": {"building_density_per_km2": 400.0, "floor_area_ratio": 0.5},
    "height_metrics": {"average_height_m": 9.0},
    "height_percentiles": {"height_50th_percentile": 9.0},
    "occupation_metrics": {"built_up_percentage": 31.5},
    "building_type_metrics": {"residential_percentage": 50.0, "commercial_percentage": 10.0},
    "data_source_used": "OpenBuildingMap",
    "details": {
        "height_coverage_percent": 19.0,
        "attribution": "OpenBuildingMap (test)",
        "notes": ["Nota de teste"],
    },
}


def test_morphology_page_sends_a_feature_and_shows_metrics() -> None:
    response = MagicMock(status_code=200)
    response.json.return_value = MORPHOLOGY
    with (
        patch("frontend.components.map_selector.render_map_selector", return_value=AREA),
        patch("requests.post", return_value=response) as post,
    ):
        app = _page("morphology.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert not app.exception
    call = post.call_args
    assert call.args[0].endswith("/morphology/analyze")
    assert call.kwargs["json"]["geojson"] == {
        "type": "Feature",
        "geometry": AREA,
        "properties": {},
    }
    assert [m.value for m in app.metric] == ["40", "31.5 %", "400 /km²", "9.0 m"]
    assert any("Only 19 %" in w.value for w in app.warning)
    chart = str(app.get("vega_lite_chart")[0].proto)
    assert "other / unknown" in chart
    assert "40" in chart and "domain" in chart
    assert any("OpenBuildingMap (test)" in c.value for c in app.caption)


def test_morphology_page_shows_backend_errors() -> None:
    response = MagicMock(status_code=503)
    response.json.return_value = {"error": {"message": "Building data source unavailable"}}
    with (
        patch("frontend.components.map_selector.render_map_selector", return_value=AREA),
        patch("requests.post", return_value=response),
    ):
        app = _page("morphology.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert any("unavailable" in e.value for e in app.error)
    assert len(app.metric) == 0


def test_reports_page_sends_the_session_token() -> None:
    analysis = MagicMock(status_code=200)
    analysis.json.return_value = {
        "max_deflection": 0.04,
        "max_stress": 1e6,
        "utilization_ratio": 0.004,
        "details": {},
    }
    created = MagicMock(status_code=201)
    created.json.return_value = {"report_id": "11111111-2222-3333-4444-555555555555"}
    with patch("requests.post", side_effect=[analysis, created]) as post:
        app = _page("reports.py", LOGGED_IN).run()
        app.button[0].click().run()
    assert not app.exception
    report_call = post.call_args_list[1]
    assert report_call.args[0].endswith("/reports/structural")
    assert report_call.kwargs["headers"] == {"Authorization": "Bearer token-de-teste"}
    assert "11111111" in app.session_state["last_report_id"]


def test_reports_page_sends_ecology_when_available() -> None:
    analysis = MagicMock(status_code=200)
    analysis.json.return_value = {"max_deflection": 0, "max_stress": 0, "utilization_ratio": 0}
    created = MagicMock(status_code=201)
    created.json.return_value = {"report_id": "11111111-2222-3333-4444-555555555555"}
    ecology = {"total_records": 1, "species": []}
    with patch("requests.post", side_effect=[analysis, created]) as post:
        app = _page("reports.py", LOGGED_IN)
        app.session_state["ecology_result"] = {"polygon": {}, "data": ecology}
        app.run()
        assert app.checkbox[0].value is True
        app.button[0].click().run()
    assert post.call_args_list[1].kwargs["json"]["ecology"] == ecology


def test_reports_page_without_ecology_disables_checkbox() -> None:
    app = _page("reports.py", LOGGED_IN).run()
    assert app.checkbox[0].disabled


def test_app_shows_login_when_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    _without_supabase_config(monkeypatch)
    app = AppTest.from_file(
        str(REPO_ROOT / "frontend" / "app.py"), default_timeout=SCRIPT_TIMEOUT_S
    ).run()
    assert not app.exception
    assert app.title[0].value.endswith("Login to City Planner Geo")


def test_app_shows_home_when_logged_in() -> None:
    app = AppTest.from_file(
        str(REPO_ROOT / "frontend" / "app.py"), default_timeout=SCRIPT_TIMEOUT_S
    )
    app.session_state["user"] = LOGGED_IN
    app.run()
    assert not app.exception
    assert "Home" in app.title[0].value


def test_anonymous_user_can_navigate_between_login_and_signup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://fake")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "fake")
    with patch("frontend.components.supabase_client.create_client", return_value=MagicMock()):
        app = AppTest.from_file(
            str(REPO_ROOT / "frontend" / "app.py"), default_timeout=SCRIPT_TIMEOUT_S
        ).run()
        next(b for b in app.button if "Sign up" in b.label).click().run()
        assert not app.exception
        assert "Sign Up" in app.title[0].value
        next(b for b in app.button if "Login" in b.label).click().run()
        assert not app.exception
        assert app.title[0].value.endswith("Login to City Planner Geo")
