"""
Sign Up Page
"""
import streamlit as st
import os
from components.sidebar import render_sidebar
from components.disclaimer_banner import render_disclaimer_banner

from supabase import create_client, Client

# Initialize Supabase client using environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Fallback to secrets
if not SUPABASE_URL:
    try:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    except:
        pass
if not SUPABASE_ANON_KEY:
    try:
        SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
    except:
        pass

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {str(e)}")
else:
    st.warning("Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY.")

st.title("📝 Sign Up")

if not supabase:
    st.stop()

# Sign up form
with st.form("signup_form"):
    email = st.text_input("Email", placeholder="Enter your email")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    submit_button = st.form_submit_button("Sign Up")

    if submit_button:
        if email and password:
            try:
                # Sign up with Supabase
                response = supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })

                if response.user:
                    st.success("Sign up successful! Please check your email for confirmation.")
                    # Optionally, auto-login after sign up
                    # For now, just show success message
                else:
                    st.error("Sign up failed. Please try again.")
            except Exception as e:
                st.error(f"Sign up error: {str(e)}")
        else:
            st.warning("Please enter both email and password.")

# Option to go back to login
st.markdown("---")
if st.button("Already have an account? Login"):
    st.switch_page("pages/login.py")

# Render sidebar and disclaimer banner
render_sidebar()
render_disclaimer_banner()