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
from calculations.new_benchmarking.config import NewBenchmarkingConfig
from calculations.new_benchmarking.efficiency_requirement_two_sided import (
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
