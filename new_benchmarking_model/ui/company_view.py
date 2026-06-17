"""
company_view.py - render the new-benchmarking result for one company.

Built for the two-sided third-quartile mechanic (not the legacy front-reference model):
the headline is the firm's *signed outcome* under the new model - a deduction if it is
less efficient than the third-quartile benchmark E75, a reward if more efficient, full
cost coverage at the benchmark.

Layout (firm-first - the user's answer comes before the sector context):
  - Verdict (pinned on top): hero (deduction / coverage / reward) + supporting KPIs.
  - A horizontally-switched panel of thematic chart groups (see chart_panel.py), each
    shown at the same vertical position:
      * "Efficiency & outcome" - the position chart (efficiency histogram with the E75
        pivot, deduction/reward zones and the model's transfer curve) + the outcome
        distribution, the firm marked in both.
      * "TOTEX bridge" - waterfall from the current-model TOTEX to the new one.
    Add a theme by adding one entry to CHART_GROUPS (bottom of this file).

The two-sided visuals live in new_benchmarking_model/ui/charts.py (NOT the M5-shared
_efficiency_charts.py). The current model (EIs_DEA) is used only as the comparison point
for the outcome swing, not as a second mechanic to display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.common.styling import COLORS
from config.colors import get_plotly_template_safe
from config.formatting import format_percent, format_pp, format_tkr, format_delta
from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL, COL_DEA_REFERENCE,
    COL_TOTEX_NEW, COL_CONTROLLABLE_AVG,
    COL_LOSS_VALUED, COL_LOSS_ACTUAL, COL_CAPITAL_COST_ENV_ADJ,
    COL_NONCTRL_GRID_SUBSCRIPTION, COL_NONCTRL_GRID_CONNECTION,
    COL_NONCTRL_FEED_IN, COL_NONCTRL_CAPACITY_RESERVE,
    COL_CAPEX_CORR_CABLE, COL_CAPEX_CORR_STATION,
    COL_KR_CURRENT, COL_KR_NEW,
)
from new_benchmarking_model.config import NewBenchmarkingConfig
from new_benchmarking_model.model import NewBenchmarkingResult
from new_benchmarking_model.ui.charts import (
    render_position_chart, render_outcome_distribution,
    render_efficiency_scatter, render_requirement_scatter,
    render_channel_regression, render_shapley_waterfall,
    render_shapley_boxplots, render_shapley_by_urban_quantile,
    outcome_kind, KIND_REWARD, KIND_DEDUCTION,
)
from new_benchmarking_model.ui.chart_panel import ChartGroup, render_chart_panel
from new_benchmarking_model.data.analysis_loader import (
    load_channels, load_slopes, load_shapley, load_residual_decomp,
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


def _ordinal(n: int) -> str:
    suffix = "th" if 11 <= (n % 100) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _reference_e75(dea_new: pd.DataFrame) -> Optional[float]:
    """The third-quartile reference (constant column written by the two-sided mechanic)."""
    if COL_DEA_REFERENCE not in dea_new.columns or dea_new.empty:
        return None
    v = dea_new[COL_DEA_REFERENCE].iloc[0]
    return None if pd.isna(v) else float(v)


def _peer_label(dea_new: pd.DataFrame, e75: Optional[float]) -> Optional[str]:
    """Short name of the non-outlier firm whose efficiency is closest to E75."""
    if e75 is None:
        return None
    d = dea_new[~dea_new[COL_IS_OUTLIER].astype(bool)].dropna(subset=[COL_DEA_EFFICIENCY])
    if d.empty:
        return None
    reid = d.loc[(d[COL_DEA_EFFICIENCY] - e75).abs().idxmin(), COL_REID]
    from frontend.utils.company_directory import get_company_name_lookup
    return get_company_name_lookup().get(reid, reid)


# ---------------------------------------------------------------------------
# Group context — everything a thematic chart group needs for one company
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GroupContext:
    """Shared state handed to every thematic chart group (see CHART_GROUPS)."""
    result: NewBenchmarkingResult
    user_reid: str
    cfg: NewBenchmarkingConfig
    user_label: str
    e75: Optional[float]
    new_eff: Optional[float]
    new_out: Optional[float]


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_company_view(
    result: NewBenchmarkingResult,
    user_reid: str,
    cfg: NewBenchmarkingConfig,
    user_label: str = "Your firm",
) -> None:
    """Full view: verdict pinned on top, then the thematic chart panel.

    user_label is the curated short company name used to mark the selected firm.
    """
    dea_new = result.dea_new
    dea_cur = result.dea_current
    e75 = _reference_e75(dea_new)

    new_eff = _val(dea_new, user_reid, COL_DEA_EFFICIENCY)
    new_out = _val(dea_new, user_reid, COL_EFF_REQ_ANNUAL)      # signed outcome
    cur_req = _val(dea_cur, user_reid, COL_EFF_REQ_ANNUAL)      # current published requirement
    kr_cur = _val(result.totex, user_reid, COL_KR_CURRENT)      # current eff-req in tkr (OPEX base)
    kr_new = _val(result.totex, user_reid, COL_KR_NEW)          # new outcome in tkr (TOTEX base)
    is_outlier_new = _flag(dea_new, user_reid, COL_IS_OUTLIER)

    # Verdict stays pinned on top — the firm's answer, always visible.
    _render_verdict(dea_new, user_reid, e75, new_eff, new_out, cur_req, kr_cur, kr_new, is_outlier_new)
    st.divider()

    # Everything else is grouped thematically and switched horizontally (see chart_panel).
    ctx = GroupContext(
        result=result, user_reid=user_reid, cfg=cfg, user_label=user_label,
        e75=e75, new_eff=new_eff, new_out=new_out,
    )
    render_chart_panel(CHART_GROUPS, ctx)


# ---------------------------------------------------------------------------
# 1. Verdict (firm-first)
# ---------------------------------------------------------------------------

def _render_transition_hero(cur_req, new_out, kr_cur, kr_new) -> None:
    """From/to hero: how the requirement changes, current to new.

    Coloured by the kronor swing (the firm's actual money impact, since the two models
    apply their % to different bases), and surfacing the OPEX→TOTEX divergence in words
    when percent and kronor point different ways (the majority of companies).
    """
    if None in (cur_req, new_out, kr_cur, kr_new):
        st.info("No outcome available for this company.")
        return

    new_kind = outcome_kind(new_out)
    swing_pct = new_out - cur_req
    swing_kr = kr_new - kr_cur
    money_better = swing_kr < -_EPS
    money_worse = swing_kr > _EPS

    if new_kind == KIND_REWARD:
        new_phrase = (
            f"a reward of {format_percent(abs(new_out))}/yr "
            f"({format_tkr(abs(kr_new))} added to the cap over the period)"
        )
    elif new_kind == KIND_DEDUCTION:
        new_phrase = (
            f"a deduction of {format_percent(new_out)}/yr "
            f"({format_tkr(kr_new)} over the period)"
        )
    else:
        new_phrase = "full cost coverage (no change to the cap)"

    headline = (
        "Lower cost under the new model" if money_better
        else "Higher cost under the new model" if money_worse
        else "About the same cost under the new model"
    )
    body = (
        f"Your efficiency requirement goes from a deduction of {format_percent(cur_req)}/yr "
        f"({format_tkr(kr_cur)} over the period) to {new_phrase}."
    )

    # Divergence: percent improves but kronor worsens, or vice versa (52% of companies).
    pct_better = swing_pct < -_EPS
    if (pct_better and money_worse) or (swing_pct > _EPS and money_better):
        body += (
            f" Note that the requirement {'falls' if pct_better else 'rises'} in percentage "
            f"terms, but the amount in kronor {'rises' if money_worse else 'falls'} because "
            "the new model applies it to your full TOTEX instead of only OPEX."
        )

    msg = f"**{headline}**\n\n{body}"
    (st.success if money_better else st.warning if money_worse else st.info)(msg)


def _render_verdict(dea_new, user_reid, e75, new_eff, new_out, cur_req,
                    kr_cur, kr_new, is_outlier) -> None:
    st.markdown("#### Your company under the new model")

    _render_transition_hero(cur_req, new_out, kr_cur, kr_new)

    swing_pct = (new_out - cur_req) if (new_out is not None and cur_req is not None) else None
    swing_kr = (kr_new - kr_cur) if (kr_new is not None and kr_cur is not None) else None
    new_rank = _rank(dea_new, user_reid)
    n_total = int(dea_new[COL_DEA_EFFICIENCY].notna().sum())

    # KPI levels (no longer a restatement of the hero): the two requirements side by side
    # on their respective bases, the change in kronor, and the efficiency score. E₇₅ and
    # the distance to it live in the position chart below.
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Current requirement",
            f"{cur_req * 100:+.2f}%/yr" if cur_req is not None else "–",
            help="Today's published efficiency requirement (annual %). The kronor figure is "
                 "the 4-year period sum, applied to the OPEX (controllable) cost base.",
        )
        st.caption(format_tkr(kr_cur) if kr_cur is not None else "")
    with c2:
        st.metric(
            "New outcome",
            f"{new_out * 100:+.2f}%/yr" if new_out is not None else "–",
            help="Two-sided outcome under the new model (annual %); negative is a reward. The "
                 "kronor figure is the 4-year period sum, applied to the full TOTEX cost base.",
        )
        st.caption(format_tkr(kr_new) if kr_new is not None else "")
    with c3:
        st.metric(
            "Change in kronor",
            format_delta(swing_kr) if swing_kr is not None else "–",
            help="New minus current, in kronor over the period. Positive means a larger cost "
                 "under the new model. The percentage-point change is shown below.",
        )
        st.caption(f"{format_pp(swing_pct)} in the requirement" if swing_pct is not None else "")
    with c4:
        st.metric(
            "Efficiency score",
            f"{new_eff:.3f}" if new_eff is not None else "–",
            help="New-model DEA efficiency (0 to 1, where 1 is the frontier). Rank is among "
                 "the 148 companies.",
        )
        st.caption(f"Rank {_ordinal(new_rank)} / {n_total}" if new_rank else "")

    if is_outlier:
        st.caption(
            "This company is a DEA outlier, excluded from the benchmark percentile but "
            "still scored and given an outcome like any other frontier firm."
        )


# ---------------------------------------------------------------------------
# 2. Sector & position
# ---------------------------------------------------------------------------

def _render_sector_and_position(result, user_reid, cfg, e75, new_eff, new_out, user_label) -> None:
    dea_new = result.dea_new
    outcomes = dea_new[COL_EFF_REQ_ANNUAL]
    kinds = outcomes.map(outcome_kind)
    n = int(outcomes.notna().sum())
    n_ded = int((kinds == KIND_DEDUCTION).sum())
    n_rew = int((kinds == KIND_REWARD).sum())
    n_cov = n - n_ded - n_rew

    st.caption(
        "Where every company lands under the new model. The third-quartile benchmark E₇₅ "
        "splits the sector: companies below it get a deduction, the top quarter get full "
        "coverage or a reward."
    )
    k1, k2, k3 = st.columns(3)
    k1.metric("Deduction", f"{n_ded} / {n}")
    k2.metric("Full coverage", f"{n_cov} / {n}")
    k3.metric("Reward", f"{n_rew} / {n}")

    render_position_chart(
        dea_new[COL_DEA_EFFICIENCY].to_numpy(), e75, cfg, new_eff, user_label,
        peer_label=_peer_label(dea_new, e75),
    )
    render_outcome_distribution(outcomes.to_numpy(), new_out, user_label)


# ---------------------------------------------------------------------------
# 3. New model TOTEX bridge — two-phase (scope, then corrections)
# ---------------------------------------------------------------------------

# Full-width bands behind the two phases of the bridge.
_BAND_SCOPE = "rgba(37, 99, 235, 0.13)"    # primary tint — scope (new cost posts)
_BAND_CORRECTION = "rgba(217, 119, 6, 0.15)"  # amber tint — benchmarking corrections


def _render_totex_waterfall(totex: pd.DataFrame, user_reid: str) -> None:
    """Two-phase bridge from the old (legacy-scope) TOTEX to the new DEA TOTEX.

    Old TOTEX is controllable + unadjusted capital cost. The journey to the new DEA input
    is split into two phases that are kept visually separate (subtle background bands plus
    an intermediate subtotal bar), so "what the new model measures" and "how it corrects
    what it measures" never blur together:

      Scope        — cost posts the new model brings into the DEA input that the old did
                     not: network losses at their actual cost, selected non-controllable.
      Corrections  — the benchmarking adjustments to those posts: losses revalued to a
                     common price; capital cost levelled for placement environment.

    Each new post enters the scope phase at its *uncorrected* value, then the correction
    phase adjusts it — which is exactly what isolates scope from correction. The granular
    bars (non-controllable by category; capex correction by cable vs station) are exact and
    sum back to their aggregates. Everything reconstructs the totex frame:

        old + losses_actual + Σ non_ctrl_cat + (losses_common − losses_actual)
            + capex_cable + capex_station  ==  totex_new.

    Capex is KENT-consistent here (Alt B): old capex is KENT(unadjusted capbase), recovered
    as env_adjusted − cable − station, so the cable/station corrections close the bridge
    exactly. This is a visualisation-only choice — the DEA input and cost bases are
    untouched and still use the published baseline capital cost.
    """
    def g(col):
        return _val(totex, user_reid, col)

    controllable = g(COL_CONTROLLABLE_AVG)
    capex_env = g(COL_CAPITAL_COST_ENV_ADJ)
    cable_corr = g(COL_CAPEX_CORR_CABLE)
    station_corr = g(COL_CAPEX_CORR_STATION)
    loss_actual = g(COL_LOSS_ACTUAL)
    loss_common = g(COL_LOSS_VALUED)
    grid_sub = g(COL_NONCTRL_GRID_SUBSCRIPTION)
    grid_conn = g(COL_NONCTRL_GRID_CONNECTION)
    feed_in = g(COL_NONCTRL_FEED_IN)
    cap_res = g(COL_NONCTRL_CAPACITY_RESERVE)
    new_totex = g(COL_TOTEX_NEW)

    needed = (controllable, capex_env, cable_corr, station_corr, loss_actual, loss_common,
              grid_sub, grid_conn, feed_in, cap_res, new_totex)
    if None in needed:
        st.info("No TOTEX data for the selected company.")
        return

    # Old capex = KENT(unadjusted) = env-adjusted minus the two corrections (Alt B), so the
    # cable/station bars close the bridge exactly.
    old_capex = capex_env - cable_corr - station_corr
    old_totex = controllable + old_capex
    nonctrl_sum = grid_sub + grid_conn + feed_in + cap_res
    subtotal = old_totex + loss_actual + nonctrl_sum   # end of the scope phase (uncorrected)
    loss_reval = loss_common - loss_actual              # correction: common price vs actual

    # Opening bar is "absolute" (it sets the starting total); the two "total" bars (the
    # scope subtotal and the final TOTEX) show the running cumulative. Order top→bottom
    # reads as the journey (y-axis is reversed below).
    rows = [
        ("Old TOTEX",                       old_totex,    "absolute"),
        ("Network losses (actual)",         loss_actual,  "relative"),
        ("Grid subscription",               grid_sub,     "relative"),
        ("Grid connection",                 grid_conn,    "relative"),
        ("Feed-in compensation",            feed_in,      "relative"),
        ("Capacity reserve",                cap_res,      "relative"),
        ("New-scope TOTEX (uncorrected)",   subtotal,     "total"),
        ("Losses → common price",           loss_reval,   "relative"),
        ("Capex: cable (jordkabel)",        cable_corr,   "relative"),
        ("Capex: station (nätstation)",     station_corr, "relative"),
        ("New TOTEX (DEA)",                 new_totex,    "total"),
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
        decreasing=dict(marker=dict(color=COLORS["success"])),  # cuts lower cost → green
        totals=dict(marker=dict(color=COLORS["primary"])),      # old / subtotal / new → blue
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
    ))

    # Phase bands (numeric y maps to category index): scope spans rows 0–6 (the opening Old
    # TOTEX, the scope additions, and the uncorrected subtotal they build), corrections spans
    # rows 7–10 (the two corrections plus the final TOTEX they land on). The floating relative
    # bars sit far to the right, so the phase labels go in the empty left of the plot.
    fig.add_hrect(y0=-0.5, y1=6.5, fillcolor=_BAND_SCOPE, line_width=0, layer="below")
    fig.add_hrect(y0=6.5, y1=10.5, fillcolor=_BAND_CORRECTION, line_width=0, layer="below")
    for y_pos, label in ((3.0, "Scope"), (8.5, "Corrections")):
        fig.add_annotation(
            xref="paper", x=0.01, y=y_pos, yref="y", text=f"<b>{label}</b>",
            showarrow=False, xanchor="left", yanchor="middle",
            font=dict(size=12, color=COLORS["text_secondary"]),
        )

    # Zero-value markers: a relative step that rounds to ~0 renders as an invisible bar (an
    # odd gap in the bridge). Mark it with a thin vertical tick at its cumulative position —
    # the same treatment as the M5 cost-impact waterfall (frontend/results/m5_efficiency_output).
    running = 0.0
    zero_x, zero_y = [], []
    for label, val, measure in zip(labels, values, measures):
        if measure == "absolute":
            running = val
        elif measure == "relative":
            if abs(val) < 0.05:
                zero_x.append(running)
                zero_y.append(label)
            running += val
    if zero_y:
        fig.add_trace(go.Scatter(
            x=zero_x, y=zero_y, mode="markers",
            marker=dict(symbol="line-ns", size=16,
                        line=dict(width=2, color=COLORS["text_muted"]),
                        color=COLORS["text_muted"]),
            showlegend=False, hoverinfo="skip",
        ))

    fig.update_layout(
        **layout_kwargs, template=template,
        margin=dict(l=10, r=80, t=10, b=40),
        height=max(300, len(labels) * 52), dragmode=False, showlegend=False,
        xaxis=dict(title="MSEK", fixedrange=True, showgrid=False, zeroline=True,
                   zerolinecolor=COLORS["bg_muted"], linecolor=COLORS["bg_muted"]),
        yaxis=dict(fixedrange=True, showgrid=True, gridcolor=COLORS["bg_muted"],
                   tickson="boundaries", automargin=True, autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="nb_totex_waterfall")
    st.caption(
        "From the old TOTEX (controllable + unadjusted capital cost) to the new DEA TOTEX, "
        "in two phases. **Scope** (blue band) adds the cost posts the new model measures but "
        "the old did not — network losses at their actual cost and the non-controllable "
        "categories (grid subscription, grid connection, feed-in compensation, capacity "
        "reserve). **Corrections** (amber band) then apply the benchmarking adjustments: "
        "losses revalued to a common price, and the placement-environment capital-cost "
        "levelling split into cable (jordkabel) and station (nätstation)."
    )


# ---------------------------------------------------------------------------
# Thematic chart groups (registry)
# ---------------------------------------------------------------------------
# The horizontal panel below the verdict is built from this list. Each group is a theme
# rendered at the same vertical position; the panel (chart_panel.render_chart_panel) owns
# the horizontal switcher. Add a theme by adding one ChartGroup entry — e.g. a future
# "New vs current" group with scatter plots of efficiency and the requirement.


def _group_efficiency_outcome(ctx: GroupContext) -> None:
    """Efficiency histogram + signed-outcome distribution (firm marked in both), then the
    two narrower new-vs-current scatters side by side."""
    _render_sector_and_position(
        ctx.result, ctx.user_reid, ctx.cfg, ctx.e75, ctx.new_eff, ctx.new_out, ctx.user_label
    )

    st.markdown("###### New vs current, company by company")
    left, right = st.columns(2)
    with left:
        render_efficiency_scatter(ctx.result.comparison, ctx.user_reid, ctx.user_label)
    with right:
        render_requirement_scatter(ctx.result.comparison, ctx.user_reid, ctx.user_label)
    st.caption(
        "Each point is a company: new model (vertical) against current model (horizontal); "
        "the dotted line is no change. Left — efficiency: above the line means more efficient "
        "under the new model. Right — efficiency requirement (%/yr): below the line is a "
        "smaller requirement, and below zero is a reward (only the new model can go negative). "
        "Your company is highlighted."
    )


def _group_totex_bridge(ctx: GroupContext) -> None:
    """Waterfall bridging the current-model TOTEX to the new-model TOTEX."""
    _render_totex_waterfall(ctx.result.totex, ctx.user_reid)


def _group_placeholder(ctx: GroupContext) -> None:
    """Sector-level decomposition of the new-model outcome (committed analysis tables).

    These figures describe the MAIN model's structure and are identical for every user
    (the firm is only highlighted): they are read from the precomputed analysis tables, not
    recomputed per run, so an active experiment does not change them — we say so when one is
    running, then always show the main-model analysis.
    """
    is_main = ctx.cfg.signature() == NewBenchmarkingConfig().signature()
    if not is_main:
        st.caption(
            "ⓘ These figures reflect the **main model** — the analysis is precomputed and "
            "not affected by experiment settings."
        )

    channels, slopes, shapley = load_channels(), load_slopes(), load_shapley()
    if channels is None or slopes is None or shapley is None:
        st.info("The decomposition analysis tables are not available.")
        return
    decomp = load_residual_decomp()   # optional; the waterfall falls back to one residual bar

    # The distribution charts show all six terms: the four cost components (shapley) plus the
    # two structural terms (mechanic, input) from the residual split, merged in when present.
    shapley_terms = shapley
    if decomp is not None and all(c in decomp.columns for c in ("phi_mechanic", "phi_input")):
        shapley_terms = shapley.merge(
            decomp[["REId", "phi_mechanic", "phi_input"]], on="REId", how="left"
        )

    render_channel_regression(channels, slopes)
    st.divider()
    render_shapley_waterfall(shapley, decomp)
    st.divider()
    render_shapley_boxplots(shapley_terms, ctx.user_reid, ctx.user_label)
    st.divider()
    render_shapley_by_urban_quantile(shapley_terms, channels, ctx.user_reid)


CHART_GROUPS = [
    ChartGroup("efficiency_outcome", "Efficiency & outcome", _group_efficiency_outcome),
    ChartGroup("totex_bridge", "TOTEX bridge", _group_totex_bridge),
    ChartGroup("placeholder", "Placeholder", _group_placeholder),
]

