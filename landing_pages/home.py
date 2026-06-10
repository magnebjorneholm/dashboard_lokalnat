"""Landing page: Home — hero, tagline, stats, feature highlights."""

import streamlit as st

from frontend.common.landing_shell import (
    apply_landing_shell, landing_cards, landing_heading, landing_footer,
)
from frontend.common.auth_dialog import auth_dialog

apply_landing_shell()

# --- Hero ---------------------------------------------------------------------
st.markdown(
    """
    <div class="rm-hero-title">Revenue-cap analysis<br>for the
        <span class="rm-accent">Swedish electricity grid</span></div>
    <div class="rm-hero-sub">
        Regumetrica replicates Energimarknadsinspektionen's regulatory model for
        all 148 distribution networks — adjust parameters, run the pipeline, and
        compare against the baseline with full transparency.
    </div>
    """,
    unsafe_allow_html=True,
)

cta1, cta2, _ = st.columns([1, 1, 2], vertical_alignment="center")
with cta1:
    if st.button("Get started", type="primary", width="stretch"):
        auth_dialog()
with cta2:
    st.page_link("landing_pages/tools.py", label="Explore the tools  →")

st.markdown(
    """
    <div class="rm-stats">
        <div><div class="rm-stat-num">148</div>
             <div class="rm-stat-label">distribution networks</div></div>
        <div><div class="rm-stat-num">Ei</div>
             <div class="rm-stat-label">revenue-cap model</div></div>
        <div><div class="rm-stat-num">DEA</div>
             <div class="rm-stat-label">+ TOTEX benchmarking</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# --- Feature highlights -------------------------------------------------------
landing_heading("What you get", eyebrow="Why Regumetrica")
landing_cards([
    {"icon": "🎯", "title": "Regulatory precision",
     "body": "Faithful replication of Ei's revenue-cap model — capital base, "
             "WACC, operating expenditure, efficiency requirements and incentives."},
    {"icon": "🔍", "title": "Case vs baseline",
     "body": "Every adjustment is shown side by side with the baseline, so the "
             "impact of each parameter change is always explicit."},
    {"icon": "📊", "title": "Built for analysis",
     "body": "DEA benchmarking, the proposed new TOTEX model, and exportable "
             "results — designed for regulators and operators alike."},
])

landing_footer()
