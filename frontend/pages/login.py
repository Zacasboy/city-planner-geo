"""Página de login.

T1.8: base do frontend, login com Supabase.
"""

import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.sidebar import render_sidebar
from frontend.components.supabase_client import get_supabase_client

st.title("🔐 Login to City Planner Geo")

supabase = get_supabase_client()
if not supabase:
    st.stop()

with st.form("login_form"):
    email = st.text_input("Email", placeholder="Enter your email")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    submit_button = st.form_submit_button("Login")

    if submit_button:
        if email and password:
            try:
                response = supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
                if response.user and response.session:
                    st.session_state.user = response.user
                    st.session_state.access_token = response.session.access_token
                    st.session_state.refresh_token = response.session.refresh_token
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Login failed. Please check your credentials.")
            except Exception as e:  # o cliente Supabase levanta vários tipos de erro
                st.error(f"Login error: {e}")
        else:
            st.warning("Please enter both email and password.")

st.markdown("---")
if st.button("Don't have an account? Sign up"):
    st.switch_page("pages/signup.py")

render_sidebar()
render_disclaimer_banner()
