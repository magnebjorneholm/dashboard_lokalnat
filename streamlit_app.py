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
)
from frontend.common.styling import apply_styling
from auth.firebase_auth import is_dev_mode, initialize_firebase_auth
from auth.cookie_session import (
    get_auth_cookie, set_auth_cookie, delete_auth_cookie,
    get_case_cookie, set_case_cookie, delete_case_cookie,
)
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
    if st.session_state.get("_logging_out"):
        delete_auth_cookie()
        # Only clear the flag once the browser has actually removed the cookie.
        # Until then, keep blocking cookie-based auth restoration.
        if not get_auth_cookie():
            st.session_state.pop("_logging_out", None)
        return False

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


def try_restore_case_from_cookie() -> None:
    """Restore the last active case from cookie after a page refresh.

    Runs at most once per Streamlit session (guarded by ``_case_restored``).
    Only loads a case that still exists and belongs to the current user.
    """
    if st.session_state.get("_case_restored"):
        return
    st.session_state["_case_restored"] = True

    case_id = get_case_cookie()
    if not case_id:
        return

    user_reid = get_user_reid()
    if not user_reid:
        return

    try:
        from frontend.utils.case_storage import load_case, apply_case_to_session
        case = load_case(user_reid, case_id)
        if case:
            apply_case_to_session(case, st.session_state)
            # Mark as already synced so _sync_case_cookie doesn't re-write
            st.session_state["_case_cookie_synced"] = case_id
        else:
            # Case was deleted or belongs to a different user — clean up
            delete_case_cookie()
    except Exception:
        # Storage unavailable — don't block the app
        pass


def _sync_case_cookie() -> None:
    """Keep the case cookie in sync with ``session_state["case_id"]``.

    Called on every authenticated render. Only writes a cookie when the
    active case actually changes, tracked via ``_case_cookie_synced``.
    """
    case_id = st.session_state.get("case_id")
    last_synced = st.session_state.get("_case_cookie_synced")

    if case_id == last_synced:
        return

    if case_id:
        set_case_cookie(case_id)
    else:
        delete_case_cookie()

    st.session_state["_case_cookie_synced"] = case_id


# =============================================================================
# SIDEBAR ACTIONS
# =============================================================================

def _render_sidebar_actions():
    """Render case management controls in sidebar (placeholder, buttons moved to Revenue Frame)."""
    pass


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

    # Logout button with confirmation dialog
    @st.dialog("Log out")
    def _confirm_logout():
        st.write("Are you sure you want to log out? Any unsaved changes will be lost.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, log out", type="primary", use_container_width=True):
                st.session_state["_logging_out"] = True
                auth_manager = initialize_firebase_auth()
                auth_manager.sign_out()
                st.session_state["user_reid"] = None
                st.rerun()
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.rerun()

    if st.button("Log out", use_container_width=True):
        _confirm_logout()


# =============================================================================
# NAVIGATION
# =============================================================================

login_page = st.Page(
    "pages/login.py",
    title="Login",
)

case_manager = st.Page(
    "pages/1_create_and_select_case.py",
    title="1. Create and select case",
)

case_setup = st.Page(
    "pages/2_case_setup.py",
    title="2. Select modules to modify",
)

specification = st.Page(
    "pages/3_specification.py",
    title="3. Configure selected modules",
)

revenue_frame = st.Page(
    "pages/4_revenue_frame.py",
    title="4. Compute revenue frame and save",
)

new_benchmarking = st.Page(
    "pages/5_new_benchmarking.py",
    title="5. New benchmarking model",
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

    # Restore last saved case on page refresh (once per session)
    try_restore_case_from_cookie()
    # Keep case cookie in sync when user switches/creates/resets cases
    _sync_case_cookie()

    render_sidebar()

    pg = st.navigation([case_manager, case_setup, specification, revenue_frame, new_benchmarking])
    pg.run()

else:
    # Register ALL pages to prevent "Page not found" on refresh
    # (URL may still point to a protected page after auth fails)
    pg = st.navigation(
        [login_page, case_manager, case_setup, specification, revenue_frame, new_benchmarking],
        position="hidden",
    )
    # Redirect to login if user landed on a protected page
    if pg != login_page:
        st.switch_page(login_page)
    else:
        pg.run()
