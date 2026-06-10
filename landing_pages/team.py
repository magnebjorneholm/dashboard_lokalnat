"""Landing page: Team — team presentation + contact (merged).

NOTE: team members and contact details below are placeholders — replace with
real content.
"""

import streamlit as st

from config.colors import COLORS
from frontend.common.landing_shell import apply_landing_shell, landing_footer

apply_landing_shell()

st.markdown(
    f"""
    <h1 style="color:{COLORS['text_primary']};letter-spacing:-0.02em;">Team</h1>
    <p style="font-size:1.1rem;color:{COLORS['text_secondary']};max-width:680px;">
        The people behind Regumetrica.
    </p>
    """,
    unsafe_allow_html=True,
)

st.write("")

# --- Team grid ----------------------------------------------------------------
# TODO: replace with real team members (photo / name / title / bio).
team = [
    ("Name Surname", "Role / title",
     "Short bio — area of expertise and what they work on within the project."),
    ("Name Surname", "Role / title",
     "Short bio — area of expertise and what they work on within the project."),
    ("Name Surname", "Role / title",
     "Short bio — area of expertise and what they work on within the project."),
]

cols = st.columns(3, gap="medium")
for col, (name, title, bio) in zip(cols, team):
    with col:
        with st.container(border=True):
            st.markdown(
                f"<div style='font-weight:600;font-size:1.05rem;"
                f"color:{COLORS['text_primary']}'>{name}</div>"
                f"<div style='color:{COLORS['primary']};font-size:.9rem;"
                f"margin:.15rem 0 .5rem'>{title}</div>"
                f"<div style='color:{COLORS['text_secondary']};font-size:.9rem'>{bio}</div>",
                unsafe_allow_html=True,
            )

# --- Contact ------------------------------------------------------------------
st.write("")
st.subheader("Contact")
# TODO: replace with real contact details.
st.markdown(
    f"""
    <div style="color:{COLORS['text_secondary']};font-size:1rem;">
        Questions about Regumetrica or the regulatory model?<br>
        Reach us at <a href="mailto:contact@regumetrica.se">contact@regumetrica.se</a>.
    </div>
    """,
    unsafe_allow_html=True,
)

landing_footer()
