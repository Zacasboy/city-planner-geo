"""Aplicação Streamlit: navegação entre páginas.

T1.8: base do frontend (multipágina, login, barra lateral, aviso legal).
Arranque: `streamlit run frontend/app.py`, a partir da raiz do repositório.
"""

import sys
from pathlib import Path

import streamlit as st

# As páginas importam `frontend.components...`; a raiz do repositório tem de estar no path.
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

for key in ("user", "access_token", "refresh_token"):
    st.session_state.setdefault(key, None)

st.set_page_config(
    page_title="City Planner Geo",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ANONYMOUS_PAGES = [
    st.Page("pages/login.py", title="Login", icon="🔐"),
    st.Page("pages/signup.py", title="Sign up", icon="📝"),
]

LOGGED_IN_PAGES = [
    st.Page("pages/home.py", title="Home", icon="🏠"),
    st.Page("pages/geo.py", title="Geo Validation", icon="🌍"),
    st.Page("pages/ecology.py", title="Ecological Analysis", icon="🌱"),
    st.Page("pages/forest.py", title="Forest Analysis", icon="🌲"),
    st.Page("pages/structural.py", title="Structural Analysis", icon="🏗️"),
    st.Page("pages/orchestration.py", title="Orchestration", icon="🔄"),
    st.Page("pages/reports.py", title="Reports", icon="📋"),
]

if st.session_state.user is None:
    navigation = st.navigation(ANONYMOUS_PAGES)
else:
    navigation = st.navigation(LOGGED_IN_PAGES)

navigation.run()
