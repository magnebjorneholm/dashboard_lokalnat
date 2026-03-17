"""
Persistent save bar component.

Displays case name, save status, and save actions.
Rendered on Case Setup, Specification, and Revenue Frame pages.
"""

import streamlit as st

from config.colors import COLORS
from frontend.utils.state_manager import (
    get_case_id,
    get_case_name,
    get_case_notes,
    has_unsaved_changes,
    has_saved_reference,
)


def render_save_bar() -> None:
    """Render the persistent save bar above page content.

    Three modes:
    1. Loaded case, no changes  → "Case Name"  ✓ Saved
    2. Loaded case, unsaved     → "Case Name"  ● Unsaved  [Save] [Save as new...]
    3. New case (never saved)   → "New case (unsaved)"     [Save as...]
    """
    case_id = get_case_id()
    case_name = get_case_name() or ""
    unsaved = has_unsaved_changes()
    has_saved = has_saved_reference()

    with st.container():
        if case_id:
            # --- Existing case ---
            if unsaved:
                _render_unsaved(case_name)
            else:
                _render_saved(case_name)
        else:
            # --- New case, never saved ---
            _render_new_case(case_name)


def _render_saved(case_name: str) -> None:
    """Loaded case with no unsaved changes."""
    col_info, _ = st.columns([0.7, 0.3])
    success = COLORS["success"]
    with col_info:
        st.markdown(
            f"**{case_name}** &nbsp; "
            f"<span style='color:{success};font-size:0.85em'>✓ Saved</span>",
            unsafe_allow_html=True,
        )


def _render_unsaved(case_name: str) -> None:
    """Loaded case with unsaved changes — show Save and Save as new buttons."""
    col_info, col_save, col_fork = st.columns([0.6, 0.2, 0.2])
    warning = COLORS["warning"]
    with col_info:
        st.markdown(
            f"**{case_name}** &nbsp; "
            f"<span style='color:{warning};font-size:0.85em'>● Unsaved</span>",
            unsafe_allow_html=True,
        )
    with col_save:
        if st.button("Save", key="save_bar_save", use_container_width=True):
            from frontend.utils.case_actions import do_save_case
            if do_save_case():
                st.toast(f'Updated "{case_name}"')
                st.rerun()
    with col_fork:
        if st.button("Save as new...", key="save_bar_fork"):
            _save_as_new_dialog()


def _render_new_case(case_name: str) -> None:
    """New case that has never been saved."""
    col_info, col_save = st.columns([0.7, 0.3])
    text_secondary = COLORS["text_secondary"]
    with col_info:
        st.markdown(
            f"<span style='color:{text_secondary}'>New case (unsaved)</span>",
            unsafe_allow_html=True,
        )
    with col_save:
        if st.button("Save as...", key="save_bar_save_new"):
            _save_as_new_dialog()


@st.dialog("Save case")
def _save_as_new_dialog():
    """Dialog for saving as a new case (fork or first save)."""
    from frontend.utils.case_actions import do_save_case

    case_id = get_case_id()
    case_name = get_case_name() or ""
    case_notes = get_case_notes()

    if case_id:
        default_name = f"{case_name} (copy)"
    else:
        default_name = case_name

    save_name = st.text_input("Name", value=default_name, key="save_bar_dialog_name")
    save_notes = st.text_area("Notes", value=case_notes, key="save_bar_dialog_notes")

    if st.button("Save case", type="primary", key="save_bar_dialog_confirm", use_container_width=True):
        if not save_name.strip():
            st.warning("Enter a case name.")
        else:
            force_new = case_id is not None
            if do_save_case(force_new=force_new, name_override=save_name, notes_override=save_notes):
                st.toast(f'Saved "{save_name}"')
            st.rerun()
