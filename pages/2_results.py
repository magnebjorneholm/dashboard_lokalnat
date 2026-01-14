"""
6. Model outputs

Structured presentation of revenue frame calculation results.
Follows Regumetrica User Manual nomenclature and variable IDs.
"""

import streamlit as st
import pandas as pd
from frontend.utils.state_manager import init_session_state, reset_case, get_user_reid
from frontend.utils.export_button import render_export_button
import streamlit.components.v1 as components
from frontend.utils.diagram_data import prepare_diagram_data
from frontend.utils.diagram_utils import create_interactive_diagram_html

init_session_state()


# --- Helper functions ---

def format_tkr(value: float, show_sign: bool = False) -> str:
    """Format value as tkr with thousand separators."""
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


def format_percent(value: float, show_sign: bool = False) -> str:
    """Format value as percentage."""
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:.1f}%"
    return f"{value:.1f}%"


def calc_delta(case_val: float, baseline_val: float) -> tuple:
    """Calculate absolute and percentage delta."""
    if pd.isna(case_val) or pd.isna(baseline_val):
        return None, None
    delta_abs = case_val - baseline_val
    delta_pct = (delta_abs / baseline_val * 100) if baseline_val != 0 else 0
    return delta_abs, delta_pct


def render_metric_row(
    var_id: str,
    label: str,
    case_val: float,
    baseline_val: float,
    unit: str = "tkr",
    indent: int = 0
) -> dict:
    """Create a row dict for the metrics table."""
    delta_abs, delta_pct = calc_delta(case_val, baseline_val)
    
    prefix = "  " * indent
    
    return {
        "ID": var_id,
        "Component": f"{prefix}{label}",
        "Case": format_tkr(case_val) if unit == "tkr" else f"{case_val:.2%}" if unit == "%" else str(case_val),
        "Baseline": format_tkr(baseline_val) if unit == "tkr" else f"{baseline_val:.2%}" if unit == "%" else str(baseline_val),
        "Δ (tkr)": format_tkr(delta_abs, show_sign=True) if delta_abs is not None and unit == "tkr" else "-",
        "Δ (%)": format_percent(delta_pct, show_sign=True) if delta_pct is not None else "-"
    }


# --- Page content ---

st.title("6. Model outputs")

if not st.session_state.get("calculation_done"):
    st.warning("No calculation performed yet.")
    if st.button("Go to Case Configuration"):
        st.switch_page("pages/1_case_config.py")
    st.stop()

# Get results from session state
baseline = st.session_state.get("baseline_result")
case = st.session_state.get("case_result")
user_reid = get_user_reid()

# Extract data
case_ir = case.post_dea.user_intaktsram
baseline_ir = baseline.post_dea.user_intaktsram
foretag = case.extraction.foretag

st.subheader(f"{foretag} ({user_reid})")

# =============================================================================
# SECTION A: VISUALIZATIONS (Placeholder)
# =============================================================================


with st.container():
    st.markdown("##### Revenue frame decomposition")
    
    # Prepare diagram data
    diagram_data = prepare_diagram_data(
        case_result=case,
        baseline_result=baseline
    )
    
    # Generate and render HTML diagram
    html_content = create_interactive_diagram_html(diagram_data)
    components.html(html_content, height=520, scrolling=False)

st.divider()


# =============================================================================
# SECTION B: REVENUE FRAME SUMMARY
# =============================================================================

st.markdown("##### Revenue frame summary")

# Headline metrics
total_case = case_ir['Intaktsram_Total']
total_baseline = baseline_ir['Intaktsram_Total']
delta_abs, delta_pct = calc_delta(total_case, total_baseline)

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.metric(
        label="Total revenue frame",
        value=f"{total_case:,.0f} tkr",
        delta=f"{delta_abs:+,.0f} tkr ({delta_pct:+.1f}%)" if delta_abs else None
    )

with col2:
    st.metric(
        label="Baseline",
        value=f"{total_baseline:,.0f} tkr"
    )

with col3:
    cap_case = case_ir['Kapitalkostnad_Total']
    cap_baseline = baseline_ir['Kapitalkostnad_Total']
    cap_delta, cap_pct = calc_delta(cap_case, cap_baseline)
    st.metric(
        label="30.1 Capital cost",
        value=f"{cap_case:,.0f} tkr",
        delta=f"{cap_pct:+.1f}%" if cap_pct else None
    )

st.markdown("")

# Component breakdown table
components = [
    ("30.1", "Capital cost", "Kapitalkostnad_Total", "tkr"),
    ("40.1.1", "Controllable costs (påverkbara)", "Paverkbara_Periodsumma", "tkr"),
    ("40.2.1", "Non-controllable costs", "Opaverkbara_Kostnader", "tkr"),
    ("40.1.2", "Flexibility services", "Flexibilitetstjanster", "tkr"),
    ("-", "Interruption compensation (12-24h)", "Avbrottsersattning_12_24h", "tkr"),
    ("-", "State aid deduction", "Avdrag_Statligt_Stod", "tkr"),
    ("30.5.2", "Incentive adjustment", "Incitamentjustering_Total", "tkr"),
]

rows = []
for var_id, label, col, unit in components:
    case_val = case_ir.get(col, 0)
    baseline_val = baseline_ir.get(col, 0)
    
    # State aid is subtracted, so show as negative
    if col == "Avdrag_Statligt_Stod":
        case_val = -case_val if case_val else 0
        baseline_val = -baseline_val if baseline_val else 0
    
    rows.append(render_metric_row(var_id, label, case_val, baseline_val, unit))

# Add total row
rows.append({
    "ID": "",
    "Component": "TOTAL REVENUE FRAME",
    "Case": format_tkr(total_case),
    "Baseline": format_tkr(total_baseline),
    "Δ (tkr)": format_tkr(delta_abs, show_sign=True),
    "Δ (%)": format_percent(delta_pct, show_sign=True)
})

df_summary = pd.DataFrame(rows)

st.dataframe(
    df_summary,
    hide_index=True,
    width='stretch',
    column_config={
        "ID": st.column_config.TextColumn("ID", width="small"),
        "Component": st.column_config.TextColumn("Component", width="stretch"),
        "Case": st.column_config.TextColumn("Case (tkr)", width="small"),
        "Baseline": st.column_config.TextColumn("Baseline (tkr)", width="small"),
        "Δ (tkr)": st.column_config.TextColumn("Δ (tkr)", width="small"),
        "Δ (%)": st.column_config.TextColumn("Δ (%)", width="small"),
    }
)

st.divider()

# =============================================================================
# SECTION C: MODULE OUTPUTS (Collapsible)
# =============================================================================

st.markdown("##### Module outputs")

# --- Module 1: Regulatory asset base valuation ---
with st.expander("1. Regulatory asset base valuation", expanded=False):
    # Estimate asset base from capital cost / WACC
    wacc_case = case.pre_dea.wacc_used or 0.0453
    wacc_baseline = 0.0453
    
    # Rough estimate: asset base ≈ return / WACC, return ≈ capital cost - depreciation
    # For now, show placeholder
    st.markdown("**11.1 Total asset value**")
    st.caption("Detailed asset base calculation requires KENT data.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("WACC applied", f"{wacc_case:.2%}")
    with col2:
        st.metric("Baseline WACC", f"{wacc_baseline:.2%}")
    
    st.info("Per-category breakdown (11.2-11.17) coming soon.")

# --- Module 2: Depreciation ---
with st.expander("2. Depreciation", expanded=False):
    st.markdown("**Depreciation outputs**")
    
    st.markdown("""
    | ID | Description | Status |
    |---|---|---|
    | 20.1.1 | Total depreciation (ordinary) | Coming soon |
    | 20.1.2 | Total depreciation (tail) | Coming soon |
    | 20.2-20.18 | Per-category breakdown | Coming soon |
    """)
    
    st.info("Depreciation breakdown requires detailed KENT capital base data.")

# --- Module 3: Cost of capital ---
with st.expander("3. Cost of capital", expanded=True):
    st.markdown("**WACC parameters**")
    
    wacc_case = case.pre_dea.wacc_used or 0.0453
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("3.2.5 WACC applied", f"{wacc_case:.2%}")
    with col2:
        st.metric("Baseline WACC", "4.53%")
    
    st.markdown("")
    st.markdown("**Incentive adjustments (cost of capital)**")
    
    inc_rows = [
        ("30.4.59", "Quality adjustment", "Kvalitetsjustering_Total"),
        ("30.2.5", "Network loss adjustment", "Natforlustjustering_Total"),
        ("30.3.5", "Utilization rate adjustment", "Belastningsjustering_Total"),
        ("30.5.2", "Total incentive adjustment", "Incitamentjustering_Total"),
    ]
    
    inc_data = []
    for var_id, label, col in inc_rows:
        case_val = case_ir.get(col, 0)
        baseline_val = baseline_ir.get(col, 0)
        delta, pct = calc_delta(case_val, baseline_val)
        inc_data.append({
            "ID": var_id,
            "Adjustment": label,
            "Case (tkr)": format_tkr(case_val, show_sign=True),
            "Baseline (tkr)": format_tkr(baseline_val, show_sign=True),
            "Δ (tkr)": format_tkr(delta, show_sign=True) if delta is not None else "-"
        })
    
    st.dataframe(
        pd.DataFrame(inc_data),
        hide_index=True,
        width='stretch'
    )
    
    # Missing data warning
    if case_ir.get('Missing_Incentive_Data', False):
        st.warning("Incentive data incomplete for this company.")

# --- Module 4: Operating expenditures ---
with st.expander("4. Operating expenditures", expanded=False):
    st.markdown("**OPEX components**")
    
    pav_case = case_ir['Paverkbara_Periodsumma']
    pav_baseline = baseline_ir['Paverkbara_Periodsumma']
    pav_delta, pav_pct = calc_delta(pav_case, pav_baseline)
    
    method_used = case_ir.get('Method_used', 'OPEX')
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "40.1.1 Controllable costs",
            f"{pav_case:,.0f} tkr",
            f"{pav_pct:+.1f}%" if pav_pct else None
        )
    with col2:
        st.metric("Method", method_used)
    
    opav_case = case_ir.get('Opaverkbara_Kostnader', 0)
    opav_baseline = baseline_ir.get('Opaverkbara_Kostnader', 0)
    opav_delta, opav_pct = calc_delta(opav_case, opav_baseline)
    
    st.metric(
        "40.2.1 Non-controllable costs",
        f"{opav_case:,.0f} tkr",
        f"{opav_pct:+.1f}%" if opav_pct else None
    )

# --- Module 5: Efficiency incentive ---
with st.expander("5. Efficiency incentive", expanded=True):
    st.markdown("**DEA efficiency results**")
    
    # Get efficiency data
    eff_case = case.extraction.efficiency
    eff_baseline = baseline.extraction.efficiency
    potential_case = case.extraction.potential
    potential_baseline = baseline.extraction.potential
    effkrav_case = case.post_dea.user_effkrav_proc
    effkrav_baseline = baseline.post_dea.user_effkrav_proc
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "50.3.1 Efficiency score",
            f"{eff_case:.3f}" if eff_case else "-",
            f"{(eff_case - eff_baseline):.3f}" if eff_case and eff_baseline else None
        )
    
    with col2:
        st.metric(
            "50.3.3 Efficiency potential",
            f"{potential_case:.1%}" if potential_case else "-"
        )
    
    with col3:
        st.metric(
            "50.3.4 Applied requirement",
            f"{effkrav_case:.2%}" if effkrav_case else "-",
            f"{(effkrav_case - effkrav_baseline):.2%}" if effkrav_case and effkrav_baseline and abs(effkrav_case - effkrav_baseline) > 0.0001 else None
        )
    
    st.markdown("")
    
    # Super-efficiency from DEA results if available
    if hasattr(case.dea, 'dea_results') and case.dea.dea_results is not None:
        dea_df = case.dea.dea_results
        user_row = dea_df[dea_df['REId'] == user_reid]
        if not user_row.empty and 'Supereffektivitet' in user_row.columns:
            super_eff = user_row['Supereffektivitet'].iloc[0]
            st.metric("50.3.2 Super-efficiency score", f"{super_eff:.3f}")

st.divider()

# =============================================================================
# SECTION D: EXPORT
# =============================================================================

st.markdown("##### Export")

render_export_button(
    user_reid=user_reid,
    foretag=foretag,
    baseline_result=baseline,
    case_result=case,
    ui_config=st.session_state.get("ui_config", {})
)

st.divider()

# =============================================================================
# ACTIONS
# =============================================================================

col1, col2 = st.columns(2)

with col1:
    if st.button("NEW CASE", width='stretch', type="secondary"):
        reset_case()
        st.switch_page("pages/1_case_config.py")

with col2:
    if st.button("MODIFY CASE", width='stretch', type="primary"):
        st.session_state["calculation_done"] = False
        st.switch_page("pages/1_case_config.py")