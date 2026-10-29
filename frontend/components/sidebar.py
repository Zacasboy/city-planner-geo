"""Sidebar Component
T1.8: Frontend base: sidebar component
"""

import streamlit as st


def render_sidebar():
    """Render the sidebar with user info and logout button."""
    with st.sidebar:
        st.write("### City Planner Geo")
        if st.session_state.get("user"):
            st.write(f"**User:** {st.session_state.user.email}")
            st.write("---")
            if st.button("Logout", use_container_width=True):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        else:
            st.write("Please log in to access the application.")
            st.write("---")
            if st.button("Go to Login", use_container_width=True):
                st.switch_page("pages/login.py")
