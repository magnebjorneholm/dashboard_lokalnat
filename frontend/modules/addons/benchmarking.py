"""
Add-on Module: Benchmarking

Handles DEA configuration and pre-computed StoNED model selection.
New DEA runs only if configuration differs from baseline.

Section-based rendering:
- render_dea_spec() -> DEA/StoNED specification
"""

import streamlit as st
from typing import Dict, Any, List

from frontend.utils.state_manager import get_config_value
from config.column_names import COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG, COL_TOTEX
from config.glossary import PID_OUTLIER_THRESHOLD
from data_loaders.stoned_data import (
    get_available_stoned_models,
    load_stoned_model_registry,
)

MODULE_KEY = "addon_benchmarking"

# DEA specification options
DEA_INPUT_OPTIONS: List[str] = [COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG, COL_TOTEX]
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]

# Baseline configuration (Ei regulatory specification)
BASELINE_INPUTS = [COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG]
BASELINE_OUTPUTS = ["CU", "MW", "NS", "MWhl", "MWhh"]
BASELINE_RTS = "crs"
BASELINE_MULTIPLIER = 2.0
BASELINE_Q_LOWER = 25.0
BASELINE_Q_UPPER = 75.0

# Outlier threshold formula (IQR method) for display
FORMULA_OUTLIER_THRESHOLD = r"\text{threshold} = Q_{75} + k \times (Q_{75} - Q_{25})"


def is_baseline_dea_config(config: Dict[str, Any]) -> bool:
    """Check if DEA configuration matches Ei baseline."""
    return (
        set(config.get("dea_inputs", [])) == set(BASELINE_INPUTS) and
        set(config.get("dea_outputs", [])) == set(BASELINE_OUTPUTS) and
        config.get("dea_rts", "crs") == BASELINE_RTS and
        abs(config.get("dea_multiplier", 2.0) - BASELINE_MULTIPLIER) < 0.001 and
        abs(config.get("dea_q_lower", 25.0) - BASELINE_Q_LOWER) < 0.001 and
        abs(config.get("dea_q_upper", 75.0) - BASELINE_Q_UPPER) < 0.001
    )


def render_dea_spec() -> Dict[str, Any]:
    """
    Render M7 DEA specification section.
    
    DEA configuration is always displayed. If config differs from baseline,
    new DEA runs at calculation time; otherwise cached results are used.
    
    Returns:
        Dict with DEA configuration:
        - dea_method: "baseline" or "custom"
        - dea_inputs: List of inputs
        - dea_outputs: List of outputs
        - dea_rts: "crs" or "vrs"
        - dea_multiplier: Outlier IQR multiplier
        - dea_q_lower: Lower percentile
        - dea_q_upper: Upper percentile
    """
    # Initialize config with baseline values (can be overridden by ui_config)
    config: Dict[str, Any] = {
        "dea_inputs": get_config_value(MODULE_KEY, "dea_inputs", BASELINE_INPUTS.copy()),
        "dea_outputs": get_config_value(MODULE_KEY, "dea_outputs", BASELINE_OUTPUTS.copy()),
        "dea_rts": get_config_value(MODULE_KEY, "dea_rts", BASELINE_RTS),
        "dea_multiplier": get_config_value(MODULE_KEY, "dea_multiplier", BASELINE_MULTIPLIER),
        "dea_q_lower": get_config_value(MODULE_KEY, "dea_q_lower", BASELINE_Q_LOWER),
        "dea_q_upper": get_config_value(MODULE_KEY, "dea_q_upper", BASELINE_Q_UPPER),
    }
    
    st.caption("Configure efficiency analysis model")
    
    # === METHOD SELECTION ===
    st.markdown("##### Efficiency analysis")
    
    method = st.radio(
        "Method",
        options=["DEA", "SFA", "StoNED"],
        index=0,
        key=f"{MODULE_KEY}_method",
        horizontal=True,
    )

    if method == "SFA":
        st.info("SFA planned for future release.")
        config["dea_method"] = "baseline"
        return config

    if method == "StoNED":
        return _render_stoned_spec(config)
    
    # === DEA CONFIGURATION ===
    st.caption(
        "Configure DEA model. Changes trigger new DEA analysis at calculation time."
    )
    
    dea_inputs = st.multiselect(
        "Input variables",
        options=DEA_INPUT_OPTIONS,
        default=get_config_value(MODULE_KEY, "dea_inputs", BASELINE_INPUTS),
        key=f"{MODULE_KEY}_inputs",
        help="Cost measures used as DEA inputs"
    )
    config["dea_inputs"] = dea_inputs if dea_inputs else BASELINE_INPUTS
    
    dea_outputs = st.multiselect(
        "Output variables",
        options=DEA_OUTPUT_OPTIONS,
        default=get_config_value(MODULE_KEY, "dea_outputs", BASELINE_OUTPUTS),
        key=f"{MODULE_KEY}_outputs",
        help="Service measures used as DEA outputs"
    )
    config["dea_outputs"] = dea_outputs if dea_outputs else BASELINE_OUTPUTS
    
    st.divider()
    
    # Returns to scale
    st.markdown("**Returns to scale**")
    current_rts = get_config_value(MODULE_KEY, "dea_rts", BASELINE_RTS)
    rts = st.radio(
        "RTS assumption",
        options=["crs", "vrs"],
        index=0 if current_rts == "crs" else 1,
        key=f"{MODULE_KEY}_rts",
        horizontal=True,
        help="CRS: Constant returns to scale. VRS: Variable returns to scale."
    )
    config["dea_rts"] = rts
    
    st.divider()
    
    # Outlier identification
    st.markdown(f"**{PID_OUTLIER_THRESHOLD} Outlier identification**")
    st.latex(FORMULA_OUTLIER_THRESHOLD)
    
    col1, col2 = st.columns(2)
    with col1:
        q_lower = st.number_input(
            "Lower percentile (Q_lower)",
            value=get_config_value(MODULE_KEY, "dea_q_lower", BASELINE_Q_LOWER),
            min_value=0.0,
            max_value=50.0,
            step=5.0,
            key=f"{MODULE_KEY}_q_lower",
            help="Lower bound for IQR calculation (baseline: 25)"
        )
        config["dea_q_lower"] = q_lower
    
    with col2:
        q_upper = st.number_input(
            "Upper percentile (Q_upper)",
            value=get_config_value(MODULE_KEY, "dea_q_upper", BASELINE_Q_UPPER),
            min_value=50.0,
            max_value=100.0,
            step=5.0,
            key=f"{MODULE_KEY}_q_upper",
            help="Upper bound for IQR calculation (baseline: 75)"
        )
        config["dea_q_upper"] = q_upper
    
    # 5.1.1 IQR multiplier
    multiplier = st.number_input(
        f"{PID_OUTLIER_THRESHOLD} IQR multiplier",
        value=get_config_value(MODULE_KEY, "dea_multiplier", BASELINE_MULTIPLIER),
        min_value=1.0,
        max_value=5.0,
        step=0.5,
        key=f"{MODULE_KEY}_multiplier",
        help="Threshold = Q_upper + multiplier x IQR (baseline: 2.0)"
    )
    config["dea_multiplier"] = multiplier
    
    # Set method based on config
    is_baseline = is_baseline_dea_config(config)
    config["dea_method"] = "baseline" if is_baseline else "custom"

    return config


def _render_stoned_spec(config: Dict[str, Any]) -> Dict[str, Any]:
    """Render StoNED model selection UI.

    Returns config dict with dea_method="stoned" and selected model ID.
    """
    registry = load_stoned_model_registry()
    available = get_available_stoned_models()

    if not available:
        st.warning("No pre-computed StoNED models available.")
        config["dea_method"] = "baseline"
        return config

    st.caption("Select a pre-computed StoNED model")

    # Model selector
    current_id = get_config_value(MODULE_KEY, "stoned_model_id", available[0])
    if current_id not in available:
        current_id = available[0]

    selected_id = st.radio(
        "StoNED model",
        options=available,
        index=available.index(current_id),
        format_func=lambda mid: registry.get(mid, {}).get("label", mid),
        key=f"{MODULE_KEY}_stoned_model",
    )

    # Show model details
    info = registry.get(selected_id, {})
    if info:
        st.divider()
        st.markdown("**Model specification**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Cost variable:** {info.get('cost_variable', '-')}")
            rts_label = "VRS" if info.get("rts") == "vrs" else "CRS"
            st.markdown(f"**Returns to scale:** {rts_label}")
        with col2:
            outputs = info.get("output_variables", [])
            st.markdown(f"**Outputs:** {', '.join(outputs)}")
            st.markdown(f"**Firms (excl. outliers):** {info.get('n_firms', '-')}")

        st.divider()
        st.markdown("**Estimation diagnostics**")
        c1, c2, c3 = st.columns(3)
        c1.metric("sigma_u", f"{info.get('sigma_u', 0):.4f}")
        c2.metric("sigma_v", f"{info.get('sigma_v', 0):.4f}")
        c3.metric("lambda", f"{info.get('lambda_ratio', 0):.4f}")

    config["dea_method"] = "stoned"
    config["stoned_model_id"] = selected_id
    return config