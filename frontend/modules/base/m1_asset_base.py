"""
Module 1: Regulatory Asset Base Valuation

Placeholder för framtida implementation.
Parameter-IDs: 1.1.X, 1.2.X
Variable-IDs: 10.X, 11.X
"""

import streamlit as st
from typing import Dict, Any

MODULE_KEY = "m1_asset_base"


def render() -> Dict[str, Any]:
    """
    Renderar Module 1: Regulatory asset base valuation.
    
    Returns:
        Dict med användarens val (tom i placeholder)
    """
    config: Dict[str, Any] = {}
    
    st.subheader("1. Regulatory Asset Base Valuation")
    
    with st.expander("Parameters", expanded=False):
        st.info(
            "Asset valuation parameters (1.1.X, 1.2.X) kommer i framtida version.\n\n"
            "Inkluderar:\n"
            "- General scaling factor (1.1.1)\n"
            "- Asset type specific scaling factors (1.2.1-1.2.17)"
        )
    
    with st.expander("Variables", expanded=False):
        st.info(
            "Asset quantities (10.X) och asset values (11.X) kommer i framtida version.\n\n"
            "Kräver KENT-filuppladdning för att ändra."
        )
    
    return config
