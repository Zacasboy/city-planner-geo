"""Página de análise estrutural.

T1.11: vista estrutural (formulário e resultados).
"""

from typing import Any

import requests
import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.settings import REQUEST_TIMEOUT_S, backend_url
from frontend.components.sidebar import render_sidebar

GPA_TO_PA = 1e9
MPA_TO_PA = 1e6
KN_TO_N = 1000


def _show_results(result: dict[str, Any]) -> None:
    st.subheader("Analysis Results")
    deflection_col, stress_col, utilization_col = st.columns(3)
    with deflection_col:
        st.metric(
            "Max Deflection",
            f"{result['max_deflection'] * 1000:.2f} mm",
            help="Maximum downward displacement",
        )
    with stress_col:
        st.metric(
            "Max Stress",
            f"{result['max_stress'] / MPA_TO_PA:.1f} MPa",
            help="Maximum bending stress",
        )
    with utilization_col:
        st.metric(
            "Utilization Ratio",
            f"{result.get('utilization_ratio', 0):.2f}",
            help="Stress/Yield ratio (< 1.0 is safe)",
        )

    details = result.get("details", {})
    with st.expander("Analysis Details"):
        st.write(f"**Analysis Method:** {details.get('analysis_method', 'Unknown')}")
        for key, value in details.items():
            if key != "analysis_method":
                st.write(f"**{key.replace('_', ' ').title()}:** {value}")


def _analyze(beam_data: dict[str, Any]) -> None:
    try:
        with st.spinner("Analyzing beam..."):
            response = requests.post(
                f"{backend_url()}/structural/beam", json=beam_data, timeout=REQUEST_TIMEOUT_S
            )
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend. Please ensure the backend is running.")
        return
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return

    if response.status_code == requests.codes.ok:
        _show_results(response.json())
    else:
        st.error(f"Backend error: {response.status_code} - {response.text}")


st.title("🏗️ Structural Analysis - Steel Beam Calculator")

with st.form("beam_analysis_form"):
    st.subheader("Beam Properties")
    col1, col2 = st.columns(2)
    with col1:
        length = st.number_input(
            "Length (m)", min_value=0.1, value=5.0, step=0.1, help="Total length of the beam"
        )
        width = st.number_input(
            "Width (m)",
            min_value=0.01,
            value=0.3,
            step=0.01,
            help="Width of the beam cross-section",
        )
    with col2:
        height = st.number_input(
            "Height (m)",
            min_value=0.01,
            value=0.5,
            step=0.01,
            help="Height of the beam cross-section",
        )
        youngs_modulus_gpa = st.number_input(
            "Young's Modulus (GPa)",
            min_value=1.0,
            value=200.0,
            step=1.0,
            help="Modulus of elasticity of the material",
        )

    st.subheader("Material Properties")
    col3, col4 = st.columns(2)
    with col3:
        density = st.number_input(
            "Density (kg/m³)",
            min_value=1.0,
            value=7850.0,
            step=10.0,
            help="Density of the beam material",
        )
    with col4:
        yield_stress_mpa = st.number_input(
            "Yield Stress (MPa)",
            min_value=1.0,
            value=250.0,
            step=1.0,
            help="Yield strength of the material",
        )

    st.subheader("Loads and Supports")
    st.info(
        "For simplicity, this version assumes a single point load at midspan "
        "and simple supports at both ends."
    )
    point_load_kn = st.number_input(
        "Point Load (kN)",
        min_value=0.0,
        value=10.0,
        step=0.5,
        help="Point load applied at midspan (positive downward)",
    )

    submitted = st.form_submit_button("Analyze Beam", type="primary")

if submitted:
    _analyze(
        {
            "length": length,
            "width": width,
            "height": height,
            "youngs_modulus": youngs_modulus_gpa * GPA_TO_PA,
            "density": density,
            "yield_stress": yield_stress_mpa * MPA_TO_PA,
            "point_loads": [{"position": length / 2, "magnitude": point_load_kn * KN_TO_N}],
            "supports": [
                {"position": 0.0, "type": "pin"},
                {"position": length, "type": "roller"},
            ],
        }
    )

render_sidebar()
render_disclaimer_banner()
