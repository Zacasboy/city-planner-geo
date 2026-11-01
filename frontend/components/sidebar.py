"""Barra lateral com o utilizador e o botão de sair.

T1.8: base do frontend, barra lateral.
"""

import streamlit as st


def render_sidebar() -> None:
    """Mostra o utilizador e o botão de logout, ou o botão para ir ao login."""
    with st.sidebar:
        st.write("### City Planner Geo")
        if st.session_state.get("user"):
            st.write(f"**User:** {st.session_state.user.email}")
            st.write("---")
            if st.button("Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        else:
            st.write("Please log in to access the application.")
            st.write("---")
            if st.button("Go to Login", use_container_width=True):
                st.switch_page("pages/login.py")
