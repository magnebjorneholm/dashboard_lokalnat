"""
Shared efficiency visualization components.

Used by M5 (full pipeline results) and the benchmarking mini-run (isolated DEA).
All functions accept pre-extracted data -- no PipelineResult or MiniRunResult
dependencies.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Optional

from frontend.common.styling import COLORS, CHART_COLORS
from config.colors import ZONE_COLORS, get_plotly_template_safe
from config.formatting import format_percent, format_pp
from config.glossary import (
    VID_EFFICIENCY_SCORE, VID_SUPER_EFFICIENCY, VID_EFFICIENCY_POTENTIAL,
    VID_APPLIED_POTENTIAL,
)
from config.column_names import COL_EFF_REQ_ANNUAL
from pipeline.result_helpers import fmt_pct as _fmt_pct


# ============================================================================
# CONSTANTS
# ============================================================================

BASELINE_PARAMS = {
    "trunkering_max": 0.30,
    "realiseringstid": 8,
    "kunddelning": 0.50,
    "tillsynsperiod": 4,
    "outlier_krav": 0.01,
}

# Zone colors (from design system)
ZONE_CAP = ZONE_COLORS["cap_fill"]
ZONE_ACTIVE = ZONE_COLORS["active_fill"]
ZONE_FLOOR = ZONE_COLORS["floor_fill"]
ZONE_CAP_BORDER = ZONE_COLORS["cap_border"]
ZONE_FLOOR_BORDER = ZONE_COLORS["floor_border"]


# ============================================================================
# HELPERS
# ============================================================================

def calc_trunkering_min(outlier_krav, kunddelning, realiseringstid, tillsynsperiod):
    """Calculate trunkering_min from outlier_krav (inverse formula)."""
    total_eff = (1 + outlier_krav) ** tillsynsperiod - 1
    realization_factor = tillsynsperiod / realiseringstid
    return total_eff / (kunddelning * realization_factor)


def get_params(m5_config):
    """Extract efficiency parameters, falling back to baseline defaults.

    Uses ``is None`` checks instead of ``or`` so that explicit zero values
    are respected (``or`` treats 0 / 0.0 as falsy).
    """
    trunkering_max = m5_config.get("trunkering_max")
    if trunkering_max is None:
        trunkering_max = BASELINE_PARAMS["trunkering_max"]
    realiseringstid = m5_config.get("realiseringstid")
    if realiseringstid is None:
        realiseringstid = BASELINE_PARAMS["realiseringstid"]
    kunddelning = m5_config.get("kunddelning")
    if kunddelning is None:
        kunddelning = BASELINE_PARAMS["kunddelning"]
    outlier_krav = m5_config.get("outlier_krav")
    if outlier_krav is None:
        outlier_krav = BASELINE_PARAMS["outlier_krav"]
    tillsynsperiod = BASELINE_PARAMS["tillsynsperiod"]

    trunkering_min = calc_trunkering_min(
        outlier_krav, kunddelning, realiseringstid, tillsynsperiod
    )

    return {
        "trunkering_max": trunkering_max,
        "realiseringstid": realiseringstid,
        "kunddelning": kunddelning,
        "outlier_krav": outlier_krav,
        "tillsynsperiod": tillsynsperiod,
        "trunkering_min": trunkering_min,
    }


def get_baseline_trunkering_min():
    """Baseline trunkering_min for comparison."""
    return calc_trunkering_min(
        BASELINE_PARAMS["outlier_krav"],
        BASELINE_PARAMS["kunddelning"],
        BASELINE_PARAMS["realiseringstid"],
        BASELINE_PARAMS["tillsynsperiod"],
    )


def ordinal(n: int) -> str:
    """Convert integer to ordinal string: 1 -> '1st', 2 -> '2nd', etc."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _tmpl_safe():
    """Get plotly template dict with xaxis/yaxis removed to avoid conflicts."""
    return get_plotly_template_safe()


# ============================================================================
# BLOCK 1 -- EFFICIENCY DISTRIBUTIONS (two side-by-side histograms)
# ============================================================================

def render_efficiency_distributions(
    eff_scores: np.ndarray,
    eff_case: Optional[float],
    eff_baseline: Optional[float],
    effkrav_all_df: pd.DataFrame,
    effkrav_case: Optional[float],
    effkrav_baseline: Optional[float],
    params: dict,
    key_prefix: str = "m5",
) -> None:
    """Two side-by-side histograms: efficiency scores and efficiency requirements."""

    st.markdown("**Efficiency Distribution**")

    cap_pct = params["trunkering_max"] * 100
    floor_pct = params["trunkering_min"] * 100
    outlier_krav_pct = params["outlier_krav"] * 100
    st.caption(
        f"Left chart: distribution of DEA efficiency scores for all 148 companies. "
        f"Companies with potential above {cap_pct:.0f}% (efficiency below {1 - params['trunkering_max']:.2f}) "
        f"are capped at {cap_pct:.0f}%. "
        f"Companies with potential below {floor_pct:.1f}% (efficiency above {1 - params['trunkering_min']:.3f}) "
        f"are floored at {floor_pct:.1f}% "
        f"(derived from the minimum annual requirement of {outlier_krav_pct:.1f}%/yr). "
        f"Right chart: resulting annual efficiency requirements after truncation and realization."
    )

    col_left, col_right = st.columns(2)

    with col_left:
        _render_efficiency_histogram(eff_scores, eff_case, eff_baseline, params,
                                     key_prefix=key_prefix)

    with col_right:
        _render_effkrav_histogram(effkrav_all_df, effkrav_case, effkrav_baseline,
                                  key_prefix=key_prefix)


def _render_efficiency_histogram(eff_scores, eff_case, eff_baseline, params,
                                 key_prefix="m5"):
    """Histogram of efficiency scores with truncation zones."""

    eff_cap = 1 - params["trunkering_max"]
    eff_floor = 1 - params["trunkering_min"]

    layout_kwargs, template = _tmpl_safe()
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=eff_scores,
        nbinsx=25,
        marker_color=CHART_COLORS[0],
        marker_line_color="white",
        marker_line_width=1,
        opacity=0.85,
        hovertemplate="Efficiency: %{x:.3f}<br>Companies: %{y}<extra></extra>",
        name="",
        showlegend=False,
    ))

    # Truncation zones
    fig.add_vrect(
        x0=0, x1=eff_cap,
        fillcolor=ZONE_CAP,
        line=dict(color=ZONE_CAP_BORDER, width=1, dash="dot"),
        annotation_text=f"Cap ({params['trunkering_max']*100:.0f}%)",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=COLORS["warning"],
    )

    fig.add_vrect(
        x0=eff_cap, x1=eff_floor,
        fillcolor=ZONE_ACTIVE,
        line_width=0,
    )

    fig.add_vrect(
        x0=eff_floor, x1=max(eff_scores.max() * 1.02, 1.05),
        fillcolor=ZONE_FLOOR,
        line=dict(color=ZONE_FLOOR_BORDER, width=1, dash="dot"),
        annotation_text=f"Floor ({params['trunkering_min']*100:.1f}%)",
        annotation_position="top left",
        annotation_font_size=10,
        annotation_font_color=COLORS["success"],
    )

    # Company markers
    y_max_approx = len(eff_scores) / 6

    if eff_baseline is not None:
        fig.add_vline(
            x=eff_baseline,
            line_dash="dash",
            line_color=COLORS["text_muted"],
            line_width=1.5,
        )
        fig.add_annotation(
            x=eff_baseline, y=y_max_approx * 0.92,
            text=f"Baseline: {eff_baseline:.3f}",
            showarrow=False,
            font=dict(size=10, color=COLORS["text_muted"]),
            bgcolor="rgba(255,255,255,0.85)",
            borderpad=3, yanchor="bottom",
        )

    if eff_case is not None:
        fig.add_vline(
            x=eff_case,
            line_dash="solid",
            line_color=CHART_COLORS[0],
            line_width=2,
        )
        fig.add_annotation(
            x=eff_case, y=y_max_approx * 1.05,
            text=f"<b>Case: {eff_case:.3f}</b>",
            showarrow=False,
            font=dict(size=11, color=CHART_COLORS[0]),
            bgcolor="rgba(255,255,255,0.9)",
            borderpad=3, yanchor="bottom",
        )

    fig.update_layout(
        **layout_kwargs,
        template=template,
        title=dict(text="Efficiency Scores", font=dict(size=13)),
        xaxis_title="Efficiency score",
        yaxis_title="Number of companies",
        height=340,
        bargap=0.03,
        xaxis=dict(
            range=[
                max(0, min(eff_scores.min(), eff_cap) - 0.05),
                max(eff_scores.max() * 1.02, 1.05),
            ],
            dtick=0.05,
            showgrid=False,
            linecolor=COLORS["bg_muted"],
        ),
        yaxis=dict(
            gridcolor=COLORS["bg_subtle"],
            linecolor=COLORS["bg_muted"],
        ),
    )

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False},
                    key=f"{key_prefix}_eff_hist")


def _render_effkrav_histogram(effkrav_all_df, effkrav_case, effkrav_baseline,
                              key_prefix="m5"):
    """Histogram of annual efficiency requirements for all companies."""

    if effkrav_all_df is None or COL_EFF_REQ_ANNUAL not in effkrav_all_df.columns:
        st.info("Efficiency requirement data not available.")
        return

    effkrav_values = effkrav_all_df[COL_EFF_REQ_ANNUAL].dropna().values * 100  # to %

    layout_kwargs, template = _tmpl_safe()
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=effkrav_values,
        nbinsx=20,
        marker_color=CHART_COLORS[1],
        marker_line_color="white",
        marker_line_width=1,
        opacity=0.85,
        hovertemplate="Requirement: %{x:.2f}%/yr<br>Companies: %{y}<extra></extra>",
        name="",
        showlegend=False,
    ))

    y_max_approx = len(effkrav_values) / 5

    if effkrav_baseline is not None:
        fig.add_vline(
            x=effkrav_baseline * 100,
            line_dash="dash",
            line_color=COLORS["text_muted"],
            line_width=1.5,
        )
        fig.add_annotation(
            x=effkrav_baseline * 100, y=y_max_approx * 0.92,
            text=f"Baseline: {effkrav_baseline*100:.2f}%",
            showarrow=False,
            font=dict(size=10, color=COLORS["text_muted"]),
            bgcolor="rgba(255,255,255,0.85)",
            borderpad=3, yanchor="bottom",
        )

    if effkrav_case is not None:
        fig.add_vline(
            x=effkrav_case * 100,
            line_dash="solid",
            line_color=CHART_COLORS[1],
            line_width=2,
        )
        fig.add_annotation(
            x=effkrav_case * 100, y=y_max_approx * 1.05,
            text=f"<b>Case: {effkrav_case*100:.2f}%</b>",
            showarrow=False,
            font=dict(size=11, color=CHART_COLORS[1]),
            bgcolor="rgba(255,255,255,0.9)",
            borderpad=3, yanchor="bottom",
        )

    fig.update_layout(
        **layout_kwargs,
        template=template,
        title=dict(text="Annual Efficiency Requirements", font=dict(size=13)),
        xaxis_title="Requirement (%/yr)",
        yaxis_title="Number of companies",
        height=340,
        bargap=0.03,
        xaxis=dict(
            showgrid=False,
            linecolor=COLORS["bg_muted"],
        ),
        yaxis=dict(
            gridcolor=COLORS["bg_subtle"],
            linecolor=COLORS["bg_muted"],
        ),
    )

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False},
                    key=f"{key_prefix}_effkrav_hist")


# ============================================================================
# BLOCK 2 -- COMPANY EFFICIENCY SUMMARY
# ============================================================================

def render_efficiency_summary(
    eff_case: Optional[float],
    eff_baseline: Optional[float],
    potential_case: Optional[float],
    potential_baseline: Optional[float],
    effkrav_case: Optional[float],
    effkrav_baseline: Optional[float],
    is_outlier: bool,
    super_eff: Optional[float],
    case_rank: Optional[int],
    bl_rank: Optional[int],
    n_total: int,
    params: dict,
    show_detail_tables: bool = True,
) -> None:
    """KPI hero row + super-eff badge + outlier warning + optional detail tables."""

    st.markdown("**Company Efficiency**")

    # Truncated potential
    bl_trunkering_min = get_baseline_trunkering_min()
    pot_tr_case = (
        np.clip(potential_case, params["trunkering_min"], params["trunkering_max"])
        if potential_case is not None else None
    )
    pot_tr_baseline = (
        np.clip(potential_baseline, bl_trunkering_min, BASELINE_PARAMS["trunkering_max"])
        if potential_baseline is not None else None
    )

    # --- Top row: 4 KPI metrics ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta_eff = (eff_case - eff_baseline) if eff_case and eff_baseline else None
        st.metric(
            f"{VID_EFFICIENCY_SCORE} Efficiency score",
            f"{eff_case:.3f}" if eff_case else "-",
            delta=f"{delta_eff:+.3f}" if delta_eff and abs(delta_eff) > 0.0001 else None,
        )

    with col2:
        rank_str = f"{ordinal(case_rank)} / {n_total}" if case_rank else "-"
        delta_rank = None
        if case_rank and bl_rank:
            rank_diff = bl_rank - case_rank  # positive = improved (moved up)
            if rank_diff != 0:
                delta_rank = f"{rank_diff:+d} ranks"
        st.metric(
            "Rank",
            rank_str,
            delta=delta_rank,
        )

    with col3:
        delta_pot = None
        if pot_tr_case is not None and pot_tr_baseline is not None:
            delta_pot = pot_tr_case - pot_tr_baseline
        st.metric(
            f"{VID_APPLIED_POTENTIAL} Truncated potential",
            _fmt_pct(pot_tr_case, 2) if pot_tr_case is not None else "-",
            delta=format_pp(delta_pot) if delta_pot and abs(delta_pot) > 0.0001 else None,
            delta_color="inverse",
        )

    with col4:
        delta_ek = (effkrav_case - effkrav_baseline) if effkrav_case and effkrav_baseline else None
        st.metric(
            "Applied annual requirement",
            _fmt_pct(effkrav_case, 2) if effkrav_case else "-",
            delta=format_pp(delta_ek) if delta_ek and abs(delta_ek) > 0.0001 else None,
            delta_color="inverse",
        )

    # --- Super-efficiency badge ---
    if super_eff is not None:
        st.success(
            f"**{VID_SUPER_EFFICIENCY} Super-efficiency: {super_eff:.3f}** -- "
            f"This company is on or beyond the efficient frontier."
        )

    # --- Outlier warning ---
    if is_outlier:
        st.warning(
            f"This company is classified as an outlier. "
            f"Fixed minimum requirement ({params['outlier_krav']*100:.1f}%/yr) "
            f"applies instead of DEA-based calculation."
        )

    # --- Detail tables (optional, M5 shows these, M7 mini-run skips) ---
    if show_detail_tables:
        _render_detail_tables(
            eff_case, eff_baseline,
            potential_case, potential_baseline,
            pot_tr_case, pot_tr_baseline,
            effkrav_case, effkrav_baseline,
            super_eff, case_rank, bl_rank, n_total,
            params,
        )


def _render_detail_tables(
    eff_case, eff_baseline,
    potential_case, potential_baseline,
    pot_tr_case, pot_tr_baseline,
    effkrav_case, effkrav_baseline,
    super_eff, case_rank, bl_rank, n_total,
    params,
):
    """50.3 Efficiency measures + 5.2-5.3 Parameters tables in expanders."""

    bl_trunkering_min = get_baseline_trunkering_min()

    # --- 50.3 Efficiency Measures table ---
    with st.expander("50.3 Efficiency measures"):
        rows_m = []
        _add_measure_row(rows_m, VID_EFFICIENCY_SCORE, "Efficiency score",
                         f"{eff_case:.3f}" if eff_case else "-",
                         f"{eff_baseline:.3f}" if eff_baseline else "-",
                         eff_case, eff_baseline, fmt="score")

        _add_measure_row(rows_m, VID_EFFICIENCY_POTENTIAL, "Efficiency potential (raw)",
                         _fmt_pct(potential_case, 1),
                         _fmt_pct(potential_baseline, 1),
                         potential_case, potential_baseline, fmt="pp1")

        _add_measure_row(rows_m, VID_APPLIED_POTENTIAL, "Truncated potential",
                         _fmt_pct(pot_tr_case, 2),
                         _fmt_pct(pot_tr_baseline, 2),
                         pot_tr_case, pot_tr_baseline, fmt="pp2")

        _add_measure_row(rows_m, "-", "Applied annual requirement",
                         _fmt_pct(effkrav_case, 2),
                         _fmt_pct(effkrav_baseline, 2),
                         effkrav_case, effkrav_baseline, fmt="pp2")

        if super_eff is not None:
            rows_m.append({
                "ID": VID_SUPER_EFFICIENCY, "Measure": "Super-efficiency score",
                "Case": f"{super_eff:.3f}", "Baseline": "-", "Delta": "-",
            })

        if case_rank:
            bl_rank_str = f"{ordinal(bl_rank)} / {n_total}" if bl_rank else "-"
            rank_delta_str = (
                f"{bl_rank - case_rank:+d}"
                if (case_rank and bl_rank and bl_rank != case_rank) else "-"
            )
            rows_m.append({
                "ID": "-", "Measure": "Rank (efficiency score)",
                "Case": f"{ordinal(case_rank)} / {n_total}",
                "Baseline": bl_rank_str,
                "Delta": rank_delta_str,
            })

        st.dataframe(
            pd.DataFrame(rows_m),
            hide_index=True,
            width="stretch",
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Measure": st.column_config.TextColumn("Measure", width="medium"),
                "Case": st.column_config.TextColumn("Case", width="small"),
                "Baseline": st.column_config.TextColumn("Baseline", width="small"),
                "Delta": st.column_config.TextColumn("Delta", width="small"),
            },
        )

    # --- Parameter reference table ---
    with st.expander("5.2-5.3 Efficiency parameters"):
        from config.glossary import (
            PID_MAX_POTENTIAL_CAP, PID_REALIZATION_TIME,
            PID_CUSTOMER_SHARING, PID_MIN_ANNUAL_REQ, PID_TRUNC_MIN,
        )
        p = params
        bp = BASELINE_PARAMS
        rows_p = [
            (PID_MAX_POTENTIAL_CAP, "Max potential cap", _fmt_pct(p["trunkering_max"]), _fmt_pct(bp["trunkering_max"]),
             format_pp(p['trunkering_max'] - bp['trunkering_max']) if abs(p["trunkering_max"] - bp["trunkering_max"]) > 0.0001 else "-"),
            (PID_REALIZATION_TIME, "Realization time", f"{int(p['realiseringstid'])} yr", f"{int(bp['realiseringstid'])} yr",
             f"{int(p['realiseringstid'] - bp['realiseringstid']):+d} yr" if p["realiseringstid"] != bp["realiseringstid"] else "-"),
            (PID_CUSTOMER_SHARING, "Customer sharing", _fmt_pct(p["kunddelning"]), _fmt_pct(bp["kunddelning"]),
             format_pp(p['kunddelning'] - bp['kunddelning']) if abs(p["kunddelning"] - bp["kunddelning"]) > 0.0001 else "-"),
            (PID_MIN_ANNUAL_REQ, "Min annual requirement", _fmt_pct(p["outlier_krav"]), _fmt_pct(bp["outlier_krav"]),
             format_pp(p['outlier_krav'] - bp['outlier_krav']) if abs(p["outlier_krav"] - bp["outlier_krav"]) > 0.0001 else "-"),
            (PID_TRUNC_MIN, "Truncation min (derived)", _fmt_pct(p["trunkering_min"], 2), _fmt_pct(bl_trunkering_min, 2),
             format_pp(p['trunkering_min'] - bl_trunkering_min) if abs(p["trunkering_min"] - bl_trunkering_min) > 0.0001 else "-"),
        ]
        df_params = pd.DataFrame(rows_p, columns=["ID", "Parameter", "Case", "Baseline", "Delta"])
        st.dataframe(
            df_params,
            hide_index=True,
            width="stretch",
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Parameter": st.column_config.TextColumn("Parameter", width="medium"),
                "Case": st.column_config.TextColumn("Case", width="small"),
                "Baseline": st.column_config.TextColumn("Baseline", width="small"),
                "Delta": st.column_config.TextColumn("Delta", width="small"),
            },
        )


def _add_measure_row(rows, var_id, label, case_str, bl_str, case_val, bl_val, fmt="score"):
    """Add a row to the efficiency measures table."""
    delta_str = "-"
    if case_val is not None and bl_val is not None:
        delta = case_val - bl_val
        if abs(delta) > 0.0001:
            if fmt == "score":
                delta_str = f"{delta:+.3f}".replace(".", ",")
            elif fmt == "pp1":
                delta_str = format_pp(delta, decimals=1)
            elif fmt == "pp2":
                delta_str = format_pp(delta)
    rows.append({"ID": var_id, "Measure": label, "Case": case_str, "Baseline": bl_str, "Delta": delta_str})
