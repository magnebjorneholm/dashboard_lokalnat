import streamlit as st

st.title("Contact")

st.markdown(
    "_[Placeholder intro — invite users, regulators, and partners to get in touch.]_"
)

st.divider()

col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown("#### Get in touch")
    st.markdown("**Email**")
    st.caption("contact@regumetrica.com  _(placeholder)_")
    st.write("")
    st.markdown("**Address**")
    st.caption("Placeholder street, line 2  \nPostal code, City")
    st.write("")
    st.markdown("**Hours**")
    st.caption("Mon–Fri, 09:00–17:00  _(placeholder)_")

with col2:
    st.markdown("#### Send a message")
    with st.form("contact_form_placeholder", border=True):
        st.text_input("Your name", placeholder="Jane Doe")
        st.text_input("Your email", placeholder="jane@example.com")
        st.text_area(
            "Message",
            placeholder="What would you like to ask?",
            height=140,
        )
        submitted = st.form_submit_button(
            "Send (placeholder)",
            type="primary",
            use_container_width=True,
        )
        if submitted:
            st.info(
                "Form submission is not wired up in the prototype.",
                icon=":material/info:",
            )

st.divider()

st.caption(
    "Prototype — form does not send. Final version can either email a mailbox "
    "or write to Firestore."
)
