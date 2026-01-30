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

init_session_state()

SHAPEFILE_PATH = "data/shapefiles/Samtliga nÃ¤tfÃ¶retags del- och verksamhetsomrÃ¥den.shp"

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
            case,
            value_columns=["Effektivitet", "Supereffektivitet"]
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
    cap_case = case_ir['Kapitalkostnad_Total']
    cap_baseline = baseline_ir['Kapitalkostnad_Total']
    cap_delta, cap_pct = calc_delta(cap_case, cap_baseline)
    st.metric(
        label="30.1 Capital cost",
        value=f"{cap_case:,.0f} tkr",
        delta=f"{cap_pct:+.1f}%" if cap_pct else None
    )

st.markdown("")

component_list = [
    ("30.1", "Capital cost", "Kapitalkostnad_Total", "tkr"),
    ("40.1.1", "Controllable costs (paverkbara)", "Paverkbara_Periodsumma", "tkr"),
    ("40.2.1", "Non-controllable costs", "Opaverkbara_Kostnader", "tkr"),
    ("40.1.2", "Flexibility services", "Flexibilitetstjanster", "tkr"),
    ("-", "Interruption compensation (12-24h)", "Avbrottsersattning_12_24h", "tkr"),
    ("-", "State aid deduction", "Avdrag_Statligt_Stod", "tkr"),
    ("30.5.2", "Incentive adjustment", "Incitamentjustering_Total", "tkr"),
]

rows = []
for var_id, label, col, unit in component_list:
    case_val = case_ir.get(col, 0)
    baseline_val = baseline_ir.get(col, 0)
    
    if col == "Avdrag_Statligt_Stod":
        case_val = -case_val if case_val else 0
        baseline_val = -baseline_val if baseline_val else 0
    
    rows.append(render_metric_row(var_id, label, case_val, baseline_val, unit))

rows.append({
    "ID": "",
    "Component": "TOTAL REVENUE FRAME",
    "Case": format_tkr(total_case),
    "Baseline": format_tkr(total_baseline),
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

# Tab 1: Asset base
with tabs[0]:
    st.caption("Asset base outputs - placeholder")

# Tab 2: Depreciation
with tabs[1]:
    st.caption("Depreciation outputs - placeholder")

# Tab 3: Cost of capital
with tabs[2]:
    st.caption("Cost of capital outputs - placeholder")

# Tab 4: OPEX
with tabs[3]:
    st.caption("OPEX outputs - placeholder")

# Tab 5: Efficiency
with tabs[4]:
    st.caption("Efficiency outputs - placeholder")

# Tab 7: Benchmarking
with tabs[5]:
    st.caption("Benchmarking outputs - placeholder")

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