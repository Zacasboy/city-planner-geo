"""Painel florestal.

T1.10: dashboards ecológico/florestal e ProgressTracker.
"""

import pandas as pd
import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.progress_tracker import render_progress_tracker
from frontend.components.sidebar import render_sidebar

st.title("🌲 Forest Dashboard")
st.info("Sample data: this dashboard is not connected to the backend yet.")

# Mock data for forest dashboard
st.subheader("Forest Cover Overview")

# Mock tree density data by area
tree_data = pd.DataFrame(
    {"Area": ["North", "South", "East", "West"], "Trees per Hectare": [450, 320, 510, 280]}
)

st.bar_chart(tree_data.set_index("Area"))

# Mock canopy cover and biomass
st.subheader("Forest Health Indicators")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Canopy Cover", "78%", "5% ↑")
with col2:
    st.metric("Above-ground Biomass", "240 t/ha", "12 t/ha ↑")
with col3:
    st.metric("Deforestation Rate", "0.3%/yr", "0.1% ↓")

# Progress tracker for forest analysis steps
st.subheader("Analysis Progress")
steps = ["Area Selection", "Tree Count", "Canopy Analysis", "Report Ready"]
# Simulate current step
current_step = 1  # 0-based index, so step 1 = Tree Count
render_progress_tracker(steps, current_step)

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()
