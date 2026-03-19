"""
Save bar component.

Single "Save" button that updates the current case in storage.
Rendered on Specification and Revenue Frame pages.
"""

import streamlit as st

from frontend.utils.state_manager import (
    get_case_id,
    get_case_name,
)


def render_save_bar() -> None:
    """Render save button for the current case.

    The case always has an ID (created on Page 1), so save is always
    an update. Always available — saving an unchanged config is harmless.
    """
    case_id = get_case_id()
    if case_id is None:
        return  # No case loaded — nothing to render

    col_save, _ = st.columns([0.2, 0.8])
    with col_save:
        if st.button(
            "Save", type="primary", key="save_bar_save",
            use_container_width=True,
            help="Update the saved case with your current configuration",
        ):
            from frontend.utils.case_actions import do_save_case
            if do_save_case():
                case_name = get_case_name() or "case"
                st.toast(f'Saved "{case_name}"')
                st.rerun()
