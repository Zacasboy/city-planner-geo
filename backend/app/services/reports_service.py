"""
Reports Service - PDF Report Generation with Jinja2 and WeasyPrint
T1.12: Relatório PDF (Jinja2 + WeasyPrint, upload a Storage, GET /reports/{id})
"""
import io
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from jinja2 import Template
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from supabase import Client
from backend.app.config import settings

# Create logger
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = Client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


class ReportsService:
    """Service for generating and managing PDF reports."""

    def __init__(self):
        # Initialize font configuration for WeasyPrint
        self.font_config = FontConfiguration()

    async def generate_structural_report(
        self,
        beam_data: Dict[str, Any],
        analysis_results: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """
        Generate a PDF report for structural beam analysis.

        Args:
            beam_data: Input beam parameters
            analysis_results: Results from beam analysis
            user_id: Optional user ID for report ownership

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
                "user_id": user_id or "anonymous",
                "beam_data": beam_data,
                "analysis_results": analysis_results,
                "title": "Structural Beam Analysis Report",
                "company": "City Planner Geo"
            }

            # HTML template for the report
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{{ title }}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
                    .title { color: #2c3e50; font-size: 24px; margin-bottom: 10px; }
                    .subtitle { color: #7f8c8d; font-size: 16px; }
                    .section { margin: 30px 0; }
                    .section-title { color: #34495e; border-left: 4px solid #3498db; padding-left: 15px; }
                    .table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                    .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    .table th { background-color: #f2f2f2; }
                    .table tr:nth-child(even) { background-color: #f9f9f9; }
                    .footer { text-align: center; margin-top: 50px; color: #95a5a6; font-size: 12px; }
                    .note { font-size: 14px; color: #e74c3c; }
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
                        <tr><td>Width</td><td>{{ beam_data.width }} m</td></tr>
                        <tr><td>Height</td><td>{{ beam_data.height }} m</td></tr>
                        <tr><td>Cross-sectional Area</td><td>{{ beam_data.width * beam_data.height }} m²</td></tr>
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
                        <tr><td>Point Load</td><td>{{ beam_data.point_loads[0].magnitude / 1000 }} kN at {{ beam_data.point_loads[0].position }} m</td></tr>
                        <tr><td>Supports</td><td>
                            {% for support in beam_data.supports %}
                            {{ support.type }} at {{ support.position }} m{% if not loop.last %}, {% endif %}
                            {% endfor %}
                        </td></tr>
                    </table>
                </div>

                <div class="section">
                    <div class="section-title">Analysis Results</div>
                    <table class="table">
                        <tr><th>Parameter</th><th>Value</th></tr>
                        <tr><td>Maximum Deflection</td><td>{{ analysis_results.max_deflection * 1000 }} mm</td></tr>
                        <tr><td>Maximum Stress</td><td>{{ analysis_results.max_stress / 1e6 }} MPa</td></tr>
                        <tr><td>Utilization Ratio</td><td>{{ analysis_results.utilization_ratio }}</td></tr>
                        <tr><td>Status</td><td>
                            {% if analysis_results.utilization_ratio < 1.0 %}
                            <span style="color: green;">SAFE</span>
                            {% else %}
                            <span style="color: red;">UNSAFE</span>
                            {% endif %}
                        </td></tr>
                    </table>
                </div>

                <div class="section">
                    <div class="section-title">Analysis Details</div>
                    <table class="table">
                        <tr><th>Parameter</th><th>Value</th></tr>
                        {% for key, value in analysis_results.details.items() %}
                        <tr><td>{{ key.replace('_', ' ')|title }}</td><td>{{ value }}</td></tr>
                        {% endfor %}
                    </table>
                </div>

                <div class="footer">
                    <p>Generated by City Planner Geo - Structural Analysis System</p>
                    <p>This report is for informational purposes only. Engineering judgment should be applied.</p>
                </div>
            </body>
            </html>
            """

            # Render HTML from template
            template = Template(html_template)
            html_string = template.render(**template_data)

            # Convert HTML to PDF using WeasyPrint
            html = HTML(string=html_string)
            css = CSS(string='@page { size: A4; margin: 20mm }', font_config=self.font_config)
            pdf_bytes = html.write_stylesheet([css], font_config=self.font_config)

            # Upload PDF to Supabase Storage
            file_path = f"reports/{report_id}.pdf"
            supabase.storage.from_("reports").upload(
                file_path,
                pdf_bytes,
                {"content-type": "application/pdf"}
            )

            logger.info(f"Generated and uploaded report {report_id}")
            return report_id

        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}", exc_info=True)
            raise

    async def get_report(self, report_id: str) -> bytes:
        """
        Retrieve a PDF report from storage.

        Args:
            report_id: The report ID (UUID)

        Returns:
            bytes: PDF file content
        """
        try:
            file_path = f"reports/{report_id}.pdf"
            response = supabase.storage.from_("reports").download(file_path)
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve report {report_id}: {str(e)}", exc_info=True)
            raise

    async def delete_report(self, report_id: str) -> bool:
        """
        Delete a report from storage.

        Args:
            report_id: The report ID (UUID)

        Returns:
            bool: True if successful
        """
        try:
            file_path = f"reports/{report_id}.pdf"
            supabase.storage.from_("reports").remove([file_path])
            logger.info(f"Deleted report {report_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete report {report_id}: {str(e)}", exc_info=True)
            return False