"""
Disclaimer Banner Component
T1.8: Frontend base: disclaimer banner
"""
import streamlit as st

def render_disclaimer_banner():
    """Render the disclaimer banner."""
    st.markdown("---")
    st.caption(
        """
        Disclaimer: This application is for demonstration purposes only.
        Data provided may not be accurate or complete.
        Use at your own risk.
        """
    )