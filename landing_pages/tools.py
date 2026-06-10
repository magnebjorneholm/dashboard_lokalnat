"""Landing page: Tools — overview of the tools + user-manual download.

Each tool will eventually ship with its own dedicated user manual; for now the
full Regumetrica manual (PDF) is offered here.
"""

from pathlib import Path

import streamlit as st

from config.colors import COLORS
from frontend.common.landing_shell import apply_landing_shell, landing_footer

apply_landing_shell()

st.markdown(
    f"""
    <h1 style="color:{COLORS['text_primary']};letter-spacing:-0.02em;">The tools</h1>
    <p style="font-size:1.1rem;color:{COLORS['text_secondary']};max-width:680px;">
        The revenue-cap workflow is split into focused steps. Sign in to use
        them; below is what each one does.
    </p>
    """,
    unsafe_allow_html=True,
)

st.write("")

# --- Tool overview ------------------------------------------------------------
tools = [
    ("1 · Create & select case",
     "Create, load, duplicate, compare or delete cases. A case bundles your "
     "parameter choices and computed results for one network."),
    ("2 · Select modules to modify",
     "Choose which parts of the model to adjust — asset base, depreciation, "
     "cost of capital, operating expenditure, efficiency, incentives."),
    ("3 · Configure selected modules",
     "Set parameters and company-specific variables, each shown against its "
     "baseline value so changes stay explicit."),
    ("4 · Compute revenue frame & save",
     "Run the full pipeline and inspect the resulting revenue frame, with a "
     "case-vs-baseline decomposition and export."),
    ("5 · New benchmarking model",
     "Explore Ei's proposed TOTEX-based DEA model and how it would affect the "
     "network, independent of the revenue-frame pipeline."),
]

for title, body in tools:
    with st.container(border=True):
        st.markdown(
            f"<div style='font-weight:600;font-size:1.05rem;"
            f"color:{COLORS['text_primary']}'>{title}</div>"
            f"<div style='color:{COLORS['text_secondary']};font-size:.92rem;"
            f"margin-top:.2rem'>{body}</div>",
            unsafe_allow_html=True,
        )

# --- User manual --------------------------------------------------------------
st.write("")
st.subheader("User manual")
st.caption("The full Regumetrica user manual as a PDF. Per-tool manuals will "
           "follow.")


@st.cache_data
def _manual_bytes() -> bytes | None:
    path = Path("static/regumetrica_user_manual.pdf")
    return path.read_bytes() if path.exists() else None


pdf = _manual_bytes()
if pdf:
    st.download_button(
        "Download the user manual (PDF)",
        data=pdf,
        file_name="Regumetrica user manual.pdf",
        mime="application/pdf",
        type="primary",
        width="stretch",
    )
else:
    st.info("The user manual will be available here shortly.")

landing_footer()
