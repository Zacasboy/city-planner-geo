"""
Login Page
T1.8: Frontend base: login page
"""
import streamlit as st
import os
from components.sidebar import render_sidebar
from components.disclaimer_banner import render_disclaimer_banner

# Check if supabase client is available in session state or we can access it via st.session_state
# We'll assume the supabase client is initialized in app.py and stored in st.session_state.supabase
# However, to avoid circular imports, we'll re-initialize if needed or get from cache.

# For simplicity, we'll check if we have supabase in st.session_state, else try to create it.
# But note: the supabase client initialization is in app.py, so we can access it via st.session_state if we stored it there.
# However, to keep the login page self-contained, we'll re-initialize using env vars.
# This is acceptable because the client initialization is cheap.

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

st.title("🔐 Login to City Planner Geo")

if not supabase:
    st.stop()  # Stop execution if supabase client not available

# Login form
with st.form("login_form"):
    email = st.text_input("Email", placeholder="Enter your email")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    submit_button = st.form_submit_button("Login")

    if submit_button:
        if email and password:
            try:
                # Sign in with Supabase
                response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

                if response.user:
                    # Store user and tokens in session state
                    st.session_state.user = response.user
                    st.session_state.access_token = response.session.access_token
                    st.session_state.refresh_token = response.session.refresh_token
                    st.success("Login successful!")
                    # Trigger a rerun to update the navigation (logged in state)
                    st.rerun()
                else:
                    st.error("Login failed. Please check your credentials.")
            except Exception as e:
                st.error(f"Login error: {str(e)}")
        else:
            st.warning("Please enter both email and password.")

# Option to sign up
st.markdown("---")
if st.button("Don't have an account? Sign up"):
    st.switch_page("pages/signup.py")

# Render sidebar and disclaimer banner
render_sidebar()
render_disclaimer_banner()