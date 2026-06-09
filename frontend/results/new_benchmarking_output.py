"""
new_benchmarking_output.py — render the new-benchmarking comparison for one company,
in sector context.

Layout (locked, see new_benchmarking_model/revisionsplan.md §5–§6):
  1. Sector overview — KPI row + Δ-requirement histogram + efficiency distribution
     with truncation zones (all 148 companies, the selected firm marked).
  2. Your company — headline requirement change, efficiency summary, TOTEX placeholder.
  3. Explore — Δ requirement vs. a selectable structural variable.

The headline metric is the efficiency-requirement change (NEW model vs CURRENT/EIs_DEA),
since efficiency *scores* live on each model's own frontier and are only secondary context.
Reuses the shared efficiency visualisations (frontend/results/_efficiency_charts.py),
mapping NEW model → "case" and CURRENT model (EIs_DEA) → "baseline".
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.common.styling import COLORS, CHART_COLORS
from config.colors import get_plotly_template_safe
from config.formatting import format_percent, format_pp, format_number
from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
    COL_EFF_REQ_ANNUAL, COL_TOTEX_NEW, COL_CU, COL_CABLE_LENGTH_KM,
    COL_EFF_REQ_DELTA, COL_EFFICIENCY_DELTA,
)
from calculations.new_benchmarking.config import NewBenchmarkingConfig
from calculations.new_benchmarking.model import NewBenchmarkingResult
from calculations.new_benchmarking.environment_capex_adjustment import config as env_C
from frontend.results._efficiency_charts import (
    calc_trunkering_min, render_efficiency_summary, render_efficiency_distributions,
)

_EPS = 1e-5


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _val(df: pd.DataFrame, reid: str, col: str) -> Optional[float]:
    """Single value for a company, or None if missing/NaN."""
    if col not in df.columns:
        return None
    m = df[df[COL_REID] == reid]
    if m.empty:
        return None
    v = m.iloc[0][col]
    return None if pd.isna(v) else float(v)


def _flag(df: pd.DataFrame, reid: str, col: str) -> bool:
    m = df[df[COL_REID] == reid]
    return bool(m.iloc[0][col]) if not m.empty and col in df.columns else False


def _rank(df: pd.DataFrame, reid: str, eff_col: str = COL_DEA_EFFICIENCY) -> Optional[int]:
    """1-based rank by efficiency (1 = most efficient). None if the firm has no score."""
    d = df[[COL_REID, eff_col]].dropna(subset=[eff_col]).sort_values(
        eff_col, ascending=False).reset_index(drop=True)
    idx = d.index[d[COL_REID] == reid]
    return int(idx[0]) + 1 if len(idx) else None


def _params_from_cfg(cfg: NewBenchmarkingConfig) -> dict:
    """Map cfg.eff_req_params to the keys the efficiency charts expect."""
    p = cfg.eff_req_params
    params = {
        "trunkering_max": p["truncation_max"],
        "realiseringstid": p["realization_time"],
        "kunddelning": p["customer_sharing"],
        "outlier_krav": p["outlier_req"],
        "tillsynsperiod": p["supervision_period"],
    }
    params["trunkering_min"] = calc_trunkering_min(
        params["outlier_krav"], params["kunddelning"],
        params["realiseringstid"], params["tillsynsperiod"],
    )
    return params


def _env_exposure(result: NewBenchmarkingResult) -> pd.DataFrame:
    """Per-company placement-environment capex cut [%] (cable + station, value-weighted)."""
    cab = result.env_capex.cable_adjustment.per_company
    sta = result.env_capex.station_adjustment.per_company
    c = cab[[env_C.COL_REID, env_C.COL_VALUE, env_C.COL_DEDUCTION]].rename(
        columns={env_C.COL_VALUE: "cv", env_C.COL_DEDUCTION: "cd"})
    s = sta[[env_C.COL_REID, env_C.COL_VALUE, env_C.COL_DEDUCTION]].rename(
        columns={env_C.COL_VALUE: "sv", env_C.COL_DEDUCTION: "sd"})
    m = c.merge(s, on=env_C.COL_REID, how="outer").fillna(0.0)
    total = (m["cv"] + m["sv"]).replace(0, np.nan)
    m["env_cut_pct"] = (m["cd"] + m["sd"]) / total * 100
    return m[[env_C.COL_REID, "env_cut_pct"]].rename(columns={env_C.COL_REID: COL_REID})


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_company_view(
    result: NewBenchmarkingResult,
    user_reid: str,
    cfg: NewBenchmarkingConfig,
) -> None:
    """Full view: sector overview → company → explore."""
    dea_new = result.dea_new
    dea_cur = result.dea_current
    params = _params_from_cfg(cfg)

    new_eff = _val(dea_new, user_reid, COL_DEA_EFFICIENCY)
    cur_eff = _val(dea_cur, user_reid, COL_DEA_EFFICIENCY)
    new_pot = _val(dea_new, user_reid, COL_DEA_POTENTIAL)
    cur_pot = _val(dea_cur, user_reid, COL_DEA_POTENTIAL)
    new_req = _val(dea_new, user_reid, COL_EFF_REQ_ANNUAL)
    cur_req = _val(dea_cur, user_reid, COL_EFF_REQ_ANNUAL)
    is_outlier_new = _flag(dea_new, user_reid, COL_IS_OUTLIER)
    super_eff = _val(dea_new, user_reid, COL_DEA_SUPER_EFF)
    super_eff = super_eff if (super_eff is not None and super_eff >= 1.0) else None

    _render_sector_overview(result, user_reid, params, new_eff, cur_eff, new_req, cur_req)
    st.divider()
    _render_company_section(
        result, user_reid, params, dea_new, dea_cur,
        new_eff, cur_eff, new_pot, cur_pot, new_req, cur_req, is_outlier_new, super_eff,
    )
    st.divider()
    _render_explore(result, user_reid)


# ---------------------------------------------------------------------------
# 1. Sector overview
# ---------------------------------------------------------------------------

def _render_sector_overview(result, user_reid, params, new_eff, cur_eff, new_req, cur_req) -> None:
    st.markdown("#### Sector overview")
    st.caption(
        "How the efficiency requirement shifts across all 148 companies under the new model, "
        "versus their current published values (EIs_DEA). Your company is marked."
    )

    comp = result.comparison
    delta = comp[COL_EFF_REQ_DELTA].dropna()
    n = len(delta)
    n_higher = int((delta > _EPS).sum())
    n_lower = int((delta < -_EPS).sum())
    n_unchanged = n - n_higher - n_lower

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(
            "Median Δ requirement",
            format_pp(float(delta.median())) if n else "–",
            help=f"Mean: {format_pp(float(delta.mean())) if n else '–'}. "
                 "Positive = higher requirement under the new model.",
        )
    with k2:
        st.metric("Higher requirement", f"{n_higher} / {n}")
    with k3:
        st.metric("Lower requirement", f"{n_lower} / {n}")
    with k4:
        st.metric("Unchanged", f"{n_unchanged} / {n}")

    tab_change, tab_levels = st.tabs(["Change (Δ)", "Levels"])
    with tab_change:
        st.caption("Change vs. the current published model (EIs_DEA), across all 148 companies.")
        c1, c2 = st.columns(2)
        with c1:
            _render_delta_histogram(
                comp, user_reid, value_col=COL_EFF_REQ_DELTA, scale=100.0,
                title="Δ requirement vs. current model", xtitle="Δ requirement (pp)",
                unit=" pp", decimals=2, good_is_negative=True,
                good_label="Lower (better)", bad_label="Higher (worse)", key="nb_delta_req",
            )
        with c2:
            _render_delta_histogram(
                comp, user_reid, value_col=COL_EFFICIENCY_DELTA, scale=1.0,
                title="Δ efficiency vs. current model", xtitle="Δ efficiency (score)",
                unit="", decimals=3, good_is_negative=False,
                good_label="Higher (better)", bad_label="Lower (worse)", key="nb_delta_eff",
            )
    with tab_levels:
        dea_new = result.dea_new
        eff_scores = dea_new[COL_DEA_EFFICIENCY].dropna().to_numpy()
        render_efficiency_distributions(
            eff_scores=eff_scores, eff_case=new_eff, eff_baseline=cur_eff,
            effkrav_all_df=dea_new, effkrav_case=new_req, effkrav_baseline=cur_req,
            params=params, key_prefix="nb",
        )
        _render_zone_breakdown(dea_new, params)


def _render_delta_histogram(
    comp: pd.DataFrame, user_reid: str, *, value_col: str, scale: float,
    title: str, xtitle: str, unit: str, decimals: int, good_is_negative: bool,
    good_label: str, bad_label: str, key: str,
) -> None:
    """Histogram of a per-firm delta; user firm marked.

    Colour split at 0 by which side is "good": green = better, red = worse. The good
    side is negative for the requirement (lower = better) and positive for the
    efficiency score (higher = better).
    """
    d = comp[[COL_REID, value_col]].dropna(subset=[value_col]).copy()
    d["x"] = d[value_col] * scale
    if good_is_negative:
        good, bad = d.loc[d["x"] <= 0, "x"], d.loc[d["x"] > 0, "x"]
    else:
        good, bad = d.loc[d["x"] >= 0, "x"], d.loc[d["x"] < 0, "x"]

    user_x = None
    um = d[d[COL_REID] == user_reid]
    if not um.empty:
        user_x = float(um.iloc[0]["x"])

    hover = f"Δ: %{{x:+.{decimals}f}}{unit}<br>Companies: %{{y}}<extra></extra>"
    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=good, nbinsx=20, marker_color=COLORS["success"], opacity=0.8,
        marker_line_color="white", marker_line_width=1, name=good_label, hovertemplate=hover,
    ))
    fig.add_trace(go.Histogram(
        x=bad, nbinsx=20, marker_color=COLORS["error"], opacity=0.8,
        marker_line_color="white", marker_line_width=1, name=bad_label, hovertemplate=hover,
    ))

    if user_x is not None:
        fig.add_vline(x=user_x, line_dash="solid", line_color=COLORS["text_primary"], line_width=2)
        fig.add_annotation(
            x=user_x, y=0.92, yref="paper",
            text=f"<b>Your firm: {user_x:+.{decimals}f}{unit}</b>", showarrow=False,
            font=dict(size=11, color=COLORS["text_primary"]),
            bgcolor="rgba(255,255,255,0.9)", borderpad=3, yanchor="bottom",
        )

    fig.update_layout(
        **layout_kwargs, template=template, barmode="overlay",
        title=dict(text=title, font=dict(size=13)),
        xaxis_title=xtitle, yaxis_title="Number of companies",
        height=340, bargap=0.03, dragmode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        xaxis=dict(fixedrange=True, showgrid=False, zeroline=True,
                   zerolinecolor=COLORS["bg_muted"], linecolor=COLORS["bg_muted"]),
        yaxis=dict(fixedrange=True, gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"]),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)


def _render_zone_breakdown(dea_new: pd.DataFrame, params: dict) -> None:
    """Counts and share of companies in each truncation zone (cap / active / floor)."""
    scores = dea_new[COL_DEA_EFFICIENCY].dropna().to_numpy()
    n = len(scores)
    if n == 0:
        return
    eff_cap = 1 - params["trunkering_max"]
    eff_floor = 1 - params["trunkering_min"]
    capped = int((scores < eff_cap).sum())
    floored = int((scores > eff_floor).sum())
    active = n - capped - floored
    st.caption(
        f"Truncation zones — "
        f"Capped: {capped} ({capped / n:.0%}) · "
        f"Active: {active} ({active / n:.0%}) · "
        f"Floored: {floored} ({floored / n:.0%})"
    )


# ---------------------------------------------------------------------------
# 2. Your company
# ---------------------------------------------------------------------------

def _render_company_section(
    result, user_reid, params, dea_new, dea_cur,
    new_eff, cur_eff, new_pot, cur_pot, new_req, cur_req, is_outlier_new, super_eff,
) -> None:
    st.markdown("#### Your company")

    # Headline: efficiency-requirement change.
    h1, h2, h3 = st.columns(3)
    delta = (new_req - cur_req) if (new_req is not None and cur_req is not None) else None
    with h1:
        st.metric("Current (EIs_DEA)", format_percent(cur_req) if cur_req is not None else "–")
    with h2:
        st.metric(
            "New requirement (new model)",
            format_percent(new_req) if new_req is not None else "–",
            delta=format_pp(delta) if delta is not None and abs(delta) > _EPS else None,
            delta_color="inverse",
        )
    with h3:
        st.metric(
            "Change",
            format_pp(delta) if delta is not None else "–",
            help="Positive = higher efficiency requirement under the new model.",
        )
    st.caption(
        "Current values come directly from Ei's published DEA (EIs_DEA). Efficiency scores "
        "below are measured against each model's own frontier and are therefore secondary "
        "context — the requirement change above is the headline result."
    )

    # Reused KPI summary (case = new, baseline = current).
    render_efficiency_summary(
        eff_case=new_eff, eff_baseline=cur_eff,
        potential_case=new_pot, potential_baseline=cur_pot,
        effkrav_case=new_req, effkrav_baseline=cur_req,
        is_outlier=is_outlier_new, super_eff=super_eff,
        case_rank=_rank(dea_new, user_reid), bl_rank=_rank(dea_cur, user_reid),
        n_total=len(dea_new), params=params, show_detail_tables=True,
    )
    st.caption("'Case' = new model · 'Baseline' = current model (EIs_DEA).")

    _render_totex_placeholder(result.totex, user_reid)


def _render_totex_placeholder(totex: pd.DataFrame, user_reid: str) -> None:
    """V1 placeholder: show the new-model TOTEX total only; build-up comes later."""
    st.markdown("**New model TOTEX**")
    total = _val(totex, user_reid, COL_TOTEX_NEW)
    if total is None:
        st.info("No TOTEX data for the selected company.")
        return
    st.metric("New model TOTEX", f"{format_number(total / 1e3, 1)} MSEK/yr")
    st.caption("Detailed TOTEX build-up (waterfall and components) coming in a later version.")


# ---------------------------------------------------------------------------
# 3. Explore
# ---------------------------------------------------------------------------

_STRUCTURAL_VARS = {
    "Customer density (customers/km)": "_density",
    "Size (connection points)": "_size",
    "Cable length (km)": "_length",
    "Environment capex cut (%)": "_envcut",
}


def _render_explore(result: NewBenchmarkingResult, user_reid: str) -> None:
    st.markdown("#### Explore")
    st.caption(
        "Is the requirement change driven by structure? Each point is a company; "
        "your firm is highlighted. Tests whether the new model relieves firms with a "
        "harder environment or lower customer density, as intended."
    )

    inputs = result.new_model_inputs
    comp = result.comparison[[COL_REID, COL_EFF_REQ_DELTA]].dropna(subset=[COL_EFF_REQ_DELTA])

    if COL_CABLE_LENGTH_KM not in inputs.columns or COL_CU not in inputs.columns:
        st.info("Structural variables unavailable for this run.")
        return

    df = comp.merge(inputs[[COL_REID, COL_CU, COL_CABLE_LENGTH_KM]], on=COL_REID, how="left")
    df = df.merge(_env_exposure(result), on=COL_REID, how="left")
    df["_size"] = df[COL_CU]
    df["_length"] = df[COL_CABLE_LENGTH_KM]
    df["_density"] = df[COL_CU] / df[COL_CABLE_LENGTH_KM].replace(0, np.nan)
    df["_envcut"] = df["env_cut_pct"]
    df["_dy"] = df[COL_EFF_REQ_DELTA] * 100  # pp

    label = st.selectbox("X-axis", options=list(_STRUCTURAL_VARS.keys()), key="nb_explore_var")
    xcol = _STRUCTURAL_VARS[label]

    plot_df = df.dropna(subset=[xcol, "_dy"])
    others = plot_df[plot_df[COL_REID] != user_reid]
    user = plot_df[plot_df[COL_REID] == user_reid]

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=others[xcol], y=others["_dy"], mode="markers",
        marker=dict(size=7, color=CHART_COLORS[0], opacity=0.55, line=dict(width=0)),
        name="Companies",
        hovertemplate=f"{label}: %{{x:,.2f}}<br>Δ requirement: %{{y:+.2f}} pp<extra></extra>",
    ))
    if not user.empty:
        fig.add_trace(go.Scatter(
            x=user[xcol], y=user["_dy"], mode="markers",
            marker=dict(size=14, color=COLORS["text_primary"], symbol="diamond",
                        line=dict(width=1.5, color="white")),
            name="Your firm",
            hovertemplate=f"<b>Your firm</b><br>{label}: %{{x:,.2f}}<br>Δ: %{{y:+.2f}} pp<extra></extra>",
        ))

    fig.update_layout(
        **layout_kwargs, template=template,
        height=420, dragmode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        xaxis_title=label, yaxis_title="Δ requirement (pp)",
        xaxis=dict(fixedrange=True, showgrid=True, gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"]),
        yaxis=dict(fixedrange=True, zeroline=True, zerolinecolor=COLORS["bg_muted"],
                   gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"]),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="nb_explore_scatter")
