import streamlit as st

st.title("Meet the Team")

st.markdown(
    "_[Placeholder intro about the team behind Regumetrica — backgrounds, "
    "areas of expertise, why this project exists.]_"
)

st.divider()


def _placeholder_member(col, name: str, role: str) -> None:
    with col:
        st.markdown(
            """
            <div style="background:#E2E8F0;height:160px;border-radius:8px;
            display:flex;align-items:center;justify-content:center;
            color:#64748B;font-size:0.9rem;">[Photo placeholder]</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"**{name}**")
        st.caption(role)
        st.write(
            "Short bio placeholder — role, background, area of focus. Two or "
            "three sentences."
        )


# First row
col1, col2, col3 = st.columns(3, gap="large")
_placeholder_member(col1, "Team Member 1", "Role / Title")
_placeholder_member(col2, "Team Member 2", "Role / Title")
_placeholder_member(col3, "Team Member 3", "Role / Title")

st.write("")

# Second row (demonstrates grid behaviour with more than 3 members)
col4, col5, col6 = st.columns(3, gap="large")
_placeholder_member(col4, "Team Member 4", "Role / Title")
# col5 and col6 left empty to show grid flow

st.divider()

st.caption(
    "Prototype — grid will be filled with real members. Layout adapts as the "
    "team grows."
)
