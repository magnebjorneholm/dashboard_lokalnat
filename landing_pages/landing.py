"""Single landing page: Home, Tools and Team stacked vertically.

One page, three anchored sections (``#home`` / ``#tools`` / ``#team``). The top
bar's nav links scroll to these anchors in-page (no page switch, no rerun); the
bar and the anchor nav live in ``frontend/common/landing_shell.py``.

Content sources:
- Tools cards are registry-driven (``config/tools_registry.py``); manuals are
  served from ``static/manuals/<slug>.pdf`` (``frontend/common/manuals.py``).
- The team bios are deliberate ``.rm-placeholder`` drafts (see
  ``landing_pages/for_later/team_bios.md``).
"""

import streamlit as st
import streamlit.components.v1 as components

from config.tools_registry import tools_for
from frontend.common.landing_shell import (
    apply_landing_shell, landing_anchor, landing_cards, landing_heading,
    landing_profile, landing_footer,
)
from frontend.common.manuals import manual_path, manual_reader_html

apply_landing_shell()


# =============================================================================
# IN-PAGE MANUAL (read the manual without leaving the landing)
# =============================================================================
# Each tool offers two ways into its manual: the card's "Manual (PDF)" link
# (opens the published PDF in a new window) and a "Read in page" button rendered
# under the card grid. The button is a real Streamlit widget on purpose: a click
# is a websocket rerun in place, so the manual opens in a wide dialog without a
# new tab, a URL change, or a full reload (a plain ``<a href>`` link can't do
# this — Streamlit opens markdown links in a new tab).
#
# The dialog hosts the framework-agnostic *manual reader* (a two-pane HTML doc:
# table of contents + content, with click-to-scroll and scroll-spy) in a
# components.html iframe. The iframe is required, not cosmetic: scroll-spy and
# smooth in-pane scrolling need client-side JS, which st.markdown cannot run. The
# reader's title comes from the markdown frontmatter, so the dialog chrome only
# needs a generic label. ``_READER_HEIGHT`` is the fixed iframe height; the two
# panes scroll internally within it.
_READER_HEIGHT = 680


@st.dialog("User manual", width="large")
def _manual_dialog(reader_html: str) -> None:
    """Render a manual in the two-pane reader (TOC + content, scroll-spy)."""
    components.html(reader_html, height=_READER_HEIGHT, scrolling=False)


def _render_tool_cards(branch: str) -> None:
    """Render a branch's tools as native cards (st.container, not an HTML string).

    A pure-HTML card can't hold a Streamlit widget, so building the card from a
    keyed ``st.container`` lets a real ``st.button`` ("User manual (inline)")
    sit *inside* the card, on one row next to the "User manual (PDF)" link, while
    keeping the look (.rm-card styling is re-applied to ``.st-key-toolcard_<key>``
    in landing_shell). The button opens the manual in a dialog in place (no new
    tab, no reload); the PDF stays a new-window link.
    """
    tools = tools_for(branch)  # type: ignore[arg-type]
    if not tools:
        return
    for col, t in zip(st.columns(len(tools)), tools):
        with col, st.container(border=False, key=f"toolcard_{t.key}"):
            head = []
            if t.status != "available":
                head.append(
                    f'<div class="rm-card-status {t.status}">'
                    f'{t.status.replace("_", " ")}</div>'
                )
            head.append(f'<div class="rm-card-title">{t.name}</div>')
            head.append(f'<div class="rm-card-body">{t.summary}</div>')
            st.markdown("".join(head), unsafe_allow_html=True)

            # Both actions on one row (a real button + the PDF link), styled
            # alike via .rm-card-link / the toolcard button CSS in landing_shell.
            reader_html = manual_reader_html(t.manual)
            with st.container(horizontal=True, gap="medium",
                              vertical_alignment="center"):
                if reader_html is not None:
                    if st.button("User manual (inline)", key=f"read_{t.key}",
                                 type="tertiary"):
                        _manual_dialog(reader_html)
                if manual_path(t.manual).exists():
                    st.markdown(
                        f'<a class="rm-card-link rm-card-link--inline" '
                        f'href="app/static/manuals/{t.manual}.pdf" target="_blank">'
                        "User manual (PDF)</a>",
                        unsafe_allow_html=True,
                    )


# =============================================================================
# HOME
# =============================================================================
landing_anchor("home")

st.markdown(
    """
    <div class="rm-hero-brand"><span class="rm-accent">Regumetrica</span></div>
    <div class="rm-hero-title">Revenue-cap analysis<br>for the
        <span class="rm-accent">Swedish electricity grid</span></div>
    <div class="rm-hero-sub">
        Regumetrica turns Sweden's electricity-network regulation into a model you
        can run. Replicate Energimarknadsinspektionen's revenue-cap calculation
        component by component, change any assumption, and quantify the economic
        impact. Built for the rules as they stand today, and for the reform now
        reshaping them.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="rm-stats">
        <div><div class="rm-stat-num">Transparent</div>
             <div class="rm-stat-label">every component of the model, no black box</div></div>
        <div><div class="rm-stat-num">Counterfactual</div>
             <div class="rm-stat-label">change any assumption, quantify the economic impact</div></div>
        <div><div class="rm-stat-num">Reform-ready</div>
             <div class="rm-stat-label">today's rules and the proposed 2028 regime</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

landing_heading("What you get", eyebrow="Why Regumetrica")
landing_cards([
    {"eyebrow": "Replication", "title": "Faithful to Ei's model",
     "body": "A component-by-component replica of the revenue-cap calculation: "
             "capital base, cost of capital, operating expenditure, efficiency "
             "requirement and incentives. Auditable, not a black box."},
    {"eyebrow": "Scenarios", "title": "Every assumption is a dial",
     "body": "Change a parameter or a company variable, run it, and see the effect "
             "on the revenue cap side by side with the baseline. The impact of "
             "each choice is always explicit."},
    {"eyebrow": "Always up to date", "title": "Evolves with the regulation",
     "body": "The regulation is being rebuilt for the 2028 to 2031 period, and it "
             "will keep changing after that. We interpret each change Ei makes and "
             "build it into the tools, so Regumetrica reflects where the regulation "
             "is heading, not only where it has been. The new benchmarking model is "
             "the first of these."},
])


# =============================================================================
# TOOLS
# =============================================================================
landing_anchor("tools")


landing_heading("The tools", eyebrow="What you can do", level=1)
st.markdown(
    '<div class="rm-hero-sub">Regumetrica is a small suite of regulatory tools, and '
    "the suite grows as the regulation does. Sign in to use them; each card links to "
    "that tool's manual.</div>",
    unsafe_allow_html=True,
)

st.write("")

landing_heading("Revenue cap tool", eyebrow="Core tool")
_render_tool_cards("revenue_cap")

st.write("")

landing_heading("Standalone tools", eyebrow="Add-on analyses")
_render_tool_cards("standalone")


# =============================================================================
# TEAM
# =============================================================================
landing_anchor("team")

landing_heading("Team", eyebrow="Who we are", level=1)
st.markdown(
    '<div class="rm-hero-sub">The people behind Regumetrica.</div>',
    unsafe_allow_html=True,
)

st.write("")

# --- Erik Lundin --------------------------------------------------------------
landing_profile(
    eyebrow="Role in Regumetrica",
    name="Erik Lundin",
    role="Tenured researcher in energy economics, "
         "Research Institute of Industrial Economics (IFN)",
    photo_url="app/static/team/erik_lundin.jpg",
    # TODO(Erik): replace the placeholder bio below with your own text.
    bio='<span class="rm-placeholder">Bio — to be written by Erik. Researcher in '
        "electricity markets and their regulation, with a focus on the Swedish "
        "distribution sector; expert in government inquiries (SOU) and a long "
        "history of work with Energimarknadsinspektionen (Ei).</span>",
    # TODO(Erik): choose the items to feature (kept regulation/grid-focused).
    background={
        "title": "Selected background",
        "items": [
            '<span class="rm-placeholder">Selected work — to be chosen (e.g. '
            "Reformerad intäktsreglering, Swedenergy 2024).</span>",
            '<span class="rm-placeholder">Placeholder — second selected item.</span>',
        ],
    },
    affiliations=["IFN", "Stanford (PESD)", "PhD, Stockholm School of Economics"],
    email="erik@eriklundin.org",
    link=("Personal website", "https://www.eriklundin.org"),
)

# --- Magne Björneholm ----------------------------------------------------------
# TODO(Magne): add a portrait photo (-> static/team/magne_bjorneholm.jpg).
#   Magne will send an iPhone photo (likely HEIC) that needs converting to JPEG
#   and cropping to 4:5 (~700x875), e.g.:
#       sips -s format jpeg -c 875 700 magne.heic --out magne_bjorneholm.jpg
#   Then set photo_url below and drop the initials= fallback.
landing_profile(
    eyebrow="Role in Regumetrica",
    name="Magne Björneholm",
    role="Research assistant to Erik Lundin, IFN",
    initials="MB",
    bio="Develops Regumetrica and works as research assistant to Erik Lundin at "
        "IFN. Holds an MSc in Economics from the University of Gothenburg, with a "
        "thesis on frontier analysis in regulatory benchmarking. Background in "
        "public affairs in wind power and regulatory analysis for government "
        "agencies.",
    affiliations=["IFN", "MSc Economics, University of Gothenburg"],
)

landing_footer()
