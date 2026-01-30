"""
M1 Regulatory Asset Base Valuation - Output Display

Variable-IDs: 11.1 (total), 11.2-11.18 (per category)
Requires KENT capital base data for detailed breakdown.
"""

import streamlit as st
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any]
) -> None:
    """Render M1 asset base outputs."""
    
    st.markdown("**11.1 Total asset value**")
    st.caption("Per-category asset valuation requires KENT capital base data.")
    st.info("Upload a KENT file in Configure to see detailed asset breakdown (11.2-11.18).")
