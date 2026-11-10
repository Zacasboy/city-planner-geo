"""Testes do catálogo de materiais (ÖKOBAUDAT) e da rota /materials/suggest."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import materials_service as service

CATEGORIES = {"structural", "reinforcement", "masonry", "insulation", "glazing"}


def _entry(amount: float, unit: str, density: float | None, total: float = 100.0) -> dict:
    return {
        "id": "x",
        "reference_amount": amount,
        "reference_unit": unit,
        "density_kg_m3": density,
        "gwp_a1_a3_per_reference": {"gwp_total": total, "gwp_fossil": None},
    }


@pytest.mark.parametrize(
    ("entry", "basis", "expected"),
    [
        (_entry(1000, "kg", 7850), "per_kg", 0.1),
        (_entry(1000, "kg", 7850), "per_m3", 785.0),
        (_entry(1000, "kg", None), "per_m3", None),
        (_entry(2, "m3", 500), "per_m3", 50.0),
        (_entry(2, "m3", 500), "per_kg", 0.1),
        (_entry(2, "m3", None), "per_kg", None),
        (_entry(1, "qm", None), "per_m2", 100.0),
        (_entry(1, "qm", None), "per_kg", None),
        (_entry(1, "m3", 500), "per_m2", None),
    ],
)
def test_gwp_on_basis_converts_units(entry: dict, basis: str, expected: float | None) -> None:
    value = service.gwp_on_basis(entry, "gwp_total", basis)  # type: ignore[arg-type]
    assert value == pytest.approx(expected) if expected is not None else value is None


def test_missing_indicator_has_no_value() -> None:
    assert service.gwp_on_basis(_entry(1, "kg", 1), "gwp_fossil", "per_kg") is None


def test_catalog_is_consistent() -> None:
    catalog = service.load_catalog()
    materials = catalog["materials"]
    ids = [m["id"] for m in materials]
    assert len(ids) == len(set(ids))
    assert {m["category"] for m in materials} == CATEGORIES
    assert set(service.EXPOSURE_NOTES) <= set(ids)
    assert catalog["source"]["module"] == "A1-A3"
    for material in materials:
        assert material["dataset"]["uuid"]
        assert material["gwp_a1_a3_per_reference"]["gwp_total"] is not None
        assert material["reference_amount"] > 0


def test_concrete_carbon_rises_with_strength_class() -> None:
    response = service.suggest_materials("structural", "per_m3")
    by_id = {r.id: r.gwp for r in response.results}
    ladder = [by_id[k] for k in ("concrete-c20-25", "concrete-c25-30", "concrete-c30-37")]
    assert ladder == sorted(ladder)
    assert by_id["concrete-c30-37"] < by_id["concrete-c50-60"]
    assert [r.gwp for r in response.results] == sorted(r.gwp for r in response.results)


def test_timber_total_is_negative_but_fossil_is_positive() -> None:
    results = {r.id: r for r in service.suggest_materials("structural", "per_m3").results}
    glulam = results["glulam-softwood"]
    assert glulam.gwp_fossil is not None
    assert glulam.gwp_fossil > 0
    assert glulam.gwp_total is not None
    assert glulam.gwp_total < 0
    assert glulam.gwp == glulam.gwp_fossil
    total = service.suggest_materials("structural", "per_m3", metric="total")
    assert total.results[0].id in {"glulam-softwood", "solid-construction-timber"}


def test_steel_uses_the_standard_density_for_volume() -> None:
    results = {r.id: r for r in service.suggest_materials("structural", "per_m3").results}
    steel = results["structural-steel-sections"]
    assert steel.density_kg_m3 == 7850
    assert steel.gwp == pytest.approx(steel.gwp_fossil)
    per_kg = {r.id: r for r in service.suggest_materials("structural", "per_kg").results}
    assert per_kg["structural-steel-sections"].gwp == pytest.approx(steel.gwp / 7850, rel=1e-3)


def test_glazing_only_has_values_per_m2() -> None:
    per_m2 = service.suggest_materials("glazing", "per_m2")
    assert {r.id for r in per_m2.results} == {"double-glazing", "triple-glazing"}
    assert per_m2.results[0].id == "double-glazing"
    per_kg = service.suggest_materials("glazing", "per_kg")
    assert per_kg.results == []
    assert set(per_kg.unavailable_on_basis) == {"double-glazing", "triple-glazing"}


def test_exposure_adds_standard_based_notes_only_when_asked() -> None:
    plain = service.suggest_materials("reinforcement", "per_kg")
    coastal = service.suggest_materials("reinforcement", "per_kg", exposure="coastal")
    assert plain.results[0].notes == []
    assert "EN 206" in coastal.results[0].notes[0]


def test_user_costs_are_echoed_and_can_sort() -> None:
    costs = {"concrete-c30-37": 80.0, "concrete-c20-25": 95.0}
    response = service.suggest_materials("structural", "per_m3", sort="cost", costs=costs)
    assert [r.id for r in response.results[:2]] == ["concrete-c30-37", "concrete-c20-25"]
    assert response.results[0].user_cost == 80.0
    assert all(r.user_cost is None for r in response.results[2:])


def test_limit_and_notes_and_source() -> None:
    response = service.suggest_materials("insulation", "per_m3", limit=3)
    assert len(response.results) == 3
    assert any("same function" in n for n in response.notes)
    assert any("No default costs" in n for n in response.notes)
    assert response.source["name"] == "ÖKOBAUDAT"


def test_suggest_requires_authentication() -> None:
    response = TestClient(app).get("/materials/suggest", params={"category": "structural"})
    assert response.status_code in (401, 403)


def test_suggest_route_returns_ranked_materials(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    response = TestClient(app).get(
        "/materials/suggest",
        params={"category": "masonry", "basis": "per_m3", "limit": 2},
        headers=auth_headers("user-1"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "masonry"
    assert len(body["results"]) == 2
    assert body["results"][0]["gwp"] <= body["results"][1]["gwp"]
    assert body["results"][0]["dataset"]["uuid"]


def test_suggest_route_accepts_user_costs(auth_headers: Callable[[str], dict[str, str]]) -> None:
    response = TestClient(app).get(
        "/materials/suggest?category=masonry&sort=cost&cost=facing-brick:120",
        headers=auth_headers("user-1"),
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "facing-brick"


@pytest.mark.parametrize(
    "query",
    [
        "category=nope",
        "category=masonry&basis=per_ton",
        "category=masonry&cost=facing-brick",
        "category=masonry&cost=facing-brick:abc",
        "category=masonry&cost=facing-brick:-1",
        "category=masonry&limit=0",
    ],
)
def test_suggest_route_rejects_bad_input(
    query: str, auth_headers: Callable[[str], dict[str, str]]
) -> None:
    response = TestClient(app).get(f"/materials/suggest?{query}", headers=auth_headers("user-1"))
    assert response.status_code == 422
