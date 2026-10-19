"""
Forest Analysis Page
Placeholder for T1.10: Dashboards ecológico/florestal e ProgressTracker
"""
import streamlit as st
from components.sidebar import render_sidebar
from components.disclaimer_banner import render_disclaimer_banner

st.title("🌲 Forest Analysis")
st.write("This page is under development.")
st.write("Feature: POST /forest/overlap")

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()