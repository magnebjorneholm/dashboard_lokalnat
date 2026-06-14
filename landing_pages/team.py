"""Landing page: Team — the people behind Regumetrica + contact.

Erik Lundin's profile carries real photo, affiliations and CV link; the bio and
selected-background items are deliberate placeholders (``.rm-placeholder``) for
him to write himself. The second member and the contact details are placeholders.
"""

import streamlit as st

from frontend.common.landing_shell import (
    apply_landing_shell, landing_profile, landing_heading, landing_footer,
)

apply_landing_shell()

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
    link=("Full CV & publications", "https://www.eriklundin.org"),
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
