"""Testes do levantamento de quantidades IFC (T2.4) com modelos gerados em código."""

from collections.abc import Callable
from typing import Any

import ifcopenshell
import ifcopenshell.api as ifc_api
import pytest
from fastapi.testclient import TestClient

from backend.app.api import bim as bim_api
from backend.app.main import app
from backend.app.services import bim_service as service

WALL_LENGTH_M = 5.0
WALL_HEIGHT_M = 3.0
WALL_THICKNESS_M = 0.2
WALL_VOLUME_M3 = WALL_LENGTH_M * WALL_HEIGHT_M * WALL_THICKNESS_M
DECLARED_LENGTH_MM = 5000.0  # o modelo de teste usa milímetros como unidade de comprimento


def _new_model() -> tuple[ifcopenshell.file, Any, Any]:
    model = ifc_api.run("project.create_file", version="IFC4")
    ifc_api.run("root.create_entity", model, ifc_class="IfcProject", name="Test project")
    ifc_api.run("unit.assign_unit", model)
    context = ifc_api.run("context.add_context", model, context_type="Model")
    body = ifc_api.run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context,
    )
    return model, body, context


def _add_wall(
    model: ifcopenshell.file,
    body: Any,
    ifc_class: str = "IfcWall",
    material: str | None = None,
    declared_volume: float | None = None,
    declared_length: float | None = None,
    geometry: bool = True,
) -> Any:
    element = ifc_api.run("root.create_entity", model, ifc_class=ifc_class, name="E")
    if geometry:
        representation = ifc_api.run(
            "geometry.add_wall_representation",
            model,
            context=body,
            length=WALL_LENGTH_M,
            height=WALL_HEIGHT_M,
            thickness=WALL_THICKNESS_M,
        )
        ifc_api.run(
            "geometry.assign_representation", model, product=element, representation=representation
        )
    if material:
        material_entity = ifc_api.run("material.add_material", model, name=material)
        ifc_api.run("material.assign_material", model, products=[element], material=material_entity)
    properties = {}
    if declared_volume is not None:
        properties["NetVolume"] = declared_volume
    if declared_length is not None:
        properties["Length"] = declared_length
    if properties:
        qto = ifc_api.run("pset.add_qto", model, product=element, name="Qto_WallBaseQuantities")
        ifc_api.run("pset.edit_qto", model, qto=qto, properties=properties)
    return element


def _to_bytes(model: ifcopenshell.file) -> bytes:
    return model.to_string().encode("utf-8")


@pytest.fixture
def sample_ifc() -> bytes:
    model, body, _ = _new_model()
    _add_wall(
        model,
        body,
        material="Concrete C25/30",
        declared_volume=2.5,
        declared_length=DECLARED_LENGTH_MM,
    )
    _add_wall(model, body, material="Concrete C25/30")
    _add_wall(model, body, ifc_class="IfcColumn", geometry=False)
    return _to_bytes(model)


def _by_class(result: Any) -> dict[str, Any]:
    return {item.ifc_class: item for item in result.by_class}


def test_declared_volume_is_preferred_over_geometry(sample_ifc: bytes) -> None:
    wall = _by_class(service.extract_quantities(sample_ifc))["IfcWall"]
    assert wall.volume_declared_count == 1
    assert wall.volume_computed_count == 1
    assert wall.volume_m3 == pytest.approx(2.5 + WALL_VOLUME_M3, rel=1e-3)
    assert wall.length_m == pytest.approx(5.0)


def test_element_without_volume_is_counted_not_invented(sample_ifc: bytes) -> None:
    column = _by_class(service.extract_quantities(sample_ifc))["IfcColumn"]
    assert (column.count, column.without_volume_count, column.volume_m3) == (1, 1, 0.0)


def test_groups_volume_by_material(sample_ifc: bytes) -> None:
    result = service.extract_quantities(sample_ifc)
    materials = {m.material: m for m in result.by_material}
    assert materials["Concrete C25/30"].count == 2
    assert materials["Concrete C25/30"].volume_m3 == pytest.approx(2.5 + WALL_VOLUME_M3, rel=1e-3)
    assert materials[service.NO_MATERIAL].count == 1
    assert result.total_volume_m3 == pytest.approx(2.5 + WALL_VOLUME_M3, rel=1e-3)


def test_response_metadata(sample_ifc: bytes) -> None:
    result = service.extract_quantities(sample_ifc)
    assert result.schema_name == "IFC4"
    assert result.project_name == "Test project"
    assert result.elements_total == 3
    assert result.notes == service.NOTES


def test_composite_material_is_flagged() -> None:
    model, body, _ = _new_model()
    element = _add_wall(model, body, material="Concrete")
    other = ifc_api.run("material.add_material", model, name="Steel")
    constituents = ifc_api.run(
        "material.add_material_set", model, name="Mix", set_type="IfcMaterialConstituentSet"
    )
    for material in (model.by_type("IfcMaterial")[0], other):
        ifc_api.run(
            "material.add_constituent", model, constituent_set=constituents, material=material
        )
    ifc_api.run(
        "material.assign_material",
        model,
        products=[element],
        type="IfcMaterialConstituentSet",
        material=constituents,
    )
    result = service.extract_quantities(_to_bytes(model))
    assert [(m.material, m.composite) for m in result.by_material] == [("Concrete + Steel", True)]


def test_declared_values_follow_the_model_unit_scale(
    monkeypatch: pytest.MonkeyPatch, sample_ifc: bytes
) -> None:
    scales = {"length": 1.0, "area": 1.0, "volume": 2.0}
    monkeypatch.setattr(service, "_unit_scales", lambda model: scales)
    wall = _by_class(service.extract_quantities(sample_ifc))["IfcWall"]
    assert wall.volume_m3 == pytest.approx(2.5 * 2.0 + WALL_VOLUME_M3, rel=1e-3)


def test_geometry_budget_limits_computation_and_warns(
    monkeypatch: pytest.MonkeyPatch, sample_ifc: bytes
) -> None:
    monkeypatch.setattr(service, "MAX_COMPUTED_ELEMENTS", 0)
    result = service.extract_quantities(sample_ifc)
    assert _by_class(result)["IfcWall"].without_volume_count == 1
    assert result.warnings


@pytest.mark.parametrize("payload", [b"", b"not an ifc", b"ISO-10303-21;\nGARBAGE"])
def test_invalid_input_raises(payload: bytes) -> None:
    with pytest.raises(service.InvalidIfcError):
        service.extract_quantities(payload)


def test_route_returns_quantities(
    auth_headers: Callable[[str], dict[str, str]], sample_ifc: bytes
) -> None:
    response = TestClient(app).post(
        "/bim/quantities", content=sample_ifc, headers=auth_headers("user-1")
    )
    assert response.status_code == 200
    assert response.json()["elements_total"] == 3


def test_route_rejects_invalid_file(auth_headers: Callable[[str], dict[str, str]]) -> None:
    response = TestClient(app).post(
        "/bim/quantities", content=b"hello", headers=auth_headers("user-1")
    )
    assert response.status_code == 422


def test_route_rejects_oversized_body(
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: Callable[[str], dict[str, str]],
    sample_ifc: bytes,
) -> None:
    monkeypatch.setattr(bim_api, "MAX_IFC_BYTES", 100)
    response = TestClient(app).post(
        "/bim/quantities", content=sample_ifc, headers=auth_headers("user-1")
    )
    assert response.status_code == 413
