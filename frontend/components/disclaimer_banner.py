"""Aviso legal mostrado no fundo de cada página.

T1.8: base do frontend, aviso legal.
"""

import streamlit as st


def render_disclaimer_banner() -> None:
    """Mostra o aviso legal."""
    st.markdown("---")
    st.caption("""
        Disclaimer: This application is for demonstration purposes only.
        Data provided may not be accurate or complete.
        Use at your own risk.
        """)
