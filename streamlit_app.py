"""
Regumetrica Streamlit Application.

Entry point för frontend-applikationen.
"""

import streamlit as st

from frontend.utils.state_manager import init_session_state, set_user_reid

# Page configuration
st.set_page_config(
    page_title="Regumetrica",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize state
init_session_state()

# DEV_MODE flag
DEV_MODE = True

# Sidebar: Company selection
with st.sidebar:
    st.header("Regumetrica")
    
    if DEV_MODE:
        st.caption("Development Mode")
        
        # Load company list
        @st.cache_data(ttl=3600)
        def get_company_list():
            """Retrieve list of all company REIds."""
            try:
                from data_loaders.baseline_data import load_baseline_data
                baseline = load_baseline_data()
                return sorted(baseline.df_all_companies["REId"].tolist())
            except Exception as e:
                st.error(f"Failed to load company list: {e}")
                return ["REL00886"]  # Fallback to golden test
        
        companies = get_company_list()
        
        # Default to golden test company
        default_idx = 0
        if "REL00886" in companies:
            default_idx = companies.index("REL00886")
        
        selected = st.selectbox(
            "Select Company",
            options=companies,
            index=default_idx,
            key="company_selector"
        )
        
        set_user_reid(selected)
        
        st.divider()
        st.caption(f"Selected: {selected}")
    
    else:
        # Production: Company from Firebase
        st.info("Sign in to view your company")
        # TODO: Implement Firebase integration

# Navigation
case_config = st.Page(
    "pages/1_case_config.py",
    title="Case Config",
    icon="⚙️",
    default=True
)

results = st.Page(
    "pages/2_results.py",
    title="Results",
    icon="📊"
)

# Run navigation
pg = st.navigation([case_config, results])
pg.run()