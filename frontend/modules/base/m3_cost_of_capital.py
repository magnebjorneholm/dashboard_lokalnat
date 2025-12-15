"""
Module 3: Cost of Capital

Hanterar WACC och relaterade parametrar.
Parameter-IDs: 3.1.X (base), 3.2.X (derived), 3.3-3.6 (adjustments)
Variable-IDs: 30.X
"""

import streamlit as st
from typing import Dict, Any

from calculations.wacc_calculations import (
    CAPMInputs,
    calculate_wacc,
    BASELINE_WACC,
)
from frontend.common.formatting import format_percent

MODULE_KEY = "m3_cost_of_capital"

# Baseline CAPM-parametrar (från User Manual tabell 6)
BASELINE_CAPM = CAPMInputs()


def render() -> Dict[str, Any]:
    """
    Renderar Module 3: Cost of capital.
    
    Användaren kan antingen:
    1. Ändra CAPM-komponenter och beräkna WACC
    2. Ange WACC direkt
    
    Returns:
        Dict med användarens val. Keys:
        - wacc_override: Nytt WACC-värde eller None för baseline
    """
    config: Dict[str, Any] = {}
    
    st.subheader("3. Cost of Capital")
    
    # Initiera session state för WACC
    if f"{MODULE_KEY}_current_wacc" not in st.session_state:
        st.session_state[f"{MODULE_KEY}_current_wacc"] = BASELINE_WACC
    if f"{MODULE_KEY}_input_mode" not in st.session_state:
        st.session_state[f"{MODULE_KEY}_input_mode"] = "baseline"  # baseline, capm, direct
    
    # --- Aktuellt värde (alltid synligt) ---
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if current_wacc == BASELINE_WACC:
            st.info(f"**Aktuellt WACC:** {format_percent(current_wacc)} (baseline)")
        else:
            delta = current_wacc - BASELINE_WACC
            delta_str = f"{delta*100:+.2f}".replace(".", ",")
            st.success(f"**Aktuellt WACC:** {format_percent(current_wacc)} ({delta_str} pp från baseline)")
    
    with col2:
        if current_wacc != BASELINE_WACC:
            if st.button("Återställ baseline", key=f"{MODULE_KEY}_reset"):
                st.session_state[f"{MODULE_KEY}_current_wacc"] = BASELINE_WACC
                st.session_state[f"{MODULE_KEY}_input_mode"] = "baseline"
                st.rerun()
    
    # --- Input-metod ---
    with st.expander("3.1 CAPM-komponenter", expanded=False):
        st.markdown("Beräkna WACC från underliggande parametrar.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            debt_ratio = st.number_input(
                "3.1.1 Skuldsättningsgrad",
                value=BASELINE_CAPM.debt_ratio,
                min_value=0.0,
                max_value=0.99,
                step=0.01,
                format="%.2f",
                key=f"{MODULE_KEY}_debt_ratio",
                help="Andel skuld av totalt kapital (D/(D+E))"
            )
            
            asset_beta = st.number_input(
                "3.1.2 Tillgångsbeta",
                value=BASELINE_CAPM.asset_beta,
                min_value=0.0,
                max_value=2.0,
                step=0.01,
                format="%.2f",
                key=f"{MODULE_KEY}_asset_beta",
                help="Systematisk risk för obelånade tillgångar"
            )
            
            risk_free_rate = st.number_input(
                "3.1.3 Riskfri ränta",
                value=BASELINE_CAPM.risk_free_rate,
                min_value=0.0,
                max_value=0.20,
                step=0.001,
                format="%.3f",
                key=f"{MODULE_KEY}_risk_free_rate",
                help="Baserad på 10-årig svensk statsobligation"
            )
            
            market_risk_premium = st.number_input(
                "3.1.4 Marknadsriskpremie",
                value=BASELINE_CAPM.market_risk_premium,
                min_value=0.0,
                max_value=0.20,
                step=0.001,
                format="%.3f",
                key=f"{MODULE_KEY}_market_risk_premium",
                help="Förväntad meravkastning utöver riskfri ränta"
            )
        
        with col2:
            credit_risk_premium = st.number_input(
                "3.1.5 Kreditriskpremie",
                value=BASELINE_CAPM.credit_risk_premium,
                min_value=0.0,
                max_value=0.10,
                step=0.001,
                format="%.3f",
                key=f"{MODULE_KEY}_credit_risk_premium",
                help="Räntepåslag för företagsskuld"
            )
            
            tax_rate = st.number_input(
                "3.1.6 Bolagsskatt",
                value=BASELINE_CAPM.tax_rate,
                min_value=0.0,
                max_value=0.50,
                step=0.001,
                format="%.3f",
                key=f"{MODULE_KEY}_tax_rate",
                help="Svensk bolagsskattesats"
            )
            
            inflation = st.number_input(
                "3.1.7 Inflation (CPIF)",
                value=BASELINE_CAPM.inflation,
                min_value=-0.05,
                max_value=0.20,
                step=0.001,
                format="%.3f",
                key=f"{MODULE_KEY}_inflation",
                help="CPIF-prognos för omräkning till real nivå"
            )
        
        # Beräkna WACC från inputs
        capm_inputs = CAPMInputs(
            debt_ratio=debt_ratio,
            asset_beta=asset_beta,
            risk_free_rate=risk_free_rate,
            market_risk_premium=market_risk_premium,
            credit_risk_premium=credit_risk_premium,
            tax_rate=tax_rate,
            inflation=inflation,
        )
        
        try:
            result = calculate_wacc(capm_inputs)
            calculated_wacc = result.wacc_real_pre_tax
            
            # Visa mellansteg
            st.divider()
            st.markdown("##### 3.2 Härledda parametrar")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("3.2.1 Aktiebeta", f"{result.equity_beta:.3f}")
                st.metric("3.2.2 Kostnad eget kapital", format_percent(result.cost_of_equity_nominal))
            with col2:
                st.metric("3.2.3 Kostnad skuld", format_percent(result.cost_of_debt_nominal))
                st.metric("3.2.4 WACC nominell", format_percent(result.wacc_nominal_pre_tax))
            
            st.metric("**3.2.5 WACC real före skatt**", format_percent(calculated_wacc))
            
            # Knapp för att använda beräknat värde
            if st.button("Använd detta WACC", key=f"{MODULE_KEY}_use_capm", type="primary"):
                st.session_state[f"{MODULE_KEY}_current_wacc"] = calculated_wacc
                st.session_state[f"{MODULE_KEY}_input_mode"] = "capm"
                st.rerun()
                
        except ValueError as e:
            st.error(f"Beräkningsfel: {e}")
    
    with st.expander("3.2.5 Direktinmatning WACC", expanded=False):
        st.markdown("Ange WACC direkt utan CAPM-beräkning.")
        
        direct_wacc = st.number_input(
            "Real WACC före skatt",
            value=BASELINE_WACC,
            min_value=0.01,
            max_value=0.15,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_direct_wacc",
            help="Ange värde direkt (t.ex. 0.0500 för 5%)"
        )
        
        st.caption(f"= {format_percent(direct_wacc)}")
        
        if st.button("Använd detta WACC", key=f"{MODULE_KEY}_use_direct", type="primary"):
            st.session_state[f"{MODULE_KEY}_current_wacc"] = direct_wacc
            st.session_state[f"{MODULE_KEY}_input_mode"] = "direct"
            st.rerun()
    
    with st.expander("Variables", expanded=False):
        st.info(
            "Capital cost variables (30.X) beräknas automatiskt.\n\n"
            "Output: Kapitalkostnad per tillgångstyp (ordinary + tail)"
        )
    
    with st.expander("Adjustment of cost of capital", expanded=False):
        st.info(
            "Quality adjustments (3.3-3.6) kommer i framtida version:\n"
            "- Network loss adjustment (3.4)\n"
            "- Utilization rate adjustment (3.5)\n"
            "- Interruption adjustment (3.6)"
        )
    
    # --- Sätt config baserat på aktuellt värde ---
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    if current_wacc != BASELINE_WACC:
        config["wacc_override"] = current_wacc
    
    return config