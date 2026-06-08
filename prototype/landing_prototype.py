"""
Regumetrica landing page — PROTOTYPE.

Throwaway prototype to validate layout and navigation with stakeholders before
integrating into the main app. See plans/landing_page.md for the full plan.

Run from project root:
    ./venv/Scripts/python.exe -m streamlit run prototype/landing_prototype.py --server.port 8502

Then open http://localhost:8502
"""

import sys
from pathlib import Path

# Make project root importable so we reuse the real apply_styling().
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from frontend.common.styling import apply_styling


st.set_page_config(
    page_title="Regumetrica",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_styling()

# Landing-specific CSS: hide sidebar entirely, tighten container.
# Mirrors what frontend/common/landing_styling.py will do in the final version.
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        .block-container {
            max-width: 1100px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# NAVIGATION — top nav, matches the final structure exactly
# =============================================================================

home = st.Page(
    "landing_pages/home.py",
    title="Home",
    icon=":material/home:",
    default=True,
)
user_manual = st.Page(
    "landing_pages/user_manual.py",
    title="User Manual",
    icon=":material/menu_book:",
)
team = st.Page(
    "landing_pages/team.py",
    title="Meet the Team",
    icon=":material/group:",
)
contact = st.Page(
    "landing_pages/contact.py",
    title="Contact",
    icon=":material/mail:",
)
signin = st.Page(
    "landing_pages/signin_placeholder.py",
    title="Sign in",
    icon=":material/login:",
)

pg = st.navigation([home, user_manual, team, contact, signin], position="top")
pg.run()
