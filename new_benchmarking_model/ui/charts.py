"""
_two_sided_charts.py — purpose-built visuals for the new-benchmarking two-sided model.

The legacy efficiency charts (frontend/results/_efficiency_charts.py, shared with M5)
encode the front-reference / deduction-only mental model: cap·active·floor zones on a
*potential* histogram. The two-sided third-quartile model is a different object — a signed
position relative to a threshold E75, with a deduction zone below it and a reward zone
above. These helpers render that model directly and are deliberately NOT shared with M5.

Sign convention (company perspective) — single source of truth lives here:

    r > 0  → deduction (revenue cap lowered)   → warning amber, ↓
    r < 0  → reward    (revenue cap raised)     → success green, ↑
    r ≈ 0  → full cost coverage                 → neutral
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend.common.styling import COLORS
from config.colors import get_plotly_template_safe
from config.column_names import (
    COL_REID, COL_DEA_EFFICIENCY_NEW, COL_DEA_EFFICIENCY_CURRENT,
    COL_EFF_REQ_NEW, COL_EFF_REQ_CURRENT,
)
from new_benchmarking_model.config import NewBenchmarkingConfig
from new_benchmarking_model.efficiency.efficiency_requirement_two_sided import (
    two_sided_requirement_from_gap,
)

_EPS = 1e-5

KIND_REWARD = "reward"
KIND_DEDUCTION = "deduction"
KIND_COVERAGE = "coverage"

# Subtle full-height zone tints: amber = deduction side, green = reward side.
_ZONE_DEDUCTION = "rgba(217, 119, 6, 0.07)"
_ZONE_REWARD = "rgba(5, 150, 105, 0.07)"


def outcome_kind(r: Optional[float], eps: float = _EPS) -> Optional[str]:
    """Classify a signed annual outcome from the company's perspective."""
    if r is None or pd.isna(r):
        return None
    if r > eps:
        return KIND_DEDUCTION
    if r < -eps:
        return KIND_REWARD
    return KIND_COVERAGE


def outcome_color(kind: Optional[str]) -> str:
    """Design-system colour for an outcome kind (company perspective)."""
    return {
        KIND_REWARD: COLORS["success"],
        KIND_DEDUCTION: COLORS["warning"],
        KIND_COVERAGE: COLORS["text_muted"],
    }.get(kind, COLORS["text_muted"])


def _transfer_curve(e_grid: np.ndarray, e75: float, cfg: NewBenchmarkingConfig) -> np.ndarray:
    """Outcome (%/yr) for each efficiency on the grid — the model's own transfer function.

    Reuses the calculation function so the drawn curve IS the model, with no risk of the
    chart drifting from the maths.
    """
    return np.array([
        two_sided_requirement_from_gap(
            e75 - e,
            gap_cap=cfg.gap_cap, sharing=cfg.sharing,
            realization_time=cfg.realization_time, supervision_period=cfg.supervision_period,
        ) * 100.0
        for e in e_grid
    ])


def render_position_chart(
    eff_scores: Sequence[float],
    e75: float,
    cfg: NewBenchmarkingConfig,
    user_eff: Optional[float],
    user_label: str,
    peer_label: Optional[str] = None,
    key: str = "nb_position",
) -> None:
    """Efficiency histogram (all firms) + the E75 threshold pivot splitting the deduction
    and reward zones + the transfer curve on a secondary axis + the firm's position."""
    eff = np.asarray(eff_scores, dtype=float)
    eff = eff[~np.isnan(eff)]
    if eff.size == 0 or e75 is None or np.isnan(e75):
        st.info("No efficiency data to plot.")
        return

    lo = min(float(eff.min()), e75 - cfg.gap_cap) - 0.03
    hi = max(float(eff.max()), 1.0) + 0.03
    grid = np.linspace(lo, hi, 200)
    curve = _transfer_curve(grid, e75, cfg)
    elbow = e75 - cfg.gap_cap   # left of this, deductions are capped at the max

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()

    # Zones (full-height tints): deduction left of E75, reward right.
    fig.add_vrect(x0=lo, x1=e75, fillcolor=_ZONE_DEDUCTION, line_width=0, layer="below")
    fig.add_vrect(x0=e75, x1=hi, fillcolor=_ZONE_REWARD, line_width=0, layer="below")

    # Efficiency histogram (counts, primary axis) — subtle background.
    fig.add_trace(go.Histogram(
        x=eff, nbinsx=28, marker_color=COLORS["bg_muted"],
        marker_line_color="white", marker_line_width=1, opacity=0.7, yaxis="y",
        hovertemplate="Efficiency: %{x:.3f}<br>Companies: %{y}<extra></extra>",
        showlegend=False,
    ))

    # Transfer curve (outcome %/yr, secondary axis).
    fig.add_trace(go.Scatter(
        x=grid, y=curve, mode="lines", yaxis="y2",
        line=dict(color=COLORS["primary"], width=2.5),
        hovertemplate="Efficiency: %{x:.3f}<br>Outcome: %{y:+.2f} %/yr<extra></extra>",
        showlegend=False,
    ))

    # E75 pivot + reference-peer label + deduction-cap elbow.
    fig.add_vline(x=e75, line_dash="solid", line_color=COLORS["text_secondary"], line_width=1.5)
    fig.add_annotation(
        x=e75, y=1.0, yref="paper", yanchor="bottom", text=f"<b>E₇₅ = {e75:.3f}</b>",
        showarrow=False, font=dict(size=11, color=COLORS["text_secondary"]),
        bgcolor="rgba(255,255,255,0.9)", borderpad=2,
    )
    if peer_label:
        fig.add_annotation(
            x=e75, y=0.05, yref="paper", yanchor="bottom", text=f"≈ {peer_label}",
            showarrow=False, font=dict(size=10, color=COLORS["text_muted"]),
        )
    if lo < elbow < hi:
        fig.add_vline(x=elbow, line_dash="dot", line_color=COLORS["text_muted"], line_width=1)
        fig.add_annotation(
            x=elbow, y=0.93, yref="paper", yanchor="top", text="deduction cap",
            showarrow=False, font=dict(size=9, color=COLORS["text_muted"]),
        )

    # Firm marker.
    if user_eff is not None:
        fig.add_vline(x=user_eff, line_dash="solid", line_color=COLORS["text_primary"], line_width=2)
        fig.add_annotation(
            x=user_eff, y=0.80, yref="paper", yanchor="bottom",
            text=f"<b>{user_label}: {user_eff:.3f}</b>", showarrow=False,
            font=dict(size=11, color=COLORS["text_primary"]),
            bgcolor="rgba(255,255,255,0.9)", borderpad=3,
        )

    fig.update_layout(
        **layout_kwargs, template=template,
        title=dict(text="Your position vs the third-quartile benchmark", font=dict(size=13)),
        height=400, bargap=0.05, dragmode=False, showlegend=False,
        xaxis=dict(title="Efficiency score", range=[lo, hi], fixedrange=True,
                   showgrid=False, linecolor=COLORS["bg_muted"]),
        yaxis=dict(title="Number of companies", fixedrange=True,
                   gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"]),
        yaxis2=dict(title="Outcome (%/yr)", overlaying="y", side="right", fixedrange=True,
                    zeroline=True, zerolinecolor=COLORS["bg_muted"], showgrid=False),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)
    st.caption(
        "Bars: efficiency of all 148 companies. The line is the model's transfer function — "
        "how an efficiency score maps to an annual outcome (right axis). Left of the "
        "third-quartile benchmark E₇₅ is a deduction (amber); right of it, a reward (green); "
        "exactly at E₇₅ is full cost coverage. Left of the cap mark, deductions are held at "
        "their maximum (+1.82 %/yr)."
    )


def render_outcome_distribution(
    outcomes: Sequence[float],
    user_outcome: Optional[float],
    user_label: str,
    key: str = "nb_outcome",
) -> None:
    """Diverging histogram of signed annual outcomes — deductions (amber, >0) vs rewards
    (green, <0) — with a zero pivot (full coverage) and the firm marked."""
    o = np.asarray(outcomes, dtype=float)
    o = o[~np.isnan(o)] * 100.0
    if o.size == 0:
        st.info("No outcome data to plot.")
        return

    rew = o[o < -_EPS * 100]
    ded = o[o > _EPS * 100]

    layout_kwargs, template = get_plotly_template_safe()
    bins = dict(start=min(float(o.min()), 0.0) - 0.1, end=max(float(o.max()), 0.0) + 0.1, size=0.1)
    common = dict(
        xbins=bins, marker_line_color="white", marker_line_width=1, opacity=0.85,
        hovertemplate="Outcome: %{x:+.2f} %/yr<br>Companies: %{y}<extra></extra>",
        showlegend=False,
    )

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=rew, marker_color=COLORS["success"], **common))
    fig.add_trace(go.Histogram(x=ded, marker_color=COLORS["warning"], **common))

    fig.add_vline(x=0, line_dash="solid", line_color=COLORS["text_secondary"], line_width=1.5)
    fig.add_annotation(
        x=0, y=1.0, yref="paper", yanchor="bottom", text="full coverage", showarrow=False,
        font=dict(size=10, color=COLORS["text_secondary"]),
        bgcolor="rgba(255,255,255,0.9)", borderpad=2,
    )
    if user_outcome is not None:
        ux = user_outcome * 100.0
        fig.add_vline(x=ux, line_dash="solid", line_color=COLORS["text_primary"], line_width=2)
        fig.add_annotation(
            x=ux, y=0.86, yref="paper", yanchor="bottom",
            text=f"<b>{user_label}: {ux:+.2f}</b>", showarrow=False,
            font=dict(size=11, color=COLORS["text_primary"]),
            bgcolor="rgba(255,255,255,0.9)", borderpad=3,
        )

    fig.update_layout(
        **layout_kwargs, template=template, barmode="overlay",
        title=dict(text="Outcome across all 148 companies", font=dict(size=13)),
        height=340, bargap=0.03, dragmode=False,
        xaxis=dict(title="Annual outcome (%/yr)   ← reward · deduction →", fixedrange=True,
                   showgrid=False, zeroline=False, linecolor=COLORS["bg_muted"]),
        yaxis=dict(title="Number of companies", fixedrange=True,
                   gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"]),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)


# ---------------------------------------------------------------------------
# Comparison scatters — new (y) vs current (x), one point per company
# ---------------------------------------------------------------------------
# Narrower than the histograms, so the two are meant to sit side by side. Both share the
# same machinery: a y = x identity line ("no change"), the crowd in subtle grey, and the
# user's firm highlighted. A point off the diagonal is a company the new model moves.


def _comparison_scatter(
    comparison: pd.DataFrame,
    user_reid: str,
    user_label: str,
    *,
    col_current: str,
    col_new: str,
    title: str,
    scale: float = 1.0,
    unit_label: str = "",
    tickformat: str = ".2f",
    hover_format: Optional[str] = None,
    shared_range: bool = True,
    zero_line: bool = False,
    key: str,
) -> None:
    """Scatter of each company's new (y) vs current (x) value with a y=x reference line.

    scale rescales both axes (e.g. 100 to show decimals as %); unit_label is appended to
    the axis titles and hover. shared_range ties both axes to one common range (true 45°
    diagonal, right when the two quantities live on the same natural scale); set it False
    when the two sides occupy very different ranges, so each axis fits its own data instead
    of one side stretching the other. zero_line draws a faint y=0 line (for the signed
    requirement, below which the new model is a reward).
    """
    if col_current not in comparison.columns or col_new not in comparison.columns:
        st.info("No comparison data to plot.")
        return
    d = comparison[[COL_REID, col_current, col_new]].dropna(subset=[col_current, col_new])
    if d.empty:
        st.info("No comparison data to plot.")
        return

    hover_format = hover_format or tickformat
    x = d[col_current].to_numpy(dtype=float) * scale
    y = d[col_new].to_numpy(dtype=float) * scale
    reids = d[COL_REID].tolist()

    from frontend.utils.company_directory import get_company_name_lookup
    lookup = get_company_name_lookup()
    names = [lookup.get(r, r) for r in reids]
    is_user = np.array([r == user_reid for r in reids])

    # Axis ranges. Shared → one range for both (diagonal stays at 45°). Independent → each
    # axis fits its own data, so a one-sided spread (e.g. signed new vs deduction-only
    # current) does not stretch the other axis.
    def _padded(arr, frac):
        lo, hi = float(np.min(arr)), float(np.max(arr))
        span = (hi - lo) or abs(hi) or 1.0
        return [lo - span * frac, hi + span * frac]

    if shared_range:
        both = np.concatenate([x, y])
        x_range = y_range = _padded(both, 0.05)
    else:
        x_range, y_range = _padded(x, 0.08), _padded(y, 0.08)
    diag = [min(x_range[0], y_range[0]), max(x_range[1], y_range[1])]

    # Pre-format hover values ourselves (name + current + new) and pass them via customdata,
    # so display never depends on plotly's inline number format.
    unit = f" {unit_label}" if unit_label else ""

    def _fmt(v: float) -> str:
        return f"{v:{hover_format}}{unit}"

    hover = (
        "<b>%{customdata[0]}</b>"
        "<br>Current: %{customdata[1]}"
        "<br>New: %{customdata[2]}<extra></extra>"
    )
    cd = [[names[i], _fmt(float(x[i])), _fmt(float(y[i]))] for i in range(len(names))]

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()

    # y = x identity line — "no change" reference.
    fig.add_trace(go.Scatter(
        x=diag, y=diag, mode="lines",
        line=dict(color=COLORS["bg_muted"], width=1, dash="dot"),
        hoverinfo="skip", showlegend=False,
    ))
    if zero_line:
        fig.add_hline(y=0, line_dash="dot", line_color=COLORS["text_muted"], line_width=1)

    # The crowd — subtle grey.
    fig.add_trace(go.Scatter(
        x=x[~is_user], y=y[~is_user], mode="markers",
        marker=dict(color=COLORS["text_muted"], size=6, opacity=0.5,
                    line=dict(color="white", width=0.5)),
        customdata=[cd[i] for i in range(len(cd)) if not is_user[i]],
        hovertemplate=hover, showlegend=False,
    ))

    # The user's firm — primary, larger, labelled.
    if is_user.any():
        ui = int(np.flatnonzero(is_user)[0])
        ux, uy = float(x[ui]), float(y[ui])
        fig.add_trace(go.Scatter(
            x=[ux], y=[uy], mode="markers",
            marker=dict(color=COLORS["primary"], size=12, line=dict(color="white", width=1.5)),
            customdata=[[user_label, _fmt(ux), _fmt(uy)]], hovertemplate=hover, showlegend=False,
        ))
        fig.add_annotation(
            x=ux, y=uy, text=f"<b>{user_label}</b>", showarrow=True,
            arrowwidth=1, arrowcolor=COLORS["text_secondary"], ax=18, ay=-18,
            font=dict(size=10, color=COLORS["text_primary"]),
            bgcolor="rgba(255,255,255,0.9)", borderpad=2,
        )

    axis = dict(fixedrange=True, tickformat=tickformat,
                gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"], zeroline=False)
    title_unit = f" ({unit_label})" if unit_label else ""
    fig.update_layout(
        **layout_kwargs, template=template,
        title=dict(text=title, font=dict(size=13)),
        height=360, dragmode=False, showlegend=False,
        margin=dict(l=10, r=10, t=40, b=40),
        xaxis={**axis, "range": x_range, "title": f"Current{title_unit}"},
        yaxis={**axis, "range": y_range, "title": f"New{title_unit}"},
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)


def render_efficiency_scatter(
    comparison: pd.DataFrame, user_reid: str, user_label: str,
    key: str = "nb_eff_scatter",
) -> None:
    """New vs current DEA efficiency per company (above the line = more efficient now)."""
    _comparison_scatter(
        comparison, user_reid, user_label,
        col_current=COL_DEA_EFFICIENCY_CURRENT, col_new=COL_DEA_EFFICIENCY_NEW,
        title="Efficiency: new vs current",
        tickformat=".2f", hover_format=".3f", key=key,
    )


def render_requirement_scatter(
    comparison: pd.DataFrame, user_reid: str, user_label: str,
    key: str = "nb_req_scatter",
) -> None:
    """New vs current efficiency requirement (%/yr) per company.

    Below the identity line = a smaller requirement under the new model; below the y=0
    line = a reward (only the new model can be negative — the current model is
    deduction-only).
    """
    _comparison_scatter(
        comparison, user_reid, user_label,
        col_current=COL_EFF_REQ_CURRENT, col_new=COL_EFF_REQ_NEW,
        title="Requirement: new vs current",
        scale=100.0, unit_label="%/yr", tickformat=".1f", hover_format="+.2f",
        shared_range=False, zero_line=True, key=key,
    )
