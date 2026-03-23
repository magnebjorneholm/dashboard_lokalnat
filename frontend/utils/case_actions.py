"""
Case actions: save and compute logic.

Shared by the save bar component and Revenue Frame page.
"""

import streamlit as st

from frontend.utils.state_manager import (
    get_user_reid,
    get_case_id,
    get_case_name,
    get_case_notes,
    get_selected_modules,
    mark_case_saved,
    set_computed_config,
    set_saved_reference,
    has_config_changed_since_compute,
    get_filtered_ui_config,
    compute_config_hash,
)


def do_save_case() -> bool:
    """Update the current case in storage. Always saves working state.

    Includes a result snapshot when computed results exist and match
    the current working config (i.e. config hasn't changed since compute).

    Returns True on success, False on failure.
    """
    from frontend.utils.case_storage import save_case
    from frontend.utils.result_snapshot import extract_result_snapshot

    case_id = get_case_id()
    if case_id is None:
        st.warning("No case loaded. Create a case first.")
        return False

    user_reid = get_user_reid()
    case_name = get_case_name() or "Untitled Case"
    case_notes = get_case_notes()

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
        save_case(
            user_reid=user_reid,
            case_name=case_name,
            case_notes=case_notes,
            ui_config=ui_config,
            selected_modules=selected_modules,
            case_id=case_id,
            result_snapshot=result_snapshot,
        )

        mark_case_saved()
        set_saved_reference(ui_config, selected_modules)

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

    progress = st.progress(0, text="Loading baseline data...")
    try:
        from data_loaders.baseline_data import load_baseline_data
        from pipeline.core import run_pipeline
        baseline_data = load_baseline_data()

        # Reuse cached baseline if same company
        cached_reid = st.session_state.get("_baseline_reid")
        if cached_reid == user_reid and st.session_state.get("baseline_result") is not None:
            progress.progress(25, text="Using cached baseline...")
            baseline_result = st.session_state["baseline_result"]
        else:
            progress.progress(20, text="Computing baseline...")
            from config.case_definition import get_baseline_config
            baseline_config = get_baseline_config(user_reid)
            baseline_result = run_pipeline(baseline_data, baseline_config)
            st.session_state["baseline_result"] = baseline_result
            st.session_state["_baseline_reid"] = user_reid

        progress.progress(50, text="Building case configuration...")
        filtered_config = get_filtered_ui_config()
        case_definition = build_case_definition(
            user_reid,
            filtered_config
        )

        progress.progress(60, text="Calculating revenue frame...")
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
        progress.progress(90, text="Finalizing...")
        set_computed_config(
            ui_config=st.session_state.get("ui_config", {}),
            selected_modules=get_selected_modules(),
        )

        progress.progress(100, text="Calculation complete")

    except ValueError as e:
        progress.empty()
        st.error(f"Configuration error: {e}")
        return
    except Exception as e:
        progress.empty()
        st.error(f"Calculation error: {e}")
        with st.expander("Technical details"):
            st.exception(e)
        return

    st.switch_page("pages/4_revenue_frame.py")
