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
    get_user_reid,
    get_case_id,
    get_case_name,
    get_case_notes,
    get_selected_modules,
    mark_case_saved,
    set_case_id,
    increment_saved_cases_count,
    has_main_config,
    set_main_config,
    get_snapshots,
    MAX_SNAPSHOTS,
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
# COMPANY NAME LOOKUP
# =============================================================================

@st.cache_data(ttl=3600)
def get_company_name_lookup() -> dict:
    """Build REId -> Company name lookup from baseline data."""
    try:
        from data_loaders.baseline_data import load_baseline_data
        baseline = load_baseline_data()
        df = baseline.df_all_companies[["REId", "Företag"]].copy()
        return dict(zip(df["REId"], df["Företag"]))
    except Exception:
        return {}


def get_company_display(reid: str) -> str:
    """Get display string: 'Company Name (REId)' or just REId if lookup fails."""
    if not reid:
        return "None"
    lookup = get_company_name_lookup()
    company_name = lookup.get(reid)
    if company_name:
        return f"{company_name} ({reid})"
    return reid


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
# SIDEBAR ACTIONS
# =============================================================================

def _run_calculation() -> None:
    """Run the revenue frame calculation pipeline."""
    from frontend.utils.state_manager import get_filtered_ui_config
    from frontend.utils.config_adapter import build_case_definition
    
    user_reid = get_user_reid()
    
    if user_reid is None:
        st.error("No company selected.")
        return
    
    with st.status("Running calculation...", expanded=True) as status:
        try:
            st.write("Loading baseline data...")
            from data_loaders.baseline_data import load_baseline_data
            baseline_data = load_baseline_data()
            
            st.write("Retrieving baseline...")
            from config.case_definition import get_baseline_config
            from pipeline.core import run_pipeline
            
            baseline_config = get_baseline_config(user_reid)
            baseline_result = run_pipeline(baseline_data, baseline_config)
            st.session_state["baseline_result"] = baseline_result
            
            st.write("Building case...")
            filtered_config = get_filtered_ui_config()
            case_definition = build_case_definition(
                user_reid,
                filtered_config
            )
            
            st.write("Calculating revenue frame...")
            case_result = run_pipeline(baseline_data, case_definition)
            st.session_state["case_result"] = case_result
            
            st.session_state["calculation_done"] = True
            
            # Snapshot system: first calculation becomes main, subsequent are candidates
            if not has_main_config():
                set_main_config(
                    ui_config=st.session_state.get("ui_config", {}),
                    selected_modules=get_selected_modules(),
                    case_result=case_result,
                )
            # Else: this is a snapshot candidate -- main_* keys are not touched
            
            status.update(label="Calculation complete", state="complete")
            
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            status.update(label="Error", state="error")
            return
        except Exception as e:
            st.error(f"Calculation error: {e}")
            with st.expander("Technical details"):
                st.exception(e)
            status.update(label="Error", state="error")
            return
    
    st.switch_page("pages/2_results.py")


def _do_save_case() -> bool:
    """Save the current case to storage. Uses main config if available."""
    from frontend.utils.case_storage import save_case
    
    user_reid = get_user_reid()
    case_name = get_case_name() or "Untitled Case"
    case_notes = get_case_notes()
    case_id = get_case_id()
    
    # Use main config if established, otherwise fall back to working state
    if has_main_config():
        ui_config = st.session_state["main_ui_config"]
        selected_modules = st.session_state["main_selected_modules"]
    else:
        ui_config = st.session_state.get("ui_config", {})
        selected_modules = get_selected_modules()
    
    try:
        saved = save_case(
            user_reid=user_reid,
            case_name=case_name,
            case_notes=case_notes,
            ui_config=ui_config,
            selected_modules=selected_modules,
            case_id=case_id,
        )
        
        set_case_id(saved.id)
        mark_case_saved()
        
        if case_id is None:
            increment_saved_cases_count()
        
        return True
        
    except ValueError as e:
        st.error(str(e))
        return False
    except Exception as e:
        st.error(f"Failed to save case: {e}")
        return False


def _render_sidebar_actions():
    """Render Compute and Save buttons in sidebar."""
    st.divider()
    
    # Compute button
    if st.button("Compute Revenue Frame", type="primary", width='stretch'):
        _run_calculation()
    
    # Save/Update button
    case_id = get_case_id()
    save_label = "Update saved case" if case_id else "Save case"
    
    if st.button(save_label, width='stretch'):
        if _do_save_case():
            action = "updated" if case_id else "saved"
            st.toast(f"Case {action} successfully")
    
    # Snapshot count indicator
    snapshots = get_snapshots()
    if snapshots:
        st.caption(f"Snapshots: {len(snapshots)}/{MAX_SNAPSHOTS}")


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
        
        # Action buttons (always visible when company is selected)
        if get_user_reid():
            _render_sidebar_actions()


def _render_dev_mode_selector():
    """Render company selector for dev mode."""
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
    
    options = [c["display"] for c in companies]
    reid_lookup = {c["display"]: c["REId"] for c in companies}
    
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
    current_reid = st.session_state.get('user_reid')
    st.caption(f"Selected: {get_company_display(current_reid)}")


def _render_authenticated_sidebar():
    """Render sidebar for authenticated users."""
    email = get_auth_email()
    role = get_auth_role()
    reid = get_auth_reid()
    
    st.caption(f"User: {email}")
    
    if role == "regulator":
        st.caption("Regulator access")
        st.divider()
        
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
            
            current_reid = st.session_state.get('user_reid')
            st.caption(f"Analyzing: {get_company_display(current_reid)}")
    
    else:
        company_display = get_company_display(reid)
        st.caption(f"Company: {company_display}")
        
        if reid and st.session_state.get("user_reid") != reid:
            set_user_reid(reid)
    
    st.divider()
    
    # Logout button
    if st.button("Logout", width='stretch'):
        auth_manager = initialize_firebase_auth()
        auth_manager.sign_out()
        st.session_state["user_reid"] = None
        st.rerun()


# =============================================================================
# NAVIGATION
# =============================================================================

login_page = st.Page(
    "pages/login.py",
    title="Login",
)

case_definition = st.Page(
    "pages/0_case_definition.py",
    title="Define",
)

case_config = st.Page(
    "pages/1_case_config.py",
    title="Configure",
)

results = st.Page(
    "pages/2_results.py",
    title="Results",
)


# =============================================================================
# MAIN
# =============================================================================

if check_auth():
    render_sidebar()
    
    pg = st.navigation([case_definition, case_config, results])
    pg.run()

else:
    pg = st.navigation([login_page])
    pg.run()