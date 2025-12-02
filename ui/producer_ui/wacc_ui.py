"""
WACC UI-komponenter
Extraherat från kapitalkostnad.py
"""

import streamlit as st
from typing import Dict, Any, Optional


def render_wacc_ui(
    current_values: Optional[Dict[str, float]] = None,
    baseline_wacc: float = 0.0453
) -> Dict[str, Any]:
    """
    Renderar UI för WACC-konfiguration från CAPM-komponenter.
    
    Args:
        current_values: Nuvarande parametervärden (optional)
        baseline_wacc: Baseline WACC-värde för jämförelse
        
    Returns:
        Dict med WACC-parametrar och beräknat WACC
    """
    if current_values is None:
        current_values = {}
    
    defaults = {
        'rf_nom': 0.0287,
        'mrp': 0.0668,
        'infl': 0.0202,
        'credit': 0.0114,
        'debt_share': 0.36,
        'tax_rate': 0.206,
        'beta_mode': 'β_A',
        'beta_a': 0.37,
        'beta_e': 0.54
    }
    
    current = {**defaults, **current_values}
    
    st.markdown("**CAPM-komponenter**")
    st.caption("Kalkylräntan beräknas från marknadspriser och riskmått")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rf_nom = st.number_input(
            "Riskfri ränta (nominell)",
            min_value=0.0,
            max_value=0.10,
            value=float(current['rf_nom']),
            step=0.0001,
            format="%.4f",
            help="KI:s 9-årsprognos för 10-årig svensk statsobligation",
            key="wacc_rf"
        )
        
        mrp = st.number_input(
            "Marknadens riskpremie",
            min_value=0.0,
            max_value=0.15,
            value=float(current['mrp']),
            step=0.0001,
            format="%.4f",
            help="Historisk avkastningsdifferens aktier vs. statsobligationer",
            key="wacc_mrp"
        )
        
        infl = st.number_input(
            "Inflation",
            min_value=0.0,
            max_value=0.10,
            value=float(current['infl']),
            step=0.0001,
            format="%.4f",
            help="KI:s inflationsprognos",
            key="wacc_infl"
        )
    
    with col2:
        beta_mode = st.radio(
            "Beta-typ",
            options=['β_A', 'β_E'],
            index=0 if current['beta_mode'] == 'β_A' else 1,
            help="β_A: Asset beta (avlevered), β_E: Equity beta (leverad)",
            key="wacc_beta_mode"
        )
        
        if beta_mode == 'β_A':
            beta_a = st.number_input(
                "Asset beta (β_A)",
                min_value=0.0,
                max_value=2.0,
                value=float(current['beta_a']),
                step=0.01,
                format="%.2f",
                help="Systematisk risk för avleverat företag",
                key="wacc_beta_a"
            )
            beta_e = current['beta_e']
        else:
            beta_e = st.number_input(
                "Equity beta (β_E)",
                min_value=0.0,
                max_value=2.0,
                value=float(current['beta_e']),
                step=0.01,
                format="%.2f",
                help="Systematisk risk för leverat företag",
                key="wacc_beta_e"
            )
            beta_a = current['beta_a']
    
    with col3:
        debt_share = st.number_input(
            "Skuldsättningsgrad",
            min_value=0.0,
            max_value=1.0,
            value=float(current['debt_share']),
            step=0.01,
            format="%.2f",
            help="Andel skuld i kapitalstrukturen",
            key="wacc_debt"
        )
        
        tax_rate = st.number_input(
            "Bolagsskatt",
            min_value=0.0,
            max_value=0.5,
            value=float(current['tax_rate']),
            step=0.001,
            format="%.3f",
            help="Bolagsskattesats",
            key="wacc_tax"
        )
        
        credit = st.number_input(
            "Kreditspread",
            min_value=0.0,
            max_value=0.05,
            value=float(current['credit']),
            step=0.0001,
            format="%.4f",
            help="Spread över riskfri ränta för skuld",
            key="wacc_credit"
        )
    
    try:
        from core.calculations import EiWaccInputs, ei_wacc_real_pre_tax
        
        wacc_inputs = EiWaccInputs(
            rf_nominal=rf_nom,
            mrp_nominal=mrp,
            inflation=infl,
            credit_spread=credit,
            debt_share=debt_share,
            tax_rate=tax_rate,
            beta_asset=beta_a if beta_mode == 'β_A' else None,
            beta_equity=beta_e if beta_mode == 'β_E' else None
        )
        
        Re, Rd, Wn, wacc_calculated = ei_wacc_real_pre_tax(wacc_inputs)
        
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Re (nominell)",
                f"{Re * 100:.2f}%",
                help="Kostnad för eget kapital efter skatt"
            )
        
        with col2:
            st.metric(
                "Rd (nominell)",
                f"{Rd * 100:.2f}%",
                help="Kostnad för skuld före skatt"
            )
        
        with col3:
            st.metric(
                "WACC (nominell)",
                f"{Wn * 100:.2f}%",
                help="Vägd kapitalkostnad före skatt, nominell"
            )
        
        with col4:
            st.metric(
                "WACC (real)",
                f"{wacc_calculated * 100:.2f}%",
                delta=f"{(wacc_calculated - baseline_wacc) * 100:.2f}%" if baseline_wacc else None,
                help="Vägd kapitalkostnad före skatt, real"
            )
        
        return {
            'rf_nom': rf_nom,
            'mrp': mrp,
            'infl': infl,
            'credit': credit,
            'debt_share': debt_share,
            'tax_rate': tax_rate,
            'beta_mode': beta_mode,
            'beta_a': beta_a,
            'beta_e': beta_e,
            'wacc_calculated': wacc_calculated
        }
    
    except Exception as e:
        st.error(f"Kunde inte beräkna WACC: {e}")
        return {}