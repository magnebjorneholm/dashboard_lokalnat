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

from config.tools_registry import tools_for
from frontend.common.landing_shell import (
    apply_landing_shell, landing_anchor, landing_cards, landing_heading,
    landing_profile, landing_footer,
)
from frontend.common.manuals import manual_path

apply_landing_shell()


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
             "on the revenue frame side by side with the baseline. The impact of "
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


def _tool_cards(branch: str) -> list[dict]:
    """Build card dicts for the public tools in a branch (registry-driven)."""
    items: list[dict] = []
    for t in tools_for(branch):  # type: ignore[arg-type]
        item: dict = {"title": t.name, "body": t.summary}
        if t.status != "available":
            item["status"] = t.status
        # Link to the manual only if its PDF has actually been built.
        if manual_path(t.manual).exists():
            item["manual_url"] = f"app/static/manuals/{t.manual}.pdf"
        items.append(item)
    return items


landing_heading("The tools", eyebrow="What you can do", level=1)
st.markdown(
    '<div class="rm-hero-sub">Regumetrica is a small suite of regulatory tools, and '
    "the suite grows as the regulation does. Sign in to use them; each card links to "
    "that tool's manual.</div>",
    unsafe_allow_html=True,
)

st.write("")

landing_heading("Revenue cap tool", eyebrow="Core tool")
landing_cards(_tool_cards("revenue_cap"))

st.write("")

landing_heading("Standalone tools", eyebrow="Add-on analyses")
landing_cards(_tool_cards("standalone"))


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
# TODO(Magne): add a portrait photo (-> static/team/) and write the bio.
landing_profile(
    eyebrow="Role in Regumetrica",
    name="Magne Björneholm",
    role="Research assistant in energy economics, "
         "Research Institute of Industrial Economics (IFN)",
    initials="MB",
    bio='<span class="rm-placeholder">Bio — to be written. Develops Regumetrica and '
        "works as a research assistant at IFN; MSc in economics (University of "
        "Gothenburg) with a thesis on benchmarking of Swedish distribution "
        "networks.</span>",
    affiliations=["IFN", "MSc Economics, University of Gothenburg"],
)

landing_footer()
