"""
M5 Efficiency Incentive - Output Display

Displays:
- 5.2-5.3 Efficiency parameters (reference)
- 50.3 DEA efficiency measures with full calculation chain
- 50.4 Efficiency-adjusted costs (OPEX/CAPEX before/after)

Variable-IDs:
- 5.2.1-5.3.2: Efficiency calculation parameters
- 50.3.1: Efficiency score
- 50.3.2: Super-efficiency score
- 50.3.3: Efficiency potential
- 50.3.4: Applied efficiency requirement
- 50.4.1: OPEX efficiency adjustment
- 50.4.2: CAPEX efficiency adjustment (TOTEX only)
- 50.4.3: OPEX after adjustment
- 50.4.4: CAPEX after adjustment (TOTEX only)
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.core import PipelineResult


# Baseline parameter values
BASELINE_PARAMS = {
    "trunkering_max": 0.30,
    "realiseringstid": 8,
    "kunddelning": 0.50,
    "tillsynsperiod": 4,
    "outlier_krav": 0.01,
    "trunkering_min": 0.162416,  # Derived from outlier_krav
}


def _format_tkr(value: float, show_sign: bool = False) -> str:
    if pd.isna(value) or value is None:
        return "-"
    if show_sign and value > 0:
        return f"+{value:,.0f}"
    elif show_sign and value < 0:
        return f"{value:,.0f}"
    return f"{value:,.0f}"


def _format_percent(value: float, decimals: int = 2) -> str:
    if pd.isna(value) or value is None:
        return "-"
    return f"{value*100:.{decimals}f}%"


def _calc_delta(case_val: float, baseline_val: float) -> tuple:
    if pd.isna(case_val) or pd.isna(baseline_val) or case_val is None or baseline_val is None:
        return None, None
    delta_abs = case_val - baseline_val
    return delta_abs, None


def render(
    case: "PipelineResult",
    baseline: "PipelineResult",
    ui_config: Dict[str, Any],
    user_reid: str = None
) -> None:
    """Render M5 efficiency incentive outputs."""
    
    case_ir = case.post_dea.user_intaktsram
    baseline_ir = baseline.post_dea.user_intaktsram
    
    # Get M5 config for parameter display
    m5_config = ui_config.get("m5_efficiency", {})
    
    # === SECTION 1: EFFICIENCY PARAMETERS ===
    _render_parameters_section(m5_config)
    
    st.divider()
    
    # === SECTION 2: DEA EFFICIENCY MEASURES ===
    _render_efficiency_measures_section(case, baseline, m5_config, user_reid)
    
    st.divider()
    
    # === SECTION 3: EFFICIENCY-ADJUSTED COSTS ===
    _render_adjusted_costs_section(case_ir, baseline_ir, m5_config)


def _render_parameters_section(m5_config: Dict[str, Any]) -> None:
    """Render 5.2-5.3 efficiency parameters as reference."""
    
    st.markdown("**5.2-5.3 Efficiency Parameters**")
    st.caption("Parameters used for efficiency requirement calculation")
    
    # Get current values (from config or baseline)
    trunkering_max = m5_config.get("trunkering_max", BASELINE_PARAMS["trunkering_max"])
    realiseringstid = m5_config.get("realiseringstid", BASELINE_PARAMS["realiseringstid"])
    kunddelning = m5_config.get("kunddelning", BASELINE_PARAMS["kunddelning"])
    outlier_krav = m5_config.get("outlier_krav", BASELINE_PARAMS["outlier_krav"])
    tillsynsperiod = BASELINE_PARAMS["tillsynsperiod"]  # Fixed
    
    # Calculate derived trunkering_min
    total_eff = (1 + outlier_krav) ** tillsynsperiod - 1
    realization_factor = tillsynsperiod / realiseringstid
    trunkering_min = total_eff / (kunddelning * realization_factor)
    
    params = [
        ("5.2.1", "Max potential cap", trunkering_max, BASELINE_PARAMS["trunkering_max"], "percent"),
        ("5.2.2", "Realization time", realiseringstid, BASELINE_PARAMS["realiseringstid"], "years"),
        ("5.2.3", "Customer sharing", kunddelning, BASELINE_PARAMS["kunddelning"], "percent"),
        ("5.3.1", "Min annual requirement", outlier_krav, BASELINE_PARAMS["outlier_krav"], "percent"),
        ("5.3.2", "Truncation min (derived)", trunkering_min, BASELINE_PARAMS["trunkering_min"], "percent"),
    ]
    
    rows = []
    for param_id, label, case_val, baseline_val, fmt in params:
        if fmt == "percent":
            case_str = _format_percent(case_val, 2)
            baseline_str = _format_percent(baseline_val, 2)
            delta, _ = _calc_delta(case_val, baseline_val)
            delta_str = f"{delta*100:+.2f} pp" if delta and abs(delta) > 0.0001 else "-"
        elif fmt == "years":
            case_str = f"{int(case_val)} yr"
            baseline_str = f"{int(baseline_val)} yr"
            delta = case_val - baseline_val
            delta_str = f"{int(delta):+d} yr" if delta != 0 else "-"
        else:
            case_str = f"{case_val}"
            baseline_str = f"{baseline_val}"
            delta_str = "-"
        
        rows.append({
            "ID": param_id,
            "Parameter": label,
            "Case": case_str,
            "Baseline": baseline_str,
            "Delta": delta_str,
        })
    
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_efficiency_measures_section(
    case: "PipelineResult",
    baseline: "PipelineResult",
    m5_config: Dict[str, Any],
    user_reid: str
) -> None:
    """Render 50.3 DEA efficiency measures."""
    
    st.markdown("**50.3 Efficiency Measures**")
    
    # Get values
    eff_case = case.extraction.efficiency
    eff_baseline = baseline.extraction.efficiency
    potential_case = case.extraction.potential
    potential_baseline = baseline.extraction.potential
    effkrav_case = case.post_dea.user_effkrav_proc
    effkrav_baseline = baseline.post_dea.user_effkrav_proc
    is_outlier = case.extraction.is_outlier
    
    # Get parameters for truncation display
    trunkering_max = m5_config.get("trunkering_max", BASELINE_PARAMS["trunkering_max"])
    outlier_krav = m5_config.get("outlier_krav", BASELINE_PARAMS["outlier_krav"])
    realiseringstid = m5_config.get("realiseringstid", BASELINE_PARAMS["realiseringstid"])
    kunddelning = m5_config.get("kunddelning", BASELINE_PARAMS["kunddelning"])
    tillsynsperiod = BASELINE_PARAMS["tillsynsperiod"]
    
    # Calculate trunkering_min
    total_eff = (1 + outlier_krav) ** tillsynsperiod - 1
    realization_factor = tillsynsperiod / realiseringstid
    trunkering_min = total_eff / (kunddelning * realization_factor)
    
    # Calculate truncated potential
    if potential_case is not None:
        potential_trunkerad_case = np.clip(potential_case, trunkering_min, trunkering_max)
    else:
        potential_trunkerad_case = None
    
    if potential_baseline is not None:
        potential_trunkerad_baseline = np.clip(potential_baseline, trunkering_min, trunkering_max)
    else:
        potential_trunkerad_baseline = None
    
    rows = []
    
    # 50.3.1 Efficiency score
    eff_delta, _ = _calc_delta(eff_case, eff_baseline)
    rows.append({
        "ID": "50.3.1",
        "Measure": "Efficiency score",
        "Case": f"{eff_case:.3f}" if eff_case else "-",
        "Baseline": f"{eff_baseline:.3f}" if eff_baseline else "-",
        "Delta": f"{eff_delta:+.3f}" if eff_delta and abs(eff_delta) > 0.0001 else "-",
    })
    
    # 50.3.3 Efficiency potential (raw)
    pot_delta, _ = _calc_delta(potential_case, potential_baseline)
    rows.append({
        "ID": "50.3.3",
        "Measure": "Efficiency potential (raw)",
        "Case": _format_percent(potential_case, 1) if potential_case is not None else "-",
        "Baseline": _format_percent(potential_baseline, 1) if potential_baseline is not None else "-",
        "Delta": f"{pot_delta*100:+.1f} pp" if pot_delta and abs(pot_delta) > 0.001 else "-",
    })
    
    # Truncated potential (not in spec but useful)
    pot_tr_delta, _ = _calc_delta(potential_trunkerad_case, potential_trunkerad_baseline)
    rows.append({
        "ID": "-",
        "Measure": "Truncated potential",
        "Case": _format_percent(potential_trunkerad_case, 2) if potential_trunkerad_case is not None else "-",
        "Baseline": _format_percent(potential_trunkerad_baseline, 2) if potential_trunkerad_baseline is not None else "-",
        "Delta": f"{pot_tr_delta*100:+.2f} pp" if pot_tr_delta and abs(pot_tr_delta) > 0.001 else "-",
    })
    
    # 50.3.4 Applied requirement
    effkrav_delta, _ = _calc_delta(effkrav_case, effkrav_baseline)
    rows.append({
        "ID": "50.3.4",
        "Measure": "Applied requirement (annual)",
        "Case": _format_percent(effkrav_case, 2) if effkrav_case else "-",
        "Baseline": _format_percent(effkrav_baseline, 2) if effkrav_baseline else "-",
        "Delta": f"{effkrav_delta*100:+.2f} pp" if effkrav_delta and abs(effkrav_delta) > 0.0001 else "-",
    })
    
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    
    # Super-efficiency if available
    if user_reid and hasattr(case.dea, 'dea_results') and case.dea.dea_results is not None:
        dea_df = case.dea.dea_results
        user_row = dea_df[dea_df['REId'] == user_reid]
        if not user_row.empty and 'Supereffektivitet' in user_row.columns:
            super_eff = user_row['Supereffektivitet'].iloc[0]
            if super_eff is not None and not pd.isna(super_eff):
                st.metric("50.3.2 Super-efficiency score", f"{super_eff:.3f}")
    
    # Outlier warning
    if is_outlier:
        st.warning(
            f"This company is classified as an outlier. "
            f"Fixed minimum requirement ({outlier_krav*100:.1f}%) applies instead of DEA-based calculation."
        )


def _render_adjusted_costs_section(
    case_ir: pd.Series,
    baseline_ir: pd.Series,
    m5_config: Dict[str, Any]
) -> None:
    """Render 50.4 efficiency-adjusted costs."""
    
    st.markdown("**50.4 Efficiency-Adjusted Costs**")
    
    # Get method
    method_used = case_ir.get('Method_used', 'OPEX')
    if method_used == 'TOTEX':
        st.caption("Cost base: TOTEX (CAPEX excl. incentive adjustments)")
    else:
        st.caption("Cost base: OPEX")
    
    # Get new separated OPEX/CAPEX values
    opex_fore_case = case_ir.get('OPEX_Fore', None)
    opex_fore_baseline = baseline_ir.get('OPEX_Fore', None)
    opex_efter_case = case_ir.get('OPEX_Efter', None)
    opex_efter_baseline = baseline_ir.get('OPEX_Efter', None)
    opex_eff_case = case_ir.get('OPEX_Effektivisering', None)
    opex_eff_baseline = baseline_ir.get('OPEX_Effektivisering', None)
    
    capex_fore_case = case_ir.get('CAPEX_Fore', None)
    capex_fore_baseline = baseline_ir.get('CAPEX_Fore', None)
    capex_efter_case = case_ir.get('CAPEX_Efter', None)
    capex_efter_baseline = baseline_ir.get('CAPEX_Efter', None)
    capex_eff_case = case_ir.get('CAPEX_Effektivisering', None)
    capex_eff_baseline = baseline_ir.get('CAPEX_Effektivisering', None)
    
    # Fallback to legacy fields if new fields not available
    if opex_fore_case is None:
        opex_fore_case = case_ir.get('Paverkbara_Fore_Periodsumma', 0)
        opex_fore_baseline = baseline_ir.get('Paverkbara_Fore_Periodsumma', 0)
        opex_efter_case = case_ir.get('Paverkbara_Periodsumma', 0)
        opex_efter_baseline = baseline_ir.get('Paverkbara_Periodsumma', 0)
        opex_eff_case = case_ir.get('Effektivisering_Total', 0)
        opex_eff_baseline = baseline_ir.get('Effektivisering_Total', 0)
        capex_eff_case = 0
        capex_eff_baseline = 0
    
    rows = []
    
    # Show allocation percentages for TOTEX
    if method_used == 'TOTEX':
        opex_andel = case_ir.get('OPEX_Andel', None)
        capex_andel = case_ir.get('CAPEX_Andel', None)
        if opex_andel is not None and capex_andel is not None:
            st.caption(
                f"Efficiency allocation: OPEX {opex_andel*100:.1f}% / CAPEX {capex_andel*100:.1f}%"
            )
    
    # OPEX before
    if opex_fore_case is not None:
        fore_delta, _ = _calc_delta(opex_fore_case, opex_fore_baseline)
        rows.append({
            "ID": "-",
            "Component": "OPEX before efficiency adj.",
            "Case (tkr)": _format_tkr(opex_fore_case),
            "Baseline (tkr)": _format_tkr(opex_fore_baseline),
            "Delta (tkr)": _format_tkr(fore_delta, show_sign=True) if fore_delta else "-",
        })
    
    # 50.4.1 OPEX efficiency adjustment
    if opex_eff_case is not None:
        adj_delta, _ = _calc_delta(opex_eff_case, opex_eff_baseline)
        rows.append({
            "ID": "50.4.1",
            "Component": "OPEX efficiency adjustment",
            "Case (tkr)": _format_tkr(-opex_eff_case, show_sign=True),  # Show as negative (reduction)
            "Baseline (tkr)": _format_tkr(-opex_eff_baseline, show_sign=True),
            "Delta (tkr)": _format_tkr(-adj_delta, show_sign=True) if adj_delta else "-",
        })
    
    # 50.4.3 OPEX after adjustment
    if opex_efter_case is not None:
        efter_delta, _ = _calc_delta(opex_efter_case, opex_efter_baseline)
        rows.append({
            "ID": "50.4.3",
            "Component": "OPEX after efficiency adj.",
            "Case (tkr)": _format_tkr(opex_efter_case),
            "Baseline (tkr)": _format_tkr(opex_efter_baseline),
            "Delta (tkr)": _format_tkr(efter_delta, show_sign=True) if efter_delta else "-",
        })
    
    # --- CAPEX Section (only for TOTEX) ---
    if method_used == 'TOTEX':
        # Add separator row
        rows.append({
            "ID": "",
            "Component": "",
            "Case (tkr)": "",
            "Baseline (tkr)": "",
            "Delta (tkr)": "",
        })
        
        # CAPEX before
        if capex_fore_case is not None:
            fore_delta, _ = _calc_delta(capex_fore_case, capex_fore_baseline)
            rows.append({
                "ID": "-",
                "Component": "CAPEX before efficiency adj.",
                "Case (tkr)": _format_tkr(capex_fore_case),
                "Baseline (tkr)": _format_tkr(capex_fore_baseline),
                "Delta (tkr)": _format_tkr(fore_delta, show_sign=True) if fore_delta else "-",
            })
        
        # 50.4.2 CAPEX efficiency adjustment
        if capex_eff_case is not None:
            adj_delta, _ = _calc_delta(capex_eff_case, capex_eff_baseline)
            rows.append({
                "ID": "50.4.2",
                "Component": "CAPEX efficiency adjustment",
                "Case (tkr)": _format_tkr(-capex_eff_case, show_sign=True),  # Show as negative (reduction)
                "Baseline (tkr)": _format_tkr(-capex_eff_baseline, show_sign=True),
                "Delta (tkr)": _format_tkr(-adj_delta, show_sign=True) if adj_delta else "-",
            })
        
        # 50.4.4 CAPEX after adjustment
        if capex_efter_case is not None:
            efter_delta, _ = _calc_delta(capex_efter_case, capex_efter_baseline)
            rows.append({
                "ID": "50.4.4",
                "Component": "CAPEX after efficiency adj.",
                "Case (tkr)": _format_tkr(capex_efter_case),
                "Baseline (tkr)": _format_tkr(capex_efter_baseline),
                "Delta (tkr)": _format_tkr(efter_delta, show_sign=True) if efter_delta else "-",
            })
        
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    
    # Summary metrics
    total_eff_case = (opex_eff_case or 0) + (capex_eff_case or 0)
    total_eff_baseline = (opex_eff_baseline or 0) + (capex_eff_baseline or 0)
    
    if total_eff_case != 0 or total_eff_baseline != 0:
        col1, col2 = st.columns(2)
        with col1:
            delta = total_eff_case - total_eff_baseline
            st.metric(
                "Total efficiency adjustment",
                f"-{total_eff_case:,.0f} tkr",
                delta=f"{-delta:,.0f} tkr" if delta != 0 else None,
                delta_color="inverse"
            )