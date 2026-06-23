"""
Full-page sign-in gate for the tool zone.

The tool window's "Open tool" launch (see streamlit_app.py) lands a logged-out
visitor here: ``render_auth_gate()`` fills the window with a glass-card sign-in
panel over the faded ``login_pic.jpg`` backdrop (the landing's photo), with the
sidebar hidden and the native header made transparent. It handles login,
registration, password reset and the email-verification follow-up.

Why a full page (not a dialog): the launch flow is "open tool -> sign in ->
tool", so sign-in is a *destination*, not a popup over the landing. A page has no
close button (the visitor signs in or stays out), fills the window, and lets us
own the header. A verified login defers the auth cookie and reruns the app
(app scope); the controller then renders the tool in the same window. Sub-view
switches (login -> verify) ride on session-state flags across app reruns.

Cookie deferral matches the established pattern: the refresh token is stashed in
``st.session_state["_pending_auth_cookie"]`` and written by streamlit_app.py
after the auth check passes (the JS cookie component needs a clean render).
"""

import streamlit as st

from config.colors import COLORS, CHART_COLORS
from auth.firebase_auth import initialize_firebase_auth
from frontend.utils.state_manager import set_user_reid
from frontend.utils.company_directory import get_company_options
from frontend.common.landing_shell import apply_auth_backdrop


# =============================================================================
# Session keys
# =============================================================================

_STEP = "_auth_step"                       # None/"login" -> tabs ; "verify" -> verification view
_PENDING_VERIFY_TOKEN = "_pending_verify_token"


def _store_auth_session(user: dict, email: str, claims: dict | None) -> None:
    """Mirror Firebase auth result into session state (same keys as before)."""
    st.session_state["auth_user"] = user
    st.session_state["auth_token"] = user.get("idToken")
    st.session_state["auth_email"] = email
    st.session_state["auth_uid"] = user.get("localId")
    if claims:
        st.session_state["auth_role"] = claims.get("role", "company")
        st.session_state["auth_reid"] = claims.get("reid")


# =============================================================================
# Page styling
# =============================================================================

def _apply_auth_page_style() -> None:
    """Faded login_pic backdrop + glass card + transparent header, sidebar hidden."""
    apply_auth_backdrop()
    st.markdown(
        f"""
        <style>
        /* Let the backdrop show through the native bar (no bare white strip) */
        [data-testid="stHeader"]{{ background:transparent; }}
        [data-testid="stToolbar"]{{ display:none !important; }}
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"]{{ display:none !important; }}

        /* The whole content column becomes the centered glass card */
        .main .block-container{{
            max-width:480px; margin:7vh auto 2rem;
            background:rgba(255,255,255,0.72);
            backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
            border:1px solid {COLORS['bg_muted']}; border-radius:16px;
            padding:2.2rem 2.4rem; box-shadow:0 8px 32px rgba(15,23,42,.12);
        }}
        /* Hero typography lifted from the landing (landing_shell.py): blue->teal
           gradient accent (background-clip:text) + compact "financial" type. */
        .rm-auth-brand{{ font-size:1.4rem; font-weight:700; letter-spacing:-0.01em;
            line-height:1.1; margin-bottom:.2rem; }}
        .rm-auth-title{{ font-size:clamp(1.9rem, 5vw, 2.3rem); font-weight:700;
            letter-spacing:-0.025em; line-height:1.1; color:{COLORS['text_primary']};
            margin:0 0 1.5rem; }}
        .rm-accent{{ background:linear-gradient(90deg, {COLORS['primary']}, {CHART_COLORS[1]});
            -webkit-background-clip:text; background-clip:text; color:transparent; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Sub-views
# =============================================================================

def _render_login(auth_manager) -> None:
    """Login form + an inline password-reset expander."""
    with st.form("auth_login_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", type="primary", width="stretch")

    if submit:
        if not email or not password:
            st.error("Please enter email and password.")
        else:
            with st.spinner("Signing in..."):
                ok, error, user = auth_manager.sign_in(email, password)
            if not ok:
                st.error(error or "Login failed.")
            elif not user.get("emailVerified", False):
                # Switch to the verification view on the next app run.
                st.session_state[_PENDING_VERIFY_TOKEN] = user.get("idToken")
                st.session_state[_STEP] = "verify"
                st.rerun()
            else:
                # Defer the cookie write; streamlit_app sets it after auth passes.
                st.session_state["_pending_auth_cookie"] = user.get("refreshToken", "")
                claims = auth_manager.get_user_claims(user["idToken"])
                _store_auth_session(user, email, claims)
                if claims and claims.get("role") == "company" and claims.get("reid"):
                    set_user_reid(claims["reid"])
                # App-scope rerun: auth now passes, so the controller renders the
                # tool in this same window (no redirect needed).
                st.rerun()

    with st.expander("Forgot your password?"):
        with st.form("auth_reset_form"):
            reset_email = st.text_input(
                "Email", key="auth_reset_email",
                placeholder="your.email@company.com",
            )
            send = st.form_submit_button("Send reset link", width="stretch")
        if send:
            if not reset_email:
                st.error("Please enter your email.")
            else:
                ok, error = auth_manager.send_password_reset_email(reset_email)
                if ok:
                    st.success("Reset link sent — check your inbox (and spam).")
                else:
                    st.error(error or "Could not send reset email.")


def _render_register(auth_manager) -> None:
    """Registration form: email, password, role, and company (for company users)."""
    options = get_company_options()  # [(display, reid), ...]

    with st.form("auth_register_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password", help="Minimum 6 characters")
        password_confirm = st.text_input("Confirm password", type="password")

        st.divider()

        role = st.radio(
            "Account type",
            options=["company", "regulator"],
            format_func=lambda x: "Company user" if x == "company" else "Regulator",
            horizontal=True,
            help="Company users are linked to a specific network. "
                 "Regulators can view all networks.",
        )

        selected_reid = None
        if role == "company":
            if options:
                labels = ["— Select your company —"] + [o[0] for o in options]
                idx = st.selectbox(
                    "Select your company",
                    range(len(labels)),
                    format_func=lambda i: labels[i],
                )
                if idx > 0:
                    selected_reid = options[idx - 1][1]
            else:
                st.error("Could not load company list.")

        submit = st.form_submit_button("Create account", type="primary", width="stretch")

    if submit:
        if not email or not password:
            st.error("Please fill in all required fields.")
            return
        if password != password_confirm:
            st.error("Passwords do not match.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        if role == "company" and not selected_reid:
            st.error("Please select your company.")
            return

        with st.spinner("Creating account..."):
            ok, error, _user = auth_manager.sign_up(
                email=email,
                password=password,
                role=role,
                reid=selected_reid if role == "company" else None,
            )
        if ok:
            st.success(
                "Account created! Check your email to verify your account, then "
                "sign in. If you don't see it, check your junk/spam folder."
            )
        else:
            st.error(error or "Registration failed.")


def _render_verify(auth_manager) -> None:
    """Email-verification follow-up — reached when login succeeds but is unverified."""
    st.warning("Your email is not verified yet.")
    st.info("Check your inbox and click the verification link. "
            "If you don't see it, check your junk/spam folder.")

    token = st.session_state.get(_PENDING_VERIFY_TOKEN)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Resend verification email", width="stretch", disabled=not token):
            ok, error = auth_manager.resend_verification_email(token)
            st.toast("Verification email sent." if ok else (error or "Could not send."))
    with col2:
        if st.button("Back to sign in", width="stretch"):
            st.session_state[_STEP] = "login"
            st.session_state.pop(_PENDING_VERIFY_TOKEN, None)
            st.rerun()


# =============================================================================
# Page entry point
# =============================================================================

def render_auth_gate() -> None:
    """Render the full-page sign-in gate (tool window, logged out)."""
    _apply_auth_page_style()

    try:
        auth_manager = initialize_firebase_auth()
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not connect to the authentication service: {e}")
        return

    st.markdown(
        '<div class="rm-auth-brand"><span class="rm-accent">Regumetrica</span></div>'
        '<div class="rm-auth-title">Revenue-cap analysis for the '
        '<span class="rm-accent">Swedish electricity grid</span></div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get(_STEP) == "verify":
        _render_verify(auth_manager)
        return

    tab_login, tab_register = st.tabs(["Sign in", "Create account"])
    with tab_login:
        _render_login(auth_manager)
    with tab_register:
        _render_register(auth_manager)
