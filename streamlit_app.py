"""
Regumetrica Streamlit Application.

Entry point. A two-zone controller:

  ZON 1 — Landing (public): native top-nav (Home / Tools / Team), no sidebar,
          its own look (frontend/common/landing_shell.py). Sign in happens in a
          dialog (frontend/common/auth_dialog.py).
  ZON 2 — Tool (authenticated): the "Revenue cap tool" pages with the locked
          sidebar + company selector + logout, exactly as before.

A successful login reruns the app; check_auth() then routes into zone 2.
See landing_pages/FRONTEND_FILES.md for the full architecture.
"""

import streamlit as st

from frontend.utils.state_manager import (
    init_session_state,
    set_user_reid,
    is_authenticated,
    get_auth_role,
    get_auth_reid,
    get_auth_email,
    get_user_reid,
)
from frontend.utils.company_directory import get_company_records, get_company_display
from frontend.common.styling import apply_base_styling, apply_tool_chrome
from auth.firebase_auth import is_dev_mode, initialize_firebase_auth
from auth.cookie_session import (
    get_auth_cookie, set_auth_cookie, delete_auth_cookie,
    get_case_cookie, set_case_cookie, delete_case_cookie,
)

# Page configuration
st.set_page_config(
    page_title="Regumetrica",
    page_icon="static/favicon.svg",  # monochrome "R" in the primary color
    layout="wide",
    initial_sidebar_state="expanded",
)

# Base styling (fonts + branding) applies to both zones.
apply_base_styling()

# Initialize state
init_session_state()


# =============================================================================
# AUTHENTICATION CHECK
# =============================================================================

def check_auth() -> bool:
    """True if the user may access the tool zone (dev mode or logged in)."""
    if is_dev_mode():
        return True
    return is_authenticated()


def try_restore_auth_from_cookie() -> bool:
    """Restore auth session from the browser cookie after a page refresh.

    Reads the Firebase refresh token, exchanges it for a new ID token, verifies
    claims, and restores session state. Returns True if auth was restored.
    """
    if st.session_state.get("_logging_out"):
        delete_auth_cookie()
        # Only clear the flag once the browser has actually removed the cookie.
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
            st.session_state["_case_cookie_synced"] = case_id
        else:
            delete_case_cookie()
    except Exception:
        # Storage unavailable — don't block the app
        pass


def _sync_case_cookie() -> None:
    """Keep the case cookie in sync with ``session_state["case_id"]``."""
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
# SIDEBAR (tool zone only)
# =============================================================================

def render_sidebar():
    """Render the tool-zone sidebar: company selection + logout."""
    with st.sidebar:
        if is_dev_mode():
            st.caption("Dev Mode (auth bypassed)")
            _render_dev_mode_selector()
        elif is_authenticated():
            _render_authenticated_sidebar()
        else:
            st.warning("Not logged in")


def _render_dev_mode_selector():
    """Company selector for dev mode."""
    companies = get_company_records()
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
        key="company_selector",
    )

    if selected_display:
        reid = reid_lookup.get(selected_display)
        if reid:
            set_user_reid(reid)


def _render_authenticated_sidebar():
    """Sidebar for authenticated users: company context + logout."""
    email = get_auth_email()
    role = get_auth_role()
    reid = get_auth_reid()

    st.caption(f"User: {email}")

    if role == "regulator":
        st.caption("Regulator access")
        st.divider()

        companies = get_company_records()
        if companies:
            options = [c["display"] for c in companies]
            reid_lookup = {c["display"]: c["REId"] for c in companies}

            selected_display = st.selectbox(
                "Select Company to Analyze",
                options=options,
                key="regulator_company_selector",
            )
            if selected_display:
                selected_reid = reid_lookup.get(selected_display)
                if selected_reid:
                    set_user_reid(selected_reid)

            current_reid = st.session_state.get("user_reid")
            st.caption(f"Analyzing: {get_company_display(current_reid)}")
    else:
        st.caption(f"Company: {get_company_display(reid)}")
        if reid and st.session_state.get("user_reid") != reid:
            set_user_reid(reid)

    st.divider()

    @st.dialog("Log out")
    def _confirm_logout():
        st.write("Are you sure you want to log out? Any unsaved changes will be lost.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, log out", type="primary", width="stretch"):
                st.session_state["_logging_out"] = True
                auth_manager = initialize_firebase_auth()
                auth_manager.sign_out()
                st.session_state["user_reid"] = None
                delete_case_cookie()
                # Auth is now cleared; the rerun lands on the public landing zone.
                st.rerun()
        with col2:
            if st.button("Cancel", width="stretch"):
                st.rerun()

    if st.button("Log out", width="stretch"):
        _confirm_logout()


# =============================================================================
# NAVIGATION REGISTRY
# =============================================================================

# --- Zon 1: public landing (single page, anchored Home/Tools/Team sections) ---
# One page; the top bar's nav links scroll to in-page anchors (no page switch).
# The native st.navigation top-nav is hidden via CSS (see landing_shell.py).
landing_main = st.Page("landing_pages/landing.py", title="Home", default=True)
LANDING_PAGES = [landing_main]

# --- Zon 2: tool pages (protected) ---
# Defined once; built as visible objects for the authenticated nav and as hidden
# objects so bookmarked tool URLs redirect to the landing page instead of 404.
# The revenue-cap pages form one grouped "folder"; standalone tools sit beside it.
_REVENUE_CAP_SPECS = [
    ("pages/1_create_and_select_case.py", "1. Create and select case"),
    ("pages/2_case_setup.py", "2. Select modules to modify"),
    ("pages/3_specification.py", "3. Configure selected modules"),
    ("pages/4_revenue_frame.py", "4. Compute revenue frame and save"),
]
_STANDALONE_TOOL_SPECS = [
    ("pages/5_new_benchmarking.py", "New benchmarking model"),
    ("pages/6_placeholder.py", "Placeholder"),
]
_TOOL_PAGE_SPECS = _REVENUE_CAP_SPECS + _STANDALONE_TOOL_SPECS

REVENUE_CAP_PAGES = [st.Page(path, title=title) for path, title in _REVENUE_CAP_SPECS]
STANDALONE_PAGES = [st.Page(path, title=title) for path, title in _STANDALONE_TOOL_SPECS]
APP_PAGES_HIDDEN = [
    st.Page(path, title=title, visibility="hidden") for path, title in _TOOL_PAGE_SPECS
]


# =============================================================================
# MAIN
# =============================================================================

# Restore auth from cookie if the session was lost (page refresh).
try_restore_auth_from_cookie()

if check_auth():
    # ZON 2 — the tool.
    apply_tool_chrome()

    # Set pending auth cookie (deferred from the sign-in dialog so JS renders).
    pending_token = st.session_state.pop("_pending_auth_cookie", None)
    if pending_token:
        set_auth_cookie(pending_token)

    # Restore last saved case on refresh (once) + keep the case cookie in sync.
    try_restore_case_from_cookie()
    _sync_case_cookie()

    pg = st.navigation({
        "Revenue cap tool": REVENUE_CAP_PAGES,
        "Standalone tools": STANDALONE_PAGES,
    })
    render_sidebar()
    pg.run()

else:
    # ZON 1 — the landing zone. Native top-nav; no sidebar.
    # Protected tool pages are registered hidden so bookmarked URLs redirect to
    # the landing home (which carries the Sign in CTA) instead of 404'ing.
    pg = st.navigation(LANDING_PAGES + APP_PAGES_HIDDEN, position="top")
    if pg in APP_PAGES_HIDDEN:
        st.switch_page(landing_main)
    else:
        pg.run()
