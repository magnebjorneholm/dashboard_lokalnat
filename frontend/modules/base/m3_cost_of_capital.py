"""
Module 3: Cost of Capital

Hanterar WACC och relaterade parametrar.
Parameter-IDs: 3.1.X (base), 3.2.X (derived), 3.3-3.6 (adjustments)
Variable-IDs: 30.X
"""

import streamlit as st
import pandas as pd
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

# Baseline härledda parametrar (beräknade från CAPM baseline)
BASELINE_DERIVED = {
    "cost_of_equity_nominal": 0.0645,   # Re: Rf + βE × MRP
    "cost_of_debt_nominal": 0.0401,     # Rd: Rf + credit spread
    "debt_ratio": 0.36,                  # S: skuldsättningsgrad
    "tax_rate": 0.206,                   # τ: bolagsskatt
    "inflation": 0.0202,                 # π: CPIF
    "wacc_nominal_pre_tax": 0.0664,      # WACC nominell
    "wacc_real_pre_tax": BASELINE_WACC,  # 0.0453
}

# Kundtyper för AIT/AIF
SNI_LABELS = {
    1: "Jordbruk",
    2: "Industri",
    3: "Handel/tjänster",
    4: "Offentlig verksamhet",
    5: "Hushåll",
    6: "Gränspunkt",
}

# Baseline-värden för incitamentparametrar
BASELINE_INCENTIVE = {
    "enable_quality": True,
    "enable_netloss": True,
    "enable_load": True,
    "adj_max_agg": 1/3,
    "adj_max_cemi4": 0.25,
    "sharing_netloss": 0.75,
    "kpi": {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546},
    "k_nf": {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44},
    "ait_costs": {
        "o_1": 34.35, "o_2": 159.96, "o_3": 175.06,
        "o_4": 96.97, "o_5": 5.84, "o_6": 96.01,
        "a_1": 14.10, "a_2": 76.00, "a_3": 79.31,
        "a_4": 43.70, "a_5": 4.98, "a_6": 45.16,
    },
    "aif_costs": {
        "o_1": 9.78, "o_2": 70.75, "o_3": 17.78,
        "o_4": 7.65, "o_5": 1.95, "o_6": 22.18,
        "a_1": 1.72, "a_2": 20.71, "a_3": 5.94,
        "a_4": 0.92, "a_5": 1.85, "a_6": 7.08,
    },
}


def _calculate_wacc_from_derived(
    cost_of_equity: float,
    cost_of_debt: float,
    debt_ratio: float,
    tax_rate: float,
    inflation: float
) -> tuple[float, float]:
    """
    Beräknar WACC från härledda parametrar.
    
    Formler:
        WACC_nom_efter_skatt = (1 - S) × Re + S × Rd × (1 - τ)
        WACC_nom_före_skatt  = WACC_nom_efter_skatt / (1 - τ)
        WACC_real            = (1 + WACC_nom_före_skatt) / (1 + π) - 1
    
    Args:
        cost_of_equity: Re - Kostnad eget kapital (nominell, efter skatt)
        cost_of_debt: Rd - Kostnad skuld (nominell, före skatt)
        debt_ratio: S - Skuldsättningsgrad D/(D+E)
        tax_rate: τ - Bolagsskatt
        inflation: π - Inflation (CPIF)
    
    Returns:
        Tuple (wacc_nominal_pre_tax, wacc_real_pre_tax)
    """
    # WACC efter skatt (viktad genomsnitt)
    wacc_nominal_after_tax = (
        (1 - debt_ratio) * cost_of_equity + 
        debt_ratio * cost_of_debt * (1 - tax_rate)
    )
    
    # Konvertera till före skatt
    wacc_nominal_pre_tax = wacc_nominal_after_tax / (1 - tax_rate)
    
    # Fisher: nominell → real
    wacc_real_pre_tax = (1 + wacc_nominal_pre_tax) / (1 + inflation) - 1
    
    return wacc_nominal_pre_tax, wacc_real_pre_tax


def render() -> Dict[str, Any]:
    """
    Renderar Module 3: Cost of capital.
    
    Tre inmatningsmetoder via radioknapp:
    1. CAPM-komponenter - beräkna från basparametrar
    2. Härledda parametrar - ändra Re, Rd, S, τ, π direkt
    3. Direktinmatning - ange WACC direkt
    
    Returns:
        Dict med användarens val. Keys:
        - wacc_override: Nytt WACC-värde eller None för baseline
    """
    config: Dict[str, Any] = {}
    
    st.subheader("3. Cost of Capital")
    
    # Initiera session state
    if f"{MODULE_KEY}_current_wacc" not in st.session_state:
        st.session_state[f"{MODULE_KEY}_current_wacc"] = BASELINE_WACC
    
    # --- Aktuellt värde (alltid synligt) ---
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if abs(current_wacc - BASELINE_WACC) < 0.0001:
            st.info(f"**Aktuellt WACC:** {format_percent(current_wacc)} (baseline)")
        else:
            delta = current_wacc - BASELINE_WACC
            delta_str = f"{delta*100:+.2f}".replace(".", ",")
            st.success(f"**Aktuellt WACC:** {format_percent(current_wacc)} ({delta_str} pp från baseline)")
    
    with col2:
        if abs(current_wacc - BASELINE_WACC) > 0.0001:
            if st.button("Återställ baseline", key=f"{MODULE_KEY}_reset"):
                st.session_state[f"{MODULE_KEY}_current_wacc"] = BASELINE_WACC
                st.rerun()
    
    st.divider()
    
    # === INMATNINGSMETOD VIA RADIO ===
    input_method = st.radio(
        "Inmatningsmetod",
        options=["CAPM-komponenter", "Härledda parametrar", "Direktinmatning"],
        index=0,
        key=f"{MODULE_KEY}_input_method",
        horizontal=True,
        help="Välj hur du vill ange WACC"
    )
    
    # === 1. CAPM-KOMPONENTER ===
    if input_method == "CAPM-komponenter":
        _render_capm_section()
    
    # === 2. HÄRLEDDA PARAMETRAR ===
    elif input_method == "Härledda parametrar":
        _render_derived_section()
    
    # === 3. DIREKTINMATNING ===
    else:
        _render_direct_section()
    
    # --- Sätt config baserat på aktuellt värde ---
    current_wacc = st.session_state[f"{MODULE_KEY}_current_wacc"]
    if abs(current_wacc - BASELINE_WACC) > 0.0001:
        config["wacc_override"] = current_wacc
    
    return config


def _render_capm_section() -> None:
    """Renderar 3.1 CAPM-komponenter."""
    st.markdown("##### 3.1 CAPM-komponenter")
    st.caption("Beräkna WACC från underliggande parametrar")
    
    col1, col2 = st.columns(2)
    
    with col1:
        debt_ratio = st.number_input(
            "3.1.1 Skuldsättningsgrad (S)",
            value=BASELINE_CAPM.debt_ratio,
            min_value=0.0,
            max_value=0.99,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_debt_ratio",
            help="Andel skuld av totalt kapital (D/(D+E))"
        )
        
        asset_beta = st.number_input(
            "3.1.2 Tillgångsbeta (βA)",
            value=BASELINE_CAPM.asset_beta,
            min_value=0.0,
            max_value=2.0,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_asset_beta",
            help="Systematisk risk för obelånade tillgångar"
        )
        
        risk_free_rate = st.number_input(
            "3.1.3 Riskfri ränta (Rf)",
            value=BASELINE_CAPM.risk_free_rate,
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_risk_free_rate",
            help="Baserad på 10-årig svensk statsobligation"
        )
        
        market_risk_premium = st.number_input(
            "3.1.4 Marknadsriskpremie (MRP)",
            value=BASELINE_CAPM.market_risk_premium,
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_market_risk_premium",
            help="Förväntad överavkastning mot riskfri ränta"
        )
    
    with col2:
        credit_risk_premium = st.number_input(
            "3.1.5 Kreditriskpremie",
            value=BASELINE_CAPM.credit_risk_premium,
            min_value=0.0,
            max_value=0.10,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_credit_risk_premium",
            help="Tillägg för företagsspecifik kreditrisk"
        )
        
        tax_rate = st.number_input(
            "3.1.6 Skattesats (τ)",
            value=BASELINE_CAPM.tax_rate,
            min_value=0.0,
            max_value=0.50,
            step=0.001,
            format="%.3f",
            key=f"{MODULE_KEY}_tax_rate",
            help="Bolagsskattesats"
        )
        
        inflation = st.number_input(
            "3.1.7 Inflation (π, CPIF)",
            value=BASELINE_CAPM.inflation,
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_inflation",
            help="Förväntad inflation"
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
        
        # Visa härledda parametrar (read-only)
        st.divider()
        st.markdown("##### 3.2 Härledda parametrar (beräknade)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("3.2.1 Aktiebeta (βE)", f"{result.equity_beta:.4f}")
            st.metric("3.2.2 Kostnad eget kapital (Re)", format_percent(result.cost_of_equity_nominal))
        with col2:
            st.metric("3.2.3 Kostnad skuld (Rd)", format_percent(result.cost_of_debt_nominal))
            st.metric("3.2.4 WACC nominell", format_percent(result.wacc_nominal_pre_tax))
        
        st.metric("**3.2.5 WACC real före skatt**", format_percent(calculated_wacc))
        
        # Knapp för att använda beräknat värde
        if st.button("Använd detta WACC", key=f"{MODULE_KEY}_use_capm", type="primary"):
            st.session_state[f"{MODULE_KEY}_current_wacc"] = calculated_wacc
            st.rerun()
            
    except ValueError as e:
        st.error(f"Beräkningsfel: {e}")


def _render_derived_section() -> None:
    """
    Renderar 3.2 Härledda parametrar för direktinmatning.
    
    Inputs: Re, Rd, S, τ, π
    Output: WACC nominell och real (beräknade)
    """
    st.markdown("##### 3.2 Härledda parametrar")
    st.caption("Ange kostnader för eget kapital och skuld direkt")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cost_of_equity = st.number_input(
            "3.2.2 Kostnad eget kapital (Re)",
            value=BASELINE_DERIVED["cost_of_equity_nominal"],
            min_value=0.0,
            max_value=0.30,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_derived_cost_equity",
            help="Nominell kostnad för eget kapital (efter skatt). Baseline: Rf + βE × MRP"
        )
        
        cost_of_debt = st.number_input(
            "3.2.3 Kostnad skuld (Rd)",
            value=BASELINE_DERIVED["cost_of_debt_nominal"],
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_derived_cost_debt",
            help="Nominell kostnad för skuld (före skatt). Baseline: Rf + kreditriskpremie"
        )
        
        debt_ratio = st.number_input(
            "3.1.1 Skuldsättningsgrad (S)",
            value=BASELINE_DERIVED["debt_ratio"],
            min_value=0.0,
            max_value=0.99,
            step=0.01,
            format="%.2f",
            key=f"{MODULE_KEY}_derived_debt_ratio",
            help="Andel skuld av totalt kapital D/(D+E)"
        )
    
    with col2:
        tax_rate = st.number_input(
            "3.1.6 Skattesats (τ)",
            value=BASELINE_DERIVED["tax_rate"],
            min_value=0.0,
            max_value=0.50,
            step=0.001,
            format="%.3f",
            key=f"{MODULE_KEY}_derived_tax_rate",
            help="Bolagsskattesats"
        )
        
        inflation = st.number_input(
            "3.1.7 Inflation (π, CPIF)",
            value=BASELINE_DERIVED["inflation"],
            min_value=0.0,
            max_value=0.20,
            step=0.001,
            format="%.4f",
            key=f"{MODULE_KEY}_derived_inflation",
            help="Förväntad inflation för Fisher-omräkning"
        )
    
    # Beräkna WACC från härledda parametrar
    wacc_nominal, wacc_real = _calculate_wacc_from_derived(
        cost_of_equity=cost_of_equity,
        cost_of_debt=cost_of_debt,
        debt_ratio=debt_ratio,
        tax_rate=tax_rate,
        inflation=inflation
    )
        
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("3.2.4 WACC nominell före skatt", format_percent(wacc_nominal))
    with col2:
        delta = wacc_real - BASELINE_WACC
        st.metric(
            "3.2.5 WACC real före skatt", 
            format_percent(wacc_real),
            delta=f"{delta*100:+.2f} pp" if abs(delta) > 0.0001 else None
        )
    
    if st.button("Använd detta WACC", key=f"{MODULE_KEY}_use_derived", type="primary"):
        st.session_state[f"{MODULE_KEY}_current_wacc"] = wacc_real
        st.rerun()


def _render_direct_section() -> None:
    """Renderar direktinmatning av WACC."""
    st.markdown("##### 3.2.5 Direktinmatning")
    st.caption("Ange WACC direkt utan mellansteg")
    
    direct_wacc = st.number_input(
        "Real WACC före skatt",
        value=BASELINE_WACC,
        min_value=0.01,
        max_value=0.15,
        step=0.0001,
        format="%.4f",
        key=f"{MODULE_KEY}_direct_wacc",
        help="Ange värde direkt (t.ex. 0.0500 för 5%)"
    )
    
    # Visa som procent
    st.caption(f"= {format_percent(direct_wacc)}")
    
    # Visa baseline-jämförelse
    if abs(direct_wacc - BASELINE_WACC) > 0.0001:
        delta = direct_wacc - BASELINE_WACC
        st.caption(f":orange[{delta*100:+.2f} procentenheter från baseline ({format_percent(BASELINE_WACC)})]")
    else:
        st.caption(f"= baseline ({format_percent(BASELINE_WACC)})")
    
    if st.button("Använd detta WACC", key=f"{MODULE_KEY}_use_direct", type="primary"):
        st.session_state[f"{MODULE_KEY}_current_wacc"] = direct_wacc
        st.rerun()


# =============================================================================
# INCITAMENTJUSTERINGAR (3.3-3.6)
# =============================================================================

def render_quality_adjustments() -> Dict[str, Any]:
    """
    Renderar Quality Adjustments (3.3-3.6).
    
    Alla inputs visas alltid. Endast värden som skiljer sig från baseline
    sparas till config.
    
    Returns:
        Dict med ändrade incitamentparametrar
    """
    config: Dict[str, Any] = {}
    
    st.subheader("3.3-3.6 Incitamentjusteringar")
    st.caption("Justering av kapitalkostnad baserat på kvalitet, nätförlust och belastning")
    
    # === AKTIVERA/INAKTIVERA ===
    st.markdown("##### Aktivera incitament")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        enable_quality = st.checkbox(
            "Kvalitetsincitament",
            value=BASELINE_INCENTIVE["enable_quality"],
            key=f"{MODULE_KEY_QA}_enable_quality",
            help="Aktivera kvalitetsjustering baserat på AIT/AIF"
        )
        if enable_quality != BASELINE_INCENTIVE["enable_quality"]:
            config["enable_quality"] = enable_quality
    
    with col2:
        enable_netloss = st.checkbox(
            "Nätförlustincitament",
            value=BASELINE_INCENTIVE["enable_netloss"],
            key=f"{MODULE_KEY_QA}_enable_netloss",
            help="Aktivera justering för nätförluster"
        )
        if enable_netloss != BASELINE_INCENTIVE["enable_netloss"]:
            config["enable_netloss"] = enable_netloss
    
    with col3:
        enable_load = st.checkbox(
            "Belastningsincitament",
            value=BASELINE_INCENTIVE["enable_load"],
            key=f"{MODULE_KEY_QA}_enable_load",
            help="Aktivera justering för belastningsutnyttjande"
        )
        if enable_load != BASELINE_INCENTIVE["enable_load"]:
            config["enable_load"] = enable_load
    
    st.divider()
    
    # === 3.3 KVALITETSINCITAMENT ===
    with st.expander("3.3 Kvalitetsincitament", expanded=False):
        _render_quality_section(config)
    
    # === 3.4 NÄTFÖRLUSTINCITAMENT ===
    with st.expander("3.4 Nätförlustincitament", expanded=False):
        _render_netloss_section(config)
    
    # === 3.5 BELASTNINGSINCITAMENT ===
    with st.expander("3.5 Belastningsincitament", expanded=False):
        st.info("Belastningsincitamentet beräknas automatiskt baserat på utnyttjningsgrad.\n\n"
                "Formel: `(ug_obs - ug_norm) × k_upstream`\n\n"
                "Inga justerbara parametrar utöver on/off.")
    
    # === 3.6 BEGRÄNSNINGAR (CAPS) ===
    with st.expander("3.6 Begränsningar", expanded=False):
        _render_caps_section(config)
    
    # === 3.7 KPI-FAKTORER (avancerat) ===
    with st.expander("3.7 KPI-faktorer (avancerat)", expanded=False):
        _render_kpi_section(config)
    
    return config


def _render_quality_section(config: Dict[str, Any]) -> None:
    """Renderar 3.3 Kvalitetsincitament."""
    st.markdown("Parametrar för kvalitetsjustering baserat på AIT/AIF.")
    
    # CEMI-korrigering
    st.markdown("###### CEMI-korrigering")
    adj_max_cemi4 = st.slider(
        "Max CEMI4-korrigering",
        min_value=0.0,
        max_value=1.0,
        value=BASELINE_INCENTIVE["adj_max_cemi4"],
        step=0.05,
        format="%.2f",
        key=f"{MODULE_KEY_QA}_adj_max_cemi4",
        help="Andel av incitament som kan reduceras vid försämrad CEMI4"
    )
    
    if abs(adj_max_cemi4 - BASELINE_INCENTIVE["adj_max_cemi4"]) > 0.001:
        config["adj_max_cemi4"] = adj_max_cemi4
        st.caption(f":orange[Ändrat] från baseline ({BASELINE_INCENTIVE['adj_max_cemi4']:.2f})")
    else:
        st.caption(f"= baseline ({BASELINE_INCENTIVE['adj_max_cemi4']:.2f})")
    
    st.divider()
    
    # AIT-kostnader
    st.markdown("###### AIT-kostnader (kr/kWh)")
    ait_df = _create_cost_dataframe("ait")
    edited_ait = st.data_editor(
        ait_df,
        key=f"{MODULE_KEY_QA}_ait_editor",
        use_container_width=True,
        hide_index=False,
        column_config={
            "Oaviserade": st.column_config.NumberColumn(format="%.2f"),
            "Aviserade": st.column_config.NumberColumn(format="%.2f"),
        }
    )
    ait_costs = _dataframe_to_cost_dict(edited_ait, "ait")
    if ait_costs != BASELINE_INCENTIVE["ait_costs"]:
        config["ait_costs"] = ait_costs
        st.caption(":orange[AIT-kostnader ändrade från baseline]")
    
    st.divider()
    
    # AIF-kostnader
    st.markdown("###### AIF-kostnader (kr/kW)")
    aif_df = _create_cost_dataframe("aif")
    edited_aif = st.data_editor(
        aif_df,
        key=f"{MODULE_KEY_QA}_aif_editor",
        use_container_width=True,
        hide_index=False,
        column_config={
            "Oaviserade": st.column_config.NumberColumn(format="%.2f"),
            "Aviserade": st.column_config.NumberColumn(format="%.2f"),
        }
    )
    aif_costs = _dataframe_to_cost_dict(edited_aif, "aif")
    if aif_costs != BASELINE_INCENTIVE["aif_costs"]:
        config["aif_costs"] = aif_costs
        st.caption(":orange[AIF-kostnader ändrade från baseline]")


def _render_netloss_section(config: Dict[str, Any]) -> None:
    """Renderar 3.4 Nätförlustincitament."""
    st.markdown("Parametrar för nätförlustjustering.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sharing = st.slider(
            "Delningsfaktor",
            min_value=0.0,
            max_value=1.0,
            value=BASELINE_INCENTIVE["sharing_netloss"],
            step=0.05,
            format="%.2f",
            key=f"{MODULE_KEY_QA}_sharing_netloss",
            help="Andel av vinst/förlust som tillfaller företaget"
        )
        
        if abs(sharing - BASELINE_INCENTIVE["sharing_netloss"]) > 0.001:
            config["sharing_netloss"] = sharing
            st.caption(f":orange[Ändrat] från baseline ({BASELINE_INCENTIVE['sharing_netloss']:.2f})")
        else:
            st.caption(f"= baseline ({BASELINE_INCENTIVE['sharing_netloss']:.2f})")
    
    with col2:
        st.markdown("**Elpris (K_NF) per år**")
        k_nf_df = _create_yearly_dataframe("k_nf", "Elpris (kr/MWh)")
        edited_k_nf = st.data_editor(
            k_nf_df,
            key=f"{MODULE_KEY_QA}_k_nf_editor",
            use_container_width=True,
            hide_index=False,
            column_config={
                "Elpris (kr/MWh)": st.column_config.NumberColumn(format="%.2f"),
            }
        )
        k_nf_dict = _dataframe_to_yearly_dict(edited_k_nf, "Elpris (kr/MWh)")
        if k_nf_dict != BASELINE_INCENTIVE["k_nf"]:
            config["k_nf"] = k_nf_dict
            st.caption(":orange[Elpris ändrat från baseline]")


def _render_caps_section(config: Dict[str, Any]) -> None:
    """Renderar 3.6 Begränsningar."""
    st.markdown("Max incitamentjustering som andel av avkastning.")
    
    adj_agg = st.slider(
        "Max totalt per år",
        min_value=0.0,
        max_value=1.0,
        value=BASELINE_INCENTIVE["adj_max_agg"],
        step=0.05,
        format="%.3f",
        key=f"{MODULE_KEY_QA}_adj_max_agg",
        help="Max total incitamentjustering per år"
    )
    
    if abs(adj_agg - BASELINE_INCENTIVE["adj_max_agg"]) > 0.001:
        config["adj_max_agg"] = adj_agg
        st.caption(f":orange[Ändrat] från baseline ({BASELINE_INCENTIVE['adj_max_agg']:.3f})")
    else:
        st.caption(f"= baseline ({BASELINE_INCENTIVE['adj_max_agg']:.3f} ≈ 1/3)")


def _render_kpi_section(config: Dict[str, Any]) -> None:
    """Renderar 3.7 KPI-faktorer."""
    st.markdown("KPI-faktorer för prisjustering till 2022 års priser.")
    
    kpi_df = _create_yearly_dataframe("kpi", "KPI-faktor")
    edited_kpi = st.data_editor(
        kpi_df,
        key=f"{MODULE_KEY_QA}_kpi_editor",
        use_container_width=True,
        hide_index=False,
        column_config={
            "KPI-faktor": st.column_config.NumberColumn(format="%.4f"),
        }
    )
    kpi_dict = _dataframe_to_yearly_dict(edited_kpi, "KPI-faktor")
    if kpi_dict != BASELINE_INCENTIVE["kpi"]:
        config["kpi"] = kpi_dict
        st.caption(":orange[KPI-faktorer ändrade från baseline]")
    else:
        st.caption(f"= baseline ({BASELINE_INCENTIVE['kpi'][2024]:.4f} alla år)")


# =============================================================================
# HJÄLPFUNKTIONER
# =============================================================================

def _create_cost_dataframe(cost_type: str) -> pd.DataFrame:
    """Skapar DataFrame för AIT/AIF-kostnader."""
    baseline = BASELINE_INCENTIVE[f"{cost_type}_costs"]
    
    data = []
    for sni, label in SNI_LABELS.items():
        data.append({
            "Kundtyp": label,
            "Oaviserade": baseline[f"o_{sni}"],
            "Aviserade": baseline[f"a_{sni}"],
        })
    
    df = pd.DataFrame(data)
    df = df.set_index("Kundtyp")
    return df


def _dataframe_to_cost_dict(df: pd.DataFrame, cost_type: str) -> Dict[str, float]:
    """Konverterar DataFrame tillbaka till cost dict."""
    result = {}
    label_to_sni = {v: k for k, v in SNI_LABELS.items()}
    
    for label in df.index:
        sni = label_to_sni.get(label)
        if sni is not None:
            result[f"o_{sni}"] = float(df.loc[label, "Oaviserade"])
            result[f"a_{sni}"] = float(df.loc[label, "Aviserade"])
    
    return result


def _create_yearly_dataframe(param_key: str, column_name: str) -> pd.DataFrame:
    """Skapar DataFrame för per-år parametrar."""
    baseline = BASELINE_INCENTIVE[param_key]
    
    data = []
    for year in [2024, 2025, 2026, 2027]:
        data.append({
            "År": year,
            column_name: baseline[year],
        })
    
    df = pd.DataFrame(data)
    df = df.set_index("År")
    return df


def _dataframe_to_yearly_dict(df: pd.DataFrame, column_name: str) -> Dict[int, float]:
    """Konverterar DataFrame tillbaka till yearly dict."""
    result = {}
    for year in df.index:
        result[int(year)] = float(df.loc[year, column_name])
    return result