"""Página inicial.

T1.8: base do frontend.
"""

import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.sidebar import render_sidebar

st.title("🏙️ City Planner Geo - Home")

if st.session_state.user:
    st.write(f"Welcome, {st.session_state.user.email}!")
else:
    st.warning("Please log in to access the home page.")
    st.stop()

# Render sidebar
render_sidebar()

st.write("---")
st.write("### Available Features")

# Feature buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🌍 Geo Validation", use_container_width=True):
        st.switch_page("pages/geo.py")
    if st.button("🌱 Ecological Analysis", use_container_width=True):
        st.switch_page("pages/ecology.py")
    if st.button("🌲 Forest Analysis", use_container_width=True):
        st.switch_page("pages/forest.py")

with col2:
    if st.button("🏗️ Structural Analysis", use_container_width=True):
        st.switch_page("pages/structural.py")
    if st.button("🔄 Orchestration", use_container_width=True):
        st.switch_page("pages/orchestration.py")
    if st.button("📋 Reports", use_container_width=True):
        st.switch_page("pages/reports.py")

with col3:
    st.info("More features coming soon...")
    st.write("")
    st.write("")
    st.write("")
    st.button("🔄 Refresh", use_container_width=True, on_click=st.rerun)

# Render disclaimer banner
render_disclaimer_banner()
