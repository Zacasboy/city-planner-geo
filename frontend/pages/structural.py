"""Structural Analysis Page
T1.11: Vista estrutural (formulário + resultados)
"""

import streamlit as st
from components.disclaimer_banner import render_disclaimer_banner
from components.sidebar import render_sidebar

# Try to import requests for making HTTP calls to backend
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    st.warning("Requests library not available. Backend communication will be simulated.")

st.title("🏗️ Structural Analysis - Steel Beam Calculator")

# Backend URL configuration
BACKEND_URL = (
    st.secrets.get("BACKEND_URL", "http://localhost:8000")
    if hasattr(st, "secrets")
    else "http://localhost:8000"
)

# Form for beam analysis parameters
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
        youngs_modulus = (
            st.number_input(
                "Young's Modulus (GPa)",
                min_value=1.0,
                value=200.0,
                step=1.0,
                help="Modulus of elasticity of the material",
            )
            * 1e9
        )  # Convert GPa to Pa

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
        yield_stress = (
            st.number_input(
                "Yield Stress (MPa)",
                min_value=1.0,
                value=250.0,
                step=1.0,
                help="Yield strength of the material",
            )
            * 1e6
        )  # Convert MPa to Pa

    st.subheader("Loads and Supports")
    st.info(
        "For simplicity, this version assumes a single point load at midspan and simple supports at both ends."
    )

    point_load = (
        st.number_input(
            "Point Load (kN)",
            min_value=0.0,
            value=10.0,
            step=0.5,
            help="Point load applied at midspan (positive downward)",
        )
        * 1000
    )  # Convert kN to N

    # Submit button
    submitted = st.form_submit_button("Analyze Beam", type="primary")

# Process form submission
if submitted:
    if not REQUESTS_AVAILABLE:
        # Simulate backend response for demo purposes
        st.info("Running in demo mode (requests library not available)")

        # Calculate using analytical formulas for simply supported beam with point load at midspan
        L = length
        b = width
        h = height
        E = youngs_modulus
        I = b * h**3 / 12
        P = point_load

        max_deflection = (P * L**3) / (48 * E * I)
        max_moment = P * L / 4
        c = h / 2
        max_stress = (max_moment * c) / I
        utilization_ratio = max_stress / yield_stress if yield_stress != 0 else float("inf")

        # Display results
        st.subheader("Analysis Results")

        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            st.metric(
                "Max Deflection",
                f"{max_deflection*1000:.2f} mm",
                help="Maximum downward displacement",
            )
        with res_col2:
            st.metric("Max Stress", f"{max_stress/1e6:.1f} MPa", help="Maximum bending stress")
        with res_col3:
            st.metric(
                "Utilization Ratio",
                f"{utilization_ratio:.2f}",
                help="Stress/Yield ratio (< 1.0 is safe)",
            )

        # Additional details
        with st.expander("Analysis Details"):
            st.write(f"**Beam Length:** {L} m")
            st.write(f"**Cross Section:** {b} m × {h} m")
            st.write(f"**Moment of Inertia:** {I:.6f} m⁴")
            st.write(f"**Young's Modulus:** {E/1e9:.1f} GPa")
            st.write(f"**Applied Load:** {P/1000:.1f} kN")
            st.write(f"**Max Moment:** {max_moment/1000:.1f} kN·m")
            st.write("**Analysis Method:** Analytical (simply supported beam)")

    else:
        # Make actual HTTP request to backend
        try:
            # Prepare request data
            beam_data = {
                "length": length,
                "width": width,
                "height": height,
                "youngs_modulus": youngs_modulus,
                "density": density,
                "yield_stress": yield_stress,
                "point_loads": [{"position": length / 2, "magnitude": point_load}],  # Midspan load
                "supports": [
                    {"position": 0.0, "type": "pin"},
                    {"position": length, "type": "roller"},
                ],
            }

            # Show loading spinner
            with st.spinner("Analyzing beam..."):
                response = requests.post(
                    f"{BACKEND_URL}/structural/beam", json=beam_data, timeout=30
                )

            if response.status_code == 200:
                result = response.json()

                # Display results
                st.subheader("Analysis Results")

                res_col1, res_col2, res_col3 = st.columns(3)
                with res_col1:
                    st.metric(
                        "Max Deflection",
                        f"{result['max_deflection']*1000:.2f} mm",
                        help="Maximum downward displacement",
                    )
                with res_col2:
                    st.metric(
                        "Max Stress",
                        f"{result['max_stress']/1e6:.1f} MPa",
                        help="Maximum bending stress",
                    )
                with res_col3:
                    utilization = result.get("utilization_ratio", 0)
                    st.metric(
                        "Utilization Ratio",
                        f"{utilization:.2f}",
                        help="Stress/Yield ratio (< 1.0 is safe)",
                    )

                # Additional details
                with st.expander("Analysis Details"):
                    st.write(
                        f"**Analysis Method:** {result.get('details', {}).get('analysis_method', 'Unknown')}"
                    )
                    if "details" in result:
                        for key, value in result["details"].items():
                            if key != "analysis_method":
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")

            else:
                st.error(f"Backend error: {response.status_code} - {response.text}")

        except requests.exceptions.ConnectionError:
            st.error("Could not connect to backend. Please ensure the backend is running.")
        except requests.exceptions.Timeout:
            st.error("Request timed out. Please try again.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()
