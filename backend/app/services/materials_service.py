"""Catálogo de materiais com pegada de carbono do ÖKOBAUDAT (T2.3).

O catálogo é gerado por ``scripts/build_materials_catalog.py`` a partir do CSV oficial e só
tem valores do ficheiro. Não há custos por omissão (não existe fonte aberta de preços unitários
em Portugal): o utilizador pode indicar os seus.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.services.materials_models import (
    Basis,
    CarbonMetric,
    Category,
    Exposure,
    MaterialResult,
    SortBy,
    SuggestResponse,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "materials_oekobaudat.json"
KG_UNIT = "kg"
M3_UNIT = "m3"
M2_UNIT = "qm"
UNIT_LABELS = {"per_kg": "kg CO2e per kg", "per_m3": "kg CO2e per m3", "per_m2": "kg CO2e per m2"}
GWP_KEYS = {"fossil": "gwp_fossil", "total": "gwp_total", "biogenic": "gwp_biogenic"}
STEEL_NOTE = "Needs corrosion protection in humid or coastal exposure (EN ISO 12944)."
CONCRETE_NOTE = "Exposure classes XC/XD/XS (EN 206) set the mix and cover; check the site class."
TIMBER_NOTE = "Needs a use class and moisture protection in humid exposure (EN 335)."
EXPOSURE_NOTES = {
    "structural-steel-sections": STEEL_NOTE,
    "galvanized-structural-steel": STEEL_NOTE,
    "reinforcing-steel": CONCRETE_NOTE,
    "concrete-c20-25": CONCRETE_NOTE,
    "concrete-c25-30": CONCRETE_NOTE,
    "concrete-c30-37": CONCRETE_NOTE,
    "concrete-c50-60": CONCRETE_NOTE,
    "recycled-concrete-c25-30": CONCRETE_NOTE,
    "recycled-concrete-c30-37": CONCRETE_NOTE,
    "glulam-softwood": TIMBER_NOTE,
    "solid-construction-timber": TIMBER_NOTE,
}
NOTES = [
    "Cradle-to-gate carbon only (modules A1-A3), from generic or average German/European "
    "ÖKOBAUDAT datasets; Portuguese production can differ.",
    "Compare materials only for the same function: per kg, per m3 or per m2 are not "
    "equivalent (strength, insulation value and lifetime differ).",
    "Timber and other bio-based materials have a large negative biogenic value (carbon stored "
    "in the product, released at end of life). The default ranking uses fossil GWP; "
    "ask for 'total' to include the biogenic part.",
    "No default costs: there is no open unit-price source for Portugal. Costs shown are the "
    "ones you supplied. No durability data is included.",
    "Check each dataset's validity year before relying on a value.",
]


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    """Lê o catálogo gerado a partir do ÖKOBAUDAT."""
    catalog: dict[str, Any] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return catalog


def gwp_on_basis(entry: dict[str, Any], key: str, basis: Basis) -> float | None:
    """GWP de um material (kg CO2e) por kg, m3 ou m2; None se não houver forma de o obter."""
    value: float | None = entry["gwp_a1_a3_per_reference"].get(key)
    if value is None:
        return None
    amount: float = entry["reference_amount"]
    unit: str = entry["reference_unit"]
    density: float | None = entry["density_kg_m3"]
    per_reference = value / amount
    if basis == "per_m2":
        return per_reference if unit == M2_UNIT else None
    if basis == "per_kg":
        if unit == KG_UNIT:
            return per_reference
        return per_reference / density if unit == M3_UNIT and density else None
    if unit == M3_UNIT:
        return per_reference
    return per_reference * density if unit == KG_UNIT and density else None


def _result(
    entry: dict[str, Any],
    metric: CarbonMetric,
    basis: Basis,
    exposure: Exposure,
    cost: float | None,
) -> MaterialResult | None:
    values = {name: gwp_on_basis(entry, key, basis) for name, key in GWP_KEYS.items()}
    selected = values[metric]
    if selected is None:
        return None
    notes = (
        [EXPOSURE_NOTES[entry["id"]]]
        if exposure != "general" and entry["id"] in EXPOSURE_NOTES
        else []
    )
    return MaterialResult(
        id=entry["id"],
        name=entry["name"],
        category=entry["category"],
        unit=UNIT_LABELS[basis],
        gwp=round(selected, 4),
        gwp_fossil=_rounded(values["fossil"]),
        gwp_total=_rounded(values["total"]),
        gwp_biogenic=_rounded(values["biogenic"]),
        density_kg_m3=entry["density_kg_m3"],
        user_cost=cost,
        dataset=entry["dataset"],
        notes=notes,
    )


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def suggest_materials(
    category: Category,
    basis: Basis = "per_m3",
    metric: CarbonMetric = "fossil",
    sort: SortBy = "carbon",
    exposure: Exposure = "general",
    costs: dict[str, float] | None = None,
    limit: int | None = None,
) -> SuggestResponse:
    """Materiais de uma categoria ordenados por pegada de carbono (ou pelo custo indicado).

    Args:
        category: Categoria do catálogo.
        basis: Por kg, por m3 ou por m2.
        metric: ``fossil`` (por omissão) ou ``total`` (inclui o carbono biogénico).
        sort: ``carbon`` ou ``cost`` (os materiais com custo indicado primeiro).
        exposure: Acrescenta notas normativas para exposição húmida ou costeira.
        costs: Custos do utilizador por id de material, na unidade da base pedida.
        limit: Número máximo de resultados.

    Returns:
        Os materiais, os que não têm valor nessa base e as notas e fonte dos dados.
    """
    catalog = load_catalog()
    costs = costs or {}
    results: list[MaterialResult] = []
    unavailable: list[str] = []
    for entry in catalog["materials"]:
        if entry["category"] != category:
            continue
        result = _result(entry, metric, basis, exposure, costs.get(entry["id"]))
        if result is None:
            unavailable.append(entry["id"])
        else:
            results.append(result)
    results.sort(key=lambda r: r.gwp)
    if sort == "cost":
        results.sort(key=lambda r: (r.user_cost is None, r.user_cost or 0.0))
    return SuggestResponse(
        category=category,
        basis=basis,
        carbon_metric=metric,
        sort=sort,
        results=results[:limit],
        unavailable_on_basis=unavailable,
        notes=NOTES,
        source=catalog["source"],
    )
