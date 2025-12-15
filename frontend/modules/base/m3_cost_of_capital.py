"""
Module 3: Cost of Capital

Hanterar WACC och relaterade parametrar.
Parameter-IDs: 3.1.X (base), 3.2.X (derived), 3.3-3.6 (adjustments)
Variable-IDs: 30.X
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_input

MODULE_KEY = "m3_cost_of_capital"

# Baseline-värden från User Manual
BASELINE_WACC = 0.0453  # Real WACC before tax


def render() -> Dict[str, Any]:
    """
    Renderar Module 3: Cost of capital.
    
    Returns:
        Dict med användarens val. Keys:
        - wacc_override: Nytt WACC-värde eller None för baseline
    """
    config: Dict[str, Any] = {}
    
    st.subheader("3. Cost of Capital")
    
    with st.expander("Parameters", expanded=True):
        st.markdown("##### 3.2 Derived parameters")
        
        # 3.2.5 Real WACC before tax
        wacc, wacc_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="3.2.5",
            label="Real WACC före skatt",
            baseline=BASELINE_WACC,
            min_val=0.01,
            max_val=0.15,
            step=0.001,
            help_text="Weighted Average Cost of Capital. Påverkar kapitalkostnaden för alla tillgångar.",
            format_as_percent=True
        )
        
        if wacc_changed:
            config["wacc_override"] = wacc
            st.caption(f"Nytt WACC: {wacc*100:.2f}% (baseline: {BASELINE_WACC*100:.2f}%)")
        
        st.divider()
        
        # Framtida: CAPM-komponenter
        st.markdown("##### 3.1 Base parameters (CAPM)")
        st.info(
            "CAPM-komponenter (3.1.1-3.1.7) kommer i framtida version:\n"
            "- Debt ratio, Asset beta, Risk-free rate\n"
            "- Market risk premium, Credit risk premium\n"
            "- Tax rate, Inflation"
        )
    
    with st.expander("Variables", expanded=False):
        st.info(
            "Capital cost variables (30.X) beräknas automatiskt.\n\n"
            "Output: Kapitalkostnad per tillgångstyp (ordinary + tail)"
        )
    
    with st.expander("Adjustment of cost of capital", expanded=False):
        st.info(
            "Quality adjustments (3.3-3.6) kommer i framtida version:\n"
            "- Network loss adjustment (3.4)\n"
            "- Utilization rate adjustment (3.5)\n"
            "- Interruption adjustment (3.6)"
        )
    
    return config
