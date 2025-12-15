"""
Module Outputs komponent.

Visar detaljerad output per module.
"""

import streamlit as st
from typing import Any

from frontend.common.formatting import format_tkr, format_percent


def render(baseline: Any, case: Any) -> None:
    """
    Renderar detaljerad output per module.
    
    Args:
        baseline: Baseline PipelineResult
        case: Case PipelineResult
    """
    st.subheader("Detaljerad output")
    
    # Tabs för varje module-grupp
    tab1, tab2, tab3 = st.tabs([
        "Intäktsramskomponenter",
        "DEA-resultat", 
        "Case-konfiguration"
    ])
    
    with tab1:
        render_intaktsram_components(baseline, case)
    
    with tab2:
        render_dea_results(baseline, case)
    
    with tab3:
        render_case_config(case)


def render_intaktsram_components(baseline: Any, case: Any) -> None:
    """Renderar intäktsramskomponenter jämförelse."""
    
    baseline_ir = baseline.post_dea.user_intaktsram
    case_ir = case.post_dea.user_intaktsram
    
    # Huvudkomponenter
    components = [
        ("Påverkbara kostnader", "Paverkbara_Total"),
        ("Opåverkbara kostnader", "Opaverkbara_Total"),
        ("Effektiviseringskrav", "Effektiviseringskrav"),
        ("Löpande kostnader", "Lopande_Total"),
        ("Kapitalkostnader", "Kapitalkostnader_Total"),
        ("Intäktsram", "Intaktsram_Total"),
    ]
    
    st.markdown("##### Jämförelse: Case vs Baseline")
    
    # Tabell
    table_data = []
    for label, key in components:
        b_val = baseline_ir.get(key, 0)
        c_val = case_ir.get(key, 0)
        delta = c_val - b_val
        
        table_data.append({
            "Komponent": label,
            "Case (tkr)": f"{c_val:,.0f}".replace(",", " "),
            "Baseline (tkr)": f"{b_val:,.0f}".replace(",", " "),
            "Delta (tkr)": f"{delta:+,.0f}".replace(",", " "),
        })
    
    st.table(table_data)


def render_dea_results(baseline: Any, case: Any) -> None:
    """Renderar DEA-resultat."""
    
    st.markdown("##### DEA-effektivitet")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Case**")
        st.write(f"- Effektivitet: {format_percent(case.extraction.efficiency, 4)}")
        st.write(f"- Potential: {format_percent(case.extraction.potential, 4)}")
        st.write(f"- Outlier: {'Ja' if case.extraction.is_outlier else 'Nej'}")
    
    with col2:
        st.markdown("**Baseline**")
        st.write(f"- Effektivitet: {format_percent(baseline.extraction.efficiency, 4)}")
        st.write(f"- Potential: {format_percent(baseline.extraction.potential, 4)}")
        st.write(f"- Outlier: {'Ja' if baseline.extraction.is_outlier else 'Nej'}")
    
    # DEA-metod
    st.divider()
    st.markdown("##### DEA-specifikation")
    
    dea_method = case.dea.dea_method
    if dea_method == "dea":
        st.info("Custom DEA kördes med användarens specifikation.")
    else:
        st.info("Ei's baseline DEA-resultat användes.")


def render_case_config(case: Any) -> None:
    """Renderar case-konfiguration som användes."""
    
    st.markdown("##### Case-konfiguration")
    
    # Pre-DEA
    st.markdown("**Pre-DEA**")
    pre_dea = case.pre_dea if hasattr(case, 'pre_dea') else None
    if pre_dea:
        st.write(f"- Metod: {pre_dea.capex_method}")
        if pre_dea.capex_modified:
            st.write(f"- CAPEX modifierad: Ja")
    
    # DEA
    st.markdown("**DEA**")
    dea = case.dea if hasattr(case, 'dea') else None
    if dea:
        st.write(f"- Metod: {dea.dea_method}")
        st.write(f"- DEA kördes: {'Ja' if dea.dea_executed else 'Nej'}")
    
    # Post-DEA
    st.markdown("**Post-DEA**")
    post_dea = case.post_dea if hasattr(case, 'post_dea') else None
    if post_dea:
        effkrav = post_dea.user_effkrav_proc
        st.write(f"- Effektiviseringskrav: {format_percent(effkrav, 3)}")
