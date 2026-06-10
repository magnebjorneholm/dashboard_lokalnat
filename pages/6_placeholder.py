"""
Placeholder page — a standalone-tool stub for future development.

Intentionally empty: registered under the "Standalone tools" group so the
navigation slot exists. Replace the body with the real tool when ready.
"""

from __future__ import annotations

import streamlit as st

from frontend.utils.state_manager import init_session_state

init_session_state()

st.title("Regumetrica")
st.subheader("Placeholder")
st.caption("Placeholder for a future standalone tool. Nothing here yet.")
