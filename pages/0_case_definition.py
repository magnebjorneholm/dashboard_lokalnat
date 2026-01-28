"""
Case Definition Page.

Entry point for configuring a regulatory case.
Allows users to:
- Name their case
- Add notes
- Select which modules and sections to configure
- Load previously saved cases
"""

import streamlit as st
from typing import Set

from frontend.utils.state_manager import (
    init_session_state,
    reset_case,
    get_user_reid,
    get_case_name,
    set_case_name,
    get_case_notes,
    set_case_notes,
    get_selected_modules,
    set_selected_modules,
    get_default_case_name,
    set_saved_cases_count,
    get_case_id,
    is_case_saved,
)
from frontend.common.module_registry import (
    ALL_MODULES,
    BASE_MODULES,
    ADDON_MODULES,
    ModuleDefinition,
    build_selection_key,
)
from frontend.utils.case_storage import (
    list_cases,
    load_case,
    delete_case,
    apply_case_to_session,
    get_case_count,
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
st.subheader("Define")

# Check company selection
user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

# Update saved cases count for default naming
case_count = get_case_count(user_reid)
set_saved_cases_count(case_count)

st.caption(
    "Define your case by selecting which regulatory modules to configure. "
    "Each module contains parameters (regulatory constants) and variables "
    "(company-specific data) that can be modified from baseline values. "
    "**Only selected items will be applied** - unselected use baseline."
)

st.divider()


# =============================================================================
# LOAD SAVED CASE
# =============================================================================

st.markdown("##### Load saved case")

saved_cases = list_cases(user_reid)

if saved_cases:
    st.caption(f"You have {len(saved_cases)} saved case(s). Select one to load or continue with a new case.")
    
    # Build options for selectbox
    case_display_names = ["-- Select a case --"] + [
        f"{c.name} ({c.updated_at[:16] if c.updated_at else 'unknown'})"
        for c in saved_cases
    ]
    
    selected_idx = st.selectbox(
        "Saved cases",
        range(len(case_display_names)),
        format_func=lambda i: case_display_names[i],
        key="load_case_select",
        label_visibility="collapsed",
    )
    
    if selected_idx > 0:
        selected_case = saved_cases[selected_idx - 1]
        
        col_load, col_delete = st.columns([1, 1])
        
        with col_load:
            if st.button("Load case", type="primary", width='stretch'):
                case_data = load_case(user_reid, selected_case.id)
                if case_data:
                    apply_case_to_session(case_data, st.session_state)
                    st.session_state["_toast_message"] = f"Loaded: {case_data.name}"
                    st.rerun()
        
        with col_delete:
            if st.button("Delete case", type="secondary", width='stretch'):
                if delete_case(user_reid, selected_case.id):
                    st.session_state["_toast_message"] = "Case deleted"
                    st.rerun()
else:
    st.caption("No saved cases yet. Cases can be saved after running a calculation.")


st.divider()


# =============================================================================
# CASE METADATA
# =============================================================================

st.markdown("##### Case identification")

# Show if editing existing case
current_case_id = get_case_id()
if current_case_id and is_case_saved():
    st.caption(f"Editing saved case (ID: {current_case_id[:8]}...)")

col1, col2 = st.columns([1, 2])

with col1:
    # Case name
    current_name = get_case_name() or get_default_case_name()
    case_name = st.text_input(
        "Case name",
        value=current_name,
        placeholder="e.g., WACC sensitivity analysis",
        key="case_name_input",
        help="Give your case a descriptive name"
    )
    if case_name != get_case_name():
        set_case_name(case_name)

with col2:
    # Case notes
    current_notes = get_case_notes()
    case_notes = st.text_area(
        "Notes (optional)",
        value=current_notes,
        placeholder="Add detailed notes about this case...",
        key="case_notes_input",
        height=80,
        help="Document assumptions or purpose of this analysis"
    )
    if case_notes != get_case_notes():
        set_case_notes(case_notes)


st.divider()


# =============================================================================
# MODULE SELECTION
# =============================================================================

st.markdown("##### Select modules to configure")
st.caption(
    "Check the items you want to modify. Tooltips provide User Manual references."
)

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


st.divider()


# =============================================================================
# RESET BUTTON
# =============================================================================

if st.button("Reset to defaults", type="secondary"):
    reset_case()
    st.rerun()

with st.sidebar:
    st.caption(f"Saved cases: {len(saved_cases)}/10")