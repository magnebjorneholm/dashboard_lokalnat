"""
Module 5: Efficiency Incentive

Handles efficiency requirement parameters.
Parameter-IDs: 5.1.X - 5.4.X
Variable-IDs: 50.X
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_input
from frontend.common.formulas import (
    get_formula_with_caption,
    FORMULA_TOTAL_EFFICIENCY,
    FORMULA_ANNUAL_EFFICIENCY_REQ,
    FORMULA_EFFICIENCY_COMPLETE,
    FORMULA_OUTLIER_THRESHOLD,
)

MODULE_KEY = "m5_efficiency"

# Baseline values from Ei methodology for regulatory period 2024-2027
BASELINE_OUTLIER_THRESHOLD = 2.0
BASELINE_MAX_POTENTIAL = 0.30
BASELINE_REALIZATION_TIME = 8
BASELINE_CUSTOMER_SHARING = 0.50
BASELINE_SUPERVISION_PERIOD = 4
BASELINE_MIN_REQUIREMENT = 0.01


def render() -> Dict[str, Any]:
    """
    Render Module 5: Efficiency incentive.
    
    All inputs are always displayed with baseline as default. Only values
    differing from baseline are saved to config.
    
    Returns:
        Dict with user selections:
        - trunkering_max: Max potential cap or None
        - outlier_krav: Min annual requirement for outliers or None
        - kunddelning: Share allocated to customers or None
        - realiseringstid: Years for full efficiency realization or None
    """
    config: Dict[str, Any] = {}
    
    st.subheader("5. Efficiency Incentive")
    
    with st.expander("Parameters", expanded=True):
        st.markdown("##### 5.1 Outlier identification")

        # 5.1.1 Outlier threshold - handled in DEA add-on
        st.caption("Outlier threshold (5.1.1): see Add-on Benchmarking")

        # Show outlier formula for reference
        st.markdown("**Outlier threshold (IQR method)**")
        st.latex(FORMULA_OUTLIER_THRESHOLD)
        st.caption("Firms exceeding threshold flagged as outliers")
        
        st.divider()
        
        st.markdown("##### 5.2 Efficiency requirement conversion")
        
        # === CALCULATION FORMULAS ===
        st.markdown("**Calculation formulas**")
        
        st.markdown("*Total efficiency gain over regulatory period:*")
        st.latex(FORMULA_TOTAL_EFFICIENCY)
        st.caption("Truncated potential × customer share × realization factor")
        
        st.markdown("*Annual efficiency requirement:*")
        formula_eff, caption_eff = get_formula_with_caption("EFFICIENCY_REQ")
        st.latex(formula_eff)
        st.caption(caption_eff)
        
        st.divider()
        
        # 5.2.1 Max potential cap
        max_pot, max_pot_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.2.1",
            label="Maximum efficiency potential cap",
            baseline=BASELINE_MAX_POTENTIAL,
            min_val=0.0,
            max_val=1.0,
            step=0.01,
            help_text="Upper bound on assessed efficiency potential",
            format_as_percent=True
        )
        
        if max_pot_changed:
            config["trunkering_max"] = max_pot
        
        # 5.2.2 Realization time
        real_time, real_time_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.2.2",
            label="Realization time",
            baseline=float(BASELINE_REALIZATION_TIME),
            min_val=1.0,
            max_val=20.0,
            step=1.0,
            unit="years",
            help_text="Time horizon for full efficiency realization",
            format_as_percent=False
        )
        
        if real_time_changed:
            config["realiseringstid"] = int(real_time)
        
        # 5.2.3 Customer sharing factor
        kund_del, kund_del_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.2.3",
            label="Customer sharing factor",
            baseline=BASELINE_CUSTOMER_SHARING,
            min_val=0.0,
            max_val=1.0,
            step=0.05,
            help_text="Proportion of efficiency gains allocated to customers",
            format_as_percent=True
        )
        
        if kund_del_changed:
            config["kunddelning"] = kund_del
        
        st.divider()
        
        st.markdown("##### 5.3 Efficiency requirement bounds")
        
        # 5.3.1 Minimum annual requirement (for outliers)
        min_req, min_req_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.3.1",
            label="Minimum annual requirement",
            baseline=BASELINE_MIN_REQUIREMENT,
            min_val=0.0,
            max_val=0.10,
            step=0.001,
            help_text="Minimum annual requirement for outliers",
            format_as_percent=True
        )
        
        if min_req_changed:
            config["outlier_krav"] = min_req
    
        # Show complete formula
        st.divider()
        st.markdown("**Complete formula**")
        st.latex(FORMULA_EFFICIENCY_COMPLETE)
    
    return config