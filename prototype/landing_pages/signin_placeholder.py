import streamlit as st

st.write("")
st.write("")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(
        """
        <div style="text-align:center;padding:3rem 2rem;border:1px dashed #CBD5E1;
        border-radius:12px;background:#F8FAFC;">
            <div style="font-size:3rem;">🔐</div>
            <h3 style="margin-top:1rem;color:#0F172A;">Login screen would appear here</h3>
            <p style="color:#64748B;margin-top:0.5rem;">
                In the final integration, this top-nav link points to the existing
                Firebase login at <code>pages/login.py</code>. After successful
                login the user lands in the dashboard.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.caption(
    "Prototype — sign-in is not wired up. Real flow: click 'Sign in' → Firebase "
    "login → dashboard."
)
