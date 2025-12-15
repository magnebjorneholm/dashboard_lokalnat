"""
Module 5: Efficiency Incentive

Hanterar effektiviseringskrav-parametrar.
Parameter-IDs: 5.1.X - 5.4.X
Variable-IDs: 50.X
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_input

MODULE_KEY = "m5_efficiency"

# Baseline-värden från User Manual
BASELINE_OUTLIER_THRESHOLD = 2.0
BASELINE_MAX_POTENTIAL = 0.30
BASELINE_REALIZATION_TIME = 8
BASELINE_CUSTOMER_SHARING = 0.50
BASELINE_MIN_REQUIREMENT = 0.01


def render() -> Dict[str, Any]:
    """
    Renderar Module 5: Efficiency incentive.
    
    Returns:
        Dict med användarens val. Keys:
        - trunkering_max: Max potential cap eller None
        - outlier_krav: Min årligt krav för outliers eller None
    """
    config: Dict[str, Any] = {}
    
    st.subheader("5. Efficiency Incentive")
    
    with st.expander("Parameters", expanded=True):
        st.markdown("##### 5.1 Outlier identification")
        
        # 5.1.1 Outlier threshold - hanteras i DEA add-on
        st.caption("Outlier threshold (5.1.1) konfigureras i Add-on: Benchmarking")
        
        st.divider()
        
        st.markdown("##### 5.2 Efficiency requirement conversion")
        
        # 5.2.1 Max potential cap
        max_pot, max_pot_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.2.1",
            label="Max effektiviseringspotential",
            baseline=BASELINE_MAX_POTENTIAL,
            min_val=0.0,
            max_val=1.0,
            step=0.01,
            help_text="Effektivitetspotential trunkeras vid detta tak.",
            format_as_percent=True
        )
        
        if max_pot_changed:
            config["trunkering_max"] = max_pot
        
        # 5.2.2 och 5.2.3 - endast information
        st.caption(f"Realiseringstid (5.2.2): {BASELINE_REALIZATION_TIME} år (ej konfigurerbar i MVP)")
        st.caption(f"Kunddelning (5.2.3): {BASELINE_CUSTOMER_SHARING*100:.0f}% (ej konfigurerbar i MVP)")
        
        st.divider()
        
        st.markdown("##### 5.3 Efficiency requirement bounds")
        
        # 5.3.1 Minimum annual requirement (för outliers)
        min_req, min_req_changed = parameter_input(
            module_key=MODULE_KEY,
            param_id="5.3.1",
            label="Minimum årligt effkrav",
            baseline=BASELINE_MIN_REQUIREMENT,
            min_val=0.0,
            max_val=0.10,
            step=0.001,
            help_text="Fast årligt krav som tillämpas på outliers.",
            format_as_percent=True
        )
        
        if min_req_changed:
            config["outlier_krav"] = min_req
    
    with st.expander("Variables", expanded=False):
        st.info(
            "DEA variables (50.X) visas som output efter beräkning.\n\n"
            "Inkluderar:\n"
            "- Efficiency score (50.3.1)\n"
            "- Super-efficiency score (50.3.2)\n"
            "- Efficiency potential (50.3.3)\n"
            "- Efficiency-adjusted costs (50.4.X)"
        )
    
    return config
