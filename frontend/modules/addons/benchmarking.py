"""
Add-on Module: Benchmarking

Handles DEA configuration and future SFA/StoNED methods.
New DEA runs only if configuration differs from baseline.
"""

import streamlit as st
from typing import Dict, Any, List

from frontend.common.parameter_input import parameter_input
from frontend.common.formulas import (
    get_formula_with_caption,
    FORMULA_DEA_LP,
    FORMULA_DEA_COMPACT,
    FORMULA_DEA_VRS_CONSTRAINT,
    FORMULA_OUTLIER_THRESHOLD,
    FORMULA_EFFICIENCY_POTENTIAL,
)

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
        help="DEA = Data Envelopment Analysis"
    )

    if method != "DEA":
        st.info("Planned.")
        config["dea_method"] = "baseline"
        return config
    
    # === DEA CONFIGURATION ===
    with st.expander("DEA specification", expanded=True):
        
        # === CALCULATION FORMULAS ===
        st.markdown("**DEA optimization (input-oriented)**")
        
        # Compact formula for quick overview
        formula_compact, caption_compact = get_formula_with_caption("DEA")
        st.latex(formula_compact)
        st.caption(caption_compact)
        
        # Full LP formulation in sub-expander
        with st.expander("View complete LP formulation", expanded=False):
            st.markdown("**Super-efficiency DEA** (excludes DMU i from reference set)")
            formula_lp, caption_lp = get_formula_with_caption("DEA_SUPER")
            st.latex(formula_lp)
            st.caption(caption_lp)
            
            st.markdown("**VRS constraint** (variable returns to scale)")
            st.latex(FORMULA_DEA_VRS_CONSTRAINT)
            st.caption("Added under VRS to permit variable returns to scale")
            
            st.markdown("**Efficiency potential**")
            st.latex(FORMULA_EFFICIENCY_POTENTIAL)
            st.caption("Potential = 1 - θ, where θ is the efficiency score")
        
        st.divider()
        
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
        
        # --- Outlier detection ---
        st.markdown("**Outlier detection (IQR method)**")
        
        # Show outlier formula
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
        
        multiplier = st.number_input(
            "IQR multiplier (5.1.1)",
            value=BASELINE_MULTIPLIER,
            min_value=1.0,
            max_value=5.0,
            step=0.5,
            key=f"{MODULE_KEY}_multiplier",
            help="Threshold = Q_upper + multiplier × IQR"
        )
        config["dea_multiplier"] = multiplier
        
        st.divider()
        
        # === STATUS: Baseline or Custom ===
        is_baseline = is_baseline_dea_config(config)
        
        if is_baseline:
            config["dea_method"] = "baseline"
            st.success(
                "**Baseline specification**\n\n"
                "Ei baseline. Pre-computed results applied."
            )
        else:
            config["dea_method"] = "custom"
            
            # Show differences
            differences = []
            if set(config["dea_inputs"]) != set(BASELINE_INPUTS):
                differences.append(f"Inputs: {config['dea_inputs']} (baseline: {BASELINE_INPUTS})")
            if set(config["dea_outputs"]) != set(BASELINE_OUTPUTS):
                differences.append(f"Outputs: {config['dea_outputs']} (baseline: {BASELINE_OUTPUTS})")
            if config["dea_rts"] != BASELINE_RTS:
                differences.append(f"RTS: {config['dea_rts']} (baseline: {BASELINE_RTS})")
            if abs(config["dea_multiplier"] - BASELINE_MULTIPLIER) > 0.001:
                differences.append(f"Multiplier: {config['dea_multiplier']} (baseline: {BASELINE_MULTIPLIER})")
            if abs(config["dea_q_lower"] - BASELINE_Q_LOWER) > 0.001:
                differences.append(f"Q_lower: {config['dea_q_lower']} (baseline: {BASELINE_Q_LOWER})")
            if abs(config["dea_q_upper"] - BASELINE_Q_UPPER) > 0.001:
                differences.append(f"Q_upper: {config['dea_q_upper']} (baseline: {BASELINE_Q_UPPER})")
            
            st.warning(
                "**Custom specification**\n\n"
                "Custom specification. New DEA required.\n\n"
                "Modifications:\n- " + "\n- ".join(differences)
            )
        
        # === SUMMARY ===
        st.divider()
        st.markdown("**Summary**")
        st.code(f"""Inputs:  {', '.join(config['dea_inputs'])}
Outputs: {', '.join(config['dea_outputs'])}
RTS:     {config['dea_rts'].upper()}
Outlier: Q{config['dea_q_lower']:.0f}-Q{config['dea_q_upper']:.0f}, multiplier={config['dea_multiplier']:.1f}""")
    
    return config