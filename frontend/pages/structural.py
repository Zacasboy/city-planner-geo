"""
Structural Analysis Page
Placeholder for T1.11: Vista estrutural (formulário + resultados)
"""
import streamlit as st
from components.sidebar import render_sidebar
from components.disclaimer_banner import render_disclaimer_banner

st.title("🏗️ Structural Analysis")
st.write("This page is under development.")
st.write("Feature: Serviço Estrutural: viga de aço com PyNite + validação com casos de referência/TimoDS")

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()