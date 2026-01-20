"""
Module 4: Operating Expenditures

Handles OPEX parameters.
Parameter-IDs: 4.1.X
Variable-IDs: 40.X
"""

import streamlit as st
from typing import Dict, Any

MODULE_KEY = "m4_operating_exp"


def render() -> Dict[str, Any]:
    """
    Render Module 4: Operating expenditures.
    
    Returns:
        Dict with user selections.
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
    
    return config