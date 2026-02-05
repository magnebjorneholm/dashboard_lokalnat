"""
6. Model outputs

Structured presentation of revenue frame calculation results.
Follows Regumetrica User Manual nomenclature and variable IDs.
"""

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from frontend.utils.state_manager import (
    init_session_state, 
    get_user_reid,
    get_case_name,
    get_case_notes,
    get_filtered_ui_config,
)
from frontend.utils.export_button import render_export_button
from frontend.utils.diagram_data import prepare_diagram_data
from frontend.utils.diagram_utils import create_interactive_diagram_html
from frontend.utils.geo_data import prepare_map_data_from_pipeline
from frontend.utils.geo_visualization import (
    create_efficiency_map, 
    get_available_value_columns,
    get_column_label
)
from frontend.modules.base import case_summary
from frontend.results import (
    m1_asset_base_output,
    m2_depreciation_output,
    m3_cost_of_capital_output,
    m4_operating_exp_output,
    m5_efficiency_output,
    m7_benchmarking_output,
)

init_session_state()

SHAPEFILE_PATH = "data/shapefiles/Samtliga nätföretags del- och verksamhetsområden.shp"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_tkr(value: float, show_sign: bool = False) -> str:
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:,.0f}"
    return f"{value:,.0f}"


def format_percent(value: float, show_sign: bool = False) -> str:
    if pd.isna(value):
        return "-"
    if show_sign and value > 0:
        return f"+{value:.1f}%"
    return f"{value:.1f}%"


def calc_delta(case_val: float, baseline_val: float) -> tuple:
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
    delta_abs, delta_pct = calc_delta(case_val, baseline_val)
    prefix = "  " * indent
    
    return {
        "ID": var_id,
        "Component": f"{prefix}{label}",
        "Case": format_tkr(case_val) if unit == "tkr" else f"{case_val:.2%}" if unit == "%" else str(case_val),
        "Baseline": format_tkr(baseline_val) if unit == "tkr" else f"{baseline_val:.2%}" if unit == "%" else str(baseline_val),
        "Delta (tkr)": format_tkr(delta_abs, show_sign=True) if delta_abs is not None and unit == "tkr" else "-",
        "Delta (%)": format_percent(delta_pct, show_sign=True) if delta_pct is not None else "-"
    }


# =============================================================================
# PAGE HEADER
# =============================================================================

st.title("Regumetrica")

case_name = get_case_name()
if case_name:
    st.subheader(f"Results: {case_name}")
else:
    st.subheader("Results")

user_reid = get_user_reid()
if user_reid is None:
    st.warning("Select a company in the sidebar to continue.")
    st.stop()

# If no calculation done yet, show case summary
if not st.session_state.get("calculation_done"):
    case_summary.render()
    st.info("Use the **Compute Revenue Frame** button in the sidebar to run the calculation.")
    st.stop()

# From here on, calculation has been performed
baseline = st.session_state.get("baseline_result")
case = st.session_state.get("case_result")

case_ir = case.post_dea.user_intaktsram
baseline_ir = baseline.post_dea.user_intaktsram
foretag = case.extraction.foretag

st.markdown(f"**{foretag}** ({user_reid})")

case_notes = get_case_notes()
if case_notes:
    with st.expander("Case notes", expanded=False):
        st.caption(case_notes)


# =============================================================================
# SECTION A: VISUALIZATIONS
# =============================================================================

col_diagram, col_map = st.columns([0.50, 0.50])

with col_diagram:
    st.markdown("##### Revenue frame decomposition")
    diagram_data = prepare_diagram_data(case_result=case, baseline_result=baseline)
    html_content = create_interactive_diagram_html(diagram_data)
    components.html(html_content, height=560, scrolling=False)

with col_map:
    st.markdown("##### Geographic efficiency")
    
    try:
        gdf, user_geoms = prepare_map_data_from_pipeline(
            SHAPEFILE_PATH,
            case
        )
        
        available_cols = get_available_value_columns(gdf)
        if available_cols:
            selected_var = st.selectbox(
                "Variable",
                options=available_cols,
                index=0,
                format_func=get_column_label,
                label_visibility="collapsed"
            )
            
            fig = create_efficiency_map(
                gdf,
                user_geoms,
                value_column=selected_var,
                height=500,
                zoom=3.0
            )
            st.plotly_chart(fig, key="efficiency_map", width='stretch')
        else:
            st.info("No efficiency data available for map visualization.")
            
    except FileNotFoundError:
        st.caption("Shapefile not found. Map visualization unavailable.")
    except Exception as e:
        st.caption(f"Map unavailable: {e}")

st.divider()


# =============================================================================
# SECTION B: REVENUE FRAME SUMMARY
# =============================================================================

st.markdown("##### Revenue frame summary")

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
    st.metric(label="Baseline", value=f"{total_baseline:,.0f} tkr")

with col3:
    op_case = diagram_data['lopande']['value']
    op_baseline = diagram_data['lopande']['baseline']
    op_delta, op_pct = calc_delta(op_case, op_baseline)
    st.metric(
        label="Operating costs",
        value=f"{op_case:,.0f} tkr",
        delta=f"{op_pct:+.1f}%" if op_pct else None
    )

st.markdown("")


def _diagram_row(var_id: str, label: str, key: str, negate: bool = False) -> dict:
    """Build a table row from diagram_data component."""
    comp = diagram_data.get(key, {})
    case_val = comp.get('value', 0)
    baseline_val = comp.get('baseline', 0)
    if negate:
        case_val = -abs(case_val)
        baseline_val = -abs(baseline_val)
    return render_metric_row(var_id, label, case_val, baseline_val, "tkr")


method = diagram_data.get('method', 'OPEX')

rows = [
    _diagram_row("40.1", "Controllable costs", "paverkbara"),
    _diagram_row("40.2", "Non-controllable costs", "ej_paverkbara"),
]

if method == 'TOTEX':
    rows.append(_diagram_row("50.4.1", "OPEX efficiency", "opex_effektivisering", negate=True))
else:
    rows.append(_diagram_row("50.4", "OPEX efficiency", "effektivisering", negate=True))

rows.append(_diagram_row("", "Operating costs", "lopande"))
rows.append(_diagram_row("11.1", "Capital base", "kapitalbas"))
rows.append(_diagram_row("20.1", "Depreciation", "avskrivningar"))
rows.append(_diagram_row("30.1", "Return (WACC)", "avkastning"))

if method == 'TOTEX':
    rows.append(_diagram_row("50.4.2", "CAPEX efficiency", "capex_effektivisering", negate=True))

rows.append(_diagram_row("30.5", "Quality & incentive adjustment", "kvalitet"))
rows.append(_diagram_row("30.1", "Capital costs", "kapitalkostnader"))
rows.append(_diagram_row("", "Other adjustments", "other_adjustments"))

rows.append({
    "ID": "60.1",
    "Component": "REVENUE FRAME",
    "Case": format_tkr(diagram_data['intaktsram']['value']),
    "Baseline": format_tkr(diagram_data['intaktsram']['baseline']),
    "Delta (tkr)": format_tkr(delta_abs, show_sign=True),
    "Delta (%)": format_percent(delta_pct, show_sign=True)
})

df_summary = pd.DataFrame(rows)

st.dataframe(
    df_summary,
    hide_index=True,
    width='stretch',
    column_config={
        "ID": st.column_config.TextColumn("ID", width="small"),
        "Component": st.column_config.TextColumn("Component", width="large"),
        "Case": st.column_config.TextColumn("Case (tkr)", width="small"),
        "Baseline": st.column_config.TextColumn("Baseline (tkr)", width="small"),
        "Delta (tkr)": st.column_config.TextColumn("Delta (tkr)", width="small"),
        "Delta (%)": st.column_config.TextColumn("Delta (%)", width="small"),
    }
)

st.divider()


# =============================================================================
# SECTION C: MODULE OUTPUTS
# =============================================================================

st.markdown("##### Module outputs")

# Change detection for tab styling
ui_config = get_filtered_ui_config()

def _has_m1_changes() -> bool:
    m1 = ui_config.get("m1_asset_base", {})
    return (
        m1.get("kent_file_bytes") is not None or
        (m1.get("general_scaling") is not None and m1.get("general_scaling") != 1.0) or
        (m1.get("cat_scaling") and len(m1.get("cat_scaling")) > 0) or
        (m1.get("var_scaling") and len(m1.get("var_scaling")) > 0)
    )

def _has_m2_changes() -> bool:
    m2 = ui_config.get("m2_depreciation", {})
    lifetime_adj = m2.get("lifetime_adjustments")
    return lifetime_adj is not None and len(lifetime_adj) > 0

def _has_m3_changes() -> bool:
    m3_wacc = ui_config.get("m3_cost_of_capital", {})
    m3_qual = ui_config.get("m3_quality_adjustments", {})
    return (
        m3_wacc.get("wacc_override") is not None or
        m3_qual.get("adj_max_agg") is not None or
        m3_qual.get("adj_max_cemi4") is not None or
        m3_qual.get("sharing_netloss") is not None or
        not m3_qual.get("enable_quality", True) or
        not m3_qual.get("enable_netloss", True) or
        not m3_qual.get("enable_load", True)
    )

def _has_m4_changes() -> bool:
    return False  # No OPEX parameters implemented yet

def _has_m5_changes() -> bool:
    m5 = ui_config.get("m5_efficiency", {})
    return (
        m5.get("trunkering_max") is not None or
        m5.get("realiseringstid") is not None or
        m5.get("kunddelning") is not None or
        m5.get("outlier_krav") is not None or
        m5.get("trunkering_min") is not None or
        m5.get("paverkbara_method") is not None
    )

has_changes = {
    "m1": _has_m1_changes(),
    "m2": _has_m2_changes(),
    "m3": _has_m3_changes(),
    "m4": _has_m4_changes(),
    "m5": _has_m5_changes(),
    "m7": ui_config.get("addon_benchmarking", {}).get("dea_method") == "custom",
}

def tab_label(key: str, name: str) -> str:
    if has_changes[key]:
        return f":orange[{name}]"
    return name

tab_labels = [
    tab_label("m1", "M1 Regulatory asset base valuation"),
    tab_label("m2", "M2 Depreciation"),
    tab_label("m3", "M3 Cost of Capital"),
    tab_label("m4", "M4 Operating expenditures"),
    tab_label("m5", "M5 Efficiency incentive"),
    tab_label("m7", "M7 Benchmarking"),
]

tabs = st.tabs(tab_labels)

# Tab 1: Asset base (M1)
with tabs[0]:
    m1_asset_base_output.render(case, baseline, ui_config)

# Tab 2: Depreciation (M2)
with tabs[1]:
    m2_depreciation_output.render(case, baseline, ui_config)

# Tab 3: Cost of Capital (M3)
with tabs[2]:
    m3_cost_of_capital_output.render(case, baseline, ui_config)

# Tab 4: Operating expenditures (M4)
with tabs[3]:
    m4_operating_exp_output.render(case, baseline, ui_config)

# Tab 5: Efficiency incentive (M5)
with tabs[4]:
    m5_efficiency_output.render(case, baseline, ui_config, user_reid=user_reid)

# Tab 7: Benchmarking (M7)
with tabs[5]:
    m7_benchmarking_output.render(case, baseline, ui_config)

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

st.caption("Use **Save case** in the sidebar to save this configuration.")