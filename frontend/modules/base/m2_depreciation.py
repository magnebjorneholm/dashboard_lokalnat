"""
Module 2: Depreciation

Placeholder för framtida implementation.
Parameter-IDs: 2.X.1 (ordinary), 2.X.2 (tail)
Variable-IDs: 20.X
"""

import streamlit as st
from typing import Dict, Any

MODULE_KEY = "m2_depreciation"


def render() -> Dict[str, Any]:
    """
    Renderar Module 2: Depreciation.
    
    Returns:
        Dict med användarens val (tom i placeholder)
    """
    config: Dict[str, Any] = {}
    
    st.subheader("2. Depreciation")
    
    with st.expander("Parameters", expanded=False):
        st.info(
            "Asset lifetime parameters (2.X.1, 2.X.2) kommer i framtida version.\n\n"
            "Inkluderar:\n"
            "- Ordinary lifetime per asset type\n"
            "- Tail lifetime per asset type"
        )
    
    with st.expander("Variables", expanded=False):
        st.info(
            "Depreciation cost variables (20.X) kommer i framtida version.\n\n"
            "Beräknas automatiskt baserat på asset base och lifetimes."
        )
    
    return config
