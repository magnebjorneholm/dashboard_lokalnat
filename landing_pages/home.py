"""Landing page: Home — hero, tagline, intro, feature highlights."""

import streamlit as st

from config.colors import COLORS
from frontend.common.landing_shell import apply_landing_shell, landing_footer
from frontend.common.auth_dialog import auth_dialog

apply_landing_shell()

# --- Hero ---------------------------------------------------------------------
st.markdown(
    f"""
    <div style="padding: 2.5rem 0 1rem 0;">
        <h1 style="font-size: 3rem; line-height: 1.1; margin-bottom: 0.5rem;
                   color: {COLORS['text_primary']}; letter-spacing: -0.02em;">
            Revenue-cap analysis<br>for the Swedish electricity grid
        </h1>
        <p style="font-size: 1.25rem; color: {COLORS['text_secondary']};
                  max-width: 640px; margin-top: 0.75rem;">
            Regumetrica replicates Energimarknadsinspektionen's regulatory model
            for all 148 distribution networks — adjust parameters, run the
            pipeline, and compare against the baseline with full transparency.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cta, _ = st.columns([1, 3])
with cta:
    if st.button("Get started", type="primary", width="stretch"):
        auth_dialog()

st.write("")
st.write("")

# --- Feature highlights -------------------------------------------------------
features = [
    ("🎯", "Regulatory precision",
     "Faithful replication of Ei's revenue-cap model — capital base, WACC, "
     "operating expenditure, efficiency requirements and incentives."),
    ("🔍", "Case-vs-baseline",
     "Every adjustment is shown side by side with the baseline, so the impact "
     "of each parameter change is always explicit."),
    ("📊", "Built for analysis",
     "DEA benchmarking, the proposed new TOTEX model, and exportable results — "
     "designed for regulators and network operators alike."),
]

cols = st.columns(3, gap="medium")
for col, (icon, title, body) in zip(cols, features):
    with col:
        with st.container(border=True):
            st.markdown(
                f"<div style='font-size:1.8rem'>{icon}</div>"
                f"<div style='font-weight:600;font-size:1.05rem;margin:.3rem 0;"
                f"color:{COLORS['text_primary']}'>{title}</div>"
                f"<div style='color:{COLORS['text_secondary']};font-size:.92rem'>{body}</div>",
                unsafe_allow_html=True,
            )

landing_footer()
