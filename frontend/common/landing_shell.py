"""
Landing-zone shell (public, pre-login).

Design layer only — touches no app infrastructure (auth, routing, controller).
``apply_landing_shell()`` is called at the top of every landing page and:
- injects the landing theme (faded ``login_pic.jpg`` background + soft gradient
  overlay, full-width, no sidebar),
- renders the brand wordmark + the "Sign in" CTA that opens ``auth_dialog()``.

Section navigation (Home / Tools / Team) is the native top-nav rendered by
streamlit_app.py via ``st.navigation(position="top")``.

Helpers for the pages:
- ``landing_heading(title, eyebrow, level)`` — section / page heading.
- ``landing_cards(items)`` — responsive card grid (pure HTML, full styling control).
- ``landing_footer()`` — closing footer.

This zone deliberately does NOT follow the tool's "Nordic Energy" sidebar chrome;
it is a separate, business-facing layer (and will be replaced by the future
React/Next landing — kept intentionally lean here).
"""

import base64
from pathlib import Path
from typing import List, Dict, Optional

import streamlit as st

from config.colors import COLORS, CHART_COLORS
from frontend.common.auth_dialog import auth_dialog


# Static stylesheet (plain string → literal braces; colors via CSS variables).
_CSS = """
/* Soft gradient overlay over the photo for readability */
[data-testid="stAppViewContainer"]::before{
    content:""; position:fixed; inset:0; width:100%; height:100%;
    background:linear-gradient(180deg, rgba(248,250,252,0.80) 0%, rgba(248,250,252,0.93) 55%);
    backdrop-filter:blur(7px); -webkit-backdrop-filter:blur(7px); z-index:0;
}
[data-testid="stAppViewContainer"] > div{ position:relative; z-index:1; }
[data-testid="stHeader"]{ background:transparent; }

/* Hide tool chrome (no sidebar in the landing zone) */
[data-testid="stSidebar"],
[data-testid="collapsedControl"]{ display:none !important; }

/* Centered, width-limited content column */
.main .block-container{ max-width:1080px; padding-top:1.4rem; padding-bottom:4rem; }

/* === Header === */
.rm-brand{ font-weight:700; font-size:1.3rem; letter-spacing:-0.01em; color:var(--rm-text);
    display:flex; align-items:center; gap:.45rem; white-space:nowrap; }
[data-testid="stPageLink"] a{ padding:.3rem .2rem !important; border-radius:6px;
    transition:color .15s ease; }
[data-testid="stPageLink"] a p{ color:var(--rm-text2) !important; font-weight:500 !important;
    font-size:.97rem !important; }
[data-testid="stPageLink"] a:hover p{ color:var(--rm-primary) !important; }
[data-testid="stPageLink"] a[aria-current] p{ color:var(--rm-primary) !important;
    font-weight:600 !important; }

/* === Hero === */
.rm-hero-title{ font-size:3.1rem; line-height:1.08; letter-spacing:-0.025em; font-weight:700;
    color:var(--rm-text); margin:1.2rem 0 .6rem; }
.rm-accent{ background:linear-gradient(90deg, var(--rm-primary), var(--rm-teal));
    -webkit-background-clip:text; background-clip:text; color:transparent; }
.rm-hero-sub{ font-size:1.2rem; line-height:1.5; color:var(--rm-text2); max-width:620px;
    margin-bottom:1rem; }
.rm-stats{ display:flex; gap:2.4rem; flex-wrap:wrap; margin:1.6rem 0 .4rem; }
.rm-stat-num{ font-size:1.5rem; font-weight:700; color:var(--rm-text); line-height:1.1; }
.rm-stat-label{ font-size:.82rem; color:var(--rm-muted); }

/* === Headings === */
.rm-eyebrow{ font-size:.8rem; font-weight:600; letter-spacing:.05em; text-transform:uppercase;
    color:var(--rm-primary); margin-bottom:.2rem; }
.rm-h1{ font-size:2.3rem; font-weight:700; letter-spacing:-0.02em; color:var(--rm-text);
    margin:1rem 0 .4rem; }
.rm-h2{ font-size:1.6rem; font-weight:700; letter-spacing:-0.01em; color:var(--rm-text);
    margin:0 0 1rem; }

/* === Card grid === */
.rm-grid{ display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:1rem;
    margin:.4rem 0 1.4rem; }
.rm-card{ background:var(--rm-card); border:1px solid var(--rm-border); border-radius:14px;
    padding:1.4rem; box-shadow:0 1px 2px rgba(15,23,42,.04);
    transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
.rm-card:hover{ transform:translateY(-3px); box-shadow:0 12px 30px rgba(15,23,42,.10);
    border-color:#CBD5E1; }
.rm-card-icon{ font-size:1.7rem; line-height:1; margin-bottom:.55rem; }
.rm-card-eyebrow{ font-size:.76rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
    color:var(--rm-primary); margin-bottom:.3rem; }
.rm-card-title{ font-weight:600; font-size:1.06rem; color:var(--rm-text); margin-bottom:.32rem; }
.rm-card-body{ color:var(--rm-text2); font-size:.92rem; line-height:1.5; }

/* Landing button + dialog polish */
[data-testid="stMain"] [data-testid="stBaseButton-primary"]{ border-radius:8px; }
[data-testid="stDialog"] div[role="dialog"]{ border-radius:16px; }

/* === Footer === */
.rm-footer{ color:var(--rm-muted); font-size:.85rem; text-align:center; line-height:1.8; }
.rm-footer a{ color:var(--rm-text2); text-decoration:none; }
.rm-footer a:hover{ color:var(--rm-primary); }
"""


@st.cache_data
def _bg_data_uri() -> Optional[str]:
    """Base64 data URI for the landing background image, or None if missing."""
    for name in ("login_pic.jpg", "login_pic.jpeg", "login_pic.png"):
        path = Path(name)
        if path.exists():
            mime = "png" if path.suffix == ".png" else "jpeg"
            return f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    return None


def _inject_theme() -> None:
    bg = _bg_data_uri()
    bg_rule = f'background-image:url("{bg}");' if bg else f'background:{COLORS["bg_page"]};'
    dynamic = f"""
    :root {{
        --rm-primary:{COLORS['primary']};
        --rm-text:{COLORS['text_primary']};
        --rm-text2:{COLORS['text_secondary']};
        --rm-muted:{COLORS['text_muted']};
        --rm-card:{COLORS['bg_card']};
        --rm-border:{COLORS['bg_muted']};
        --rm-teal:{CHART_COLORS[1]};
    }}
    [data-testid="stAppViewContainer"] {{
        {bg_rule}
        background-size:cover; background-position:center;
        background-repeat:no-repeat; background-attachment:fixed;
    }}
    """
    st.markdown(f"<style>{dynamic}{_CSS}</style>", unsafe_allow_html=True)


def apply_landing_shell() -> None:
    """Inject the landing theme and render the brand + Sign in CTA row.

    Section navigation (Home / Tools / Team) is the native top-nav rendered by
    streamlit_app.py via st.navigation(position="top").
    """
    _inject_theme()

    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        st.markdown('<div class="rm-brand">⚡ Regumetrica</div>', unsafe_allow_html=True)
    with right:
        if st.button("Sign in", type="primary", width="stretch"):
            auth_dialog()

    st.divider()


def landing_heading(title: str, eyebrow: Optional[str] = None, level: int = 2) -> None:
    """Section (level=2) or page (level=1) heading, with an optional eyebrow."""
    html = ""
    if eyebrow:
        html += f'<div class="rm-eyebrow">{eyebrow}</div>'
    html += f'<div class="rm-h{1 if level == 1 else 2}">{title}</div>'
    st.markdown(html, unsafe_allow_html=True)


def landing_cards(items: List[Dict[str, str]]) -> None:
    """Responsive grid of cards.

    Each item: ``{title, body, icon?, eyebrow?}``.
    """
    cards = []
    for it in items:
        parts = []
        if it.get("icon"):
            parts.append(f'<div class="rm-card-icon">{it["icon"]}</div>')
        if it.get("eyebrow"):
            parts.append(f'<div class="rm-card-eyebrow">{it["eyebrow"]}</div>')
        parts.append(f'<div class="rm-card-title">{it["title"]}</div>')
        parts.append(f'<div class="rm-card-body">{it["body"]}</div>')
        cards.append(f'<div class="rm-card">{"".join(parts)}</div>')
    st.markdown(f'<div class="rm-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def landing_footer() -> None:
    """Closing footer for landing pages."""
    st.divider()
    st.markdown(
        '<div class="rm-footer">© Regumetrica — regulatory analysis of Swedish '
        "electricity distribution networks.</div>",
        unsafe_allow_html=True,
    )
