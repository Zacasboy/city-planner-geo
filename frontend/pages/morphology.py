"""Morfologia urbana.

T2.1/T2.7: métricas de uma área a partir dos edifícios do OpenBuildingMap.
"""

from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.map_selector import render_map_selector, validate_polygon
from frontend.components.morphology_client import fetch_morphology
from frontend.components.sidebar import render_sidebar

RESULT_KEY = "morphology_result"
LOW_HEIGHT_COVERAGE_PERCENT = 50
HECTARES_PER_M2 = 1e-4
PERCENT_TOTAL = 100.0

st.title("🏙️ Urban Morphology")
st.write(
    "Draw a polygon (up to 5 km², Portugal mainland) to measure the existing buildings "
    "(footprints: OpenBuildingMap; missing heights estimated with GlobalBuildingAtlas — "
    "non-commercial use only)."
)


def _summary_table(data: dict[str, Any]) -> pd.DataFrame:
    rows = {
        "Area (ha)": data["analysis_area_m2"] * HECTARES_PER_M2,
        "Buildings": data["building_count"],
        **data["density_metrics"],
        **data["height_metrics"],
        **data["height_percentiles"],
        "built_up_percentage": data["occupation_metrics"]["built_up_percentage"],
        **data["building_type_metrics"],
    }
    return pd.DataFrame({"metric": list(rows), "value": list(rows.values())})


def _render_type_chart(metrics: dict[str, float]) -> None:
    """Percentagem de edifícios por tipo, com o resto como "other / unknown"."""
    types = {name.removesuffix("_percentage"): value for name, value in metrics.items()}
    types["other / unknown"] = max(0.0, PERCENT_TOTAL - sum(types.values()))
    chart = (
        alt.Chart(pd.DataFrame({"type": list(types), "percent": list(types.values())}))
        .mark_bar()
        .encode(
            x=alt.X("type:N", sort=None, title=None),
            y=alt.Y(
                "percent:Q", title="% of buildings", scale=alt.Scale(domain=[0, PERCENT_TOTAL])
            ),
        )
    )
    st.altair_chart(chart, width="stretch")


def _render_result(data: dict[str, Any]) -> None:
    details = data["details"]
    coverage = details["height_coverage_percent"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Buildings", data["building_count"])
    col2.metric("Built-up area", f"{data['occupation_metrics']['built_up_percentage']:.1f} %")
    col3.metric("Density", f"{data['density_metrics']['building_density_per_km2']:.0f} /km²")
    col4.metric("Average height", f"{data['height_metrics']['average_height_m']:.1f} m")
    if data["building_count"] and coverage < LOW_HEIGHT_COVERAGE_PERCENT:
        st.warning(
            f"Only {coverage:.0f} % of the buildings have a known height; height figures "
            "are based on that sample and the floor area ratio is a lower bound."
        )
    _render_type_chart(data["building_type_metrics"])
    st.dataframe(_summary_table(data), hide_index=True, width="stretch")
    st.download_button(
        "Download metrics (CSV)",
        _summary_table(data).to_csv(index=False),
        file_name="morphology_metrics.csv",
        mime="text/csv",
    )
    for note in details.get("notes", []):
        st.caption(note)
    st.caption(f"Data: {details.get('attribution', data['data_source_used'])}")


polygon = render_map_selector(key="morphology_map")

if polygon is None:
    st.info("Please draw a polygon on the map to select an area.")
else:
    is_valid, error_msg = validate_polygon(polygon)
    if not is_valid:
        st.error(f"Invalid polygon: {error_msg}")
    else:
        if st.button("Analyse morphology", type="primary"):
            with st.spinner("Reading buildings (the first query of an area can take ~15 s)..."):
                data, error = fetch_morphology(polygon)
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
