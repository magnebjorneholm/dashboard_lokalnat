"""
Persistent save bar component.

Displays save buttons and an unsaved-changes warning.
Rendered on Case Setup, Specification, and Revenue Frame pages.
"""

import streamlit as st

from frontend.utils.state_manager import (
    get_case_id,
    get_case_name,
    get_case_notes,
    has_unsaved_changes,
    has_config_changed_since_compute,
)


def render_save_bar(show_warning: bool = False) -> None:
    """Render save buttons, optionally with a stale-results warning.

    Args:
        show_warning: If True, show st.warning when results may be outdated.
                      Only relevant on the Revenue Frame page.

    Three modes:
    1. Loaded case, no changes  → no buttons
    2. Loaded case, unsaved     → [Update config] [Save as new config...]
    3. New case (never saved)   → [Save config as...]
    """
    case_id = get_case_id()
    case_name = get_case_name() or ""
    unsaved = has_unsaved_changes()

    if case_id:
        if unsaved:
            _render_unsaved_buttons(case_name)
    else:
        _render_new_case_button()

    if show_warning and has_config_changed_since_compute():
        st.warning("Configuration changed since last computation, results may be outdated.")


def _render_unsaved_buttons(case_name: str) -> None:
    """Buttons for existing case with unsaved changes."""
    col_save, col_fork, _ = st.columns([0.2, 0.25, 0.55])
    with col_save:
        if st.button(
            "Update case", type="primary", key="save_bar_save",
            use_container_width=True,
            help="Overwrite the saved case with your current configuration",
        ):
            from frontend.utils.case_actions import do_save_case
            if do_save_case():
                st.toast(f'Updated "{case_name}"')
                st.rerun()
    with col_fork:
        if st.button(
            "Save as new case", key="save_bar_fork",
            use_container_width=True,
            help="Create a new case from your current configuration",
        ):
            _save_as_new_dialog()


def _render_new_case_button() -> None:
    """Button for new case that has never been saved."""
    col_save, _ = st.columns([0.2, 0.8])
    with col_save:
        if st.button(
            "Save as new case", type="primary", key="save_bar_save_new",
            use_container_width=True,
            help="Save your current configuration as a new case",
        ):
            _save_as_new_dialog()


@st.dialog("Save configuration")
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

    if st.button(
        "Save configuration", type="primary",
        key="save_bar_dialog_confirm", use_container_width=True,
    ):
        if not save_name.strip():
            st.warning("Enter a case name.")
        else:
            force_new = case_id is not None
            if do_save_case(force_new=force_new, name_override=save_name, notes_override=save_notes):
                st.toast(f'Saved "{save_name}"')
            st.rerun()
