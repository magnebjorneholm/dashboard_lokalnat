"""
Regumetrica Streamlit Application.

Entry point. A route-based two-zone controller. All pages live in ONE
``st.navigation`` so Streamlit resolves the requested page from the real URL
(reliable); the zone is then chosen by the returned page, and auth only gates the
tool pages. This lets a logged-in user keep the public landing open in one window
and a tool in another at the same time:

  ZON 1 — Landing (public): the hidden default page (root URL), shown regardless
          of auth. No sidebar; it draws its own top bar
          (frontend/common/landing_shell.py). Its single CTA is an "Open tool"
          link that opens the tool in its own window (new tab), for everyone.
  ZON 2 — Tool: the tool pages, gated by auth. A tool window opened while logged
          out shows the sign-in gate *in place* (no bounce); once auth passes the
          same window renders the tool. Locked sidebar + company selector +
          logout, and a link back to the landing (opens a new tab).

Launch flow (Option B): the landing's "Open tool" link opens the tool window
with one reliable click; a logged-out visitor signs in there on the full-page
sign-in gate (frontend/common/auth_page.py), keeping the landing (and its
manuals) open beside it. No cross-zone redirect is needed.
See landing_pages/FRONTEND_FILES.md for the full architecture.
"""

import streamlit as st

from config.colors import COLORS

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
from frontend.common.auth_page import render_auth_gate
from auth.firebase_auth import is_dev_mode, initialize_firebase_auth
from auth.cookie_session import (
    get_auth_cookie, set_auth_cookie, delete_auth_cookie,
    get_case_cookie, set_case_cookie, delete_case_cookie,
)

# Page configuration
st.set_page_config(
    page_title="Regumetrica",
    page_icon="static/favicon.svg",  # monochrome "R" in near-black
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

def _render_home_button():
    """Sidebar link back to the public landing.

    Opens in a NEW tab (``target="_blank"``) so the tool window stays open — the
    point of the route-based zones is to allow landing + tool side by side.
    """
    st.markdown(
        f"""
        <style>
        /* Match Streamlit's secondary button (the "Log out" button below it):
           white fill, light border, dark centred label, full width. !important
           overrides Streamlit's default markdown-link theme (blue + underline). */
        .rm-home-btn{{ display:block; width:100%; box-sizing:border-box; text-align:center;
            padding:.5rem 1rem; line-height:1.6; background:#FFFFFF;
            border:1px solid {COLORS['bg_muted']}; border-radius:.5rem;
            color:{COLORS['text_primary']} !important; text-decoration:none !important;
            font-weight:400; font-size:.9rem; margin-bottom:.5rem;
            transition:border-color .15s ease, color .15s ease; }}
        .rm-home-btn:hover{{ border-color:{COLORS['primary']};
            color:{COLORS['primary']} !important; text-decoration:none !important; }}
        </style>
        <a class="rm-home-btn" href="/" target="_blank" rel="noopener">Back to Home</a>
        """,
        unsafe_allow_html=True,
    )


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

    st.divider()
    _render_home_button()


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
    _render_home_button()

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
                # Land on the public landing (not the sign-in gate): the controller
                # switch_page's to Home when it sees this one-shot flag.
                st.session_state["_post_logout_home"] = True
                st.rerun()
        with col2:
            if st.button("Cancel", width="stretch"):
                st.rerun()

    if st.button("Log out", width="stretch"):
        _confirm_logout()


# =============================================================================
# NAVIGATION REGISTRY
# =============================================================================

# All pages live in ONE st.navigation so Streamlit resolves the requested page
# from the real URL (reliable) — we then branch the zone on the returned page.
#
# Zon 1 — landing: a single page (anchored Home/Tools/Team sections). It is the
# default page (root URL) and is hidden from the menu — the landing draws its own
# top bar and hides the sidebar (see landing_shell.py), so it never appears in the
# tool sidebar nav.
landing_main = st.Page(
    "landing_pages/landing.py", title="Home", default=True, visibility="hidden"
)

# Zon 2 — tool pages (protected). The revenue-cap pages form one grouped "folder";
# standalone tools sit beside it. Both groups render in the tool sidebar nav.
_REVENUE_CAP_SPECS = [
    ("pages/1_create_and_select_case.py", "1. Create and select case"),
    ("pages/2_case_setup.py", "2. Select modules to modify"),
    ("pages/3_specification.py", "3. Configure selected modules"),
    ("pages/4_revenue_frame.py", "4. Compute revenue cap and save"),
]
_STANDALONE_TOOL_SPECS = [
    ("pages/5_new_benchmarking.py", "New benchmarking model"),
]

REVENUE_CAP_PAGES = [st.Page(path, title=title) for path, title in _REVENUE_CAP_SPECS]
STANDALONE_PAGES = [st.Page(path, title=title) for path, title in _STANDALONE_TOOL_SPECS]
TOOL_PAGES = REVENUE_CAP_PAGES + STANDALONE_PAGES


# =============================================================================
# MAIN
# =============================================================================

# Restore auth from cookie if the session was lost (page refresh).
try_restore_auth_from_cookie()

# One navigation for everything. Streamlit resolves the requested page from the
# real URL (reliable — no guessing the path ourselves); we branch the zone on the
# returned page. landing_main is the hidden default, so it owns the root URL but
# never shows in the tool sidebar nav. The two visible groups are the tool zone.
pg = st.navigation({
    "Main module": [landing_main, *REVENUE_CAP_PAGES],
    "Add-on modules": STANDALONE_PAGES,
})

# A fresh logout returns to the public landing, not the sign-in gate. switch_page
# runs after st.navigation (so landing_main is registered) and is a no-op on every
# other run (one-shot flag set by the logout dialog).
if st.session_state.pop("_post_logout_home", False):
    st.switch_page(landing_main)

if pg in TOOL_PAGES:
    # ZON 2 — the tool, gated by auth.
    if not check_auth():
        # Tool window opened while logged out (Option B launch, or a bookmark):
        # sign in right here instead of bouncing to the landing, so the landing
        # (and its manuals) can stay open beside it. A verified login reruns the
        # app; auth then passes and this same window renders the tool.
        render_auth_gate()
    else:
        apply_tool_chrome()

        # Set pending auth cookie (deferred from the sign-in dialog so JS renders).
        pending_token = st.session_state.pop("_pending_auth_cookie", None)
        if pending_token:
            set_auth_cookie(pending_token)

        # Restore last saved case on refresh (once) + keep the case cookie in sync.
        try_restore_case_from_cookie()
        _sync_case_cookie()

        render_sidebar()
        pg.run()

else:
    # ZON 1 — the public landing (pg is landing_main), shown regardless of auth so
    # a logged-in user can keep it open alongside a tool. It draws its own top bar
    # and hides the sidebar (landing_shell.py).
    pg.run()
