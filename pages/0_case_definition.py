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
    get_case_display_info,
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
    "**Only selected modules/sections will be applied** - unselected use baseline."
)

st.divider()


# =============================================================================
# LOAD SAVED CASE
# =============================================================================

st.markdown("##### Load saved case")

saved_cases = list_cases(user_reid)

if saved_cases:
    st.caption(f"You have {len(saved_cases)} saved case(s). Select one to load or continue with a new case.")
    
    # Create options for selectbox
    case_options = {case.id: case for case in saved_cases}
    case_names = ["-- Create new case --"] + [
        f"{case.name} (updated {get_case_display_info(case)['updated']})"
        for case in saved_cases
    ]
    case_ids = [None] + [case.id for case in saved_cases]
    
    selected_idx = st.selectbox(
        "Select case",
        range(len(case_names)),
        format_func=lambda i: case_names[i],
        key="load_case_select",
        label_visibility="collapsed"
    )
    
    if selected_idx > 0:
        selected_case_id = case_ids[selected_idx]
        selected_case = case_options[selected_case_id]
        
        # Show case details
        info = get_case_display_info(selected_case)
        
        with st.container(border=True):
            st.markdown(f"**{selected_case.name}**")
            if selected_case.notes:
                st.caption(info["notes"])
            
            # Show which modules/sections are included
            if selected_case.selected_modules:
                st.caption(f"Selections: {', '.join(sorted(selected_case.selected_modules))} | Created: {info['created']}")
            else:
                st.caption(f"Baseline only | Created: {info['created']}")
            
            if info["had_kent"]:
                st.warning(
                    f"This case originally included a KENT file ({info['kent_name']}). "
                    "You will need to re-upload it after loading."
                )
            
            col_load, col_delete = st.columns([1, 1])
            
            with col_load:
                if st.button("Load case", type="primary", use_container_width=True):
                    apply_case_to_session(selected_case, st.session_state)
                    st.session_state["_toast_message"] = f"Loaded: {selected_case.name}"
                    st.rerun()
            
            with col_delete:
                if st.button("Delete case", type="secondary", use_container_width=True):
                    if delete_case(user_reid, selected_case_id):
                        st.session_state["_toast_message"] = "Case deleted"
                        st.rerun()
                    else:
                        st.error("Failed to delete case")

else:
    st.info("No saved cases yet. Cases can be saved after running a calculation.")


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
    "Check the modules you want to modify. For modules with sections, "
    "you can select individual parts. **Only checked items affect the calculation.**"
)

# Get current selection
current_selection = get_selected_modules()

# Track new selections
new_selection: Set[str] = set()


def render_module_card(module: ModuleDefinition, is_addon: bool = False) -> None:
    """
    Render a module selection card with optional section checkboxes.
    
    For modules without sections: single checkbox
    For modules with sections: parent checkbox + indented section checkboxes
    """
    if module.has_sections:
        _render_module_with_sections(module, is_addon)
    else:
        _render_simple_module(module, is_addon)


def _render_simple_module(module: ModuleDefinition, is_addon: bool) -> None:
    """Render a module without sections."""
    widget_key = f"module_select_{module.key}"
    
    # Set default value if not already in session_state
    if widget_key not in st.session_state:
        st.session_state[widget_key] = module.key in current_selection
    
    # Module header with checkbox
    col_check, col_title = st.columns([0.08, 0.92])
    
    with col_check:
        selected = st.checkbox(
            module.title,
            key=widget_key,
            label_visibility="collapsed"
        )
    
    with col_title:
        if is_addon:
            st.markdown(f"**{module.title}** *(add-on)*")
        else:
            st.markdown(f"**{module.title}**")
        st.caption(module.description)
    
    # Show parameters and variables info
    _render_module_info(module)
    
    if selected:
        new_selection.add(module.key)


def _render_module_with_sections(module: ModuleDefinition, is_addon: bool) -> None:
    """Render a module with configurable sections (flat design)."""
    # Module title (no checkbox)
    if is_addon:
        st.markdown(f"**{module.title}** *(add-on)*")
    else:
        st.markdown(f"**{module.title}**")
    st.caption(module.description)
    
    # Render sections as flat checkboxes
    for section in module.sections:
        section_key = build_selection_key(module.key, section.key)
        section_widget_key = f"section_select_{section_key}"
        
        # Initialize checkbox state
        if section_widget_key not in st.session_state:
            st.session_state[section_widget_key] = section_key in current_selection
        
        col_check, col_label = st.columns([0.06, 0.94])
        
        with col_check:
            section_selected = st.checkbox(
                section.label,
                key=section_widget_key,
                label_visibility="collapsed"
            )
        
        with col_label:
            st.markdown(section.label)
        
        if section_selected:
            new_selection.add(section_key)
    
    # Show parameters and variables info
    _render_module_info(module)


def _render_module_info(module: ModuleDefinition) -> None:
    """Render parameters and variables info for a module."""
    with st.container():
        col_params, col_vars = st.columns(2)
        
        with col_params:
            if module.parameters:
                st.markdown("**Parameters**")
                for param in module.parameters:
                    st.caption(f"- {param.param_id}: {param.label}")
            else:
                st.caption("*No parameters*")
        
        with col_vars:
            if module.variables:
                st.markdown("**Variables**")
                for var in module.variables:
                    st.caption(f"- {var.var_id}: {var.label}")
            else:
                st.caption("*No variables*")


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