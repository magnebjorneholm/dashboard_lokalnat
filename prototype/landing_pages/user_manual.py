import streamlit as st

st.title("User Manual")

st.markdown(
    """
    The Regumetrica user manual provides a detailed walkthrough of the
    regulatory model, parameter definitions, and the application's UI.

    _[Placeholder description.]_
    """
)

st.divider()

col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown("#### Download")
    st.button(
        ":material/download: Download PDF (placeholder)",
        disabled=True,
        use_container_width=True,
    )
    st.caption(
        "Final version will serve `static/regumetrica_user_manual.pdf` via "
        "Streamlit's static file serving."
    )

with col2:
    st.markdown("#### Interactive version")
    st.info(
        "Web-rendered, browsable version of the manual — coming soon.",
        icon=":material/construction:",
    )
    st.caption(
        "Long-term: convert the LaTeX source to interactive web content with "
        "anchors and search."
    )

st.divider()

st.caption("Prototype — the download button is intentionally inert.")
