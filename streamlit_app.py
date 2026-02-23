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
    set_case_name,
    get_case_notes,
    set_case_notes,
    get_selected_modules,
    mark_case_saved,
    set_case_id,
    increment_saved_cases_count,
    set_computed_config,
    get_computed_config,
    set_saved_reference,
    has_saved_reference,
    has_unsaved_changes,
    has_config_changed_since_compute,
    revert_to_saved,
)
from frontend.common.styling import apply_styling
from auth.firebase_auth import is_dev_mode, initialize_firebase_auth
from auth.cookie_session import get_auth_cookie, delete_auth_cookie
from config.column_names import COL_COMPANY_NAME

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
def _get_company_list() -> list:
    """Retrieve list of all company REIds with display names."""
    try:
        from data_loaders.baseline_data import load_baseline_data
        baseline = load_baseline_data()
        df = baseline.df_all_companies[["REId", COL_COMPANY_NAME]].copy()
        df["display"] = df[COL_COMPANY_NAME] + " (" + df["REId"] + ")"
        return df.sort_values(COL_COMPANY_NAME).to_dict('records')
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_company_name_lookup() -> dict:
    """Build REId -> Company name lookup from baseline data."""
    try:
        from data_loaders.baseline_data import load_baseline_data
        baseline = load_baseline_data()
        df = baseline.df_all_companies[["REId", COL_COMPANY_NAME]].copy()
        return dict(zip(df["REId"], df[COL_COMPANY_NAME]))
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


def try_restore_auth_from_cookie() -> bool:
    """Attempt to restore auth session from browser cookie.

    Reads Firebase refresh token from cookie, exchanges it for a new
    ID token, verifies claims, and restores session state.

    Returns True if auth was successfully restored.
    """
    if is_dev_mode() or is_authenticated():
        return True

    refresh_token = get_auth_cookie()
    if not refresh_token:
        return False

    try:
        auth_manager = initialize_firebase_auth()

        # Exchange refresh token for a new ID token
        refreshed = auth_manager.auth.refresh(refresh_token)
        id_token = refreshed["idToken"]

        # Verify token and get claims via admin SDK
        claims = auth_manager.get_user_claims(id_token)
        if not claims:
            delete_auth_cookie()
            return False

        # Restore session state
        st.session_state["auth_user"] = refreshed
        st.session_state["auth_token"] = id_token
        st.session_state["auth_email"] = claims.get("email")
        st.session_state["auth_uid"] = claims.get("uid")
        st.session_state["auth_role"] = claims.get("role", "company")
        st.session_state["auth_reid"] = claims.get("reid")

        # Auto-set user_reid for company users
        if claims.get("role") == "company" and claims.get("reid"):
            set_user_reid(claims["reid"])

        return True

    except Exception:
        delete_auth_cookie()
        return False


# =============================================================================
# SIDEBAR ACTIONS
# =============================================================================

def _run_calculation() -> None:
    """Run the revenue frame calculation pipeline."""
    from frontend.utils.state_manager import get_filtered_ui_config
    from config.config_adapter import build_case_definition
    
    user_reid = get_user_reid()
    
    if user_reid is None:
        st.error("No company selected.")
        return
    
    with st.status("Running calculation...", expanded=True) as status:
        try:
            st.write("Loading baseline data...")
            from data_loaders.baseline_data import load_baseline_data
            from pipeline.core import run_pipeline
            baseline_data = load_baseline_data()

            # Reuse cached baseline if same company
            cached_reid = st.session_state.get("_baseline_reid")
            if cached_reid == user_reid and st.session_state.get("baseline_result") is not None:
                st.write("Using cached baseline...")
                baseline_result = st.session_state["baseline_result"]
            else:
                st.write("Computing baseline...")
                from config.case_definition import get_baseline_config
                baseline_config = get_baseline_config(user_reid)
                baseline_result = run_pipeline(baseline_data, baseline_config)
                st.session_state["baseline_result"] = baseline_result
                st.session_state["_baseline_reid"] = user_reid

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

            # Store which config produced this result
            set_computed_config(
                ui_config=st.session_state.get("ui_config", {}),
                selected_modules=get_selected_modules(),
            )

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


def _do_save_case(force_new: bool = False) -> bool:
    """Save the current case to storage. Uses computed config if available.

    Args:
        force_new: If True, always create a new case (ignore existing case_id).
    """
    from frontend.utils.case_storage import save_case

    user_reid = get_user_reid()
    case_name = get_case_name() or "Untitled Case"
    case_notes = get_case_notes()
    case_id = None if force_new else get_case_id()

    # Prefer computed config (last pipeline run); fall back to working state
    computed_ui, computed_modules = get_computed_config()
    if computed_ui is not None:
        ui_config = computed_ui
        selected_modules = computed_modules
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
        set_saved_reference(ui_config, selected_modules)

        if case_id is None:
            increment_saved_cases_count()

        return True

    except ValueError as e:
        st.error(str(e))
        return False
    except Exception as e:
        st.error(f"Failed to save case: {e}")
        return False


def _on_sidebar_name_change():
    """Callback: sync sidebar name input to session state and auto-persist."""
    new_name = st.session_state["sidebar_case_name"]
    set_case_name(new_name)
    # Auto-persist for saved cases
    case_id = get_case_id()
    if case_id:
        from frontend.utils.case_storage import update_case_metadata
        try:
            update_case_metadata(get_user_reid(), case_id, new_name, get_case_notes())
        except Exception:
            pass  # Best-effort, full save still available


def _on_sidebar_notes_change():
    """Callback: sync sidebar notes input to session state and auto-persist."""
    new_notes = st.session_state["sidebar_case_notes"]
    set_case_notes(new_notes)
    case_id = get_case_id()
    if case_id:
        from frontend.utils.case_storage import update_case_metadata
        try:
            update_case_metadata(get_user_reid(), case_id, get_case_name() or "Untitled Case", new_notes)
        except Exception:
            pass


@st.dialog("Update saved case")
def _confirm_update_case():
    """Confirmation dialog before overwriting an existing case."""
    case_name = get_case_name() or "Untitled Case"
    st.write(f"Overwrite saved case **{case_name}** with the last computed configuration?")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Update", type="primary", width='stretch', key="dialog_update"):
            if _do_save_case():
                st.toast("Case updated successfully")
            st.rerun()
    with col_no:
        if st.button("Cancel", width='stretch', key="dialog_update_cancel"):
            st.rerun()


@st.dialog("Save as new case")
def _confirm_save_as_new():
    """Confirmation dialog before creating a new case."""
    case_name = get_case_name() or "Untitled Case"
    st.write(f"Save current configuration as a new case: **{case_name}**?")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Save", type="primary", width='stretch', key="dialog_save"):
            if _do_save_case(force_new=True):
                st.toast("Saved as new case")
            st.rerun()
    with col_no:
        if st.button("Cancel", width='stretch', key="dialog_cancel"):
            st.rerun()


def _render_sidebar_actions():
    """Render case management controls in sidebar."""
    st.divider()

    # --- Active case identity (always shows source of truth) ---
    # Callbacks fire before script body, so values are already up-to-date here
    case_name = get_case_name()
    case_notes = get_case_notes()
    if case_name:
        st.markdown(f"**{case_name}**")
        if case_notes:
            st.caption(case_notes)
    else:
        st.caption("No case name")

    # --- Edit name / notes (on_change callbacks update immediately) ---
    st.text_input(
        "Case name",
        placeholder="Enter case name",
        key="sidebar_case_name",
        label_visibility="collapsed",
        on_change=_on_sidebar_name_change,
    )
    st.text_input(
        "Notes",
        placeholder="Notes (optional)",
        key="sidebar_case_notes",
        label_visibility="collapsed",
        on_change=_on_sidebar_notes_change,
    )

    st.divider()

    # --- Compute button ---
    if st.button("Compute Revenue Frame", type="primary", width='stretch'):
        _run_calculation()

    # --- Update saved case (only for existing cases, with confirmation) ---
    case_id = get_case_id()
    if case_id:
        if st.button("Update saved case (last run)", width='stretch'):
            _confirm_update_case()

    # --- Save as new case (always available, with confirmation) ---
    if st.button("Save as new case (last run)", width='stretch'):
        _confirm_save_as_new()

    # --- Revert button ---
    revert_label = "Revert to saved" if has_saved_reference() else "Reset to defaults"
    if st.button(revert_label, width='stretch'):
        revert_to_saved()
        st.toast("Configuration reverted")
        st.rerun()

    # --- Status indicators ---
    if has_config_changed_since_compute():
        st.caption("Config changed since last run — save will use the last computed configuration.")
    if has_unsaved_changes():
        st.caption("Unsaved changes")


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
    companies = _get_company_list()
    if not companies:
        companies = [{"REId": "REL00886", "display": "Test Company (REL00886)"}]
    
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
        
        companies = _get_company_list()
        
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
        delete_auth_cookie()
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

# Restore auth from cookie if session was lost (page refresh)
try_restore_auth_from_cookie()

if check_auth():
    render_sidebar()

    pg = st.navigation([case_definition, case_config, results])
    pg.run()

else:
    pg = st.navigation([login_page])
    pg.run()