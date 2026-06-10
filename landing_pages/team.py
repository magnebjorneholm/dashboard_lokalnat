"""Landing page: Team — team presentation + contact (merged).

NOTE: team members and contact details below are placeholders — replace with
real content.
"""

import streamlit as st

from frontend.common.landing_shell import (
    apply_landing_shell, landing_cards, landing_heading, landing_footer,
)

apply_landing_shell()

landing_heading("Team", eyebrow="Who we are", level=1)
st.markdown(
    '<div class="rm-hero-sub">The people behind Regumetrica.</div>',
    unsafe_allow_html=True,
)

st.write("")

# TODO: replace with real team members (name / title / bio).
landing_cards([
    {"eyebrow": "Role / title", "title": "Name Surname",
     "body": "Short bio — area of expertise and what they work on within the project."},
    {"eyebrow": "Role / title", "title": "Name Surname",
     "body": "Short bio — area of expertise and what they work on within the project."},
    {"eyebrow": "Role / title", "title": "Name Surname",
     "body": "Short bio — area of expertise and what they work on within the project."},
])

# --- Contact ------------------------------------------------------------------
st.write("")
landing_heading("Contact", eyebrow="Get in touch")
# TODO: replace with real contact details.
st.markdown(
    """
    <div class="rm-card" style="max-width:520px;">
        <div class="rm-card-body">
            Questions about Regumetrica or the regulatory model?<br>
            Reach us at
            <a href="mailto:contact@regumetrica.se" style="color:var(--rm-primary);
               text-decoration:none;">contact@regumetrica.se</a>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

landing_footer()
