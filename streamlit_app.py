"""
Regumetrica Streamlit Application.

Entry point för frontend-applikationen.
"""

import streamlit as st

from frontend.utils.state_manager import init_session_state, set_user_reid

# Sidkonfiguration
st.set_page_config(
    page_title="Regumetrica",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisera state
init_session_state()

# DEV_MODE flagga
DEV_MODE = True

# Sidebar: Företagsval
with st.sidebar:
    st.header("Regumetrica")
    
    if DEV_MODE:
        st.caption("Utvecklingsläge")
        
        # Ladda företagslista
        @st.cache_data(ttl=3600)
        def get_company_list():
            """Hämta lista med alla företags REId."""
            try:
                from data_loaders.baseline_data import load_baseline_data
                baseline = load_baseline_data()
                return sorted(baseline.df_all_companies["REId"].tolist())
            except Exception as e:
                st.error(f"Kunde inte ladda företagslista: {e}")
                return ["REL00886"]  # Fallback till golden test
        
        companies = get_company_list()
        
        # Default till golden test-företag
        default_idx = 0
        if "REL00886" in companies:
            default_idx = companies.index("REL00886")
        
        selected = st.selectbox(
            "Välj företag",
            options=companies,
            index=default_idx,
            key="company_selector"
        )
        
        set_user_reid(selected)
        
        st.divider()
        st.caption(f"Valt företag: {selected}")
    
    else:
        # Produktion: Företag från Firebase
        st.info("Logga in för att se ditt företag")
        # TODO: Implementera Firebase-integration

# Navigation
case_config = st.Page(
    "pages/1_case_config.py",
    title="Case Config",
    icon="⚙️",
    default=True
)

results = st.Page(
    "pages/2_results.py",
    title="Resultat",
    icon="📊"
)

# Kör navigation
pg = st.navigation([case_config, results])
pg.run()
