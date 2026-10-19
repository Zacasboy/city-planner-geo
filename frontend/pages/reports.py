"""
Reports Page
Placeholder for T1.12: Relatório PDF (Jinja2 + WeasyPrint, upload a Storage, GET /reports/{id})
"""
import streamlit as st
from components.sidebar import render_sidebar
from components.disclaimer_banner import render_disclaimer_banner

st.title("📋 Reports")
st.write("This page is under development.")
st.write("Feature: Relatório PDF (Jinja2 + WeasyPrint, upload a Storage, GET /reports/{id})")

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()