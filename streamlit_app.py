"""
Regumetrica Streamlit Application.

Entry point för frontend-applikationen.
"""

import streamlit as st

from frontend.utils.state_manager import init_session_state, set_user_reid
from frontend.common.styling import apply_styling, COLORS

# === SIDKONFIGURATION ===
st.set_page_config(
    page_title="Regumetrica",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://regumetrica.com/support",
        "Report a bug": "https://regumetrica.com/feedback",
        "About": "Regumetrica - Regulatory Analysis Platform for Swedish Electricity Distribution"
    }
)

# === APPLICERA GRAFISK PROFIL ===
apply_styling()

# === INITIALISERA STATE ===
init_session_state()

# DEV_MODE flagga
DEV_MODE = True


# === SIDEBAR ===
with st.sidebar:
    # Logotyp/varumärke
    st.markdown(
        f"""
        <div style="padding: 1rem 0 1.5rem 0;">
            <h1 style="
                color: {COLORS['sidebar_text']};
                font-size: 1.5rem;
                font-weight: 700;
                margin: 0;
                letter-spacing: -0.025em;
            ">Regumetrica</h1>
            <p style="
                color: {COLORS['sidebar_muted']};
                font-size: 0.75rem;
                margin: 4px 0 0 0;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            ">Regulatory Analysis Platform</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.divider()
    
    if DEV_MODE:
        st.markdown(
            f"<span style='color: {COLORS['warning']}; font-size: 0.75rem;'>DEV MODE</span>",
            unsafe_allow_html=True
        )
        
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
        
        # Visa valt företag med styling
        st.markdown(
            f"""
            <div style="
                background: rgba(37, 99, 235, 0.1);
                border-left: 3px solid {COLORS['primary']};
                padding: 12px 16px;
                border-radius: 0 6px 6px 0;
            ">
                <div style="color: {COLORS['sidebar_muted']}; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;">
                    Aktivt företag
                </div>
                <div style="color: {COLORS['sidebar_text']}; font-weight: 600; margin-top: 4px;">
                    {selected}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    else:
        # Produktion: Företag från Firebase
        st.info("Logga in för att se ditt företag")
        # TODO: Implementera Firebase-integration
    
    # Footer i sidebar
    st.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True)
    st.divider()
    st.markdown(
        f"""
        <div style="color: {COLORS['sidebar_muted']}; font-size: 0.7rem; text-align: center;">
            Version 1.0 Beta<br>
            IFN / Regumetrica
        </div>
        """,
        unsafe_allow_html=True
    )


# === NAVIGATION ===
case_config = st.Page(
    "pages/1_case_config.py",
    title="Case Config",
    icon=":material/tune:",
    default=True
)

results = st.Page(
    "pages/2_results.py",
    title="Resultat",
    icon=":material/analytics:"
)

# Kör navigation
pg = st.navigation([case_config, results])
pg.run()