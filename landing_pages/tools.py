"""Landing page: Tools — overview of the tools + user-manual download.

Each tool ships its own manual (built from ``user_manual_latex/manuals/<slug>/``
and published to ``static/manuals/<slug>.pdf``). The download below serves the
Regumetrica revenue-frame tool's manual; per-tool pages serve their own via
``manual_download_button("<slug>")``.
"""

import streamlit as st

from frontend.common.landing_shell import (
    apply_landing_shell, landing_cards, landing_heading, landing_footer,
)
from frontend.common.manuals import manual_download_button

apply_landing_shell()

landing_heading("The tools", eyebrow="What you can do", level=1)
st.markdown(
    '<div class="rm-hero-sub">Regumetrica is a small suite of regulatory tools. '
    "Sign in to use them; here is what each one is for.</div>",
    unsafe_allow_html=True,
)

st.write("")

# --- The core tool ------------------------------------------------------------
landing_heading("Revenue cap tool", eyebrow="Core tool")
landing_cards([
    {"title": "Counterfactual revenue frames",
     "body": "Compute counterfactual revenue frames for a Swedish electricity "
             "distribution network. You work in <em>cases</em> — each case is a "
             "workspace holding one full set of regulatory assumptions, "
             "initialised to the current regulatory model. Adjust parameters and "
             "variables across the model's base modules — asset base valuation, "
             "depreciation, cost of capital, operating expenditures and the "
             "efficiency incentive — then run the model and compare the resulting "
             "revenue frame against the baseline, component by component. Results "
             "are exportable. The current version covers the 2024–2027 regulatory "
             "period."},
])

# --- Standalone tools ---------------------------------------------------------
st.write("")
landing_heading("Standalone tools", eyebrow="Add-on analyses")
landing_cards([
    {"title": "New benchmarking model",
     "body": "Explore Energimarknadsinspektionen's proposed TOTEX-based DEA "
             "benchmarking model and how it would affect the network's efficiency "
             "requirement — independent of the revenue-frame pipeline, all else "
             "equal."},
])

# --- User manual --------------------------------------------------------------
st.write("")
landing_heading("User manual", eyebrow="Documentation")
st.caption("The Regumetrica user manual as a PDF. Each tool has its own manual.")

dl, _ = st.columns([1, 2])
with dl:
    manual_download_button(
        "regumetrica_user_manual",
        file_name="Regumetrica user manual.pdf",
    )

landing_footer()
