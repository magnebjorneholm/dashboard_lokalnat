"""
Landing-zone shell (public, pre-login).

``apply_landing_shell()`` is called at the top of every landing page. It:
- injects the landing theme (full-width, no sidebar, faded ``login_pic.jpg``
  background with a soft light overlay), and
- renders the brand wordmark + the "Sign in" CTA that opens ``auth_dialog()``.

The native top navigation bar (Home / Tools / Team) is rendered by
``st.navigation(..., position="top")`` in streamlit_app.py — NOT here. Sign in
opens a dialog (it is not a page), so it lives in the shell, not in the nav.

This zone deliberately does NOT follow the tool's "Nordic Energy" chrome
conventions (locked sidebar etc.) — it is a separate, more business-facing layer.
``landing_footer()`` is an optional closing element pages can call at the bottom.
"""

import base64
from pathlib import Path

import streamlit as st

from config.colors import COLORS
from frontend.common.auth_dialog import auth_dialog


@st.cache_data
def _bg_data_uri() -> str | None:
    """Base64 data URI for the landing background image, or None if missing."""
    for name in ("login_pic.jpg", "login_pic.jpeg", "login_pic.png"):
        path = Path(name)
        if path.exists():
            mime = "png" if path.suffix == ".png" else "jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode()
            return f"data:image/{mime};base64,{encoded}"
    return None


def _inject_theme() -> None:
    """Full-width, sidebar-less landing theme with a faded photo background."""
    bg = _bg_data_uri()
    background_rule = (
        f'background-image: url("{bg}");' if bg else f'background: {COLORS["bg_page"]};'
    )
    st.markdown(
        f"""
        <style>
        /* Faded photographic background */
        [data-testid="stAppViewContainer"] {{
            {background_rule}
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{ background: transparent; }}

        /* Soft light overlay for readability */
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            inset: 0;
            width: 100%;
            height: 100%;
            background: rgba(248, 250, 252, 0.84);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            z-index: 0;
        }}
        [data-testid="stAppViewContainer"] > div {{ position: relative; z-index: 1; }}

        /* Centered, width-limited content column */
        .main .block-container {{
            max-width: 1040px;
            padding-top: 2.5rem;
            padding-bottom: 4rem;
        }}

        /* No sidebar in the landing zone */
        [data-testid="stSidebar"] {{ display: none !important; }}
        [data-testid="collapsedControl"] {{ display: none !important; }}

        /* Landing brand wordmark */
        .rm-brand {{
            font-weight: 700;
            font-size: 1.35rem;
            letter-spacing: -0.01em;
            color: {COLORS["text_primary"]};
            display: flex;
            align-items: center;
            gap: 0.4rem;
            height: 100%;
        }}
        .rm-footer {{
            color: {COLORS["text_muted"]};
            font-size: 0.85rem;
            text-align: center;
            padding-top: 1rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_landing_shell() -> None:
    """Inject the landing theme and render the brand + Sign in CTA row."""
    _inject_theme()

    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        st.markdown('<div class="rm-brand">⚡ Regumetrica</div>', unsafe_allow_html=True)
    with right:
        if st.button("Sign in", type="primary", width="stretch"):
            auth_dialog()

    st.divider()


def landing_footer() -> None:
    """Optional closing footer for landing pages."""
    st.divider()
    st.markdown(
        '<div class="rm-footer">© Regumetrica — regulatory analysis of Swedish '
        "electricity distribution networks.</div>",
        unsafe_allow_html=True,
    )
