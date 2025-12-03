"""
DEA konfiguration UI
Extraherat från effektiviseringskrav.py
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional


def render_dea_config_ui(
    df: pd.DataFrame,
    current_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Renderar UI för DEA-konfiguration.
    
    Args:
        df: DataFrame med DEA-data
        current_config: Nuvarande konfiguration (optional)
        
    Returns:
        Dict med DEA-parametrar
    """
    if current_config is None:
        current_config = {}
    
    st.markdown("**DEA-modell konfiguration**")
    
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Variabler**")
        
        default_inputs = current_config.get('input_cols', [c for c in ["CAPEX", "OPEXp"] if c in all_inputs])
        input_cols = st.multiselect(
            "Inputvariabler",
            all_inputs,
            default=default_inputs,
            help="Kostnadsvariabler som ska ingå i analysen"
        )
        
        default_outputs = current_config.get('output_cols', all_outputs)
        output_cols = st.multiselect(
            "Outputvariabler",
            all_outputs,
            default=default_outputs,
            help="Outputvariabler som beskriver nätets storlek och aktivitet"
        )
    
    with col2:
        st.markdown("**Modellinställningar**")
        
        default_rts = current_config.get('rts', 'crs')
        rts = st.selectbox(
            "Skalavkastning",
            ["crs", "vrs"],
            index=0 if default_rts == 'crs' else 1,
            help="CRS = Constant Returns to Scale, VRS = Variable Returns to Scale"
        )
        
        default_filter = current_config.get('outlier_filter', True)
        outlier_filter = st.checkbox(
            "Filtrera outliers",
            value=default_filter,
            help="Exkluderar extremvärden från analysen"
        )
        
        if outlier_filter:
            q_lower = st.slider(
                "Nedre kvartil (%)",
                0.0, 50.0, 25.0,
                help="För outlier-detektion"
            )
            q_upper = st.slider(
                "Övre kvartil (%)",
                50.0, 100.0, 75.0,
                help="För outlier-detektion"
            )
            multiplier = st.number_input(
                "IQR-multiplikator",
                1.0, 5.0, 2.0, 0.1,
                help="För outlier-detektion"
            )
        else:
            q_lower, q_upper, multiplier = 25.0, 75.0, 2.0
    
    return {
        'input_cols': input_cols,
        'output_cols': output_cols,
        'rts': rts,
        'outlier_filter': outlier_filter,
        'q_lower': q_lower,
        'q_upper': q_upper,
        'multiplier': multiplier
    }