"""
Landing-zone shell (public, pre-login).

Design layer only — touches no app infrastructure (auth, routing, controller).
``apply_landing_shell()`` is called at the top of every landing page and:
- injects the landing theme (faded ``login_pic.jpg`` background + soft gradient
  overlay, full-width, no sidebar),
- renders the brand wordmark + a single top-bar CTA: an "Open tool" link that
  opens the tool in its own window (new tab). Sign-in happens in that tool window
  when it is opened while logged out (see streamlit_app.py), so the landing is a
  purely public surface.

Section navigation (Home / Tools / Team) is drawn here as the in-page anchor nav
in the frozen top bar (``.rm-topbar``); the native st.navigation menu is hidden on
the landing (the landing is st.navigation's hidden default page — see streamlit_app.py).

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

# Tool entry URL — the first revenue-cap page (pages/1_create_and_select_case.py;
# its inferred url_path). The "Open tool" CTA always links here; a logged-out
# visitor signs in inside the opened tool window (see streamlit_app.py).
_TOOL_ENTRY_URL = "/create_and_select_case"


# Static stylesheet (plain string → literal braces; colors via CSS variables).
_CSS = """
/* Soft gradient overlay over the photo for readability */
[data-testid="stAppViewContainer"]::before{
    content:""; position:fixed; inset:0; width:100%; height:100%;
    background:linear-gradient(180deg, rgba(248,250,252,0.66) 0%, rgba(248,250,252,0.85) 55%);
    backdrop-filter:blur(5px); -webkit-backdrop-filter:blur(5px); z-index:0;
}
[data-testid="stAppViewContainer"] > div{ position:relative; z-index:1; }

/* === Frozen top bar ===
   stHeader is the native sticky bar (top:0). Make it a solid, opaque bar that
   stays above all content while the page scrolls beneath it. The bar's contents
   are ours: the native nav links are hidden and replaced by the brand wordmark +
   in-page anchor nav (.rm-topbar, pinned left) and the "Open tool" CTA (pinned
   right, see .st-key-rm_signin). The anchor nav scrolls within this one page
   instead of switching pages. */
[data-testid="stHeader"]{
    background:rgba(248,250,252,0.88);
    backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
    border-bottom:1px solid var(--rm-border);
    z-index:1000;
}
/* Hide the native st.navigation top-nav (a single hidden "Home" entry); the
   bar is drawn by .rm-topbar below. */
[data-testid="stTopNav"]{ display:none !important; }

/* Brand wordmark + anchor nav, pinned into the left of the frozen bar */
.rm-topbar{
    position:fixed; top:0; left:0; height:3.5rem; z-index:1001;
    display:flex; align-items:center; gap:1.6rem; padding:0 1.2rem;
}
.rm-brand{ font-weight:700; font-size:1.18rem; letter-spacing:-0.01em;
    color:var(--rm-text); white-space:nowrap; }
.rm-nav{ display:flex; gap:1.2rem; }
.rm-nav a{ font-size:.95rem; font-weight:500; color:var(--rm-text2);
    text-decoration:none; padding:.25rem .1rem; transition:color .15s ease; }
.rm-nav a:hover{ color:var(--rm-primary); }
.rm-nav a:target{ color:var(--rm-primary); }
@media (max-width:560px){ .rm-nav{ display:none; } }

/* "Open tool" CTA pinned into the frozen top bar */
.st-key-rm_signin{
    position:fixed; top:.5rem; right:1.1rem; width:auto !important; z-index:1001;
}
/* "Open tool" CTA — anchor styled as the primary button (all visitors); opens
   a new tab. A logged-out visitor signs in inside the opened tool window. */
.rm-cta{ display:inline-block; background:var(--rm-primary); color:#fff !important;
    font-size:.92rem; font-weight:600; text-decoration:none !important; padding:.42rem .95rem;
    border-radius:8px; transition:filter .15s ease; }
.rm-cta:hover{ filter:brightness(1.07); text-decoration:none !important; }

/* === In-page anchor scrolling ===
   Smooth glide to a section; scroll-margin keeps the target clear of the bar. */
html{ scroll-behavior:smooth; }
[data-testid="stMain"], [data-testid="stAppViewContainer"]{ scroll-behavior:smooth; }
.rm-anchor{ display:block; height:0; scroll-margin-top:5rem; }

/* Hide tool chrome (no sidebar in the landing zone) */
[data-testid="stSidebar"],
[data-testid="collapsedControl"]{ display:none !important; }

/* Centered, width-limited content column (top padding clears the frozen bar) */
.main .block-container{ max-width:1080px; padding-top:4.5rem; padding-bottom:4rem; }

/* === Hero === */
.rm-hero-brand{ font-size:1.6rem; font-weight:700; letter-spacing:-0.01em;
    line-height:1.1; margin:1.2rem 0 .1rem; }
.rm-hero-title{ font-size:3.1rem; line-height:1.08; letter-spacing:-0.025em; font-weight:700;
    color:var(--rm-text); margin:.2rem 0 .6rem; }
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
.rm-card{ position:relative; display:flex; flex-direction:column;
    background:var(--rm-card); border:1px solid var(--rm-border); border-radius:14px;
    padding:1.4rem; box-shadow:0 1px 2px rgba(15,23,42,.04);
    transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
.rm-card:hover{ transform:translateY(-3px); box-shadow:0 12px 30px rgba(15,23,42,.10);
    border-color:#CBD5E1; }
.rm-card-eyebrow{ font-size:.76rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
    color:var(--rm-primary); margin-bottom:.3rem; }
.rm-card-title{ font-weight:600; font-size:1.06rem; color:var(--rm-text); margin-bottom:.32rem; }
.rm-card-body{ color:var(--rm-text2); font-size:.92rem; line-height:1.5; }
/* Status pill (top-right) — shown only for non-default statuses */
.rm-card-status{ position:absolute; top:1.1rem; right:1.1rem; font-size:.68rem; font-weight:700;
    letter-spacing:.04em; text-transform:uppercase; padding:.16rem .55rem; border-radius:999px; }
.rm-card-status.beta{ color:var(--rm-warning); background:var(--rm-warning-bg); }
.rm-card-status.coming_soon{ color:var(--rm-muted); background:var(--rm-border); }
/* Coming-soon cards are dimmed and don't lift on hover (not usable yet) */
.rm-card--soon{ opacity:.72; }
.rm-card--soon:hover{ transform:none; box-shadow:0 1px 2px rgba(15,23,42,.04);
    border-color:var(--rm-border); }
/* Manual link (card footer), pinned to the bottom so cards align */
.rm-card-link{ margin-top:auto; padding-top:.9rem; font-size:.86rem; font-weight:600;
    color:var(--rm-primary); text-decoration:none; display:inline-flex; align-items:center; gap:.3rem; }
.rm-card-link:hover{ text-decoration:underline; }
/* Inline variant for native cards: sits in the actions row, not at the bottom */
.rm-card-link--inline{ margin-top:0; padding-top:0; }

/* === Native tool card (st.container, so it can hold a real button) ===
   A pure-HTML card can't contain a Streamlit widget; building the card from a
   keyed container lets the "Read in page" st.button live inside it. Styled to
   match .rm-card. The key class is st-key-toolcard_<tool-key>. */
div[class*="st-key-toolcard_"]{
    position:relative; background:var(--rm-card);
    border:1px solid var(--rm-border); border-radius:14px; padding:1.4rem;
    box-shadow:0 1px 2px rgba(15,23,42,.04);
    transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
div[class*="st-key-toolcard_"]:hover{
    transform:translateY(-3px); box-shadow:0 12px 30px rgba(15,23,42,.10);
    border-color:#CBD5E1; }
/* Make the two card actions identical: the "Manual (PDF)" link (an <a>) and the
   "Read in page" tertiary button must share one look. Streamlit colors markdown
   links and tertiary-button text from the theme with selectors that beat our
   class, so we force both — every <a>/<button> and their inner label nodes — to
   the same primary color, weight, size and underline. The button also drops its
   chrome so it reads as a plain link. */
div[class*="st-key-toolcard_"] button{
    border:none !important; background:transparent !important;
    padding:0 !important; min-height:0 !important; box-shadow:none !important;
    opacity:1 !important; }
div[class*="st-key-toolcard_"] a,
div[class*="st-key-toolcard_"] a *,
div[class*="st-key-toolcard_"] button,
div[class*="st-key-toolcard_"] button *{
    color:var(--rm-primary) !important; font-weight:600 !important;
    font-size:.86rem !important; text-decoration:underline !important; }
div[class*="st-key-toolcard_"] a:hover,
div[class*="st-key-toolcard_"] button:hover,
div[class*="st-key-toolcard_"] button:hover *{
    color:var(--rm-primary) !important; background:transparent !important; }

/* === Featured profile (team) === */
.rm-profile{ display:flex; gap:1.8rem; align-items:flex-start;
    background:var(--rm-card); border:1px solid var(--rm-border); border-radius:16px;
    padding:1.8rem; box-shadow:0 1px 2px rgba(15,23,42,.04); margin:.4rem 0 1.4rem; }
.rm-profile-photo{ flex:0 0 196px; width:196px; aspect-ratio:4/5; object-fit:cover;
    border-radius:12px; background:var(--rm-subtle); }
.rm-profile-photo--ph{ display:flex; align-items:center; justify-content:center;
    color:var(--rm-muted); font-size:2.6rem; font-weight:700; border:1px dashed var(--rm-border); }
.rm-profile-body{ flex:1 1 320px; min-width:0; }
.rm-profile-eyebrow{ font-size:.76rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase;
    color:var(--rm-primary); margin-bottom:.2rem; }
.rm-profile-name{ font-size:1.5rem; font-weight:700; letter-spacing:-0.01em; color:var(--rm-text);
    line-height:1.15; }
.rm-profile-role{ font-size:1rem; color:var(--rm-text2); margin:.18rem 0 .9rem; line-height:1.4; }
.rm-profile-bio{ color:var(--rm-text2); font-size:.95rem; line-height:1.55; margin-bottom:.4rem; }
.rm-profile-section-title{ font-size:.78rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
    color:var(--rm-muted); margin:1.1rem 0 .45rem; }
.rm-profile-list{ list-style:none; padding:0; margin:0 0 .6rem; }
.rm-profile-list li{ position:relative; padding-left:1rem; margin-bottom:.4rem; color:var(--rm-text2);
    font-size:.92rem; line-height:1.45; }
.rm-profile-list li::before{ content:"–"; position:absolute; left:0; color:var(--rm-primary); }
.rm-tags{ display:flex; flex-wrap:wrap; gap:.4rem; margin:.9rem 0; }
.rm-tag{ font-size:.78rem; font-weight:500; color:var(--rm-text2); background:var(--rm-subtle);
    border:1px solid var(--rm-border); border-radius:999px; padding:.2rem .7rem; }
.rm-profile-links{ display:flex; flex-wrap:wrap; gap:1.3rem; align-items:center; margin-top:.4rem; }
.rm-profile-link{ font-size:.9rem; font-weight:600; color:var(--rm-primary); text-decoration:none;
    display:inline-flex; align-items:center; gap:.35rem; }
.rm-profile-link:hover{ text-decoration:underline; }
/* Placeholder copy — visibly "to be written" */
.rm-placeholder{ color:var(--rm-muted); font-style:italic;
    border-left:2px dashed var(--rm-border); padding-left:.7rem; }
@media (max-width:640px){
    .rm-profile{ flex-direction:column; }
    .rm-profile-photo{ width:150px; flex-basis:150px; }
}

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
    """Base64 data URI for the landing background image, or None if missing.

    The asset lives in ``static/`` (with the repo root kept as a fallback).
    """
    for name in ("login_pic.jpg", "login_pic.jpeg", "login_pic.png"):
        for path in (Path("static") / name, Path(name)):
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
        --rm-subtle:{COLORS['bg_subtle']};
        --rm-border:{COLORS['bg_muted']};
        --rm-teal:{CHART_COLORS[1]};
        --rm-warning:{COLORS['warning']};
        --rm-warning-bg:{COLORS['warning_light']};
    }}
    [data-testid="stAppViewContainer"] {{
        {bg_rule}
        background-size:cover; background-position:center;
        background-repeat:no-repeat; background-attachment:fixed;
    }}
    """
    st.markdown(f"<style>{dynamic}{_CSS}</style>", unsafe_allow_html=True)


def apply_auth_backdrop() -> None:
    """Inject only the faded ``login_pic.jpg`` backdrop (no top bar, no nav).

    Shared visual: the public landing uses the full theme; the tool's sign-in
    gate (streamlit_app.py) uses just this backdrop behind the auto-opened auth
    dialog, so a logged-out tool window matches the landing's look.
    """
    bg = _bg_data_uri()
    bg_rule = f'background-image:url("{bg}");' if bg else f'background:{COLORS["bg_page"]};'
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"]{{
            {bg_rule}
            background-size:cover; background-position:center;
            background-repeat:no-repeat; background-attachment:fixed;
        }}
        [data-testid="stAppViewContainer"]::before{{
            content:""; position:fixed; inset:0; width:100%; height:100%;
            background:linear-gradient(180deg, rgba(248,250,252,0.66) 0%, rgba(248,250,252,0.85) 55%);
            backdrop-filter:blur(5px); -webkit-backdrop-filter:blur(5px); z-index:0;
        }}
        [data-testid="stAppViewContainer"] > div{{ position:relative; z-index:1; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_landing_shell() -> None:
    """Inject the landing theme and the frozen top bar (brand + anchor nav + CTA).

    The landing is a single page with three anchored sections (``#home`` /
    ``#tools`` / ``#team``). The top bar carries the brand wordmark and the
    section nav as in-page anchor links: clicking one scrolls to that section
    instead of switching pages. The native st.navigation top-nav is hidden (CSS);
    the bar's contents are rendered here. The right-hand CTA is pinned via the
    ``.st-key-rm_signin`` container class (name kept for the stable CSS hook): a
    single "Open tool" link (new tab) for everyone; a logged-out visitor signs
    in inside the opened tool window.
    """
    _inject_theme()

    st.markdown(
        '<div class="rm-topbar">'
        '<span class="rm-brand">Regumetrica</span>'
        '<nav class="rm-nav">'
        '<a href="#home">Home</a>'
        '<a href="#tools">Tools</a>'
        '<a href="#team">Team</a>'
        '</nav></div>',
        unsafe_allow_html=True,
    )

    with st.container(key="rm_signin"):
        # Single CTA for everyone (Option B): a real link that opens the tool in
        # its own window with one reliable click (a link gesture is never
        # popup-blocked). A logged-out visitor signs in *in that tool window*; the
        # landing (with its manuals) stays open beside it, side by side.
        st.markdown(
            f'<a class="rm-cta" href="{_TOOL_ENTRY_URL}" target="_blank" '
            'rel="noopener">Open tool</a>',
            unsafe_allow_html=True,
        )


def landing_anchor(anchor_id: str) -> None:
    """Invisible scroll target for an in-page section (the top-nav links here)."""
    st.markdown(f'<span id="{anchor_id}" class="rm-anchor"></span>', unsafe_allow_html=True)


def landing_heading(title: str, eyebrow: Optional[str] = None, level: int = 2) -> None:
    """Section (level=2) or page (level=1) heading, with an optional eyebrow."""
    html = ""
    if eyebrow:
        html += f'<div class="rm-eyebrow">{eyebrow}</div>'
    html += f'<div class="rm-h{1 if level == 1 else 2}">{title}</div>'
    st.markdown(html, unsafe_allow_html=True)


def landing_cards(items: List[Dict[str, str]]) -> None:
    """Responsive grid of cards.

    Each item: ``{title, body, eyebrow?, status?}``. ``status`` (e.g. ``"beta"``,
    ``"coming_soon"``) renders a pill top-right. (Tool cards with manual actions
    are rendered natively in landing.py, not here — this helper is for plain
    content cards such as the "What you get" grid.)
    """
    cards = []
    for it in items:
        parts = []
        if it.get("status"):
            label = it["status"].replace("_", " ")
            parts.append(f'<div class="rm-card-status {it["status"]}">{label}</div>')
        if it.get("eyebrow"):
            parts.append(f'<div class="rm-card-eyebrow">{it["eyebrow"]}</div>')
        parts.append(f'<div class="rm-card-title">{it["title"]}</div>')
        parts.append(f'<div class="rm-card-body">{it["body"]}</div>')
        card_class = "rm-card rm-card--soon" if it.get("status") == "coming_soon" else "rm-card"
        cards.append(f'<div class="{card_class}">{"".join(parts)}</div>')
    st.markdown(f'<div class="rm-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def landing_profile(
    *,
    name: str,
    role: str,
    bio: str,
    photo_url: Optional[str] = None,
    initials: str = "?",
    eyebrow: Optional[str] = None,
    background: Optional[Dict] = None,
    affiliations: Optional[List[str]] = None,
    email: Optional[str] = None,
    link: Optional[tuple] = None,
) -> None:
    """Featured person profile: photo left, content right (stacks on narrow screens).

    Args:
        name, role: heading lines (HTML allowed).
        bio: short paragraph (HTML allowed — wrap drafts in ``.rm-placeholder``).
        photo_url: image URL (e.g. ``app/static/team/<file>.jpg``); falls back to an
            ``initials`` avatar tile when absent.
        eyebrow: small uppercase label above the name.
        background: ``{"title": str, "items": [str, ...]}`` — a bulleted list (e.g.
            selected work); items may be HTML.
        affiliations: list of short strings rendered as pill tags.
        email: contact address; rendered as a mail link in the footer links row.
        link: ``(label, url)`` for an external link (e.g. full CV), opened in a new tab.

    ``email`` and ``link`` share one footer row (the profile's outward actions).
    """
    if photo_url:
        photo = f'<img class="rm-profile-photo" src="{photo_url}" alt="{name}">'
    else:
        photo = f'<div class="rm-profile-photo rm-profile-photo--ph">{initials}</div>'

    parts: List[str] = []
    if eyebrow:
        parts.append(f'<div class="rm-profile-eyebrow">{eyebrow}</div>')
    parts.append(f'<div class="rm-profile-name">{name}</div>')
    parts.append(f'<div class="rm-profile-role">{role}</div>')
    parts.append(f'<div class="rm-profile-bio">{bio}</div>')
    if background and background.get("items"):
        title = background.get("title", "Selected background")
        items = "".join(f"<li>{it}</li>" for it in background["items"])
        parts.append(f'<div class="rm-profile-section-title">{title}</div>')
        parts.append(f'<ul class="rm-profile-list">{items}</ul>')
    if affiliations:
        tags = "".join(f'<span class="rm-tag">{a}</span>' for a in affiliations)
        parts.append(f'<div class="rm-tags">{tags}</div>')
    actions: List[str] = []
    if email:
        actions.append(
            f'<a class="rm-profile-link" href="mailto:{email}">{email}</a>'
        )
    if link:
        label, url = link
        actions.append(
            f'<a class="rm-profile-link" href="{url}" target="_blank">{label}</a>'
        )
    if actions:
        parts.append(f'<div class="rm-profile-links">{"".join(actions)}</div>')

    st.markdown(
        f'<div class="rm-profile">{photo}'
        f'<div class="rm-profile-body">{"".join(parts)}</div></div>',
        unsafe_allow_html=True,
    )


def landing_footer() -> None:
    """Closing footer for landing pages."""
    st.divider()
    st.markdown(
        '<div class="rm-footer">© Regumetrica — regulatory analysis of Swedish '
        "electricity distribution networks.</div>",
        unsafe_allow_html=True,
    )
