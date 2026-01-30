"""
M2 Depreciation - Output Display

Variable-IDs: 20.1.1/20.1.2 (total), 20.2-20.18 (per category)
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
    """Render M2 depreciation outputs."""
    
    st.markdown("**20.1 Total depreciation**")
    st.caption("Depreciation breakdown requires KENT capital base data.")
    
    st.markdown("""
| Variable-ID | Description | Status |
|-------------|-------------|--------|
| 20.1.1 | Total depreciation (ordinary) | Requires KENT |
| 20.1.2 | Total depreciation (tail) | Requires KENT |
| 20.2-20.18 | Per-category breakdown | Requires KENT |
    """)
