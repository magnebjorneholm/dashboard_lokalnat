"""
Add-on Module: Benchmarking

Handles DEA configuration and future SFA/StoNED methods.
New DEA runs only if configuration differs from baseline.
"""

import streamlit as st
from typing import Dict, Any, List

from frontend.common.formulas import FORMULA_OUTLIER_THRESHOLD

MODULE_KEY = "addon_benchmarking"

# DEA specification options
DEA_INPUT_OPTIONS: List[str] = ["CAPEX", "OPEXp", "TOTEX"]
DEA_OUTPUT_OPTIONS: List[str] = ["CU", "MW", "NS", "MWhl", "MWhh"]

# Baseline configuration (Ei regulatory specification)
BASELINE_INPUTS = ["CAPEX", "OPEXp"]
BASELINE_OUTPUTS = ["CU", "MW", "NS", "MWhl", "MWhh"]
BASELINE_RTS = "crs"
BASELINE_MULTIPLIER = 2.0
BASELINE_Q_LOWER = 25.0
BASELINE_Q_UPPER = 75.0


def is_baseline_dea_config(config: Dict[str, Any]) -> bool:
    """
    Check if DEA configuration matches Ei baseline.
    
    Args:
        config: DEA configuration from UI
        
    Returns:
        True if config matches baseline (no new DEA required)
    """
    return (
        set(config.get("dea_inputs", [])) == set(BASELINE_INPUTS) and
        set(config.get("dea_outputs", [])) == set(BASELINE_OUTPUTS) and
        config.get("dea_rts", "crs") == BASELINE_RTS and
        abs(config.get("dea_multiplier", 2.0) - BASELINE_MULTIPLIER) < 0.001 and
        abs(config.get("dea_q_lower", 25.0) - BASELINE_Q_LOWER) < 0.001 and
        abs(config.get("dea_q_upper", 75.0) - BASELINE_Q_UPPER) < 0.001
    )


def render() -> Dict[str, Any]:
    """
    Render Add-on: Benchmarking module.
    
    DEA configuration is always displayed. If config differs from baseline,
    new DEA runs at calculation time; otherwise cached results are used.
    
    Returns:
        Dict with user selections:
        - dea_method: "baseline" or "custom"
        - dea_inputs: List of inputs
        - dea_outputs: List of outputs
        - dea_rts: "crs" or "vrs"
        - dea_multiplier: Outlier IQR multiplier
        - dea_q_lower: Lower percentile
        - dea_q_upper: Upper percentile
    """
    # Initialize config with baseline values
    config: Dict[str, Any] = {
        "dea_inputs": BASELINE_INPUTS.copy(),
        "dea_outputs": BASELINE_OUTPUTS.copy(),
        "dea_rts": BASELINE_RTS,
        "dea_multiplier": BASELINE_MULTIPLIER,
        "dea_q_lower": BASELINE_Q_LOWER,
        "dea_q_upper": BASELINE_Q_UPPER,
    }
    
    st.subheader("Add-on: Benchmarking")
    
    # === METHOD SELECTION ===
    st.markdown("##### Efficiency analysis")
    
    method = st.radio(
        "Method",
        options=["DEA", "SFA", "StoNED"],
        index=0,
        key=f"{MODULE_KEY}_method",
        horizontal=True,
    )

    if method != "DEA":
        st.info("Planned.")
        config["dea_method"] = "baseline"
        return config
    
    # === DEA CONFIGURATION ===
    with st.expander("DEA specification", expanded=False):
        st.caption(
            "Configure DEA model. If configuration matches Ei baseline, "
            "pre-computed results are applied; otherwise, new DEA is run."
        )
        # --- Inputs ---
        st.markdown("**Inputs (costs)**")
        selected_inputs = st.multiselect(
            "Select inputs",
            options=DEA_INPUT_OPTIONS,
            default=BASELINE_INPUTS,
            key=f"{MODULE_KEY}_inputs",
            help="CAPEX = capital costs, OPEXp = adjusted OPEX, TOTEX = CAPEX + OPEXp"
        )
        
        if not selected_inputs:
            st.error("At least one input required")
            selected_inputs = BASELINE_INPUTS
        
        config["dea_inputs"] = selected_inputs
        
        st.divider()
        
        # --- Outputs ---
        st.markdown("**Outputs (delivery)**")
        selected_outputs = st.multiselect(
            "Select outputs",
            options=DEA_OUTPUT_OPTIONS,
            default=BASELINE_OUTPUTS,
            key=f"{MODULE_KEY}_outputs",
            help="CU=Subscriptions, MW=Peak capacity, NS=Substations, MWhl=Low-voltage energy, MWhh=High-voltage energy"
        )
        
        if not selected_outputs:
            st.error("At least one output required")
            selected_outputs = BASELINE_OUTPUTS
        
        config["dea_outputs"] = selected_outputs
        
        st.divider()
        
        # --- Returns to scale ---
        st.markdown("**Returns to scale**")
        rts = st.radio(
            "RTS assumption",
            options=["crs", "vrs"],
            index=0 if BASELINE_RTS == "crs" else 1,
            key=f"{MODULE_KEY}_rts",
            horizontal=True,
            help="CRS = Constant (baseline), VRS = Variable"
        )
        config["dea_rts"] = rts
        
        st.divider()
        
        # --- Outlier detection (5.1.1) ---
        st.markdown("**5.1 Outlier detection**")
        
        st.latex(FORMULA_OUTLIER_THRESHOLD)
        st.caption("Firms exceeding threshold flagged as outliers")
        
        col1, col2 = st.columns(2)
        with col1:
            q_lower = st.number_input(
                "Lower percentile",
                value=BASELINE_Q_LOWER,
                min_value=0.0,
                max_value=50.0,
                step=5.0,
                key=f"{MODULE_KEY}_q_lower",
                help="Lower bound for IQR calculation (baseline: 25)"
            )
            config["dea_q_lower"] = q_lower
        
        with col2:
            q_upper = st.number_input(
                "Upper percentile",
                value=BASELINE_Q_UPPER,
                min_value=50.0,
                max_value=100.0,
                step=5.0,
                key=f"{MODULE_KEY}_q_upper",
                help="Upper bound for IQR calculation (baseline: 75)"
            )
            config["dea_q_upper"] = q_upper
        
        # 5.1.1 IQR multiplier
        multiplier = st.number_input(
            "5.1.1 IQR multiplier",
            value=BASELINE_MULTIPLIER,
            min_value=1.0,
            max_value=5.0,
            step=0.5,
            key=f"{MODULE_KEY}_multiplier",
            help="Threshold = Q_upper + multiplier × IQR (baseline: 2.0)"
        )
        config["dea_multiplier"] = multiplier
        
        # Set method based on config (for backend to know if new DEA is needed)
        is_baseline = is_baseline_dea_config(config)
        config["dea_method"] = "baseline" if is_baseline else "custom"
        
        # === SUMMARY ===
        st.divider()
        st.markdown("**Summary**")
        st.code(f"""Inputs:  {', '.join(config['dea_inputs'])}
Outputs: {', '.join(config['dea_outputs'])}
RTS:     {config['dea_rts'].upper()}
Outlier: Q{config['dea_q_lower']:.0f}-Q{config['dea_q_upper']:.0f}, multiplier={config['dea_multiplier']:.1f}""")
    
    return config