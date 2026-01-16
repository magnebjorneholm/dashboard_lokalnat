"""
Module 4: Operating Expenditures

Handles OPEX parameters and påverkbara method.
Parameter-IDs: 4.1.X
Variable-IDs: 40.X
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_select

MODULE_KEY = "m4_operating_exp"


def render() -> Dict[str, Any]:
    """
    Render Module 4: Operating expenditures.
    
    Returns:
        Dict with user selections:
        - paverkbara_method: "OPEX" or "TOTEX"
    """
    config: Dict[str, Any] = {}
    
    st.subheader("4. Operating Expenditures")
    
    with st.expander("Parameters", expanded=False):
        st.markdown("##### 4.1 General scaling parameters")
        
        st.info(
            "OPEX scaling factors (4.1.1–4.1.3) — planned:\n"
            "- Adjustable OPEX scaling\n"
            "- Flexibility services scaling\n"
            "- Non-adjustable OPEX scaling"
        )
        
        st.divider()
        
        # Påverkbara method (5.4.1 but conceptually belongs to OPEX)
        st.markdown("##### Efficiency requirement cost base")
        
        method, method_changed = parameter_select(
            module_key=MODULE_KEY,
            param_id="5.4.1",
            label="Apply efficiency requirement to",
            options=["OPEX", "TOTEX"],
            baseline="OPEX",
            help_text="OPEX: adjustable costs. TOTEX: includes capital costs."
        )
        
        if method_changed:
            config["paverkbara_method"] = method
    
    return config