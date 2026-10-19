"""
Ecological Dashboard
T1.10: Dashboards ecológico/florestal e ProgressTracker
"""
import streamlit as st
import pandas as pd
from components.progress_tracker import render_progress_tracker
from components.sidebar import render_sidebar
from components.disclaimer_banner import render_disclaimer_banner

st.title("🌱 Ecological Dashboard")

# Mock data for ecological dashboard
# In a real app, this would come from backend API or analysis results
st.subheader("Species Diversity Overview")

# Mock species counts data
species_data = pd.DataFrame({
    'Species Group': ['Birds', 'Mammals', 'Insects', 'Plants', 'Fungi'],
    'Count': [120, 85, 340, 210, 45]
})

st.bar_chart(species_data.set_index('Species Group'))

# Mock habitat quality metrics
st.subheader("Habitat Quality Indicators")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Air Quality Index", "45", "Good")
with col2:
    st.metric("Water pH", "7.2", "Optimal")
with col3:
    st.metric("Soil Nitrogen", "2.1%", "Adequate")

# Progress tracker for ecological analysis steps
st.subheader("Analysis Progress")
steps = [
    "Data Collection",
    "Species Identification",
    "Habitat Assessment",
    "Analysis Complete"
]
# Simulate current step (in a real app, this would come from backend or session state)
current_step = 2  # 0-based index, so step 2 = Habitat Assessment
render_progress_tracker(steps, current_step)

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()