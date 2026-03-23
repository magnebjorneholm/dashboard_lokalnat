"""
Cookie-based session persistence for Regumetrica.

Stores Firebase refresh token in a browser cookie so that
authentication survives page refreshes.  Also stores the active
case ID in a session-scoped cookie so the last saved case
survives page refreshes but not browser restarts.

- Read:  st.context.cookies (built-in, server-side)
- Write: st.components.v1.html with JavaScript (client-side, same-origin)
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Optional
from urllib.parse import quote, unquote

COOKIE_NAME = "regumetrica_auth"
COOKIE_MAX_AGE_DAYS = 30
CASE_COOKIE_NAME = "regumetrica_case"


def get_auth_cookie() -> Optional[str]:
    """Read the auth refresh token from browser cookie."""
    try:
        value = st.context.cookies.get(COOKIE_NAME)
        if value:
            return unquote(value)
        return None
    except Exception:
        return None


def set_auth_cookie(refresh_token: str) -> None:
    """Store the Firebase refresh token in a browser cookie via JavaScript."""
    if not refresh_token:
        return
    max_age = COOKIE_MAX_AGE_DAYS * 24 * 60 * 60
    encoded = quote(refresh_token, safe="")
    js = f"""
    <script>
    (function() {{
        try {{
            var secure = (window.parent.location.protocol === 'https:') ? '; Secure' : '';
            window.parent.document.cookie = "{COOKIE_NAME}={encoded}; path=/; max-age={max_age}; SameSite=Lax" + secure;
        }} catch(e) {{
            document.cookie = "{COOKIE_NAME}={encoded}; path=/; max-age={max_age}; SameSite=Lax";
        }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)


def delete_auth_cookie() -> None:
    """Delete the auth cookie by expiring it."""
    js = f"""
    <script>
    (function() {{
        try {{
            window.parent.document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        }} catch(e) {{
            document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)


# =============================================================================
# CASE COOKIE (session-scoped — no max-age, dies when browser closes)
# =============================================================================

def get_case_cookie() -> Optional[str]:
    """Read the active case ID from browser cookie."""
    try:
        value = st.context.cookies.get(CASE_COOKIE_NAME)
        if value:
            return unquote(value)
        return None
    except Exception:
        return None


def set_case_cookie(case_id: str) -> None:
    """Store the active case ID in a session-scoped browser cookie.

    No max-age/expires → cookie lives until the browser is fully closed.
    """
    if not case_id:
        return
    encoded = quote(case_id, safe="")
    js = f"""
    <script>
    (function() {{
        try {{
            var secure = (window.parent.location.protocol === 'https:') ? '; Secure' : '';
            window.parent.document.cookie = "{CASE_COOKIE_NAME}={encoded}; path=/; SameSite=Lax" + secure;
        }} catch(e) {{
            document.cookie = "{CASE_COOKIE_NAME}={encoded}; path=/; SameSite=Lax";
        }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)


def delete_case_cookie() -> None:
    """Delete the case cookie by expiring it."""
    js = f"""
    <script>
    (function() {{
        try {{
            window.parent.document.cookie = "{CASE_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        }} catch(e) {{
            document.cookie = "{CASE_COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)
