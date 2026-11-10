"""Levantamento de quantidades de modelos IFC com o IfcOpenShell (T2.4).

Lê primeiro as quantidades declaradas pelo autor do modelo (``IfcElementQuantity``).
Quando um elemento não declara volume, calcula-o a partir da geometria. Cada valor
indica a sua origem (declarado ou calculado) na contagem por classe.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as element_util
import ifcopenshell.util.shape as shape_util
import ifcopenshell.util.unit as unit_util

from backend.app.services.bim_models import (
    BimQuantitiesResponse,
    ClassQuantities,
    MaterialQuantities,
)

logger = logging.getLogger(__name__)

STEP_MAGIC = b"ISO-10303-21"
MAX_COMPUTED_ELEMENTS = 1500
NO_MATERIAL = "(no material)"
ROUND_DIGITS = 4

VOLUME_NAMES = ("NetVolume", "GrossVolume")
AREA_NAMES = ("NetArea", "GrossArea", "NetSideArea", "GrossSideArea")
LENGTH_NAMES = ("Length",)

NOTES = [
    "Quantities are read from the model: declared values come from its IfcElementQuantity, "
    "computed volumes from the geometry. Accuracy depends on how the model was authored.",
    "Area and length are only reported when the model declares them; which area is reported "
    "(net, gross, side) depends on the element class.",
    "Elements with several materials are grouped under a combined label; their volume is not "
    "split between materials.",
]


class InvalidIfcError(ValueError):
    """O ficheiro não é um IFC (SPF) legível."""


@dataclass
class _Totals:
    count: int = 0
    volume: float = 0.0
    area: float = 0.0
    length: float = 0.0
    declared: int = 0
    computed: int = 0
    missing: int = 0


@dataclass
class _Context:
    scales: dict[str, float]
    settings: Any
    computed_budget: int
    warnings: list[str] = field(default_factory=list)


def open_model(data: bytes) -> ifcopenshell.file:
    """Abre um IFC em formato STEP a partir dos bytes.

    Raises:
        InvalidIfcError: Se o conteúdo não for um ficheiro IFC-SPF válido.
    """
    if not data.lstrip().startswith(STEP_MAGIC):
        raise InvalidIfcError("Not an IFC STEP file (.ifc): header ISO-10303-21 not found")
    try:
        return ifcopenshell.file.from_string(data.decode("utf-8", errors="replace"))
    except (ifcopenshell.Error, RuntimeError, ValueError) as error:
        raise InvalidIfcError(f"Unreadable IFC file: {error}") from error


def _building_elements(model: ifcopenshell.file) -> list[Any]:
    base = "IfcBuiltElement" if model.schema.startswith("IFC4X3") else "IfcBuildingElement"
    return list(model.by_type(base))


def _unit_scales(model: ifcopenshell.file) -> dict[str, float]:
    return {
        "length": unit_util.calculate_unit_scale(model, "LENGTHUNIT"),
        "area": unit_util.calculate_unit_scale(model, "AREAUNIT"),
        "volume": unit_util.calculate_unit_scale(model, "VOLUMEUNIT"),
    }


def _declared(element: Any, names: tuple[str, ...]) -> float | None:
    quantity_sets = element_util.get_psets(element, qtos_only=True)
    for name in names:
        for properties in quantity_sets.values():
            value = properties.get(name)
            if isinstance(value, int | float) and value > 0:
                return float(value)
    return None


def _computed_volume_m3(element: Any, context: _Context) -> float | None:
    if context.computed_budget <= 0:
        return None
    context.computed_budget -= 1
    try:
        shape: Any = ifcopenshell.geom.create_shape(context.settings, element)
        return abs(float(shape_util.get_volume(shape.geometry)))
    except (RuntimeError, ValueError, AttributeError) as error:
        logger.info("No geometry for %s: %s", element.is_a(), error)
        return None


def _material_label(element: Any) -> tuple[str, bool]:
    names = sorted({m.Name for m in element_util.get_materials(element) if m.Name})
    if not names:
        return NO_MATERIAL, False
    return " + ".join(names), len(names) > 1


def _element_volume_m3(element: Any, context: _Context, totals: _Totals) -> float | None:
    declared = _declared(element, VOLUME_NAMES)
    if declared is not None:
        totals.declared += 1
        return declared * context.scales["volume"]
    computed = _computed_volume_m3(element, context)
    if computed is None:
        totals.missing += 1
        return None
    totals.computed += 1
    return computed


def _scaled(value: float | None, scale: float) -> float:
    return value * scale if value is not None else 0.0


def extract_quantities(data: bytes) -> BimQuantitiesResponse:
    """Calcula quantidades por classe e por material de um modelo IFC.

    Args:
        data: Conteúdo de um ficheiro ``.ifc`` (STEP).

    Returns:
        Quantidades agregadas, com avisos e notas sobre a origem dos valores.

    Raises:
        InvalidIfcError: Se o ficheiro não for um IFC legível.
    """
    model = open_model(data)
    settings: Any = ifcopenshell.geom.settings()  # type: ignore[no-untyped-call]
    context = _Context(
        scales=_unit_scales(model),
        settings=settings,
        computed_budget=MAX_COMPUTED_ELEMENTS,
    )
    by_class: dict[str, _Totals] = defaultdict(_Totals)
    by_material: dict[tuple[str, bool], _Totals] = defaultdict(_Totals)

    elements = _building_elements(model)
    for element in elements:
        totals = by_class[element.is_a()]
        totals.count += 1
        volume = _element_volume_m3(element, context, totals)
        totals.volume += volume or 0.0
        totals.area += _scaled(_declared(element, AREA_NAMES), context.scales["area"])
        totals.length += _scaled(_declared(element, LENGTH_NAMES), context.scales["length"])
        material = by_material[_material_label(element)]
        material.count += 1
        material.volume += volume or 0.0

    if context.computed_budget <= 0 and any(t.missing for t in by_class.values()):
        context.warnings.append(
            f"Geometry volume computed for at most {MAX_COMPUTED_ELEMENTS} elements; "
            "the rest were left without volume."
        )
    return _build_response(model, elements, by_class, by_material, context)


def _build_response(
    model: ifcopenshell.file,
    elements: list[Any],
    by_class: dict[str, _Totals],
    by_material: dict[tuple[str, bool], _Totals],
    context: _Context,
) -> BimQuantitiesResponse:
    projects = model.by_type("IfcProject")
    classes = [
        ClassQuantities(
            ifc_class=name,
            count=t.count,
            volume_m3=round(t.volume, ROUND_DIGITS),
            area_m2=round(t.area, ROUND_DIGITS),
            length_m=round(t.length, ROUND_DIGITS),
            volume_declared_count=t.declared,
            volume_computed_count=t.computed,
            without_volume_count=t.missing,
        )
        for name, t in sorted(by_class.items(), key=lambda item: -item[1].volume)
    ]
    materials = [
        MaterialQuantities(
            material=label,
            composite=composite,
            count=t.count,
            volume_m3=round(t.volume, ROUND_DIGITS),
        )
        for (label, composite), t in sorted(by_material.items(), key=lambda item: -item[1].volume)
    ]
    return BimQuantitiesResponse(
        schema_name=model.schema,
        project_name=projects[0].Name if projects else None,
        elements_total=len(elements),
        total_volume_m3=round(sum(c.volume_m3 for c in classes), ROUND_DIGITS),
        by_class=classes,
        by_material=materials,
        warnings=context.warnings,
        notes=NOTES,
    )
