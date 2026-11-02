"""Painel florestal.

T1.10: sobreposição de uma área com o regime florestal (DGT), com dados reais.
"""

from typing import Any

import pandas as pd
import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.forest_client import fetch_forest_overlap
from frontend.components.map_selector import render_map_selector, validate_polygon
from frontend.components.sidebar import render_sidebar

RESULT_KEY = "forest_result"
HECTARES_PER_KM2 = 100
FEATURE_COLUMNS = ["codigo", "nome", "tipologia", "regime", "overlap_ha"]

st.title("🌲 Forest Dashboard")
st.write(
    "Draw a polygon to check how much of it lies under the forest regime "
    "(source: DGT, Portugal only)."
)


def _render_result(data: dict[str, Any]) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Overlap with forest regime", f"{data['overlap_area_km2'] * HECTARES_PER_KM2:.2f} ha"
    )
    col2.metric("Share of the selected area", f"{data['percentage_covered']:.1f} %")
    col3.metric("Forest-regime areas", data["details"]["features_count"])
    features = pd.DataFrame(data["details"]["features"])
    if features.empty:
        st.info("No forest-regime area intersects the selected polygon.")
    else:
        features["overlap_ha"] = features["overlap_km2"] * HECTARES_PER_KM2
        st.dataframe(
            features[FEATURE_COLUMNS].sort_values("overlap_ha", ascending=False),
            hide_index=True,
            width="stretch",
        )
    for warning in data["details"]["warnings"]:
        st.caption(warning)


polygon = render_map_selector(key="forest_map")

if polygon is None:
    st.info("Please draw a polygon on the map to select an area.")
else:
    is_valid, error_msg = validate_polygon(polygon)
    if not is_valid:
        st.error(f"Invalid polygon: {error_msg}")
    else:
        if st.button("Check forest regime in this area", type="primary"):
            with st.spinner("Querying the DGT forest-regime layer..."):
                data, error = fetch_forest_overlap(polygon)
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
