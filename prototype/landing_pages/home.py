import streamlit as st

st.title("Welcome to Regumetrica")
st.markdown("##### Web-based tool for computing scenario-based revenue frames")

st.write("")

st.markdown(
    """
    Regumetrica is a regulatory analysis platform for Swedish electricity
    distribution companies. It implements the Energimarknadsinspektionen revenue
    cap calculation model, letting both regulated companies and the regulator
    run scenario-based analyses against the official baseline.

    _[Placeholder intro text — final copy to be drafted with the team.]_
    """
)

st.divider()

col1, col2, col3 = st.columns(3, gap="large")
with col1:
    st.markdown("### :material/tune:")
    st.markdown("**Scenario modelling**")
    st.caption(
        "Adjust parameters and variables across 7 modules and instantly see how "
        "the revenue frame responds."
    )
with col2:
    st.markdown("### :material/compare_arrows:")
    st.markdown("**Side-by-side comparison**")
    st.caption(
        "Every result is shown against the regulatory baseline with deltas, "
        "charts, and full audit trails."
    )
with col3:
    st.markdown("### :material/save:")
    st.markdown("**Save and share cases**")
    st.caption(
        "Persist case configurations, duplicate them, and compare KPIs across "
        "multiple cases."
    )

st.divider()

st.caption(
    "Prototype — content is placeholder. Top-nav navigation between Home / User "
    "Manual / Meet the Team / Contact / Sign in is functional."
)
