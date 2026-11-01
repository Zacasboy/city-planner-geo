"""Painel ecológico.

T1.10: dashboard ecológico com dados reais do GBIF (objetivo O2).
"""

from typing import Any

import pandas as pd
import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.ecology_client import fetch_area_species
from frontend.components.map_selector import render_map_selector, validate_polygon
from frontend.components.sidebar import render_sidebar

RESULT_KEY = "ecology_result"
CHART_TOP_N = 15

st.title("🌱 Ecological Dashboard")
st.write("Draw a polygon to list the species recorded in the area (source: GBIF).")


def _render_result(data: dict[str, Any]) -> None:
    species = pd.DataFrame(data["species"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Species found", len(species))
    col2.metric("Records used", data["total_records"])
    col3.metric("Records excluded (license)", data["records_excluded_by_license"])
    if species.empty:
        st.info("No allowed-license records found in this area.")
    else:
        top = species.head(CHART_TOP_N).set_index("scientific_name")["records"]
        st.subheader(f"Top {min(CHART_TOP_N, len(species))} species by records")
        st.bar_chart(top)
        st.dataframe(
            species[["scientific_name", "records"]],
            hide_index=True,
            width="stretch",
        )
    st.caption(
        "Only records licensed "
        + " / ".join(data["allowed_licenses"])
        + ". Counts show observation effort, not abundance."
    )
    for note in data["notes"]:
        st.caption(note)


polygon = render_map_selector(key="ecology_map")

if polygon is None:
    st.info("Please draw a polygon on the map to select an area.")
else:
    is_valid, error_msg = validate_polygon(polygon)
    if not is_valid:
        st.error(f"Invalid polygon: {error_msg}")
    else:
        if st.button("Query species in this area", type="primary"):
            with st.spinner("Querying GBIF..."):
                data, error = fetch_area_species(polygon)
            if error:
                st.session_state.pop(RESULT_KEY, None)
                st.error(error)
            else:
                st.session_state[RESULT_KEY] = {"polygon": polygon, "data": data}
        stored = st.session_state.get(RESULT_KEY)
        if stored and stored["polygon"] == polygon:
            _render_result(stored["data"])

render_sidebar()
render_disclaimer_banner()
