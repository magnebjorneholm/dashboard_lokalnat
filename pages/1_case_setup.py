"""
Case Setup Page.

Select which modules and sections to configure.
Each module contains parameters (regulatory constants) and variables
(company-specific data) that can be modified from baseline values.
"""

import streamlit as st
from typing import Set

from frontend.utils.state_manager import (
    init_session_state,
    get_user_reid,
    get_case_name,
    get_selected_modules,
    set_selected_modules,
)
from config.module_registry import (
    BASE_MODULES,
    ADDON_MODULES,
    ModuleDefinition,
    build_selection_key,
)

# Initialize state
init_session_state()

# Show pending toast messages (must be after init, before page content)
if st.session_state.get("_toast_message"):
    st.toast(st.session_state["_toast_message"])
    st.session_state["_toast_message"] = None


# =============================================================================
# PAGE CONTENT
# =============================================================================

st.title("Regumetrica")

case_name = get_case_name()
if case_name:
    st.subheader(f"Case Setup: {case_name}")
else:
    st.subheader("Case Setup")

from frontend.common.save_bar import render_save_bar
_save_bar_placeholder = st.empty()

# Check company selection
user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

st.caption(
    "Select which regulatory modules to configure. "
    "Each module contains parameters (regulatory constants) and variables "
    "(company-specific data) that can be modified from baseline values. "
    "**Only selected items will be applied** — unselected use baseline."
)


# =============================================================================
# MODULE SELECTION
# =============================================================================

# Get current selection
current_selection = get_selected_modules()

# Track new selections
new_selection: Set[str] = set()


def render_module_card(module: ModuleDefinition, is_addon: bool = False) -> None:
    """
    Render a module selection card.

    For modules with sections: vertical checkboxes with descriptive labels.
    For modules without sections: single checkbox.
    """
    if module.has_sections:
        _render_module_with_sections(module, is_addon)
    else:
        _render_simple_module(module, is_addon)


def _render_simple_module(module: ModuleDefinition, is_addon: bool) -> None:
    """Render a module without sections."""
    widget_key = f"module_select_{module.key}"

    if widget_key not in st.session_state:
        st.session_state[widget_key] = module.key in current_selection

    col_check, col_title = st.columns([0.05, 0.95])

    with col_check:
        selected = st.checkbox(
            module.title,
            key=widget_key,
            label_visibility="collapsed"
        )

    with col_title:
        title = f"**{module.title}**"
        if is_addon:
            title += " *(add-on)*"
        st.markdown(title)
        st.caption(module.description)

    if selected:
        new_selection.add(module.key)


def _render_module_with_sections(module: ModuleDefinition, is_addon: bool) -> None:
    """Render a module with configurable sections (vertical checkboxes)."""
    # Module title (no parent checkbox)
    title = f"**{module.title}**"
    if is_addon:
        title += " *(add-on)*"
    st.markdown(title)
    st.caption(module.description)

    st.markdown("")  # Small spacing

    # Render each section as a vertical checkbox
    for section in module.sections:
        section_key = build_selection_key(module.key, section.key)
        section_widget_key = f"section_select_{section_key}"

        if section_widget_key not in st.session_state:
            st.session_state[section_widget_key] = section_key in current_selection

        # Checkbox with descriptive label and help tooltip
        section_selected = st.checkbox(
            section.label,
            key=section_widget_key,
            help=section.help_text if section.help_text else None,
        )

        if section_selected:
            new_selection.add(section_key)


# --- BASE MODULES ---
st.markdown("**Base modules**")

for module in BASE_MODULES:
    with st.container(border=True):
        render_module_card(module, is_addon=False)

st.markdown("")

# --- ADD-ON MODULES ---
st.markdown("**Add-on modules**")

for module in ADDON_MODULES:
    with st.container(border=True):
        render_module_card(module, is_addon=True)


# Update selection if changed
if new_selection != current_selection:
    set_selected_modules(new_selection)

# Render save bar last so it reads up-to-date state (after widget callbacks)
with _save_bar_placeholder.container():
    render_save_bar()
