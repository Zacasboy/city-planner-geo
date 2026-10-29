"""Reports Page
T1.12: Relatório PDF (Jinja2 + WeasyPrint, upload a Storage, GET /reports/{id})
"""

from datetime import datetime

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

st.title("📋 Structural Analysis Reports")

# Backend URL configuration
BACKEND_URL = (
    st.secrets.get("BACKEND_URL", "http://localhost:8000")
    if hasattr(st, "secrets")
    else "http://localhost:8000"
)

# Initialize session state for reports
if "generated_reports" not in st.session_state:
    st.session_state.generated_reports = {}
if "last_report_id" not in st.session_state:
    st.session_state.last_report_id = None

# Section to generate a new report
st.subheader("Generate New Report")

st.info(
    "To generate a report, you first need to perform a structural analysis on the Structural Analysis page, then come back here to generate a PDF report from those results."
)

# Form to input report data manually (for testing/demo purposes)
with st.form("manual_report_form"):
    st.write("Or manually enter analysis data for testing:")

    col1, col2 = st.columns(2)
    with col1:
        beam_length = st.number_input("Beam Length (m)", min_value=0.1, value=5.0, step=0.1)
        beam_width = st.number_input("Beam Width (m)", min_value=0.01, value=0.3, step=0.01)
        beam_height = st.number_input("Beam Height (m)", min_value=0.01, value=0.5, step=0.01)
    with col2:
        youngs_modulus = st.number_input(
            "Young's Modulus (GPa)", min_value=1.0, value=200.0, step=1.0
        )
        density = st.number_input("Density (kg/m³)", min_value=1.0, value=7850.0, step=10.0)
        yield_stress = st.number_input("Yield Stress (MPa)", min_value=1.0, value=250.0, step=1.0)

    point_load = st.number_input("Point Load (kN)", min_value=0.0, value=10.0, step=0.5)

    submitted = st.form_submit_button("Generate Report from Manual Data", type="secondary")

# Process manual form submission
if submitted:
    if not REQUESTS_AVAILABLE:
        # Simulate report generation
        st.info("Running in demo mode (requests library not available)")

        # Generate a fake report ID
        import uuid

        fake_report_id = str(uuid.uuid4())

        # Store in session state
        st.session_state.generated_reports[fake_report_id] = {
            "timestamp": datetime.now().isoformat(),
            "type": "manual",
            "data": {
                "beam_length": beam_length,
                "beam_width": beam_width,
                "beam_height": beam_height,
                "youngs_modulus": youngs_modulus,
                "density": density,
                "yield_stress": yield_stress,
                "point_load": point_load,
            },
        }
        st.session_state.last_report_id = fake_report_id

        st.success(f"Report generated successfully! Report ID: {fake_report_id}")
        st.info(
            "In a real implementation, this would call the backend to generate and store the PDF."
        )

    else:
        # Prepare data for backend report generation
        beam_data = {
            "length": beam_length,
            "width": beam_width,
            "height": beam_height,
            "youngs_modulus": youngs_modulus * 1e9,  # Convert GPa to Pa
            "density": density,
            "yield_stress": yield_stress * 1e6,  # Convert MPa to Pa
            "point_loads": [
                {"position": beam_length / 2, "magnitude": point_load * 1000}
            ],  # kN to N
            "supports": [
                {"position": 0.0, "type": "pin"},
                {"position": beam_length, "type": "roller"},
            ],
        }

        # Simple analysis results (in real app, these would come from structural service)
        L = beam_length
        b = beam_width
        h = beam_height
        E = youngs_modulus * 1e9
        I = b * h**3 / 12
        P = point_load * 1000

        max_deflection = (P * L**3) / (48 * E * I)
        max_moment = P * L / 4
        c = h / 2
        max_stress = (max_moment * c) / I
        utilization_ratio = max_stress / (yield_stress * 1e6) if yield_stress != 0 else float("inf")

        analysis_results = {
            "max_deflection": max_deflection,
            "max_stress": max_stress,
            "utilization_ratio": utilization_ratio,
            "details": {
                "beam_length_m": L,
                "cross_section_width_m": b,
                "cross_section_height_m": h,
                "moment_of_inertia_m4": I,
                "youngs_modulus_pa": E,
                "density_kgm3": density,
                "yield_stress_pa": yield_stress * 1e6,
                "total_point_load_n": P,
                "analysis_method": "Analytical (simply supported beam with point load at midspan)",
            },
        }

        try:
            # Show loading spinner
            with st.spinner("Generating report..."):
                response = requests.post(
                    f"{BACKEND_URL}/reports/structural",
                    json={"beam_data": beam_data, "analysis_results": analysis_results},
                    timeout=30,
                )

            if response.status_code == 201:
                result = response.json()
                report_id = result["report_id"]

                # Store in session state
                st.session_state.generated_reports[report_id] = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "backend",
                    "data": {"beam_data": beam_data, "analysis_results": analysis_results},
                }
                st.session_state.last_report_id = report_id

                st.success(f"Report generated successfully! Report ID: {report_id}")
                st.info(f"You can view or download the report using the ID: {report_id}")

            else:
                st.error(f"Failed to generate report: {response.status_code} - {response.text}")

        except requests.exceptions.ConnectionError:
            st.error("Could not connect to backend. Please ensure the backend is running.")
        except requests.exceptions.Timeout:
            st.error("Request timed out. Please try again.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Section to view existing reports
st.subheader("View Existing Reports")

if st.session_state.generated_reports:
    # Create a selectbox for reports
    report_options = list(st.session_state.generated_reports.keys())
    if st.session_state.last_report_id and st.session_state.last_report_id in report_options:
        default_index = report_options.index(st.session_state.last_report_id)
    else:
        default_index = 0 if report_options else None

    if report_options:
        selected_report_id = st.selectbox(
            "Select a report to view/download:",
            options=report_options,
            index=default_index,
            format_func=lambda x: f"Report {x[:8]}... ({st.session_state.generated_reports[x]['type']})",
        )

        if selected_report_id:
            report_info = st.session_state.generated_reports[selected_report_id]

            st.write(f"**Report ID:** {selected_report_id}")
            st.write(f"**Generated:** {report_info['timestamp']}")
            st.write(f"**Type:** {report_info['type']}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("View Report Details"):
                    st.json(report_info)

            with col2:
                if not REQUESTS_AVAILABLE:
                    if st.button("Download Report (Simulated)"):
                        st.info("In demo mode, this would download the actual PDF.")
                        st.download_button(
                            label="Download PDF (Demo)",
                            data=f"Simulated PDF content for report {selected_report_id}".encode(),
                            file_name=f"report_{selected_report_id}.pdf",
                            mime="application/pdf",
                        )
                else:
                    if st.button("Download Report"):
                        try:
                            with st.spinner("Downloading report..."):
                                response = requests.get(
                                    f"{BACKEND_URL}/reports/{selected_report_id}", timeout=30
                                )

                            if response.status_code == 200:
                                st.download_button(
                                    label="Download PDF",
                                    data=response.content,
                                    file_name=f"report_{selected_report_id}.pdf",
                                    mime="application/pdf",
                                )
                            else:
                                st.error(
                                    f"Failed to download report: {response.status_code} - {response.text}"
                                )

                        except requests.exceptions.ConnectionError:
                            st.error(
                                "Could not connect to backend. Please ensure the backend is running."
                            )
                        except requests.exceptions.Timeout:
                            st.error("Request timed out. Please try again.")
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")
    else:
        st.info("No reports generated yet.")
else:
    st.info(
        "No reports generated yet. Generate a report using the form above or from the Structural Analysis page."
    )

# Instructions section
with st.expander("How to Use This Feature"):
    st.write("""
    1. Go to the **Structural Analysis** page
    2. Enter your beam parameters and run an analysis
    3. Come back to this **Reports** page
    4. Either manually enter the same data to generate a report, or
    5. In a future enhancement, the system will automatically suggest generating a report after analysis

    The reports are generated as PDFs using:
    - Jinja2 for HTML templating
    - WeasyPrint for HTML-to-PDF conversion
    - Supabase Storage for file storage
    - FastAPI for the backend endpoints
    """)

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()
