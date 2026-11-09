"""Geração de relatórios PDF com Jinja2 e WeasyPrint.

T1.12: relatório PDF (Jinja2 + WeasyPrint, upload para Storage, `GET /reports/{id}`).
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from jinja2 import Environment

from backend.app.config import settings
from supabase import Client

logger = logging.getLogger(__name__)

supabase: Client = Client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)

# autoescape evita que valores do pedido injetem HTML no PDF.
_JINJA_ENV = Environment(autoescape=True)  # noqa: S701


STRUCTURAL_REPORT_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header {
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .title { color: #2c3e50; font-size: 24px; margin-bottom: 10px; }
        .subtitle { color: #7f8c8d; font-size: 16px; }
        .section { margin: 30px 0; }
        .section-title { color: #34495e; border-left: 4px solid #3498db; padding-left: 15px; }
        .table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .table th { background-color: #f2f2f2; }
        .table tr:nth-child(even) { background-color: #f9f9f9; }
        .footer { text-align: center; margin-top: 50px; color: #95a5a6; font-size: 12px; }
        .note { font-size: 13px; color: #555; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{{ title }}</div>
        <div class="subtitle">Report ID: {{ report_id }}</div>
        <div class="subtitle">Generated: {{ generated_at }}</div>
        {% if user_id != 'anonymous' %}
        <div class="subtitle">User: {{ user_id }}</div>
        {% endif %}
    </div>

    <div class="section">
        <div class="section-title">Beam Properties</div>
        <table class="table">
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>Length</td><td>{{ beam_data.length }} m</td></tr>
            {% if beam_data.section %}
            <tr><td>Cross-sectional Area</td><td>{{ beam_data.section.area }} m²</td></tr>
            <tr><td>Moment of Inertia</td><td>{{ beam_data.section.moment_of_inertia }} m⁴</td></tr>
            <tr><td>Section Depth</td><td>{{ beam_data.section.height }} m</td></tr>
            {% else %}
            <tr><td>Width</td><td>{{ beam_data.width }} m</td></tr>
            <tr><td>Height</td><td>{{ beam_data.height }} m</td></tr>
            <tr><td>Cross-sectional Area</td>
                <td>{{ beam_data.width * beam_data.height }} m²</td></tr>
            {% endif %}
        </table>
    </div>

    <div class="section">
        <div class="section-title">Material Properties</div>
        <table class="table">
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Young's Modulus</td><td>{{ beam_data.youngs_modulus / 1e9 }} GPa</td></tr>
            <tr><td>Density</td><td>{{ beam_data.density }} kg/m³</td></tr>
            <tr><td>Yield Stress</td><td>{{ beam_data.yield_stress / 1e6 }} MPa</td></tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Loads and Supports</div>
        <table class="table">
            <tr><th>Item</th><th>Value</th></tr>
            <tr><td>Point Load</td><td>
                {{ beam_data.point_loads[0].magnitude / 1000 }} kN
                at {{ beam_data.point_loads[0].position }} m
            </td></tr>
            <tr><td>Supports</td><td>
                {% for support in beam_data.supports %}
                {{ support.type }} at {{ support.position }} m
                {%- if not loop.last %}, {% endif %}
                {% endfor %}
            </td></tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Analysis Results</div>
        <table class="table">
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>Maximum Deflection</td>
                <td>{{ "%.3f"|format(analysis_results.max_deflection * 1000) }} mm</td></tr>
            <tr><td>Maximum Stress</td>
                <td>{{ "%.2f"|format(analysis_results.max_stress / 1e6) }} MPa</td></tr>
            <tr><td>Utilization Ratio</td>
                <td>{{ "%.3f"|format(analysis_results.utilization_ratio) }}</td></tr>
            <tr><td>Utilization check</td><td>
                {% if analysis_results.utilization_ratio < 1.0 %}
                Bending stress below the yield stress (preliminary, not a code check)
                {% else %}
                Bending stress above the yield stress (preliminary, not a code check)
                {% endif %}
            </td></tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Analysis Details</div>
        <table class="table">
            <tr><th>Parameter</th><th>Value</th></tr>
            {% for label, value in detail_rows %}
            <tr><td>{{ label }}</td><td>{{ value }}</td></tr>
            {% endfor %}
        </table>
    </div>

    {% if ecology %}
    <div class="section">
        <div class="section-title">Ecological Context</div>
        <p>Species recorded in the selected area (source: GBIF.org, only records licensed
            {{ ecology.allowed_licenses|join(' / ') }}).</p>
        <table class="table">
            <tr><th>Species found</th>
                <td>{{ ecology.species|length }}{{ "+" if ecology.species_limit_reached }}
                (top {{ ecology_top|length }} listed)</td></tr>
            <tr><th>Records used</th><td>{{ ecology.total_records }}</td></tr>
            <tr><th>Records excluded (license)</th>
                <td>{{ ecology.records_excluded_by_license }}</td></tr>
        </table>
        <table class="table">
            <tr><th>Scientific name</th><th>Records</th></tr>
            {% for item in ecology_top %}
            <tr><td>{{ item.scientific_name }}</td><td>{{ item.records }}</td></tr>
            {% endfor %}
        </table>
        <p class="note">Record counts show observation effort, not abundance.</p>
        <p class="note">GBIF data under CC0 or CC BY 4.0; attribution to each record's provider
            is required.</p>
    </div>
    {% endif %}

    <div class="section">
        <div class="section-title">Disclaimer</div>
        <p class="note">{{ disclaimer }}</p>
    </div>

    <div class="footer">
        <p>Generated by City Planner Geo ({{ generated_at }}).</p>
    </div>
</body>
</html>
"""


REPORTS_BUCKET = "reports"
ECOLOGY_TOP_SPECIES = 15
SIGNIFICANT_DIGITS = 6
DETAIL_LABELS = {
    "beam_length_m": ("Beam length", "m"),
    "cross_section_height_m": ("Section height", "m"),
    "shear_area_m2": ("Shear area", "m²"),
    "cross_section_area_m2": ("Section area", "m²"),
    "moment_of_inertia_m4": ("Moment of inertia", "m⁴"),
    "youngs_modulus_pa": ("Young's modulus", "Pa"),
    "density_kgm3": ("Density", "kg/m³"),
    "yield_stress_pa": ("Yield stress", "Pa"),
    "self_weight_n_per_m": ("Self weight", "N/m"),
    "total_load_n": ("Total load", "N"),
    "max_bending_moment_nm": ("Maximum bending moment", "N·m"),
    "max_shear_force_n": ("Maximum shear force", "N"),
    "reactions_n": ("Reactions", "N"),
    "analysis_method": ("Analysis method", ""),
    "note": ("Note", ""),
}
DISCLAIMER = (
    "These results are a preliminary estimate and decision support. They do not replace a "
    "structural design, a code check (Eurocodes) or the opinion of the competent authorities. "
    "Structural results are compared with a synthetic benchmark (TimoDS) and closed-form "
    "cases, not with experiments."
)


class ReportNotFoundError(Exception):
    """O relatório não existe ou pertence a outro utilizador."""


def _report_path(user_id: str, report_id: str) -> str:
    """Caminho no Storage; o prefixo do dono impede aceder a relatórios de outros."""
    return f"{user_id}/{report_id}.pdf"


def _format_value(value: Any, unit: str) -> str:
    if isinstance(value, dict):
        parts = [
            f"x = {position} m: {_format_value(item, unit)}" for position, item in value.items()
        ]
        return "; ".join(parts)
    if isinstance(value, float):
        value = f"{value:.{SIGNIFICANT_DIGITS}g}"
    return f"{value} {unit}".strip()


def format_details(details: dict[str, Any]) -> list[tuple[str, str]]:
    """Prepara as linhas de "Analysis Details" com rótulos, unidades e valores arredondados."""
    rows = []
    for key, value in details.items():
        label, unit = DETAIL_LABELS.get(key, (key.replace("_", " ").capitalize(), ""))
        rows.append((label, _format_value(value, unit)))
    return rows


class ReportsService:
    """Service for generating and managing PDF reports."""

    async def generate_structural_report(
        self,
        beam_data: dict[str, Any],
        analysis_results: dict[str, Any],
        user_id: str,
        ecology: dict[str, Any] | None = None,
    ) -> str:
        """Generate a PDF report for structural beam analysis.

        Args:
            beam_data: Input beam parameters
            analysis_results: Results from beam analysis
            user_id: Owner of the report; only this user can read or delete it
            ecology: Optional result of `/ecology/area-species` to include as context

        Returns:
            str: Report ID (UUID) used for storage and retrieval
        """
        try:
            # Generate unique report ID
            report_id = str(uuid.uuid4())

            # Prepare template data
            template_data = {
                "report_id": report_id,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": user_id,
                "beam_data": beam_data,
                "analysis_results": analysis_results,
                "ecology": ecology,
                "ecology_top": (ecology or {}).get("species", [])[:ECOLOGY_TOP_SPECIES],
                "disclaimer": DISCLAIMER,
                "detail_rows": format_details(analysis_results.get("details", {})),
                "title": "Structural Beam Analysis Report",
                "company": "City Planner Geo",
            }

            html_string = _JINJA_ENV.from_string(STRUCTURAL_REPORT_TEMPLATE).render(**template_data)

            pdf_bytes = self._render_pdf(html_string)

            supabase.storage.from_(REPORTS_BUCKET).upload(
                _report_path(user_id, report_id), pdf_bytes, {"content-type": "application/pdf"}
            )

            logger.info(f"Generated and uploaded report {report_id}")
            return report_id

        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _render_pdf(html_string: str) -> bytes:
        """Render HTML to PDF with WeasyPrint.

        WeasyPrint is imported here because it needs system libraries (pango); importing
        it at module level would make the whole API fail to start where they are missing.
        """
        from weasyprint import CSS, HTML
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        css = CSS(string="@page { size: A4; margin: 20mm }", font_config=font_config)
        pdf: bytes = HTML(string=html_string).write_pdf(stylesheets=[css], font_config=font_config)
        return pdf

    async def get_report(self, report_id: str, user_id: str) -> bytes:
        """Retrieve a PDF report from storage.

        Args:
            report_id: The report ID (UUID)
            user_id: The requesting user; must be the owner

        Returns:
            bytes: PDF file content

        Raises:
            ReportNotFoundError: If the report does not exist or belongs to someone else
        """
        try:
            content: bytes = supabase.storage.from_(REPORTS_BUCKET).download(
                _report_path(user_id, report_id)
            )
        except Exception as e:
            if "not found" in str(e).lower():
                raise ReportNotFoundError(report_id) from e
            logger.error("Failed to retrieve report %s: %s", report_id, e, exc_info=True)
            raise
        return content

    async def delete_report(self, report_id: str, user_id: str) -> None:
        """Delete a report from storage.

        Args:
            report_id: The report ID (UUID)
            user_id: The requesting user; must be the owner

        Raises:
            ReportNotFoundError: If the report does not exist or belongs to someone else
        """
        removed = supabase.storage.from_(REPORTS_BUCKET).remove([_report_path(user_id, report_id)])
        if not removed:
            raise ReportNotFoundError(report_id)
        logger.info("Deleted report %s", report_id)
