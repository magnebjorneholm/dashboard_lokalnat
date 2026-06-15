"""
new_benchmarking_output.py - render the new-benchmarking result for one company.

Built for the two-sided third-quartile mechanic (not the legacy front-reference model):
the headline is the firm's *signed outcome* under the new model - a deduction if it is
less efficient than the third-quartile benchmark E75, a reward if more efficient, full
cost coverage at the benchmark.

Layout (firm-first - the user's answer comes before the sector context):
  1. Your company  - verdict hero (deduction / coverage / reward) + supporting KPIs.
  2. Sector & position - counts + the position chart (efficiency histogram with the E75
     pivot, deduction/reward zones and the model's transfer curve) + the outcome
     distribution, the firm marked in both.
  3. New model TOTEX - bridge waterfall from the current-model TOTEX to the new one.

The two-sided visuals live in new_benchmarking_model/ui/charts.py (NOT the M5-shared
_efficiency_charts.py). The current model (EIs_DEA) is used only as the comparison point
for the outcome swing, not as a second mechanic to display.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.common.styling import COLORS
from config.colors import get_plotly_template_safe
from config.formatting import format_percent, format_pp, format_tkr, format_delta
from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY, COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL, COL_DEA_REFERENCE,
    COL_TOTEX_NEW, COL_CONTROLLABLE_AVG, COL_CAPITAL_COST_2024,
    COL_LOSS_VALUED, COL_NONCTRL_SELECTED, COL_CAPITAL_COST_ENV_ADJ,
    COL_KR_CURRENT, COL_KR_NEW,
)
from new_benchmarking_model.config import NewBenchmarkingConfig
from new_benchmarking_model.model import NewBenchmarkingResult
from new_benchmarking_model.ui.charts import (
    render_position_chart, render_outcome_distribution,
    outcome_kind, KIND_REWARD, KIND_DEDUCTION, KIND_COVERAGE,
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
# Main render
# ---------------------------------------------------------------------------

def render_company_view(
    result: NewBenchmarkingResult,
    user_reid: str,
    cfg: NewBenchmarkingConfig,
    user_label: str = "Your firm",
) -> None:
    """Full view: verdict → sector & position → TOTEX bridge.

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

    _render_verdict(dea_new, user_reid, e75, new_eff, new_out, cur_req, kr_cur, kr_new, is_outlier_new)
    st.divider()
    _render_sector_and_position(result, user_reid, cfg, e75, new_eff, new_out, user_label)
    st.divider()
    _render_totex_waterfall(result.totex, user_reid)


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
    st.markdown("#### Sector & your position")

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
# 3. New model TOTEX bridge (mechanic-agnostic - kept as-is)
# ---------------------------------------------------------------------------

def _render_totex_waterfall(totex: pd.DataFrame, user_reid: str) -> None:
    """Bridge from the current-model TOTEX to the new-model TOTEX.

    A horizontal waterfall that starts and ends on a blue total bar (current → new), with
    the new ingredients in between: additions (network losses, selected non-controllable)
    in red, the placement-environment capex cut in green. Controllable cost is shared by
    both models, so it sits inside the unchanged opening total.
    """
    st.markdown("#### New model TOTEX")

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
    env_cut = new_capex - old_capex  # negative - the förläggningsmiljö reduction

    # Opening bar must be "absolute" (it sets the starting total); a "total" first bar would
    # compute the cumulative of nothing = 0 and render invisible. The closing bar is "total"
    # (cumulative). Both absolute/total bars are styled by `totals` (blue).
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
