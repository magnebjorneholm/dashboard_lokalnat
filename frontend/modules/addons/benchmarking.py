"""
Add-on Module: Benchmarking

Handles DEA configuration. New DEA runs only if configuration differs from
baseline.

Section-based rendering:
- render_dea_spec() -> DEA specification
"""

import streamlit as st
from typing import Dict, Any, List

from frontend.utils.state_manager import get_config_value
from config.column_names import COL_CAPITAL_COST_2024, COL_OPEXP_DEA, COL_TOTEX_DEA
from config.glossary import PID_OUTLIER_THRESHOLD

MODULE_KEY = "addon_benchmarking"

# Cost-model choice for the DEA inputs. The frontier inputs are LOCKED to the
# frontier track (raw OPEXp + capex): the user only chooses whether they enter as
# two separate inputs or as their sum (TOTEX). The requirement-side
# controllable_cost_average is never selectable as a DEA input.
COST_MODEL_SEPARATE = "OPEXp + CAPEX"
COST_MODEL_TOTEX = "TOTEX (OPEXp + CAPEX)"
COST_MODEL_OPTIONS: List[str] = [COST_MODEL_SEPARATE, COST_MODEL_TOTEX]
COST_MODEL_TO_INPUTS = {
    COST_MODEL_SEPARATE: [COL_CAPITAL_COST_2024, COL_OPEXP_DEA],
    COST_MODEL_TOTEX: [COL_TOTEX_DEA],
}
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]

# Baseline configuration (Ei regulatory specification)
BASELINE_COST_MODEL = COST_MODEL_SEPARATE
BASELINE_INPUTS = COST_MODEL_TO_INPUTS[COST_MODEL_SEPARATE]
BASELINE_OUTPUTS = ["CU", "MW", "NS", "MWhl", "MWhh"]
BASELINE_RTS = "crs"
BASELINE_MULTIPLIER = 2.0
BASELINE_Q_LOWER = 25.0
BASELINE_Q_UPPER = 75.0

# Outlier threshold formula (IQR method) for display
FORMULA_OUTLIER_THRESHOLD = r"\text{threshold} = Q_{75} + k \times (Q_{75} - Q_{25})"


def is_baseline_dea_config(config: Dict[str, Any]) -> bool:
    """Check if DEA configuration matches Ei baseline.

    When True the pipeline serves Ei's published facit straight from EIs_DEA.xlsx
    (a cache of exactly this spec run on opexp_dea); otherwise a live DEA runs on
    the locked frontier inputs.
    """
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
        "dea_cost_model": get_config_value(MODULE_KEY, "dea_cost_model", BASELINE_COST_MODEL),
        "dea_outputs": get_config_value(MODULE_KEY, "dea_outputs", BASELINE_OUTPUTS.copy()),
        "dea_rts": get_config_value(MODULE_KEY, "dea_rts", BASELINE_RTS),
        "dea_multiplier": get_config_value(MODULE_KEY, "dea_multiplier", BASELINE_MULTIPLIER),
        "dea_q_lower": get_config_value(MODULE_KEY, "dea_q_lower", BASELINE_Q_LOWER),
        "dea_q_upper": get_config_value(MODULE_KEY, "dea_q_upper", BASELINE_Q_UPPER),
    }
    
    st.caption("Configure efficiency analysis model")

    # === DEA CONFIGURATION ===
    st.markdown("##### Efficiency analysis")
    st.caption(
        "Configure DEA model. Changes trigger new DEA analysis at calculation time."
    )
    
    # Cost model: the two frontier inputs (raw OPEXp + capex) are locked; the user only
    # chooses whether they enter separately or summed as TOTEX. controllable_cost_average
    # (the requirement base) is never a DEA input.
    current_cost_model = get_config_value(MODULE_KEY, "dea_cost_model", BASELINE_COST_MODEL)
    cost_model = st.radio(
        "Cost inputs",
        options=COST_MODEL_OPTIONS,
        index=COST_MODEL_OPTIONS.index(current_cost_model)
        if current_cost_model in COST_MODEL_OPTIONS else 0,
        key=f"{MODULE_KEY}_cost_model",
        horizontal=True,
        help="Locked frontier inputs (raw OPEXp + capital cost): pick two separate inputs or their sum (TOTEX)."
    )
    config["dea_cost_model"] = cost_model
    config["dea_inputs"] = COST_MODEL_TO_INPUTS[cost_model]
    
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