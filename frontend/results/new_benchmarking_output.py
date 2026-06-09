"""
new_benchmarking_output.py — render the new-benchmarking comparison for one company,
in sector context.

Layout (locked, see new_benchmarking_model/revisionsplan.md §5–§6):
  1. Sector overview — KPI row + Δ-requirement / Δ-efficiency histograms + efficiency
     distribution with truncation zones (all 148 companies, the selected firm marked).
  2. Your company — KPI row (score, requirement, raw/truncated potential, rank) plus a
     TOTEX bridge waterfall (current model → new model).

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
from config.formatting import format_percent, format_pp
from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
    COL_EFF_REQ_ANNUAL, COL_EFF_REQ_DELTA, COL_EFFICIENCY_DELTA,
    COL_TOTEX_NEW, COL_CONTROLLABLE_AVG, COL_CAPITAL_COST_2024,
    COL_LOSS_VALUED, COL_NONCTRL_SELECTED, COL_CAPITAL_COST_ENV_ADJ,
)
from calculations.new_benchmarking.config import NewBenchmarkingConfig
from calculations.new_benchmarking.model import NewBenchmarkingResult
from frontend.results._efficiency_charts import (
    calc_trunkering_min, render_efficiency_distributions,
    ordinal, get_baseline_trunkering_min, BASELINE_PARAMS,
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


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_company_view(
    result: NewBenchmarkingResult,
    user_reid: str,
    cfg: NewBenchmarkingConfig,
    user_label: str = "Your firm",
) -> None:
    """Full view: sector overview → company.

    user_label is the curated short company name used to mark the selected firm in the
    charts (falls back to "Your firm").
    """
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

    _render_sector_overview(result, user_reid, params, new_eff, cur_eff, new_req, cur_req, user_label)
    st.divider()
    _render_company_section(
        result, user_reid, params, dea_new, dea_cur,
        new_eff, cur_eff, new_pot, cur_pot, new_req, cur_req, is_outlier_new,
    )


# ---------------------------------------------------------------------------
# 1. Sector overview
# ---------------------------------------------------------------------------

def _render_sector_overview(result, user_reid, params, new_eff, cur_eff, new_req, cur_req, user_label="Your firm") -> None:
    st.markdown("#### Sector overview")
    st.caption(
        "How the efficiency requirement shifts across all 148 companies under the new model, "
        "versus their current published values. Your company is marked."
    )

    comp = result.comparison
    delta = comp[COL_EFF_REQ_DELTA].dropna()
    n = len(delta)
    n_higher = int((delta > _EPS).sum())
    n_lower = int((delta < -_EPS).sum())
    n_unchanged = n - n_higher - n_lower

    median_d = float(delta.median()) if n else None
    mean_d = float(delta.mean()) if n else None
    _req_help = "Across all 148 companies. Positive = higher requirement under the new model."

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric(
            "Median Δ requirement",
            format_pp(median_d) if median_d is not None else "–",
            help=_req_help,
        )
    with k2:
        st.metric(
            "Mean Δ requirement",
            format_pp(mean_d) if mean_d is not None else "–",
            help=_req_help,
        )
    with k3:
        st.metric("Higher requirement", f"{n_higher} / {n}")
    with k4:
        st.metric("Lower requirement", f"{n_lower} / {n}")
    with k5:
        st.metric("Unchanged", f"{n_unchanged} / {n}")

    tab_change, tab_levels = st.tabs(["Change (Δ)", "Levels"])
    with tab_change:
        st.caption("Change vs. the current published model, across all 148 companies.")
        c1, c2 = st.columns(2)
        with c1:
            _render_delta_histogram(
                comp, user_reid, value_col=COL_EFF_REQ_DELTA, scale=100.0,
                title="Δ requirement vs. current model", xtitle="Δ requirement (pp)",
                unit=" pp", decimals=2, color=CHART_COLORS[0], key="nb_delta_req",
                user_label=user_label,
            )
        with c2:
            _render_delta_histogram(
                comp, user_reid, value_col=COL_EFFICIENCY_DELTA, scale=1.0,
                title="Δ efficiency vs. current model", xtitle="Δ efficiency (score)",
                unit="", decimals=3, color=CHART_COLORS[1], key="nb_delta_eff",
                user_label=user_label,
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
    title: str, xtitle: str, unit: str, decimals: int, color: str, key: str,
    user_label: str = "Your firm",
) -> None:
    """Histogram of a per-firm delta in a single neutral colour; user firm marked.

    The good/bad reading is reserved for the deltas in the KPI row — the distribution
    itself is value-neutral. Direction is conveyed by the x-axis and the zero line.
    """
    d = comp[[COL_REID, value_col]].dropna(subset=[value_col]).copy()
    d["x"] = d[value_col] * scale

    user_x = None
    um = d[d[COL_REID] == user_reid]
    if not um.empty:
        user_x = float(um.iloc[0]["x"])

    hover = f"Δ: %{{x:+.{decimals}f}}{unit}<br>Companies: %{{y}}<extra></extra>"
    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=d["x"], nbinsx=20, marker_color=color, opacity=0.85,
        marker_line_color="white", marker_line_width=1, hovertemplate=hover,
        showlegend=False,
    ))

    if user_x is not None:
        fig.add_vline(x=user_x, line_dash="solid", line_color=COLORS["text_primary"], line_width=2)
        fig.add_annotation(
            x=user_x, y=0.92, yref="paper",
            text=f"<b>{user_label}: {user_x:+.{decimals}f}{unit}</b>", showarrow=False,
            font=dict(size=11, color=COLORS["text_primary"]),
            bgcolor="rgba(255,255,255,0.9)", borderpad=3, yanchor="bottom",
        )

    fig.update_layout(
        **layout_kwargs, template=template,
        title=dict(text=title, font=dict(size=13)),
        xaxis_title=xtitle, yaxis_title="Number of companies",
        height=340, bargap=0.03, dragmode=False,
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
    new_eff, cur_eff, new_pot, cur_pot, new_req, cur_req, is_outlier_new,
) -> None:
    """Row 1: five KPIs (new value + delta vs. the current published model, m5 style).
    Row 2: TOTEX waterfall placeholder (built later)."""
    st.markdown("#### Your company")

    # Truncated potential: clip raw potential into the truncation band. New side uses
    # this run's params; the current side uses Ei's baseline truncation, matching how the
    # published values were produced.
    pot_tr_new = (
        float(np.clip(new_pot, params["trunkering_min"], params["trunkering_max"]))
        if new_pot is not None else None
    )
    pot_tr_cur = (
        float(np.clip(cur_pot, get_baseline_trunkering_min(), BASELINE_PARAMS["trunkering_max"]))
        if cur_pot is not None else None
    )

    new_rank = _rank(dea_new, user_reid)
    cur_rank = _rank(dea_cur, user_reid)
    n_total = int(dea_new[COL_DEA_EFFICIENCY].notna().sum())

    def _d(new, cur):
        return (new - cur) if (new is not None and cur is not None) else None

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        d = _d(new_eff, cur_eff)
        st.metric(
            "Efficiency score",
            f"{new_eff:.3f}" if new_eff is not None else "–",
            delta=f"{d:+.3f}" if d is not None and abs(d) > _EPS else None,
        )
    with c2:
        d = _d(new_req, cur_req)
        st.metric(
            "Efficiency requirement",
            format_percent(new_req) if new_req is not None else "–",
            delta=format_pp(d) if d is not None and abs(d) > _EPS else None,
            delta_color="inverse",
        )
    with c3:
        d = _d(new_pot, cur_pot)
        st.metric(
            "Raw potential",
            format_percent(new_pot) if new_pot is not None else "–",
            delta=format_pp(d) if d is not None and abs(d) > _EPS else None,
            delta_color="inverse",
        )
    with c4:
        d = _d(pot_tr_new, pot_tr_cur)
        st.metric(
            "Truncated potential",
            format_percent(pot_tr_new) if pot_tr_new is not None else "–",
            delta=format_pp(d) if d is not None and abs(d) > _EPS else None,
            delta_color="inverse",
        )
    with c5:
        rank_delta = (cur_rank - new_rank) if (new_rank and cur_rank) else None
        st.metric(
            "Rank",
            f"{ordinal(new_rank)} / {n_total}" if new_rank else "–",
            delta=f"{rank_delta:+d}" if rank_delta else None,
        )

    st.caption(
        "Values are the new model; arrows show the change vs. the current published model.  ·  "
        f"Outlier: **{'Yes' if is_outlier_new else 'No'}**"
    )

    _render_totex_waterfall(result.totex, user_reid)


def _render_totex_waterfall(totex: pd.DataFrame, user_reid: str) -> None:
    """Bridge from the current-model TOTEX to the new-model TOTEX.

    A horizontal waterfall that starts and ends on a blue total bar (current → new),
    with the new ingredients in between: additions (network losses, selected
    non-controllable) in red, the placement-environment capex cut in green. Controllable
    cost is shared by both models, so it sits inside the unchanged opening total.
    """
    st.markdown("**New model TOTEX**")

    def g(col):
        return _val(totex, user_reid, col)

    controllable = g(COL_CONTROLLABLE_AVG)
    old_capex = g(COL_CAPITAL_COST_2024)
    losses = g(COL_LOSS_VALUED)
    nonctrl = g(COL_NONCTRL_SELECTED)
    new_capex = g(COL_CAPITAL_COST_ENV_ADJ)
    new_totex = g(COL_TOTEX_NEW)

    if None in (controllable, old_capex, losses, nonctrl, new_capex, new_totex):
        st.info("No TOTEX data for the selected company.")
        return

    old_totex = controllable + old_capex
    env_cut = new_capex - old_capex  # negative — the förläggningsmiljö reduction

    # Opening bar must be "absolute" (it sets the starting total); a "total" first bar
    # would compute the cumulative of nothing = 0 and render invisible. The closing bar
    # is "total" (cumulative). Both absolute/total bars are styled by `totals` (blue).
    rows = [
        ("Current model TOTEX",       old_totex,  "absolute"),
        ("Network losses",            losses,     "relative"),
        ("Selected non-controllable", nonctrl,    "relative"),
        ("Environment capex cut",     env_cut,    "relative"),
        ("New model TOTEX",           new_totex,  "total"),
    ]
    labels = [r[0] for r in rows]
    values = [r[1] / 1e3 for r in rows]  # tkr → MSEK
    measures = [r[2] for r in rows]
    hover = [
        f"<b>{l}</b><br>{v:,.1f} MSEK" if m != "relative" else f"<b>{l}</b><br>{v:+,.1f} MSEK"
        for l, v, m in zip(labels, values, measures)
    ]
    text = [
        f"{v:,.1f}" if m != "relative" else (f"{v:+,.1f}" if abs(v) > 0.05 else "±0")
        for v, m in zip(values, measures)
    ]

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure(go.Waterfall(
        orientation="h",
        y=labels, x=values, measure=measures,
        textposition="outside", text=text,
        textfont=dict(size=11, family="Inter, sans-serif"),
        connector=dict(line=dict(color=COLORS["bg_muted"], width=1, dash="dot")),
        increasing=dict(marker=dict(color=COLORS["error"])),    # additions raise cost → red
        decreasing=dict(marker=dict(color=COLORS["success"])),  # cut lowers cost → green
        totals=dict(marker=dict(color=COLORS["primary"])),      # current / new TOTEX → blue
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
    ))
    fig.update_layout(
        **layout_kwargs, template=template,
        margin=dict(l=10, r=80, t=10, b=40),
        height=max(300, len(labels) * 52), dragmode=False,
        xaxis=dict(title="MSEK", fixedrange=True, showgrid=False, zeroline=True,
                   zerolinecolor=COLORS["bg_muted"], linecolor=COLORS["bg_muted"]),
        yaxis=dict(fixedrange=True, showgrid=True, gridcolor=COLORS["bg_muted"],
                   tickson="boundaries", automargin=True, autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="nb_totex_waterfall")
    st.caption(
        "From the current benchmarking TOTEX to the new one: network losses (valued at a "
        "common price) and selected non-controllable costs are added; the placement-"
        "environment correction lowers capital cost. Controllable cost is unchanged."
    )
