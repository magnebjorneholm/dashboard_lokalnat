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
MODULE_KEY_QA = "m3_quality_adjustments"

# Baseline CAPM-parametrar (från User Manual tabell 6)
BASELINE_CAPM = CAPMInputs()

# Baseline incitament-parametrar
BASELINE_INCENTIVE = {
    "kpi": 17.0,           # kr/kW
    "k_nf": 0.50,          # kr/kWh
    "sharing_netloss": 0.5,
    "adj_max_agg": 1/3,
    "adj_max_cemi4": 1/3,
}


def render() -> Dict[str, Any]:
    """
    Renderar Module 3: Cost of capital.
    
    Användaren kan antingen:
    1. Ändra CAPM-komponenter och beräkna WACC
    2. Ange WACC direkt
    3. Justera incitamentparametrar (kvalitet, nätförlust, belastning)
    
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
    
    # --- Sätt config baserat på aktuellt värde ---
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    if current_wacc != BASELINE_WACC:
        config["wacc_override"] = current_wacc
    
    return config


def render_quality_adjustments() -> Dict[str, Any]:
    """
    Renderar Quality Adjustments (3.3-3.6).
    
    Incitamentjusteringar för:
    - 3.3 Kvalitetsincitament
    - 3.4 Nätförlustincitament  
    - 3.5 Begränsningar
    - 3.6 Aktivera/inaktivera
    
    Returns:
        Dict med användarens val för incitamentparametrar
    """
    config: Dict[str, Any] = {}
    
    st.subheader("3.3-3.6 Incitamentjusteringar")
    st.caption("Justering av kapitalkostnad baserat på kvalitet, nätförlust och belastning")
    
    # Aktivera/inaktivera incitament
    st.markdown("##### Aktivera incitament")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        enable_quality = st.checkbox(
            "3.6.1 Kvalitetsincitament",
            value=True,
            key=f"{MODULE_KEY_QA}_enable_quality",
            help="Aktivera kvalitetsjustering baserat på AIT/AIF"
        )
        config["enable_quality"] = enable_quality
    
    with col2:
        enable_netloss = st.checkbox(
            "3.6.2 Nätförlustincitament",
            value=True,
            key=f"{MODULE_KEY_QA}_enable_netloss",
            help="Aktivera justering för nätförluster"
        )
        config["enable_netloss"] = enable_netloss
    
    with col3:
        enable_load = st.checkbox(
            "3.6.3 Belastningsincitament",
            value=True,
            key=f"{MODULE_KEY_QA}_enable_load",
            help="Aktivera justering för belastningsutnyttjande"
        )
        config["enable_load"] = enable_load
    
    st.divider()
    
    # 3.3 Kvalitetsincitament
    with st.expander("3.3 Kvalitetsincitament", expanded=False):
        st.markdown("Parametrar för kvalitetsjustering baserat på AIT/AIF.")
        
        kpi_changed = st.checkbox(
            "Ändra KPI från baseline",
            key=f"{MODULE_KEY_QA}_kpi_changed"
        )
        
        if kpi_changed:
            kpi = st.number_input(
                "3.3.1 Kvalitetsprisindex (KPI)",
                value=BASELINE_INCENTIVE["kpi"],
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                format="%.1f",
                key=f"{MODULE_KEY_QA}_kpi",
                help="Pris per kW för kvalitetsjustering (kr/kW)"
            )
            config["kpi"] = kpi
            st.caption(f"Baseline: {BASELINE_INCENTIVE['kpi']} kr/kW")
        else:
            st.info(f"KPI = {BASELINE_INCENTIVE['kpi']} kr/kW (baseline)")
    
    # 3.4 Nätförlustincitament
    with st.expander("3.4 Nätförlustincitament", expanded=False):
        st.markdown("Parametrar för nätförlustjustering.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            k_nf_changed = st.checkbox(
                "Ändra nätförlustkostnad",
                key=f"{MODULE_KEY_QA}_k_nf_changed"
            )
            
            if k_nf_changed:
                k_nf = st.number_input(
                    "3.4.1 Nätförlustkostnad (K_NF)",
                    value=BASELINE_INCENTIVE["k_nf"],
                    min_value=0.0,
                    max_value=5.0,
                    step=0.01,
                    format="%.2f",
                    key=f"{MODULE_KEY_QA}_k_nf",
                    help="Kostnad per kWh nätförlust (kr/kWh)"
                )
                config["k_nf"] = k_nf
                st.caption(f"Baseline: {BASELINE_INCENTIVE['k_nf']} kr/kWh")
            else:
                st.info(f"K_NF = {BASELINE_INCENTIVE['k_nf']} kr/kWh (baseline)")
        
        with col2:
            sharing_changed = st.checkbox(
                "Ändra delningsfaktor",
                key=f"{MODULE_KEY_QA}_sharing_changed"
            )
            
            if sharing_changed:
                sharing = st.number_input(
                    "3.4.2 Delningsfaktor nätförlust",
                    value=BASELINE_INCENTIVE["sharing_netloss"],
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    format="%.2f",
                    key=f"{MODULE_KEY_QA}_sharing_netloss",
                    help="Andel som delas (0-1)"
                )
                config["sharing_netloss"] = sharing
                st.caption(f"Baseline: {BASELINE_INCENTIVE['sharing_netloss']}")
            else:
                st.info(f"Delning = {BASELINE_INCENTIVE['sharing_netloss']} (baseline)")
    
    # 3.5 Begränsningar
    with st.expander("3.5 Begränsningar för incitament", expanded=False):
        st.markdown("Max incitamentjustering som andel av avkastning.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            adj_agg_changed = st.checkbox(
                "Ändra max aggregerat",
                key=f"{MODULE_KEY_QA}_adj_agg_changed"
            )
            
            if adj_agg_changed:
                adj_agg = st.number_input(
                    "3.5.1 Max aggregerat incitament",
                    value=BASELINE_INCENTIVE["adj_max_agg"],
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    format="%.3f",
                    key=f"{MODULE_KEY_QA}_adj_max_agg",
                    help="Max total incitamentjustering (andel av avkastning)"
                )
                config["adj_max_agg"] = adj_agg
                st.caption(f"Baseline: {BASELINE_INCENTIVE['adj_max_agg']:.3f} (1/3)")
            else:
                st.info(f"Max agg = {BASELINE_INCENTIVE['adj_max_agg']:.3f} (1/3) (baseline)")
        
        with col2:
            adj_cemi_changed = st.checkbox(
                "Ändra max per delincitament",
                key=f"{MODULE_KEY_QA}_adj_cemi_changed"
            )
            
            if adj_cemi_changed:
                adj_cemi = st.number_input(
                    "3.5.2 Max per delincitament",
                    value=BASELINE_INCENTIVE["adj_max_cemi4"],
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    format="%.3f",
                    key=f"{MODULE_KEY_QA}_adj_max_cemi4",
                    help="Max för enskilt incitament (andel av avkastning)"
                )
                config["adj_max_cemi4"] = adj_cemi
                st.caption(f"Baseline: {BASELINE_INCENTIVE['adj_max_cemi4']:.3f} (1/3)")
            else:
                st.info(f"Max per = {BASELINE_INCENTIVE['adj_max_cemi4']:.3f} (1/3) (baseline)")
    
    return config