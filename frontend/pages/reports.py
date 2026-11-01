"""Página de relatórios PDF.

T1.12: relatório PDF (Jinja2 + WeasyPrint, upload para Storage, `GET /reports/{id}`).
"""

from datetime import datetime
from typing import Any

import requests
import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.settings import REQUEST_TIMEOUT_S, auth_headers, backend_url
from frontend.components.sidebar import render_sidebar

GPA_TO_PA = 1e9
MPA_TO_PA = 1e6
KN_TO_N = 1000
SHORT_ID_LENGTH = 8


def _connection_error() -> None:
    st.error("Could not connect to backend. Please ensure the backend is running.")


def _generate_report(beam_data: dict[str, Any]) -> None:
    """Analisa a viga no backend e pede o relatório PDF com esse resultado."""
    try:
        with st.spinner("Generating report..."):
            analysis = requests.post(
                f"{backend_url()}/structural/beam",
                json=beam_data,
                headers=auth_headers(),
                timeout=REQUEST_TIMEOUT_S,
            )
            if analysis.status_code != requests.codes.ok:
                st.error(f"Analysis failed: {analysis.status_code} - {analysis.text}")
                return
            analysis_results = analysis.json()
            response = requests.post(
                f"{backend_url()}/reports/structural",
                json={"beam_data": beam_data, "analysis_results": analysis_results},
                headers=auth_headers(),
                timeout=REQUEST_TIMEOUT_S,
            )
    except requests.exceptions.ConnectionError:
        _connection_error()
        return
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return

    if response.status_code != requests.codes.created:
        st.error(f"Failed to generate report: {response.status_code} - {response.text}")
        return
    report_id = response.json()["report_id"]
    st.session_state.generated_reports[report_id] = {
        "timestamp": datetime.now().isoformat(),
        "type": "backend",
        "data": {"beam_data": beam_data, "analysis_results": analysis_results},
    }
    st.session_state.last_report_id = report_id
    st.success(f"Report generated successfully! Report ID: {report_id}")
    st.info(f"You can view or download the report using the ID: {report_id}")


def _download_report(report_id: str) -> None:
    try:
        with st.spinner("Downloading report..."):
            response = requests.get(
                f"{backend_url()}/reports/{report_id}",
                headers=auth_headers(),
                timeout=REQUEST_TIMEOUT_S,
            )
    except requests.exceptions.ConnectionError:
        _connection_error()
        return
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return

    if response.status_code == requests.codes.ok:
        st.download_button(
            label="Download PDF",
            data=response.content,
            file_name=f"report_{report_id}.pdf",
            mime="application/pdf",
        )
    else:
        st.error(f"Failed to download report: {response.status_code} - {response.text}")


def _show_existing_reports() -> None:
    reports = st.session_state.generated_reports
    if not reports:
        st.info(
            "No reports generated yet. Generate a report using the form above "
            "or from the Structural Analysis page."
        )
        return

    report_ids = list(reports.keys())
    last_id = st.session_state.last_report_id
    selected_id = st.selectbox(
        "Select a report to view/download:",
        options=report_ids,
        index=report_ids.index(last_id) if last_id in report_ids else 0,
        format_func=lambda rid: f"Report {rid[:SHORT_ID_LENGTH]}... ({reports[rid]['type']})",
    )
    info = reports[selected_id]
    st.write(f"**Report ID:** {selected_id}")
    st.write(f"**Generated:** {info['timestamp']}")
    st.write(f"**Type:** {info['type']}")

    details_col, download_col = st.columns(2)
    with details_col:
        if st.button("View Report Details"):
            st.json(info)
    with download_col:
        if st.button("Download Report"):
            _download_report(selected_id)


st.title("📋 Structural Analysis Reports")

st.session_state.setdefault("generated_reports", {})
st.session_state.setdefault("last_report_id", None)

st.subheader("Generate New Report")
st.info(
    "To generate a report, enter the beam data below. The backend analyses the beam "
    "and generates a PDF report from the results."
)

with st.form("manual_report_form"):
    col1, col2 = st.columns(2)
    with col1:
        beam_length = st.number_input("Beam Length (m)", min_value=0.1, value=5.0, step=0.1)
        beam_width = st.number_input("Beam Width (m)", min_value=0.01, value=0.3, step=0.01)
        beam_height = st.number_input("Beam Height (m)", min_value=0.01, value=0.5, step=0.01)
    with col2:
        youngs_modulus_gpa = st.number_input(
            "Young's Modulus (GPa)", min_value=1.0, value=200.0, step=1.0
        )
        density = st.number_input("Density (kg/m³)", min_value=1.0, value=7850.0, step=10.0)
        yield_stress_mpa = st.number_input(
            "Yield Stress (MPa)", min_value=1.0, value=250.0, step=1.0
        )
    point_load_kn = st.number_input("Point Load (kN)", min_value=0.0, value=10.0, step=0.5)
    submitted = st.form_submit_button("Generate Report from Manual Data", type="secondary")

if submitted:
    _generate_report(
        {
            "length": beam_length,
            "width": beam_width,
            "height": beam_height,
            "youngs_modulus": youngs_modulus_gpa * GPA_TO_PA,
            "density": density,
            "yield_stress": yield_stress_mpa * MPA_TO_PA,
            "point_loads": [{"position": beam_length / 2, "magnitude": point_load_kn * KN_TO_N}],
            "supports": [
                {"position": 0.0, "type": "pin"},
                {"position": beam_length, "type": "roller"},
            ],
        }
    )

st.subheader("View Existing Reports")
_show_existing_reports()

with st.expander("How to Use This Feature"):
    st.write("""
    1. Enter the beam parameters in the form above
    2. Click **Generate Report from Manual Data**
    3. Select the report below to view its details or download the PDF

    The reports are generated as PDFs using:
    - Jinja2 for HTML templating
    - WeasyPrint for HTML-to-PDF conversion
    - Supabase Storage for file storage
    - FastAPI for the backend endpoints
    """)

render_sidebar()
render_disclaimer_banner()
