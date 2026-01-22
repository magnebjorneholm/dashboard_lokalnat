"""
Module 4: Operating Expenditures

Handles OPEX parameters.
Parameter-IDs: 4.1.X
Variable-IDs: 40.X

Section-based rendering:
- render_scaling() -> 4.1.X OPEX scaling parameters
- render_opex_vars() -> 40.X OPEX variables
"""

import streamlit as st
from typing import Dict, Any

MODULE_KEY = "m4_operating_exp"


def render_scaling() -> Dict[str, Any]:
    """
    Render M4 scaling section: 4.1.X OPEX scaling parameters.
    
    Returns:
        Dict with OPEX scaling parameter overrides
    """
    config: Dict[str, Any] = {}
    
    st.markdown("### 4. Operating Expenditures - Scaling Parameters")
    st.caption("Parameters 4.1.X: OPEX scaling factors")
    
    with st.expander("4.1 General scaling parameters", expanded=False):
        st.info(
            "OPEX scaling factors (4.1.1-4.1.3) - planned for future release:\n"
            "- 4.1.1 Scaling factor adjustable OPEX\n"
            "- 4.1.2 Scaling factor flexibility services\n"
            "- 4.1.3 Scaling factor non-adjustable OPEX"
        )
    
    return config


def render_opex_vars() -> Dict[str, Any]:
    """
    Render M4 variables section: 40.X OPEX variables.
    
    Returns:
        Dict with OPEX variable overrides
    """
    config: Dict[str, Any] = {}
    
    st.markdown("### 4. Operating Expenditures - Variables")
    st.caption("Variables 40.X: Company-specific OPEX inputs")
    
    with st.expander("40.X OPEX variables", expanded=False):
        st.info(
            "OPEX variables (40.X) - planned for future release:\n"
            "- 40.1.1 Adjusted OPEX (OPEXp)\n"
            "- 40.1.2 Flexibility service cost\n"
            "- 40.2.1 Total non-adjustable costs (prognosis)"
        )
    
    return config