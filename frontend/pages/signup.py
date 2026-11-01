"""Página de registo."""

import streamlit as st

from frontend.components.disclaimer_banner import render_disclaimer_banner
from frontend.components.sidebar import render_sidebar
from frontend.components.supabase_client import get_supabase_client

st.title("📝 Sign Up")

supabase = get_supabase_client()
if not supabase:
    st.stop()

with st.form("signup_form"):
    email = st.text_input("Email", placeholder="Enter your email")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    submit_button = st.form_submit_button("Sign Up")

    if submit_button:
        if email and password:
            try:
                response = supabase.auth.sign_up({"email": email, "password": password})
                if response.user:
                    st.success("Sign up successful! Please check your email for confirmation.")
                else:
                    st.error("Sign up failed. Please try again.")
            except Exception as e:  # o cliente Supabase levanta vários tipos de erro
                st.error(f"Sign up error: {e}")
        else:
            st.warning("Please enter both email and password.")

st.markdown("---")
if st.button("Already have an account? Login"):
    st.switch_page("pages/login.py")

render_sidebar()
render_disclaimer_banner()
