"""
Results Summary komponent.

Visar sammanfattning av intäktsram med jämförelse mot baseline.
"""

import streamlit as st
from typing import Any

from frontend.common.formatting import format_tkr, format_percent, format_delta


def render(baseline: Any, case: Any) -> None:
    """
    Renderar sammanfattning med jämförelse mot baseline.
    
    Args:
        baseline: Baseline PipelineResult
        case: Case PipelineResult
    """
    st.subheader("Sammanfattning")
    
    # Hämta intäktsram
    baseline_ir = baseline.post_dea.user_intaktsram["Intaktsram_Total"]
    case_ir = case.post_dea.user_intaktsram["Intaktsram_Total"]
    delta = case_ir - baseline_ir
    delta_pct = (delta / baseline_ir) * 100 if baseline_ir else 0
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Intäktsram (case)",
            value=format_tkr(case_ir)
        )
    
    with col2:
        st.metric(
            label="Intäktsram (baseline)",
            value=format_tkr(baseline_ir)
        )
    
    with col3:
        delta_str = f"{delta_pct:+.2f}%".replace(".", ",")
        st.metric(
            label="Förändring",
            value=format_delta(delta),
            delta=delta_str
        )
    
    st.divider()
    
    # Effektiviseringskrav
    st.markdown("##### Effektiviseringskrav")
    
    baseline_eff = baseline.post_dea.user_effkrav_proc
    case_eff = case.post_dea.user_effkrav_proc
    eff_delta = case_eff - baseline_eff
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Effkrav (case)",
            value=format_percent(case_eff, 3)
        )
    
    with col2:
        st.metric(
            label="Effkrav (baseline)",
            value=format_percent(baseline_eff, 3)
        )
    
    with col3:
        eff_delta_str = f"{eff_delta*100:+.3f}%".replace(".", ",")
        st.metric(
            label="Förändring",
            value=eff_delta_str
        )
    
    # Effektivitet
    st.divider()
    st.markdown("##### DEA-effektivitet")
    
    baseline_efficiency = baseline.extraction.efficiency
    case_efficiency = case.extraction.efficiency
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label="Effektivitet (case)",
            value=format_percent(case_efficiency, 2)
        )
    
    with col2:
        st.metric(
            label="Effektivitet (baseline)",
            value=format_percent(baseline_efficiency, 2)
        )
    
    # Outlier-status
    if case.extraction.is_outlier:
        st.warning("Företaget klassas som outlier i DEA-analysen.")
    else:
        st.success("Företaget klassas INTE som outlier.")
