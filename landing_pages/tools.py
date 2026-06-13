"""Landing page: Tools — index of Regumetrica's tools, grouped by branch.

A pure index: one card per tool (short description + a link to that tool's own
manual, which carries the in-depth documentation). Content is driven by the
tool registry (``config/tools_registry.py``); manuals are served statically from
``static/manuals/<slug>.pdf`` (see ``frontend/common/manuals.py``).
"""

import streamlit as st

from config.tools_registry import tools_for
from frontend.common.landing_shell import (
    apply_landing_shell, landing_cards, landing_heading, landing_footer,
)
from frontend.common.manuals import manual_path

apply_landing_shell()


def _cards(branch: str) -> list[dict]:
    """Build card dicts for the public tools in a branch (registry-driven)."""
    items: list[dict] = []
    for t in tools_for(branch):  # type: ignore[arg-type]
        item: dict = {"icon": t.icon, "title": t.name, "body": t.summary}
        if t.status != "available":
            item["status"] = t.status
        # Link to the manual only if its PDF has actually been built.
        if manual_path(t.manual).exists():
            item["manual_url"] = f"app/static/manuals/{t.manual}.pdf"
        items.append(item)
    return items


landing_heading("The tools", eyebrow="What you can do", level=1)
st.markdown(
    '<div class="rm-hero-sub">Regumetrica is a small suite of regulatory tools. '
    "Sign in to use them; each card links to that tool's manual.</div>",
    unsafe_allow_html=True,
)

st.write("")

landing_heading("Revenue cap tool", eyebrow="Core tool")
landing_cards(_cards("revenue_cap"))

st.write("")

landing_heading("Standalone tools", eyebrow="Add-on analyses")
landing_cards(_cards("standalone"))

landing_footer()
