"""
Create & Select Case Page.

Landing page for managing regulatory cases.
Allows users to:
- Create new cases (saved to DB immediately)
- Load previously saved cases (with snapshot info)
- Delete saved cases
- Duplicate saved cases
- Edit case name/notes
- Compare cases with result snapshots
"""

import copy
import streamlit as st
from datetime import datetime

from frontend.utils.state_manager import (
    init_session_state,
    reset_case,
    get_user_reid,
    get_case_id,
    get_case_name,
    get_case_notes,
    set_case_name,
    set_case_notes,
    set_saved_cases_count,
    DEFAULT_UI_CONFIG,
)
from frontend.utils.case_storage import (
    SavedCase,
    list_cases,
    load_case,
    delete_case,
    save_case,
    apply_case_to_session,
    get_case_count,
    case_name_exists,
)
from frontend.common.case_comparison import render_comparison_table
from config.module_registry import parse_selection_key
from config.formatting import format_tkr as format_tkr_display
from pipeline.result_helpers import fmt_tkr

# Initialize state
init_session_state()

# Show pending toast messages (must be after init, before page content)
if st.session_state.get("_toast_message"):
    st.toast(st.session_state["_toast_message"])
    st.session_state["_toast_message"] = None


# =============================================================================
# HELPERS
# =============================================================================


def _format_timestamp(iso_str: str) -> str:
    """Format ISO timestamp as '17 Mar 2026, 09:43'."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return f"{dt.day} {dt.strftime('%b %Y, %H:%M')}"
    except (ValueError, TypeError):
        return iso_str or ""


def _format_modules_display(selected_modules: list) -> str:
    """Format selected modules for display, e.g. 'M1, M3, M5'."""
    if not selected_modules:
        return "(none)"
    prefixes = set()
    for key in selected_modules:
        module_key, _ = parse_selection_key(key)
        prefixes.add(module_key.upper())
    return ", ".join(sorted(prefixes))


def _format_case_display(c: SavedCase) -> str:
    """Format a case for display in selectbox."""
    return c.name


def _format_case_compare(c: SavedCase) -> str:
    """Format a case for display in comparison multiselect (with revenue)."""
    has_snapshot = (
        c.result_snapshot is not None
        and c.result_snapshot.get("revenue_frame") is not None
    )
    if has_snapshot:
        rf = fmt_tkr(c.result_snapshot["revenue_frame"])
        return f"{c.name} — {rf}"
    return f"{c.name} — (no results)"


# =============================================================================
# DIALOGS
# =============================================================================


@st.dialog("Delete case")
def _confirm_delete_dialog(case_id: str, case_name: str):
    """Modal confirmation dialog for case deletion."""
    st.warning(f"Delete **{case_name}**? This cannot be undone.")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Confirm delete", type="primary"):
            user = get_user_reid()
            delete_case(user, case_id)
            if get_case_id() == case_id:
                reset_case()
            st.session_state["_toast_message"] = "Case deleted"
            st.rerun()
    with col_no:
        if st.button("Cancel"):
            st.rerun()


@st.dialog("Duplicate case")
def _confirm_duplicate_dialog(case_id: str, case_name: str, case_notes: str):
    """Modal dialog for duplicating a case with editable name and notes."""
    default_name = f"{case_name} (copy)"

    dup_name = st.text_input("Name", value=default_name, key="cm_dup_name")
    dup_notes = st.text_area("Notes", value=case_notes, key="cm_dup_notes")

    if st.button("Duplicate", type="primary", use_container_width=True):
        if not dup_name.strip():
            st.warning("Enter a name for the duplicate.")
        elif case_name_exists(get_user_reid(), dup_name):
            st.warning(f'A case named "{dup_name}" already exists.')
        else:
            user_reid = get_user_reid()
            source = load_case(user_reid, case_id)
            if source:
                duplicated = save_case(
                    user_reid=user_reid,
                    case_name=dup_name,
                    case_notes=dup_notes,
                    ui_config=source.ui_config,
                    selected_modules=set(source.selected_modules),
                    case_id=None,  # new case
                    result_snapshot=source.result_snapshot,
                )
                apply_case_to_session(duplicated, st.session_state)
                st.session_state["_toast_message"] = (
                    f'Duplicated as "{dup_name}"'
                )
                st.rerun()


@st.dialog("Edit case")
def _confirm_edit_dialog(case: SavedCase):
    """Modal dialog for editing a saved case's name and notes."""
    edit_name = st.text_input("Name", value=case.name, key="cm_edit_name")
    edit_notes = st.text_area("Notes", value=case.notes, key="cm_edit_notes")

    if st.button("Save", type="primary", use_container_width=True):
        if not edit_name.strip():
            st.warning("Enter a case name.")
        elif case_name_exists(get_user_reid(), edit_name, exclude_case_id=case.id):
            st.warning(f'A case named "{edit_name}" already exists.')
        else:
            save_case(
                user_reid=case.user_reid,
                case_name=edit_name,
                case_notes=edit_notes,
                ui_config=case.ui_config,
                selected_modules=case.selected_modules,
                case_id=case.id,
                result_snapshot=case.result_snapshot,
            )
            # If the edited case is the currently loaded one, sync session state
            if get_case_id() == case.id:
                set_case_name(edit_name)
                set_case_notes(edit_notes)
            st.session_state["_toast_message"] = f'Updated "{edit_name}"'
            st.rerun()


# =============================================================================
# PAGE CONTENT
# =============================================================================

st.title("Regumetrica")
st.subheader("1. Create and select case")

# Check company selection
user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

# Update saved cases count for default naming
case_count = get_case_count(user_reid)
set_saved_cases_count(case_count)


# =============================================================================
# CREATE NEW CASE
# =============================================================================

st.markdown("##### New case")

create_name = st.text_input(
    "Case name",
    value="",
    placeholder="Enter case name",
    key="cm_create_name",
)
create_notes = st.text_area(
    "Notes",
    value="",
    placeholder="Notes (optional)",
    key="cm_create_notes",
    height=80,
)

col_create, _ = st.columns([0.2, 0.8])
with col_create:
    if st.button("Create case", type="primary", use_container_width=True):
        name = create_name.strip()
        if not name:
            st.warning("Enter a case name.")
        elif case_name_exists(user_reid, name):
            st.warning(f'A case named "{name}" already exists.')
        else:
            created = save_case(
                user_reid=user_reid,
                case_name=name,
                case_notes=create_notes,
                ui_config=copy.deepcopy(DEFAULT_UI_CONFIG),
                selected_modules=set(),
                case_id=None,
            )
            apply_case_to_session(created, st.session_state)
            st.session_state["_toast_message"] = f'Created "{name}"'
            st.rerun()

st.divider()


# =============================================================================
# SAVED CASES — SELECTBOX
# =============================================================================

st.markdown("##### Saved cases")

saved_cases = list_cases(user_reid)

if saved_cases:
    st.caption(
        f"You have {len(saved_cases)} saved case(s). "
        "Select one to view details."
    )

    case_display_names = ["-- Select a case --"] + [
        _format_case_display(c) for c in saved_cases
    ]

    selected_idx = st.selectbox(
        "Saved cases",
        range(len(case_display_names)),
        format_func=lambda i: case_display_names[i],
        key="cm_case_select",
        label_visibility="collapsed",
    )

    if selected_idx > 0:
        selected_case = saved_cases[selected_idx - 1]
        has_snapshot = (
            selected_case.result_snapshot is not None
            and selected_case.result_snapshot.get("revenue_frame") is not None
        )

        # Highlight if this is the currently loaded case
        is_loaded = get_case_id() == selected_case.id

        with st.container(border=True):
            if is_loaded:
                st.markdown(f"**{selected_case.name}** *(current)*")
            else:
                st.markdown(f"**{selected_case.name}**")

            # Metadata
            if has_snapshot:
                revenue_str = format_tkr_display(
                    selected_case.result_snapshot["revenue_frame"]
                )
            else:
                revenue_str = "(no results)"

            meta_lines = [
                f"**Revenue:** {revenue_str}",
                f"**Last updated:** {_format_timestamp(selected_case.updated_at)}",
                f"**Modules:** {_format_modules_display(selected_case.selected_modules)}",
            ]
            if selected_case.notes:
                meta_lines.append(f"**Notes:** {selected_case.notes}")
            st.caption("  \n".join(meta_lines))

            if has_snapshot:
                st.caption("Has computed results")
            else:
                st.caption("No computed results")

            # Action buttons
            col_load, col_edit, col_dup, col_delete = st.columns(4)
            with col_load:
                if st.button(
                    "Load case", type="primary", key="cm_load_case",
                    use_container_width=True,
                    disabled=is_loaded,
                ):
                    case_data = load_case(user_reid, selected_case.id)
                    if case_data:
                        apply_case_to_session(case_data, st.session_state)
                        st.session_state["_toast_message"] = (
                            f"Loaded: {case_data.name}"
                        )
                        st.rerun()

            with col_edit:
                if st.button(
                    "Edit", key="cm_edit_case",
                    use_container_width=True,
                ):
                    _confirm_edit_dialog(selected_case)

            with col_dup:
                if st.button(
                    "Duplicate", key="cm_duplicate_case",
                    use_container_width=True,
                ):
                    _confirm_duplicate_dialog(
                        selected_case.id,
                        selected_case.name,
                        selected_case.notes,
                    )

            with col_delete:
                if st.button(
                    "Delete", key="cm_delete_case",
                    use_container_width=True,
                ):
                    _confirm_delete_dialog(
                        selected_case.id, selected_case.name,
                    )

else:
    st.caption("No saved cases yet. Create a case above to get started.")

st.divider()


# =============================================================================
# COMPARE CASES — MULTISELECT
# =============================================================================

st.markdown("##### Compare cases")

comparable = [
    c for c in saved_cases
    if c.result_snapshot is not None
    and c.result_snapshot.get("revenue_frame") is not None
]

if comparable:
    comparable_map = {c.id: c for c in comparable}

    selected_ids = st.multiselect(
        "Select cases to compare",
        options=list(comparable_map.keys()),
        format_func=lambda cid: _format_case_compare(comparable_map[cid]),
        key="cm_compare_multiselect",
    )

    if len(selected_ids) >= 2:
        selected_for_compare = [comparable_map[cid] for cid in selected_ids]
        render_comparison_table(selected_for_compare)
    elif len(selected_ids) == 1:
        st.caption("Select at least 2 cases to compare.")
else:
    st.caption("No cases with computed results available for comparison.")

with st.sidebar:
    st.caption(f"Saved cases: {len(saved_cases)}/10")
