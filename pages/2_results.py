"""
6. Model outputs

Structured presentation of revenue frame calculation results.
Follows Regumetrica User Manual nomenclature and variable IDs.
"""

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import plotly.graph_objects as go

from frontend.utils.state_manager import (
    init_session_state, 
    get_user_reid,
    get_case_name,
    get_case_notes,
    get_filtered_ui_config,
    is_snapshot_calculation,
    has_main_config,
    get_snapshots,
    add_snapshot,
    remove_snapshot,
    promote_snapshot,
    MAX_SNAPSHOTS,
)
from frontend.utils.export_button import render_export_button
from visualization.diagram_data import prepare_diagram_data
from visualization.diagram_utils import create_interactive_diagram_html
from visualization.geo_data import prepare_map_data_from_pipeline
from visualization.geo_visualization import (
    create_efficiency_map,
    get_available_value_columns,
    get_column_label
)

from frontend.common.styling import COLORS, get_plotly_template
from pipeline.result_helpers import (
    fmt_tkr as format_tkr,
    fmt_percent as format_percent,
    calc_delta,
)
from config.column_names import COL_REVENUE_FRAME, COL_CAPITAL_COST_PERIOD
from frontend.results import (
    m1_asset_base_output,
    m2_depreciation_output,
    m3_return_output,
    m3_incentive_output,
    m4_operating_exp_output,
    m5_efficiency_output,
    m7_benchmarking_output,
)

init_session_state()

SHAPEFILE_PATH = "data/shapefiles/all_network_operator_areas.shp"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


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
    st.info("Use the **Compute Revenue Frame** button in the sidebar to run the calculation.")
    st.stop()

# From here on, calculation has been performed
baseline = st.session_state.get("baseline_result")
case = st.session_state.get("case_result")

case_ir = case.post_dea.user_revenue_frame
baseline_ir = baseline.post_dea.user_revenue_frame
company_name = case.extraction.company_name

st.markdown(f"**{company_name}** ({user_reid})")

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
    st.markdown("##### Geographic comparison")
    
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

total_case = case_ir[COL_REVENUE_FRAME]
total_baseline = baseline_ir[COL_REVENUE_FRAME]
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
    cap_case = case_ir[COL_CAPITAL_COST_PERIOD]
    cap_baseline = baseline_ir[COL_CAPITAL_COST_PERIOD]
    cap_delta, cap_pct = calc_delta(cap_case, cap_baseline)
    st.metric(
        label="30.1 Capital cost",
        value=f"{cap_case:,.0f} tkr",
        delta=f"{cap_pct:+.1f}%" if cap_pct else None
    )

st.markdown("")

# Build waterfall from diagram_data (same source of truth as decomposition diagram)
dd = diagram_data
method = dd.get('method', 'OPEX')

# --- Waterfall chart: Revenue frame decomposition ---
# Components: (label, diagram_key, negate, measure)
# measure: "relative" for additive steps, "total" for subtotals/final
# Always split OPEX/CAPEX efficiency adjustments (CAPEX = 0 in OPEX mode).
# All three adjustments grouped together after Return (WACC).
wf_components = [
    ("40.1.1 Controllable OPEX",              "paverkbara",            False, "relative"),
    ("40.2.1 Non-controllable OPEX",          "ej_paverkbara",         False, "relative"),
    ("20.1 Depreciation",                     "avskrivningar",         False, "relative"),
    ("30.1 Return (WACC)",                    "avkastning",            False, "relative"),
    ("50.4.1 Efficiency OPEX adjustment",     "opex_effektivisering",  True,  "relative"),
    ("50.4.2 Efficiency CAPEX adjustment",    "capex_effektivisering", True,  "relative"),
    ("30.5.2 Return incentive adjustment",    "kvalitet",              False, "relative"),
    ("40.1.2 Flexibility services",           "flexibilitetstjanster", False, "relative"),
    ("Interruption compensation",             "avbrottsersattning",    False, "relative"),
    ("State aid deduction",                   "avdrag_statligt_stod",  True,  "relative"),
    ("Total Revenue Frame",                   "intaktsram",            False, "total"),
]

wf_labels = []
wf_values = []
wf_measures = []

for label, dd_key, negate, measure in wf_components:
    comp = dd.get(dd_key, {})
    val = float(comp.get('value', 0))
    if negate:
        val = -val
    wf_labels.append(label)
    wf_values.append(val / 1e3)  # tkr to MSEK
    wf_measures.append(measure)

tmpl = get_plotly_template()

fig_wf = go.Figure(go.Waterfall(
    orientation="h",
    y=wf_labels,
    x=wf_values,
    measure=wf_measures,
    textposition="outside",
    text=[f"{v:+,.1f}" if m != "total" and abs(v) > 0.05 else (f"{v:,.1f}" if m == "total" else "") for v, m in zip(wf_values, wf_measures)],
    textfont=dict(size=11, family="Inter, sans-serif"),
    connector=dict(
        line=dict(color=COLORS["bg_muted"], width=1, dash="dot")
    ),
    increasing=dict(marker=dict(color=COLORS["success"])),
    decreasing=dict(marker=dict(color=COLORS["error"])),
    totals=dict(marker=dict(color=COLORS["primary"])),
))

fig_wf.update_layout(
    font=tmpl.get("font", {}),
    paper_bgcolor=tmpl.get("paper_bgcolor", "rgba(0,0,0,0)"),
    plot_bgcolor=tmpl.get("plot_bgcolor", "rgba(0,0,0,0)"),
    margin=dict(l=10, r=80, t=10, b=40),
    height=max(380, len(wf_labels) * 38),
    xaxis=dict(
        title="MSEK",
        showgrid=True,
        gridcolor=COLORS["bg_subtle"],
        zeroline=True,
        zerolinecolor=COLORS["bg_muted"],
        zerolinewidth=1,
    ),
    yaxis=dict(
        showgrid=False,
        automargin=True,
        autorange="reversed",
    ),
    showlegend=False,
)

st.plotly_chart(fig_wf, key="revenue_frame_waterfall", width='stretch')

st.divider()


# =============================================================================
# SECTION B2: SNAPSHOT MANAGEMENT
# =============================================================================

_is_snapshot = is_snapshot_calculation()
_snapshots = get_snapshots()

# Status indicator
if _is_snapshot:
    st.info(
        "Viewing: **Unsaved snapshot result.** "
        "Save it below, or go back to Configure to discard and return to main."
    )
elif _snapshots:
    st.caption("Viewing: Main result")

# Save Snapshot form (only for snapshot-candidate calculations)
if _is_snapshot:
    st.markdown("##### Save as snapshot")
    
    col_name, col_desc, col_btn = st.columns([2, 3, 1])
    
    with col_name:
        _snap_name = st.text_input(
            "Snapshot name",
            placeholder="e.g., WACC 5%",
            key="snapshot_name_input",
            label_visibility="collapsed",
        )
    
    with col_desc:
        _snap_desc = st.text_input(
            "Description (optional)",
            placeholder="Description (optional)",
            key="snapshot_desc_input",
            label_visibility="collapsed",
        )
    
    with col_btn:
        if st.button("Save Snapshot", type="primary", width='stretch'):
            if not _snap_name or not _snap_name.strip():
                st.warning("Enter a name for the snapshot.")
            elif len(_snapshots) >= MAX_SNAPSHOTS:
                st.warning(f"Maximum {MAX_SNAPSHOTS} snapshots reached. Delete one first.")
            else:
                success = add_snapshot(
                    name=_snap_name.strip(),
                    description=_snap_desc.strip() if _snap_desc else "",
                    ui_config=st.session_state.get("ui_config", {}),
                    selected_modules=st.session_state.get("selected_modules", set()),
                    case_result=case,
                )
                if success:
                    st.toast(f"Snapshot saved: {_snap_name.strip()}")
                    st.rerun()

# Snapshot list (only when snapshots exist)
if _snapshots:
    with st.expander(f"Saved snapshots ({len(_snapshots)}/{MAX_SNAPSHOTS})", expanded=False):
        for _idx, _snap in enumerate(_snapshots):
            with st.container(border=True):
                _col_info, _col_promote, _col_delete = st.columns([4, 1, 1])
                
                with _col_info:
                    st.markdown(f"**{_snap['name']}**")
                    _desc_parts = []
                    if _snap.get("description"):
                        _desc_parts.append(_snap["description"])
                    _desc_parts.append(_snap["timestamp"][:16].replace("T", " "))
                    st.caption(" -- ".join(_desc_parts))
                
                with _col_promote:
                    if st.button(
                        "Promote to Main",
                        key=f"promote_snap_{_idx}",
                        width='stretch',
                    ):
                        _promoted_name = _snap["name"]
                        promote_snapshot(_idx)
                        st.toast(f"Promoted: {_promoted_name} is now the main result")
                        st.rerun()
                
                with _col_delete:
                    if st.button(
                        "Delete",
                        key=f"delete_snap_{_idx}",
                        width='stretch',
                    ):
                        _deleted_name = _snap["name"]
                        remove_snapshot(_idx)
                        st.toast(f"Deleted snapshot: {_deleted_name}")
                        st.rerun()

if _is_snapshot or _snapshots:
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
    m4 = ui_config.get("m4_operating_exp", {})
    return (
        m4.get("opex_scaling") is not None
        or m4.get("flex_scaling") is not None
        or m4.get("non_adj_scaling") is not None
        or m4.get("opex_override") is not None
        or m4.get("flex_override") is not None
        or m4.get("non_controllable_override") is not None
    )

def _has_m5_changes() -> bool:
    m5 = ui_config.get("m5_efficiency", {})
    # Compare against baseline values (not just is not None) because
    # the M5 widget_map always writes current widget values to config
    trunkering_max = m5.get("trunkering_max")
    realiseringstid = m5.get("realiseringstid")
    kunddelning = m5.get("kunddelning")
    outlier_krav = m5.get("outlier_krav")
    paverkbara_method = m5.get("paverkbara_method")
    return (
        (trunkering_max is not None and abs(trunkering_max - 0.30) > 1e-9)
        or (realiseringstid is not None and realiseringstid != 8)
        or (kunddelning is not None and abs(kunddelning - 0.50) > 1e-9)
        or (outlier_krav is not None and abs(outlier_krav - 0.01) > 1e-9)
        or (paverkbara_method is not None and paverkbara_method != "OPEX")
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

# Tab 3: Cost of Capital (M3) -- WACC/Return + Incentives
with tabs[2]:
    m3_return_output.render(case, baseline, ui_config)
    st.divider()
    m3_incentive_output.render(case, baseline, ui_config)

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
    company_name=company_name,
    baseline_result=baseline,
    case_result=case,
    ui_config=st.session_state.get("ui_config", {})
)

st.caption("Use **Save case** in the sidebar to save this configuration.")