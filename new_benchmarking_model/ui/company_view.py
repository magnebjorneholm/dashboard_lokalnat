"""
company_view.py - render the new-benchmarking result for one company.

Built for the two-sided third-quartile mechanic (not the legacy front-reference model):
the headline is the firm's *signed outcome* under the new model - a deduction if it is
less efficient than the third-quartile benchmark E75, a reward if more efficient, full
cost coverage at the benchmark.

Layout (firm-first - the user's answer comes before the sector context):
  - Verdict (pinned on top): hero (deduction / coverage / reward) + supporting KPIs.
  - The thematic chart groups (see chart_panel.py), stacked vertically under their own
    headings (the user scrolls through them):
      * "Efficiency & outcome" - the position chart (efficiency histogram with the E75
        pivot, deduction/reward zones and the model's transfer curve) + the outcome
        distribution, the firm marked in both.
      * "TOTEX bridge" - waterfall from the current-model TOTEX to the new one.
    A third group, "Outcome decomposition", is built and wired but hidden for V1 (see
    HIDDEN_CHART_GROUPS at the bottom of this file). Add a theme by adding one entry to
    CHART_GROUPS (bottom of this file).

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
    render_efficiency_scatter, render_requirement_scatter, render_rank_scatter,
    render_channel_regression, render_shapley_waterfall,
    render_shapley_boxplots, render_shapley_by_urban_quantile,
    outcome_kind, revenue_frame_impact, KIND_REWARD, KIND_DEDUCTION,
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


def _reference_e75(dea_new: pd.DataFrame) -> Optional[float]:
    """The third-quartile reference (constant column written by the two-sided mechanic)."""
    if COL_DEA_REFERENCE not in dea_new.columns or dea_new.empty:
        return None
    v = dea_new[COL_DEA_REFERENCE].iloc[0]
    return None if pd.isna(v) else float(v)


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
    _render_verdict(dea_new, dea_cur, user_reid, e75, new_eff, new_out, cur_req, kr_cur, kr_new, is_outlier_new, user_label)
    st.divider()

    # Everything else is grouped thematically and stacked vertically (see chart_panel).
    ctx = GroupContext(
        result=result, user_reid=user_reid, cfg=cfg, user_label=user_label,
        e75=e75, new_eff=new_eff, new_out=new_out,
    )
    render_chart_panel(CHART_GROUPS, ctx)


# ---------------------------------------------------------------------------
# 1. Verdict (firm-first)
# ---------------------------------------------------------------------------

def _render_transition_hero(cur_req, new_out, kr_cur, kr_new) -> None:
    """From/to hero: how the new benchmarking model changes the revenue frame vs the current
    model.

    The page isolates the benchmarking change, all else equal, so the headline is the change
    relative to the current model (does the reform raise or lower the cap?). Coloured by the
    kronor swing (the firm's actual money impact, since the two models apply their % to
    different bases), and surfacing the OPEX→TOTEX divergence in words when percent and
    kronor point different ways (the majority of companies).
    """
    if None in (cur_req, new_out, kr_cur, kr_new):
        st.info("No outcome available for this company.")
        return

    new_kind = outcome_kind(new_out)
    # Revenue-frame swings, new vs current (>0 = the new model raises the cap relative to today).
    swing_pct = cur_req - new_out
    swing_kr = kr_cur - kr_new
    money_better = swing_kr > _EPS
    money_worse = swing_kr < -_EPS

    if new_kind == KIND_REWARD:
        new_phrase = (
            f"raising it by {format_percent(abs(new_out))}/yr "
            f"({format_tkr(abs(kr_new))} added to the cap over the period)"
        )
    elif new_kind == KIND_DEDUCTION:
        new_phrase = (
            f"lowering it by {format_percent(new_out)}/yr "
            f"({format_tkr(kr_new)} removed over the period)"
        )
    else:
        new_phrase = "full cost coverage (no change to the cap)"

    headline = (
        "The new benchmarking model raises your revenue frame" if money_better
        else "The new benchmarking model lowers your revenue frame" if money_worse
        else "The new benchmarking model leaves your revenue frame about unchanged"
    )
    body = (
        f"Compared with the current model, your efficiency requirement goes from lowering the "
        f"cap by {format_percent(cur_req)}/yr ({format_tkr(kr_cur)} over the period) to {new_phrase}."
    )

    # Divergence: the reform helps the cap in percentage terms but hurts it in kronor, or vice
    # versa (the majority of companies), because the new model applies it to the full TOTEX.
    pct_better = swing_pct > _EPS
    if (pct_better and money_worse) or (swing_pct < -_EPS and money_better):
        body += (
            f" Note that in percentage terms the new model is {'more' if pct_better else 'less'} "
            "favourable to your cap, but the kronor effect points the other way, because the new "
            "model applies the requirement to your full TOTEX instead of only OPEX."
        )

    msg = f"**{headline}**\n\n{body}"
    (st.success if money_better else st.warning if money_worse else st.info)(msg)


def _render_verdict(dea_new, dea_cur, user_reid, e75, new_eff, new_out, cur_req,
                    kr_cur, kr_new, is_outlier, user_label="Your company") -> None:
    st.markdown(f"#### {user_label} under the new model")

    _render_transition_hero(cur_req, new_out, kr_cur, kr_new)

    # Each card shows where the firm lands under the new model, with the change versus the
    # current model as a coloured st.metric delta (green = the new model raises the cap /
    # improves the position; Streamlit reads the delta string's sign). Everything is in
    # revenue-frame terms (positive raises the cap). The page isolates the benchmarking
    # change, all else equal, so the delta IS the reform's effect on each dimension.
    new_impact = revenue_frame_impact(new_out)
    swing_pct = (cur_req - new_out) if (new_out is not None and cur_req is not None) else None
    swing_kr = (kr_cur - kr_new) if (kr_new is not None and kr_cur is not None) else None
    cur_eff = _val(dea_cur, user_reid, COL_DEA_EFFICIENCY)
    new_rank = _rank(dea_new, user_reid)
    cur_rank = _rank(dea_cur, user_reid)
    n_total = int(dea_new[COL_DEA_EFFICIENCY].notna().sum())

    # Each delta is "<change> <unit> from <current-model value>" so the colour-coded arrow and
    # the baseline it is measured against read in one line. Streamlit colours the delta on its
    # leading sign only (st.metric / _is_negative_delta), so the trailing "from ..." is inert.
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cur_impact = revenue_frame_impact(cur_req)
        delta = (f"{format_pp(swing_pct)} from {cur_impact * 100:+.2f}%/yr"
                 if swing_pct is not None and cur_impact is not None else None)
        st.metric(
            "Efficiency requirement",
            f"{new_impact * 100:+.2f}%/yr" if new_impact is not None else "–",
            delta,
            help="The new model's outcome as its impact on the revenue frame (annual %); "
                 "positive raises the cap. The delta is the change from the current model.",
        )
    with c2:
        delta = (f"{format_delta(swing_kr)} from {format_delta(-kr_cur)}"
                 if swing_kr is not None and kr_cur is not None else None)
        st.metric(
            "In kronor",
            format_delta(-kr_new) if kr_new is not None else "–",
            delta,
            help="The same outcome in kronor over the 4-year period; the new model applies it "
                 "to the full TOTEX base. The delta is the change from the current model "
                 "(OPEX base) - a firm can improve in % yet worsen in kronor.",
        )
    with c3:
        places = (cur_rank - new_rank) if (new_rank is not None and cur_rank is not None) else None
        st.metric(
            "Rank",
            f"{new_rank} / {n_total}" if new_rank else "–",
            f"{places:+d} places from {cur_rank}" if places else None,
            help="Efficiency rank under the new model (1 = most efficient). The delta is how "
                 "many places the firm moves from its current-model rank; up is better.",
        )
    with c4:
        eff_delta = (new_eff - cur_eff) if (new_eff is not None and cur_eff is not None) else None
        st.metric(
            "Efficiency",
            f"{new_eff:.3f}" if new_eff is not None else "–",
            f"{eff_delta:+.3f} from {cur_eff:.3f}" if eff_delta is not None else None,
            help="New-model DEA efficiency (0 to 1, 1 = frontier). The delta is from the "
                 "current model; the two models use different DEA inputs, so read it alongside "
                 "the efficiency scatter below.",
        )

    st.caption(
        "These figures use current-regulation (RP4) data and our reading of Ei's method, with "
        "incentive parameters not yet set by Ei. Read them as the isolated effect of the "
        "benchmarking change, all else equal, not a forecast of the 2028-2031 levels."
    )

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
        "splits the sector: companies below it have their cap lowered, the top quarter get "
        "full coverage or a higher cap."
    )
    k1, k2, k3 = st.columns(3)
    k1.metric("Lower cap", f"{n_ded} / {n}")
    k2.metric("Full coverage", f"{n_cov} / {n}")
    k3.metric("Higher cap", f"{n_rew} / {n}")

    render_position_chart(
        dea_new[COL_DEA_EFFICIENCY].to_numpy(), e75, cfg, new_eff, user_label,
    )
    render_outcome_distribution(outcomes.to_numpy(), new_out, user_label)


# ---------------------------------------------------------------------------
# 3. New model TOTEX bridge — two-phase (cost coverage, then corrections)
# ---------------------------------------------------------------------------

# Full-width bands behind the two phases of the bridge.
_BAND_SCOPE = "rgba(37, 99, 235, 0.13)"    # primary tint — scope (new cost posts)
_BAND_CORRECTION = "rgba(217, 119, 6, 0.15)"  # amber tint — benchmarking corrections


def _render_totex_waterfall(totex: pd.DataFrame, user_reid: str) -> None:
    """Two-phase bridge from the old (legacy) TOTEX to the new DEA TOTEX.

    Old TOTEX is controllable + unadjusted capital cost. The journey to the new DEA input
    is split into two phases that are kept visually separate (subtle background bands plus
    an intermediate subtotal bar), so "what the new model measures" and "how it corrects
    what it measures" never blur together:

      Cost coverage — cost posts the new model brings into the DEA input that the old did
                      not: network losses at their actual cost, selected non-controllable.
      Corrections   — the benchmarking adjustments to those posts: losses revalued to a
                      common price; capital cost levelled for placement environment.

    Each new post enters the cost-coverage phase at its *uncorrected* value, then the
    correction phase adjusts it, which is exactly what isolates cost coverage from correction.
    The granular
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
    subtotal = old_totex + loss_actual + nonctrl_sum   # end of the cost-coverage phase (uncorrected)
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
        ("Full cost base (uncorrected)",     subtotal,     "total"),
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

    # Phase bands (numeric y maps to category index): cost coverage spans rows 0-6 (the opening
    # Old TOTEX, the coverage additions, and the uncorrected subtotal they build), corrections spans
    # rows 7–10 (the two corrections plus the final TOTEX they land on). The floating relative
    # bars sit far to the right, so the phase labels go in the empty left of the plot.
    fig.add_hrect(y0=-0.5, y1=6.5, fillcolor=_BAND_SCOPE, line_width=0, layer="below")
    fig.add_hrect(y0=6.5, y1=10.5, fillcolor=_BAND_CORRECTION, line_width=0, layer="below")
    for y_pos, label in ((3.0, "Cost coverage"), (8.5, "Corrections")):
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
        "in two phases. **Cost coverage** (blue band) adds the cost posts the new model measures but "
        "the old did not: network losses at their actual cost and the non-controllable "
        "categories (grid subscription, grid connection, feed-in compensation, capacity "
        "reserve). **Corrections** (amber band) then apply the benchmarking adjustments: "
        "losses revalued to a common price, and the placement-environment capital-cost "
        "levelling split into cable (jordkabel) and station (nätstation)."
    )


# ---------------------------------------------------------------------------
# Thematic chart groups (registry)
# ---------------------------------------------------------------------------
# The section below the verdict is built from this list. Each group is a theme rendered as
# its own vertical section; the panel (chart_panel.render_chart_panel) stacks them under
# headings. Add a theme by adding one ChartGroup entry — e.g. a future "New vs current"
# group with scatter plots of efficiency and the requirement.


def _group_efficiency_outcome(ctx: GroupContext) -> None:
    """Efficiency histogram + signed-outcome distribution (firm marked in both), then the
    two narrower new-vs-current scatters side by side."""
    _render_sector_and_position(
        ctx.result, ctx.user_reid, ctx.cfg, ctx.e75, ctx.new_eff, ctx.new_out, ctx.user_label
    )

    st.markdown("###### Model comparison")
    c_rank, c_eff, c_imp = st.columns(3)
    with c_rank:
        render_rank_scatter(ctx.result.comparison, ctx.user_reid, ctx.user_label)
    with c_eff:
        render_efficiency_scatter(ctx.result.comparison, ctx.user_reid, ctx.user_label)
    with c_imp:
        render_requirement_scatter(ctx.result.comparison, ctx.user_reid, ctx.user_label)
    st.caption(
        "Each point is a company: new model (vertical) against current model (horizontal); "
        "the dashed line is no change, and your company is highlighted in every panel. Green "
        "means the new model is better for the firm, amber worse. **Rank** (1 = most "
        "efficient, top-right): above the line means a better rank under the new model. "
        "**Efficiency**: above the line means more efficient under the new model. "
        "**Efficiency adjustment** (%/yr), its impact on the revenue frame: above the line "
        "means the new model is more favourable to your cap, and above zero is an addition "
        "that raises it (only the new model can go positive)."
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
            "ⓘ These figures reflect the **main model**; the analysis is precomputed and "
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


# Visible groups, stacked vertically (see chart_panel.render_chart_panel).
CHART_GROUPS = [
    ChartGroup("efficiency_outcome", "Model outputs", _group_efficiency_outcome),
    ChartGroup("totex_bridge", "TOTEX decomposition", _group_totex_bridge),
]

# Hidden for V1: the outcome decomposition is considered too technical for the first
# Regumetrica release, but it is kept fully wired (_group_placeholder + the analysis
# loaders/charts it uses) so we can keep building on it behind the scenes and re-enable it
# for stakeholder discussions with Ei. Re-enabling is a one-line move into CHART_GROUPS above.
HIDDEN_CHART_GROUPS = [
    ChartGroup("placeholder", "Outcome decomposition", _group_placeholder),
]

