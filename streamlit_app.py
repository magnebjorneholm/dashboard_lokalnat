"""
Regumetrica Streamlit Application.

Entry point for the frontend application.
Handles authentication guard and navigation.
"""

import streamlit as st

from frontend.utils.state_manager import (
    init_session_state, 
    set_user_reid,
    is_authenticated,
    get_auth_role,
    get_auth_reid,
    get_auth_email,
    is_regulator,
)
from frontend.common.styling import apply_styling
from auth.firebase_auth import is_dev_mode, initialize_firebase_auth

# Page configuration
st.set_page_config(
    page_title="Regumetrica",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styling (fonts, refinements)
apply_styling()

# Initialize state
init_session_state()


# =============================================================================
# AUTHENTICATION CHECK
# =============================================================================

def check_auth() -> bool:
    """
    Check if user is authorized to access the app.
    
    Returns True if:
    - Dev mode is enabled (skip_auth = true in secrets)
    - User is logged in via Firebase
    """
    if is_dev_mode():
        return True
    return is_authenticated()


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Render sidebar with company selection based on auth state."""
    with st.sidebar:
        st.header("Regumetrica")
        
        # Dev mode indicator
        if is_dev_mode():
            st.caption("Dev Mode (auth bypassed)")
            _render_dev_mode_selector()
        
        elif is_authenticated():
            _render_authenticated_sidebar()
        
        else:
            st.warning("Not logged in")


def _render_dev_mode_selector():
    """Render company selector for dev mode."""
    # Load company list
    @st.cache_data(ttl=3600)
    def get_company_list():
        """Retrieve list of all company REIds with names."""
        try:
            from data_loaders.baseline_data import load_baseline_data
            baseline = load_baseline_data()
            df = baseline.df_all_companies[["REId", "Företag"]].copy()
            df["display"] = df["Företag"] + " (" + df["REId"] + ")"
            return df.sort_values("Företag").to_dict('records')
        except Exception as e:
            st.error(f"Failed to load company list: {e}")
            return [{"REId": "REL00886", "display": "Test Company (REL00886)"}]
    
    companies = get_company_list()
    
    # Create lookup
    options = [c["display"] for c in companies]
    reid_lookup = {c["display"]: c["REId"] for c in companies}
    
    # Default to golden test company
    default_idx = 0
    for i, c in enumerate(companies):
        if c["REId"] == "REL00886":
            default_idx = i
            break
    
    selected_display = st.selectbox(
        "Select Company",
        options=options,
        index=default_idx,
        key="company_selector"
    )
    
    if selected_display:
        reid = reid_lookup.get(selected_display)
        if reid:
            set_user_reid(reid)
    
    st.divider()
    st.caption(f"REId: {st.session_state.get('user_reid', 'None')}")


def _render_authenticated_sidebar():
    """Render sidebar for authenticated users."""
    email = get_auth_email()
    role = get_auth_role()
    reid = get_auth_reid()
    
    # User info
    st.caption(f"User: {email}")
    
    if role == "regulator":
        st.caption("Regulator access")
        st.divider()
        
        # Regulator gets dropdown to select any company
        @st.cache_data(ttl=3600)
        def get_company_list():
            try:
                from data_loaders.baseline_data import load_baseline_data
                baseline = load_baseline_data()
                df = baseline.df_all_companies[["REId", "Företag"]].copy()
                df["display"] = df["Företag"] + " (" + df["REId"] + ")"
                return df.sort_values("Företag").to_dict('records')
            except Exception:
                return []
        
        companies = get_company_list()
        
        if companies:
            options = [c["display"] for c in companies]
            reid_lookup = {c["display"]: c["REId"] for c in companies}
            
            selected_display = st.selectbox(
                "Select Company to Analyze",
                options=options,
                key="regulator_company_selector"
            )
            
            if selected_display:
                selected_reid = reid_lookup.get(selected_display)
                if selected_reid:
                    set_user_reid(selected_reid)
            
            st.caption(f"Analyzing: {st.session_state.get('user_reid', 'None')}")
    
    else:
        # Company user - fixed REId
        st.caption(f"Company: {reid}")
        
        # Auto-set user_reid from auth
        if reid and st.session_state.get("user_reid") != reid:
            set_user_reid(reid)
    
    st.divider()
    
    # Logout button
    if st.button("Logout", use_container_width=True):
        auth_manager = initialize_firebase_auth()
        auth_manager.sign_out()
        # Clear user_reid as well
        st.session_state["user_reid"] = None
        st.rerun()


# =============================================================================
# NAVIGATION
# =============================================================================

# Define pages
login_page = st.Page(
    "pages/login.py",
    title="Login",
)

case_definition = st.Page(
    "pages/0_case_definition.py",
    title="Case Definition",
)

case_config = st.Page(
    "pages/1_case_config.py",
    title="Case Configuration",
)

results = st.Page(
    "pages/2_results.py",
    title="Results",
)


# =============================================================================
# MAIN
# =============================================================================

if check_auth():
    # User is authorized - show sidebar and main navigation
    render_sidebar()
    
    pg = st.navigation([case_definition, case_config, results])
    pg.run()

else:
    # User not authorized - show only login page
    pg = st.navigation([login_page])
    pg.run()