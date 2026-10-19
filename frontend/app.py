"""
City Planner Geo - Frontend Application
T1.8: Frontend base: app.py, multipage, login, sidebar, DisclaimerBanner
"""
import streamlit as st
import os
from typing import Optional

# Import Supabase client if available
try:
    from supabase import create_client, Client
except ImportError:
    st.warning("Supabase client not installed. Please install supabase package.")
    Client = None

# Initialize session state for authentication
if "user" not in st.session_state:
    st.session_state.user = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

# Load environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# If not set via env, try to get from secrets (for Streamlit Cloud deployment)
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

# Initialize Supabase client
supabase: Optional[Client] = None
if Client and SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {str(e)}")

# Set page configuration
st.set_page_config(
    page_title="City Planner Geo",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define pages using st.Page
login_page = st.Page(
    "pages/login.py",
    title="Login",
    icon="🔐",
)
home_page = st.Page(
    "pages/home.py",
    title="Home",
    icon="🏠",
)
# Additional pages will be added as they are implemented
geo_page = st.Page(
    "pages/geo.py",
    title="Geo Validation",
    icon="🌍",
)
ecology_page = st.Page(
    "pages/ecology.py",
    title="Ecological Analysis",
    icon="🌱",
)
forest_page = st.Page(
    "pages/forest.py",
    title="Forest Analysis",
    icon="🌲",
)
structural_page = st.Page(
    "pages/structural.py",
    title="Structural Analysis",
    icon="🏗️",
)
orchestration_page = st.Page(
    "pages/orchestration.py",
    title="Orchestration",
    icon="🔄",
)
reports_page = st.Page(
    "pages/reports.py",
    title="Reports",
    icon="📋",
)

# Create navigation structure
# For now, we have login and home; others will be added later
if st.session_state.user is None:
    # Not logged in: only show login page
    pg = st.navigation([login_page])
else:
    # Logged in: show home and other pages
    pg = st.navigation([
        home_page,
        geo_page,
        ecology_page,
        forest_page,
        structural_page,
        orchestration_page,
        reports_page,
    ])

# Run the selected page
pg.run()

# Add disclaimer banner at the bottom (outside navigation)
def disclaimer_banner():
    """Display disclaimer banner."""
    st.markdown("---")
    st.caption(
        """
        Disclaimer: This application is for demonstration purposes only.
        Data provided may not be accurate or complete.
        Use at your own risk.
        """
    )

disclaimer_banner()