"""
Module 4: Operating Expenditures

Hanterar OPEX-parametrar och påverkbara metod.
Parameter-IDs: 4.1.X
Variable-IDs: 40.X
"""

import streamlit as st
from typing import Dict, Any

from frontend.common.parameter_input import parameter_select

MODULE_KEY = "m4_operating_exp"


def render() -> Dict[str, Any]:
    """
    Renderar Module 4: Operating expenditures.
    
    Returns:
        Dict med användarens val. Keys:
        - paverkbara_method: "OPEX" eller "TOTEX"
    """
    config: Dict[str, Any] = {}
    
    st.subheader("4. Operating Expenditures")
    
    with st.expander("Parameters", expanded=True):
        st.markdown("##### 4.1 General scaling parameters")
        
        st.info(
            "OPEX scaling factors (4.1.1-4.1.3) kommer i framtida version:\n"
            "- Scaling factor adjustable OPEX\n"
            "- Scaling factor flexibility services\n"
            "- Scaling factor non-adjustable OPEX"
        )
        
        st.divider()
        
        # Påverkbara metod (5.4.1 men hör konceptuellt till OPEX)
        st.markdown("##### Effektivitetskravets kostnadsbas")
        
        method, method_changed = parameter_select(
            module_key=MODULE_KEY,
            param_id="5.4.1",
            label="Tillämpa effkrav på",
            options=["OPEX", "TOTEX"],
            baseline="OPEX",
            help_text="OPEX = endast påverkbara kostnader. TOTEX = påverkbara + kapitalkostnader."
        )
        
        config["paverkbara_method"] = method
        
        if method_changed and method == "TOTEX":
            st.warning("TOTEX-metod valdes. Effektiviseringskravet tillämpas på både OPEX och CAPEX.")
    
    with st.expander("Variables", expanded=False):
        st.info(
            "OPEX variables (40.X) visas som output.\n\n"
            "Inkluderar:\n"
            "- Adjustable OPEX (OPEXp)\n"
            "- Flexibility services\n"
            "- Non-adjustable OPEX"
        )
    
    return config
