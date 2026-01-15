"""
Case Definition Page.

Entry point for configuring a regulatory case.
Allows users to:
- Name their case
- Add notes
- Select which modules to configure
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
)
from frontend.common.module_registry import (
    ALL_MODULES,
    BASE_MODULES,
    ADDON_MODULES,
    ModuleDefinition,
)

# Initialize state
init_session_state()


# =============================================================================
# PAGE CONTENT
# =============================================================================

st.title("Regumetrica")
st.subheader("Case Definition")

# Check company selection
user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

st.info(f"Company: **{user_reid}**")

st.caption(
    "Define your case by selecting which regulatory modules to configure. "
    "Each module contains parameters (regulatory constants) and variables "
    "(company-specific data) that can be modified from baseline values."
)

st.divider()


# =============================================================================
# CASE METADATA
# =============================================================================

st.markdown("##### Case identification")

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
    "Check the modules you want to modify. Unchecked modules will use baseline values. "
    "You can run a baseline-only simulation by leaving all modules unchecked."
)

# Get current selection
current_selection = get_selected_modules()

# Track new selections
new_selection: Set[str] = set()


def render_module_card(module: ModuleDefinition, is_addon: bool = False) -> bool:
    """
    Render a module selection card with parameters/variables info.
    
    Returns True if module is selected.
    """
    # Determine if currently selected
    is_selected = module.key in current_selection
    
    # Module header with checkbox
    col_check, col_title = st.columns([0.08, 0.92])
    
    with col_check:
        selected = st.checkbox(
            module.title,
            value=is_selected,
            key=f"module_select_{module.key}",
            label_visibility="collapsed"
        )
    
    with col_title:
        if is_addon:
            st.markdown(f"**{module.title}** *(add-on)*")
        else:
            st.markdown(f"**{module.title}**")
        st.caption(module.description)
    
    # Show parameters and variables (always visible for information)
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
    
    return selected


# --- BASE MODULES ---
st.markdown("**Base modules**")

for module in BASE_MODULES:
    with st.container(border=True):
        if render_module_card(module, is_addon=False):
            new_selection.add(module.key)

st.markdown("")

# --- ADD-ON MODULES ---
st.markdown("**Add-on modules**")

for module in ADDON_MODULES:
    with st.container(border=True):
        if render_module_card(module, is_addon=True):
            new_selection.add(module.key)


# Update selection if changed
if new_selection != current_selection:
    set_selected_modules(new_selection)


st.divider()


# =============================================================================
# LOAD SAVED CASE (PLACEHOLDER FOR PHASE 2)
# =============================================================================

st.markdown("##### Load saved case")

# Placeholder - will be implemented in phase 2
st.caption("Load a previously saved case to continue working on it.")

# Placeholder selectbox
saved_cases = []  # Will be populated from storage in phase 2

if saved_cases:
    selected_case = st.selectbox(
        "Select saved case",
        options=[""] + saved_cases,
        format_func=lambda x: "Choose a case..." if x == "" else x,
        key="load_case_select"
    )
    
    if selected_case:
        if st.button("Load case", type="secondary"):
            # TODO: Implement in phase 2
            st.info("Case loading will be implemented in phase 2")
else:
    st.info("No saved cases yet. Cases can be saved after running a calculation.")


st.divider()


# =============================================================================
# NAVIGATION
# =============================================================================

col_left, col_right = st.columns([1, 1])

with col_left:
    if st.button("Reset to defaults", type="secondary", use_container_width=True):
        reset_case()
        st.rerun()

with col_right:
    if st.button("Continue to Configuration", type="primary", use_container_width=True):
        # Ensure case has a name
        if not get_case_name():
            set_case_name(get_default_case_name())
        
        st.switch_page("pages/1_case_config.py")


# =============================================================================
# SIDEBAR: SELECTION SUMMARY
# =============================================================================

with st.sidebar:
    st.markdown("### Case Summary")
    
    name = get_case_name() or get_default_case_name()
    st.markdown(f"**{name}**")
    
    selected = get_selected_modules()
    if selected:
        st.caption(f"{len(selected)} module(s) selected:")
        for module in ALL_MODULES:
            if module.key in selected:
                st.caption(f"- {module.title}")
    else:
        st.caption("No modules selected (baseline only)")