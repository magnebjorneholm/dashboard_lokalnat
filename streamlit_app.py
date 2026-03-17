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
    get_case_name,
    get_case_notes,
    has_saved_reference,
    has_config_changed_since_compute,
    revert_to_saved,
    get_computed_at,
)
from frontend.common.styling import apply_styling
from auth.firebase_auth import is_dev_mode, initialize_firebase_auth
from auth.cookie_session import get_auth_cookie, set_auth_cookie, delete_auth_cookie
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

def _render_sidebar_actions():
    """Render case management controls in sidebar."""
    from frontend.utils.case_actions import run_calculation

    st.divider()

    # --- Case info ---
    case_name = get_case_name()
    if case_name:
        st.markdown(f"**{case_name}**")
        case_notes = get_case_notes()
        if case_notes:
            st.caption(case_notes)
    computed_at = get_computed_at()
    if computed_at:
        st.caption(f"Computed {computed_at.strftime('%H:%M, %d %b')}")

    # --- Compute button ---
    if st.button("Compute Revenue Frame", type="primary", width='stretch'):
        run_calculation()

    # --- Revert / New case button ---
    revert_label = "Revert to saved" if has_saved_reference() else "New case"
    if st.button(revert_label, width='stretch'):
        revert_to_saved()
        st.toast("Configuration reverted")
        st.rerun()

    # --- Status indicators ---
    if has_config_changed_since_compute():
        st.caption("Config changed since last run — results may be outdated.")


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
        # Clear session store before wiping auth state
        auth_uid = st.session_state.get("auth_uid")
        if auth_uid:
            from frontend.utils.state_manager import clear_session_store
            clear_session_store(auth_uid)
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

case_manager = st.Page(
    "pages/0_case_manager.py",
    title="1. Case Manager",
)

case_setup = st.Page(
    "pages/1_case_setup.py",
    title="2. Case Setup",
)

specification = st.Page(
    "pages/2_specification.py",
    title="3. Specification",
)

revenue_frame = st.Page(
    "pages/3_revenue_frame.py",
    title="4. Revenue Frame",
)


# =============================================================================
# MAIN
# =============================================================================

# Restore auth from cookie if session was lost (page refresh)
try_restore_auth_from_cookie()

if check_auth():
    # Set pending auth cookie (deferred from login to ensure JS renders)
    pending_token = st.session_state.pop("_pending_auth_cookie", None)
    if pending_token:
        set_auth_cookie(pending_token)

    # Restore working state from session store (page refresh)
    auth_uid = st.session_state.get("auth_uid")
    if auth_uid and not st.session_state.get("calculation_done"):
        from frontend.utils.state_manager import restore_from_session_store
        restore_from_session_store(auth_uid)

    render_sidebar()

    pg = st.navigation([case_manager, case_setup, specification, revenue_frame])
    pg.run()

else:
    # Register ALL pages to prevent "Page not found" on refresh
    # (URL may still point to a protected page after auth fails)
    pg = st.navigation(
        [login_page, case_manager, case_setup, specification, revenue_frame],
        position="hidden",
    )
    # Redirect to login if user landed on a protected page
    if pg != login_page:
        st.switch_page(login_page)
    else:
        pg.run()
