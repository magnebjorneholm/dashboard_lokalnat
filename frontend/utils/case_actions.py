"""
Case actions: save and compute logic extracted from streamlit_app.py.

Shared by the sidebar (compute button) and the save bar component.
"""

import streamlit as st

from frontend.utils.state_manager import (
    get_user_reid,
    get_case_id,
    get_case_name,
    get_case_notes,
    get_selected_modules,
    set_case_id,
    set_case_name,
    set_case_notes,
    mark_case_saved,
    set_computed_config,
    set_saved_reference,
    has_config_changed_since_compute,
    increment_saved_cases_count,
    get_filtered_ui_config,
    compute_config_hash,
)


def do_save_case(
    force_new: bool = False,
    name_override: str = None,
    notes_override: str = None,
) -> bool:
    """Save the current case to storage. Always saves working state.

    Includes a result snapshot when computed results exist and match
    the current working config (i.e. config hasn't changed since compute).

    Args:
        force_new: If True, always create a new case (ignore existing case_id).
        name_override: If set, use this name instead of session state.
        notes_override: If set, use this notes instead of session state.
    """
    from frontend.utils.case_storage import save_case
    from frontend.utils.result_snapshot import extract_result_snapshot

    user_reid = get_user_reid()
    case_name = name_override if name_override is not None else (get_case_name() or "Untitled Case")
    case_notes = notes_override if notes_override is not None else get_case_notes()
    case_id = None if force_new else get_case_id()

    # Always save working state (not computed state)
    ui_config = st.session_state.get("ui_config", {})
    selected_modules = get_selected_modules()

    # Include result snapshot if results exist and config hasn't changed
    result_snapshot = None
    if st.session_state.get("calculation_done") and not has_config_changed_since_compute():
        case_result = st.session_state.get("case_result")
        baseline_result = st.session_state.get("baseline_result")
        if case_result is not None and baseline_result is not None:
            config_hash = compute_config_hash(ui_config, selected_modules)
            result_snapshot = extract_result_snapshot(
                case_result, baseline_result, config_hash,
            )

    try:
        saved = save_case(
            user_reid=user_reid,
            case_name=case_name,
            case_notes=case_notes,
            ui_config=ui_config,
            selected_modules=selected_modules,
            case_id=case_id,
            result_snapshot=result_snapshot,
        )

        set_case_id(saved.id)
        set_case_name(case_name)
        set_case_notes(case_notes)
        mark_case_saved()
        set_saved_reference(ui_config, selected_modules)

        if case_id is None:
            increment_saved_cases_count()

        # Update session store so refresh reflects saved state
        auth_uid = st.session_state.get("auth_uid")
        if auth_uid:
            from frontend.utils.state_manager import save_to_session_store
            save_to_session_store(auth_uid)

        return True

    except ValueError as e:
        st.error(str(e))
        return False
    except Exception as e:
        st.error(f"Failed to save case: {e}")
        return False


def run_calculation() -> None:
    """Run the revenue frame calculation pipeline."""
    from config.config_adapter import build_case_definition

    user_reid = get_user_reid()

    if user_reid is None:
        st.error("No company selected.")
        return

    with st.status("Running calculation...", expanded=True) as status:
        try:
            st.write("Loading baseline data...")
            from data_loaders.baseline_data import load_baseline_data
            from pipeline.core import run_pipeline
            baseline_data = load_baseline_data()

            # Reuse cached baseline if same company
            cached_reid = st.session_state.get("_baseline_reid")
            if cached_reid == user_reid and st.session_state.get("baseline_result") is not None:
                st.write("Using cached baseline...")
                baseline_result = st.session_state["baseline_result"]
            else:
                st.write("Computing baseline...")
                from config.case_definition import get_baseline_config
                baseline_config = get_baseline_config(user_reid)
                baseline_result = run_pipeline(baseline_data, baseline_config)
                st.session_state["baseline_result"] = baseline_result
                st.session_state["_baseline_reid"] = user_reid

            st.write("Building case...")
            filtered_config = get_filtered_ui_config()
            case_definition = build_case_definition(
                user_reid,
                filtered_config
            )

            st.write("Calculating revenue frame...")
            case_result = run_pipeline(baseline_data, case_definition)
            st.session_state["case_result"] = case_result

            st.session_state["calculation_done"] = True

            # Persist KENT-derived capbase_a as parquet bytes (for case save/load)
            if case_result.pre_dea.user_capbase_a is not None:
                import io as _io
                _buf = _io.BytesIO()
                case_result.pre_dea.user_capbase_a.to_parquet(_buf, index=False)
                m1_cfg = st.session_state.get("ui_config", {}).get("m1_asset_base", {})
                m1_cfg["kent_capbase_parquet"] = _buf.getvalue()
                st.session_state["ui_config"]["m1_asset_base"] = m1_cfg

            # Store which config produced this result
            set_computed_config(
                ui_config=st.session_state.get("ui_config", {}),
                selected_modules=get_selected_modules(),
            )

            # Persist to session store (survives page refresh)
            auth_uid = st.session_state.get("auth_uid")
            if auth_uid:
                from frontend.utils.state_manager import save_to_session_store
                save_to_session_store(auth_uid)

            status.update(label="Calculation complete", state="complete")

        except ValueError as e:
            st.error(f"Configuration error: {e}")
            status.update(label="Error", state="error")
            return
        except Exception as e:
            st.error(f"Calculation error: {e}")
            with st.expander("Technical details"):
                st.exception(e)
            status.update(label="Error", state="error")
            return

    st.switch_page("pages/4_revenue_frame.py")
