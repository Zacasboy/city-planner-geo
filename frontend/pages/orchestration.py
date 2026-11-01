"""Página de orquestração.

Placeholder da T1.7: Celery + Redis, modelo de tarefa e `GET /analysis/{id}`.
"""

import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.sidebar import render_sidebar

st.title("🔄 Orchestration")
st.write("This page is under development.")
st.write("Feature: Celery + Redis, task model and GET /analysis/{id} with status and progress")

# Render sidebar and disclaimer
render_sidebar()
render_disclaimer_banner()
