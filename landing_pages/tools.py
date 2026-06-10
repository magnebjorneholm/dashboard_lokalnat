"""Landing page: Tools — overview of the tools + user-manual download.

Each tool will eventually ship with its own dedicated user manual; for now the
full Regumetrica manual (PDF) is offered here.
"""

from pathlib import Path

import streamlit as st

from frontend.common.landing_shell import (
    apply_landing_shell, landing_cards, landing_heading, landing_footer,
)

apply_landing_shell()

landing_heading("The tools", eyebrow="Workflow", level=1)
st.markdown(
    '<div class="rm-hero-sub">The revenue-cap workflow is split into focused '
    "steps. Sign in to use them; here is what each one does.</div>",
    unsafe_allow_html=True,
)

st.write("")

landing_cards([
    {"eyebrow": "Step 1", "title": "Create & select case",
     "body": "Create, load, duplicate, compare or delete cases. A case bundles "
             "your parameter choices and computed results for one network."},
    {"eyebrow": "Step 2", "title": "Select modules to modify",
     "body": "Choose which parts of the model to adjust — asset base, "
             "depreciation, cost of capital, operating expenditure, efficiency, "
             "incentives."},
    {"eyebrow": "Step 3", "title": "Configure selected modules",
     "body": "Set parameters and company-specific variables, each shown against "
             "its baseline value so changes stay explicit."},
    {"eyebrow": "Step 4", "title": "Compute revenue frame & save",
     "body": "Run the full pipeline and inspect the resulting revenue frame, "
             "with a case-vs-baseline decomposition and export."},
    {"eyebrow": "Step 5", "title": "New benchmarking model",
     "body": "Explore Ei's proposed TOTEX-based DEA model and how it would "
             "affect the network, independent of the revenue-frame pipeline."},
])

# --- User manual --------------------------------------------------------------
st.write("")
landing_heading("User manual", eyebrow="Documentation")
st.caption("The full Regumetrica user manual as a PDF. Per-tool manuals will follow.")


@st.cache_data
def _manual_bytes() -> bytes | None:
    path = Path("static/regumetrica_user_manual.pdf")
    return path.read_bytes() if path.exists() else None


pdf = _manual_bytes()
if pdf:
    dl, _ = st.columns([1, 2])
    with dl:
        st.download_button(
            "Download the manual (PDF)",
            data=pdf,
            file_name="Regumetrica user manual.pdf",
            mime="application/pdf",
            type="primary",
            width="stretch",
        )
else:
    st.info("The user manual will be available here shortly.")

landing_footer()
