"""Gera o catálogo de materiais a partir do CSV do ÖKOBAUDAT.

Uso:
    python scripts/build_materials_catalog.py <OBD_....csv> [saida.json]

Descarregue o CSV (ponto decimal) em https://www.oekobaudat.de/en/service/downloads.html.
Só lê o módulo A1-A3 (produção, "do berço ao portão"), indicador GWP total (EN 15804+A2), e
falha se um dataset escolhido não existir ou for ambíguo. Não inventa valores: tudo o que está
no catálogo vem do ficheiro, exceto a massa volúmica do aço (EN 1993-1-1, 3.2.6).
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

OUTPUT = Path("backend/app/data/materials_oekobaudat.json")
MODULE = "A1-A3"
STEEL_DENSITY_KG_M3 = 7850.0
STEEL_DENSITY_SOURCE = "EN 1993-1-1, 3.2.6"
LICENSE_STATEMENT = "BMWSB provides the ÖKOBAUDAT data free of charge and without any restrictions"
GWP_COLUMNS = {
    "gwp_total": "GWPtotal (A2)",
    "gwp_fossil": "GWPfossil (A2)",
    "gwp_biogenic": "GWPbiogenic (A2)",
    "gwp_luluc": "GWPluluc (A2)",
}


@dataclass(frozen=True)
class Choice:
    """Um material do catálogo e o dataset do ÖKOBAUDAT que o representa."""

    slug: str
    category: str
    name: str
    uuid_prefix: str
    steel: bool = False


CHOICES = (
    Choice(
        "structural-steel-sections", "structural", "Structural steel sections", "20c29cbd", True
    ),
    Choice(
        "galvanized-structural-steel",
        "structural",
        "Hot-dip galvanized structural steel",
        "0f0618af",
        True,
    ),
    Choice("concrete-c20-25", "structural", "Ready-mix concrete C20/25", "e3d7a045"),
    Choice("concrete-c25-30", "structural", "Ready-mix concrete C25/30", "a71e60a5"),
    Choice("concrete-c30-37", "structural", "Ready-mix concrete C30/37", "d6f982e3"),
    Choice("concrete-c50-60", "structural", "Ready-mix concrete C50/60", "0a1fa7f9"),
    Choice(
        "recycled-concrete-c25-30", "structural", "Recycled-aggregate concrete C25/30", "61c0c795"
    ),
    Choice(
        "recycled-concrete-c30-37", "structural", "Recycled-aggregate concrete C30/37", "3e15eb88"
    ),
    Choice("glulam-softwood", "structural", "Glued laminated timber (softwood)", "aeab0f39"),
    Choice("solid-construction-timber", "structural", "Solid construction timber", "6b363ddc"),
    Choice(
        "reinforcing-steel", "reinforcement", "Reinforcing steel (coils and bars)", "b14811fa", True
    ),
    Choice("facing-brick", "masonry", "Facing brick", "1401638f"),
    Choice("sand-lime-brick", "masonry", "Sand-lime brick", "c916ceb3"),
    Choice("concrete-masonry-brick", "masonry", "Concrete masonry brick", "2cdcffc6"),
    Choice(
        "aerated-concrete-p4-05", "masonry", "Aerated concrete P4 05 (non-reinforced)", "f1e6c40e"
    ),
    Choice("eps-insulation", "insulation", "EPS rigid foam insulation", "121c71e8"),
    Choice("xps-insulation", "insulation", "Extruded polystyrene (XPS)", "c4ddfdbc"),
    Choice("pur-insulation", "insulation", "PUR rigid foam", "b960f95d"),
    Choice("mineral-wool-facade", "insulation", "Mineral wool (facade insulation)", "50d421e2"),
    Choice("wood-fibre-board", "insulation", "Wood fibre board (wet process)", "c91aa879"),
    Choice("expanded-cork", "insulation", "Expanded cork", "fdbe82c6"),
    Choice("cellulose-insulation", "insulation", "Cellulose fibre blowing insulation", "5fac6347"),
    Choice("double-glazing", "glazing", "Insulated glazing, double pane", "d7bf4202"),
    Choice("triple-glazing", "glazing", "Insulated glazing, triple pane", "ba58d8b9"),
)


def _number(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(str(value).replace(",", "."))


def _row(frame: pd.DataFrame, choice: Choice) -> pd.Series:
    rows = frame[frame["UUID"].str.startswith(choice.uuid_prefix) & (frame["Modul"] == MODULE)]
    if len(rows) != 1:
        raise SystemExit(f"{choice.slug}: expected 1 row for {choice.uuid_prefix}, got {len(rows)}")
    return rows.iloc[0]


def _entry(choice: Choice, row: pd.Series) -> dict[str, object]:
    amount = _number(row["Bezugsgroesse"])
    unit = str(row["Bezugseinheit"])
    density = _number(row["Rohdichte (kg/m3)"])
    density_source = "ÖKOBAUDAT dataset" if density else None
    if density is None and choice.steel:
        density, density_source = STEEL_DENSITY_KG_M3, STEEL_DENSITY_SOURCE
    gwp = {key: _number(row[column]) for key, column in GWP_COLUMNS.items()}
    if amount is None or amount <= 0 or gwp["gwp_total"] is None:
        raise SystemExit(f"{choice.slug}: missing reference amount or GWP")
    return {
        "id": choice.slug,
        "name": choice.name,
        "category": choice.category,
        "reference_amount": amount,
        "reference_unit": unit,
        "density_kg_m3": density,
        "density_source": density_source,
        "gwp_a1_a3_per_reference": gwp,
        "dataset": {
            "uuid": row["UUID"],
            "version": row["Version"],
            "name_en": row["Name (en)"],
            "type": row["Typ"],
            "country": row["Laenderkennung"],
            "valid_until": row["Gueltig bis"],
            "declaration_owner": (
                None if pd.isna(row["Declaration owner"]) else row["Declaration owner"]
            ),
            "conformity": row["Konformitaet"].replace("'", ""),
        },
    }


def main(csv_path: str, output: Path = OUTPUT) -> None:
    """Lê o CSV, escolhe os datasets e escreve o catálogo."""
    frame = pd.read_csv(csv_path, sep=";", encoding="cp1252", dtype=str, low_memory=False)
    materials = [_entry(choice, _row(frame, choice)) for choice in CHOICES]
    catalog = {
        "source": {
            "name": "ÖKOBAUDAT",
            "release": "-".join(Path(csv_path).name.split("_")[1:3]),
            "module": MODULE,
            "indicator": "GWP-total (EN 15804+A2), kg CO2e per reference amount",
            "license_statement": LICENSE_STATEMENT,
        },
        "materials": materials,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(f"{len(materials)} materials written to {output}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1], Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT)
