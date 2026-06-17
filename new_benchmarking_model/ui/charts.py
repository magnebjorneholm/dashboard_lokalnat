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
from config.colors import get_plotly_template_safe, CHART_COLORS
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


# ===========================================================================
# Sector decomposition — the "Placeholder" chart group
# ===========================================================================
# Static, sector-level read of the committed analysis tables (channel isolation +
# Shapley attribution). The four cost-component PLAYERS keep one colour each across the
# waterfall, boxplots and quantile bars so a component is recognisable everywhere. All
# figures work in percentage points (pp/yr) of the signed two-sided requirement; the
# analysis tables already store the *_pp / phi_* columns in pp, so no ×100 here.

# Ordered by mean |phi| dominance (matches the Shapley summary).
PLAYER_KEYS = ("nonctrl", "capex_adj", "cable", "losses")
PLAYER_LABELS = {
    "nonctrl": "Non-controllable",
    "capex_adj": "Capex levelling",
    "cable": "Cable length",
    "losses": "Network losses",
}
PLAYER_COLORS = {
    "nonctrl": CHART_COLORS[0],    # blue
    "capex_adj": CHART_COLORS[2],  # violet
    "cable": CHART_COLORS[1],      # teal
    "losses": CHART_COLORS[4],     # orange
}
_RESIDUAL_COLOR = CHART_COLORS[6]  # slate — the held-out mechanic/structural term
# Faint two-phase bands behind the Shapley waterfall.
_BAND_COMPUTE = "rgba(100, 116, 139, 0.10)"     # slate tint — how the requirement is computed
_BAND_COMPONENTS = "rgba(37, 99, 235, 0.06)"    # primary tint — the cost components

# Distribution charts (Fig 3a boxplots, Fig 3b quartile bars) show all six contributions:
# the four cost components plus the two structural terms (mechanic switch, input aggregation)
# from the residual split. Structural terms first (top / left), in slate to set them apart.
# A term is only drawn if its phi_<key> column is present, so the charts degrade to the four
# cost components when the residual decomposition is unavailable.
STRUCTURAL_KEYS = ("mechanic", "input")
DIST_TERM_KEYS = STRUCTURAL_KEYS + PLAYER_KEYS
DIST_TERM_LABELS = {"mechanic": "Mechanic switch", "input": "Input structure", **PLAYER_LABELS}
DIST_TERM_COLORS = {"mechanic": "#475569", "input": "#94A3B8", **PLAYER_COLORS}  # slate pair


# ---------------------------------------------------------------------------
# Fig 1 — channel tilt along urbanity (regression lines + scatter + boot-CI band)
# ---------------------------------------------------------------------------

def _slope_row(slopes: pd.DataFrame, fragment: str):
    """(slope, boot_ci_low, boot_ci_high) for the channel whose label contains `fragment`."""
    row = slopes[slopes["channel"].str.contains(fragment, case=False, na=False)]
    if row.empty:
        return None
    r = row.iloc[0]
    return float(r["slope"]), float(r["boot_ci_low"]), float(r["boot_ci_high"])


def render_channel_regression(
    channels: pd.DataFrame,
    slopes: pd.DataFrame,
    key: str = "nb_channel_reg",
) -> None:
    """Two opposing förläggningsmiljö channels projected on the urban axis.

    Y = each channel's per-firm contribution to the requirement (pp; <0 = lowers the
    requirement = favours the firm). The regression line uses the stored OLS slope drawn
    through the point cloud's centroid; the band is the bootstrap slope CI pivoting at the
    same centroid (a wedge — narrow at the centre, wide at the edges). Channel A (capex
    levelling) tilts down (favours urban), channel B (cable length) tilts up (favours
    rural); the net line (A + B) is their sum and sits ~flat near zero.
    """
    need = ["urbanity_index", "dA_pp", "dB_pp"]
    if any(c not in channels.columns for c in need):
        st.info("No channel data to plot.")
        return
    d = channels.dropna(subset=need).copy()
    if d.empty:
        st.info("No channel data to plot.")
        return

    x = d["urbanity_index"].to_numpy(dtype=float)
    xbar = float(x.mean())
    xs = np.array([x.min(), x.max()])

    a = _slope_row(slopes, "capex-adj")
    b = _slope_row(slopes, "cable-length")
    if a is None or b is None:
        st.info("No channel slopes to plot.")
        return

    series = [
        # (key, y-array, label, color, slope, boot_ci or None for net)
        ("A", d["dA_pp"].to_numpy(float), "Capex levelling", PLAYER_COLORS["capex_adj"], a[0], (a[1], a[2])),
        ("B", d["dB_pp"].to_numpy(float), "Cable length", PLAYER_COLORS["cable"], b[0], (b[1], b[2])),
        ("N", (d["dA_pp"] + d["dB_pp"]).to_numpy(float), "Net (A + B)", COLORS["text_secondary"],
         a[0] + b[0], None),
    ]

    # Robust y-window: a handful of firms have extreme channel contributions (down to
    # ~-1.9 pp) that would otherwise crush the lines, bands and bulk into a flat strip near
    # zero. Clip to a readable window and disclose the off-scale count in the caption.
    Y_LO, Y_HI = -0.4, 0.4

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["text_muted"], line_width=1)

    # Drawn in phases so the regression lines always sit on top of every cloud and band.
    # Phase 1 — bootstrap-CI wedges (A and B only; the net has no stored CI).
    for skey, y, label, color, slope, boot in series:
        if boot is None:
            continue
        ybar = float(np.nanmean(y))
        lo = ybar + boot[0] * (xs - xbar)
        hi = ybar + boot[1] * (xs - xbar)
        fig.add_trace(go.Scatter(x=xs, y=lo, mode="lines", line=dict(width=0),
                                 hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=xs, y=hi, mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor=_rgba(color, 0.13), hoverinfo="skip", showlegend=False))

    # Phase 2 — scatter points (A and B only; the net is a line, no third cloud).
    for skey, y, label, color, slope, boot in series:
        if boot is None:
            continue
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(color=color, size=5, opacity=0.35, line=dict(color="white", width=0.4)),
            hoverinfo="skip", showlegend=False,
        ))

    # Phase 3 — regression lines, on top of the clouds.
    for skey, y, label, color, slope, boot in series:
        ybar = float(np.nanmean(y))
        line_y = ybar + slope * (xs - xbar)
        name = (f"{label}  (slope {slope:+.3f} [{boot[0]:+.2f}, {boot[1]:+.2f}])"
                if boot is not None else f"{label}  (slope {slope:+.3f})")
        fig.add_trace(go.Scatter(
            x=xs, y=line_y, mode="lines", name=name,
            line=dict(color=color, width=3, dash=("dash" if skey == "N" else "solid")),
            hovertemplate=f"{label}<br>urbanity %{{x:.2f}} to %{{y:+.3f}} pp<extra></extra>",
        ))

    # Points (A and B) beyond the window, disclosed in the caption (no silent truncation).
    ab = np.concatenate([d["dA_pp"].to_numpy(float), d["dB_pp"].to_numpy(float)])
    n_off = int(((ab < Y_LO) | (ab > Y_HI)).sum())

    fig.update_layout(
        **layout_kwargs, template=template,
        title=dict(text="Who the corrections favour — channel tilt along urbanity", font=dict(size=13)),
        height=440, dragmode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=10)),
        margin=dict(l=10, r=10, t=70, b=45),
        xaxis=dict(title="Urbanity index  (0 = rural → urban)", fixedrange=True,
                   showgrid=False, linecolor=COLORS["bg_muted"]),
        yaxis=dict(title="Channel contribution (pp/yr)", range=[Y_LO, Y_HI], fixedrange=True,
                   gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"], zeroline=False),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)
    st.caption(
        "Each point is a company; the line is the channel's regression on urbanity (drawn "
        "from the stored slope, band = bootstrap CI). **Capex levelling** tilts down, "
        "favouring urban firms; **cable length** tilts up, favouring rural firms. The dashed "
        "**net** line (A + B) is roughly flat near zero: the two channels cancel along the "
        "urban axis. The bootstrap bands are wide and cross zero, so read direction over "
        "significance. The y-axis is clipped to ±0.4 pp/yr"
        + (f"; {n_off} extreme points fall outside and are not shown." if n_off else ".")
    )


# ---------------------------------------------------------------------------
# Fig 2 — what explains the new mean requirement (Shapley waterfall, sector mean)
# ---------------------------------------------------------------------------

def render_shapley_waterfall(
    shapley: pd.DataFrame, decomp: Optional[pd.DataFrame] = None,
    key: str = "nb_shapley_waterfall",
) -> None:
    """Sector-mean bridge from today's requirement to the new outcome.

    The four cost players' mean Shapley contributions net to ~0; the bulk of the shift is the
    held-out residual. When the residual decomposition is supplied, the residual is split into
    the mechanic switch (legacy front-reference to two-sided E75, the dominant term) and the
    input-structure change (two separate DEA inputs to one summed TOTEX), anchored on the
    recomputed legacy baseline C1 (the reconciliation against Ei's published figure is solver
    noise and is dropped, so the bridge closes exactly). Without it, the residual is one bar.
    """
    need = ["v_full_pp", *[f"phi_{p}" for p in PLAYER_KEYS]]
    if any(c not in shapley.columns for c in need):
        st.info("No Shapley data to plot.")
        return
    d = shapley.dropna(subset=["v_full_pp"])
    if d.empty:
        st.info("No Shapley data to plot.")
        return

    phis = {p: float(d[f"phi_{p}"].mean()) for p in PLAYER_KEYS}
    player_rows = [(PLAYER_LABELS[p], phis[p], "relative") for p in PLAYER_KEYS]

    split_ok = decomp is not None and all(
        c in decomp.columns for c in ("C1_legacy_2in", "phi_mechanic", "phi_input")
    )
    boundary = None
    if split_ok:
        dd = decomp.dropna(subset=["C1_legacy_2in", "phi_mechanic", "phi_input"])
        c1 = float(dd["C1_legacy_2in"].mean())
        mech = float(dd["phi_mechanic"].mean())
        inp = float(dd["phi_input"].mean())
        v_empty = c1 + mech + inp                  # mean v(∅), the two-sided baseline
        v_full = v_empty + sum(phis.values())      # exact cumulative end
        rows = [
            ("Current requirement (legacy)", c1, "absolute"),
            ("Mechanic: front-reference → two-sided", mech, "relative"),
            ("Input structure: 2 inputs → 1 TOTEX", inp, "relative"),
            ("Two-sided baseline", v_empty, "total"),
            *player_rows,
            ("New outcome", v_full, "total"),
        ]
        boundary = 3.5   # phases split after the subtotal (rows 0-3 vs 4-8)
    else:
        if any(c not in d.columns for c in ("residual_vs_current_pp", "v_empty_pp")):
            st.info("No Shapley data to plot.")
            return
        resid = float(d["residual_vs_current_pp"].mean())
        v_empty = float(d["v_empty_pp"].mean())
        v_full = float(d["v_full_pp"].mean())
        rows = [
            ("Current requirement", v_empty - resid, "absolute"),
            ("Mechanic + structure (residual)", resid, "relative"),
            *player_rows,
            ("New outcome", v_full, "total"),
        ]

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    measures = [r[2] for r in rows]
    text = [f"{v:+.3f}" if m == "relative" else f"{v:.3f}" for v, m in zip(values, measures)]
    hover = [
        f"<b>{l}</b><br>{v:+.3f} pp/yr" if m == "relative" else f"<b>{l}</b><br>{v:.3f} pp/yr"
        for l, v, m in zip(labels, values, measures)
    ]

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure(go.Waterfall(
        orientation="h", y=labels, x=values, measure=measures,
        textposition="outside", text=text,
        textfont=dict(size=11, family="Inter, sans-serif"),
        connector=dict(line=dict(color=COLORS["bg_muted"], width=1, dash="dot")),
        increasing=dict(marker=dict(color=COLORS["warning"])),   # req up = bigger deduction → amber
        decreasing=dict(marker=dict(color=COLORS["success"])),   # req down = reward → green
        totals=dict(marker=dict(color=COLORS["primary"])),       # start / subtotal / new → blue
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
    ))

    # Two-phase bands (only with the residual split): how the requirement is computed
    # (mechanic + input) vs the four cost components.
    if boundary is not None:
        end = len(rows) - 0.5
        fig.add_hrect(y0=-0.5, y1=boundary, fillcolor=_BAND_COMPUTE, line_width=0, layer="below")
        fig.add_hrect(y0=boundary, y1=end, fillcolor=_BAND_COMPONENTS, line_width=0, layer="below")
        for y_pos, lab in ((1.5, "How the requirement is computed"),
                           ((boundary + end) / 2, "Cost components")):
            fig.add_annotation(
                xref="paper", x=0.01, y=y_pos, yref="y", text=f"<b>{lab}</b>",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(size=11, color=COLORS["text_secondary"]),
            )

    fig.update_layout(
        **layout_kwargs, template=template,
        title=dict(text="What explains the new mean requirement", font=dict(size=13)),
        margin=dict(l=10, r=70, t=40, b=40),
        height=max(300, len(labels) * 50), dragmode=False, showlegend=False,
        xaxis=dict(title="Mean annual requirement (pp/yr)", fixedrange=True, showgrid=False,
                   zeroline=True, zerolinecolor=COLORS["bg_muted"], linecolor=COLORS["bg_muted"]),
        yaxis=dict(fixedrange=True, showgrid=True, gridcolor=COLORS["bg_muted"],
                   tickson="boundaries", automargin=True, autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)
    net_players = sum(phis.values())
    if split_ok:
        st.caption(
            "Sector mean, from the recomputed legacy baseline to the new outcome. The shift is "
            "overwhelmingly the **mechanic** switch (legacy front-reference to the two-sided E₇₅ "
            "rule), with the **input-structure** change (two DEA inputs to one TOTEX) small. "
            "Only past the two-sided baseline do the four cost components enter, and they net to "
            f"{net_players:+.3f} pp/yr. Amber raises the requirement, green lowers it."
        )
    else:
        st.caption(
            "Sector mean, current model to new model. The **residual** (the two-sided E₇₅ "
            "mechanic plus structural input differences, held out of the four players) accounts "
            f"for almost the whole shift. The four cost components net to {net_players:+.3f} "
            "pp/yr. Amber raises the requirement, green lowers it."
        )


# ---------------------------------------------------------------------------
# Fig 3a — small on average, large in redistribution (Shapley boxplots)
# ---------------------------------------------------------------------------

def render_shapley_boxplots(
    shapley: pd.DataFrame, user_reid: str, user_label: str,
    key: str = "nb_shapley_box",
) -> None:
    """One horizontal box per contribution term over the signed Shapley value (pp).

    Shows all six terms: the two structural terms (mechanic switch, input aggregation) on top,
    then the four cost components. Categories on the y-axis (more horizontal room for the
    spread). Every company is a faint point jittered *inside* the box's footprint (drawn behind
    a translucent box so the median (solid) and mean (dashed) lines stay crisp on top). The
    cost components sit near zero but spread wide (redistribution); the mechanic switch is a
    large near-uniform downward shift. A term is only drawn if its phi_<key> column is present.
    """
    keys = [k for k in DIST_TERM_KEYS if f"phi_{k}" in shapley.columns]
    if not keys:
        st.info("No Shapley data to plot.")
        return

    # Numeric y positions so the points can jitter inside each box; first key on top.
    n = len(keys)
    y_pos = {k: (n - 1 - i) for i, k in enumerate(keys)}
    box_width, jitter_w = 0.5, 0.20
    rng = np.random.default_rng(0)   # deterministic jitter — points don't jump between reruns

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()
    fig.add_vline(x=0, line_dash="dot", line_color=COLORS["text_muted"], line_width=1)

    vals_by_term = {
        k: pd.to_numeric(shapley[f"phi_{k}"], errors="coerce").dropna().to_numpy()
        for k in keys
    }

    # Layer 1 — the points, behind, jittered inside the box band, faint (box stays prominent).
    for k in keys:
        vals = vals_by_term[k]
        yj = y_pos[k] + rng.uniform(-jitter_w, jitter_w, len(vals))
        fig.add_trace(go.Scatter(
            x=vals, y=yj, mode="markers",
            marker=dict(color=DIST_TERM_COLORS[k], size=4, opacity=0.30, line=dict(width=0)),
            hoverinfo="skip",
            showlegend=False,
        ))

    # Layer 2 — the box on top: translucent fill so points show through, opaque median + mean.
    for k in keys:
        vals = vals_by_term[k]
        fig.add_trace(go.Box(
            x=vals, y=np.full(len(vals), y_pos[k]), width=box_width, orientation="h",
            line=dict(color=DIST_TERM_COLORS[k], width=1.5),
            fillcolor=_rgba(DIST_TERM_COLORS[k], 0.16),
            boxmean=True,                  # dashed mean line alongside the solid median
            boxpoints=False,               # raw points are the separate layer above
            hoverinfo="skip",
            showlegend=False,
        ))

    # Layer 3 — the user's firm, on top.
    u = shapley[shapley["REId"] == user_reid]
    if not u.empty:
        ux, uy = [], []
        for k in keys:
            v = u[f"phi_{k}"].iloc[0]
            if pd.notna(v):
                ux.append(float(v))
                uy.append(y_pos[k])
        if ux:
            fig.add_trace(go.Scatter(
                x=ux, y=uy, mode="markers", name=user_label,
                marker=dict(symbol="diamond", color=COLORS["text_primary"], size=11,
                            line=dict(color="white", width=1.5)),
                hoverinfo="skip",
            ))

    fig.update_layout(
        **layout_kwargs, template=template,
        title=dict(text="Contribution distribution by term", font=dict(size=13)),
        height=max(460, n * 95), dragmode=False, hovermode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        margin=dict(l=10, r=10, t=60, b=40),
        xaxis=dict(title="Shapley contribution (pp/yr)", fixedrange=True,
                   gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"], zeroline=False),
        yaxis=dict(
            fixedrange=True, showgrid=False, linecolor=COLORS["bg_muted"],
            range=[-0.6, n - 0.4],
            tickmode="array", tickvals=[y_pos[k] for k in keys],
            ticktext=[DIST_TERM_LABELS[k] for k in keys],
        ),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)
    st.caption(
        "Each box is one term's signed Shapley contribution across the 145 scored companies "
        "(negative = lowers the requirement = favours the firm). The solid line is the median, "
        "the dashed line the mean, and every company is a faint point inside the box. The four "
        "**cost components** sit near zero but spread wide (redistribution between firms); the "
        "**mechanic switch** and **input structure** (slate, the two structural terms) are how "
        "the requirement is computed, with the mechanic a large near-uniform downward shift. "
        "Your firm is the diamond."
    )


# ---------------------------------------------------------------------------
# Fig 3b — redistribution along urbanity (mean Shapley per urban quartile)
# ---------------------------------------------------------------------------

def render_shapley_by_urban_quantile(
    shapley: pd.DataFrame, channels: pd.DataFrame, user_reid: str,
    key: str = "nb_shapley_quantile",
) -> None:
    """Mean Shapley contribution per term, grouped by urban quartile (grouped bars).

    Joins the per-firm contributions to urbanity_index and bins firms into four equal urban
    quartiles (Q1 least urban to Q4 most). The x-axis is the urbanity axis (the quartiles);
    each term is a bar in its own colour (matching the boxplot), so scanning one colour across
    Q1 to Q4 reveals its gradient. Click a legend entry to hide/show a term; the y-axis
    rescales to the visible terms, so hiding the large mechanic term lets the cost-component
    gradients expand.
    """
    keys = [k for k in DIST_TERM_KEYS if f"phi_{k}" in shapley.columns]
    phi_cols = [f"phi_{k}" for k in keys]
    if not keys or "urbanity_index" not in channels.columns:
        st.info("No data to plot.")
        return

    d = shapley[["REId", *phi_cols]].merge(
        channels[["REId", "urbanity_index"]], on="REId", how="inner"
    ).dropna(subset=["urbanity_index", *phi_cols])
    if len(d) < 4:
        st.info("No data to plot.")
        return

    # Rank-based quartiles so ties (many rural firms near 0) cannot collapse the bins.
    q_labels = ["Q1 (least urban)", "Q2", "Q3", "Q4 (most urban)"]
    d = d.copy()
    d["_q"] = pd.qcut(d["urbanity_index"].rank(method="first"), 4, labels=q_labels)
    agg = d.groupby("_q", observed=True)[phi_cols].mean()

    user_q = None
    u = d[d["REId"] == user_reid]
    if not u.empty:
        user_q = str(u["_q"].iloc[0])

    layout_kwargs, template = get_plotly_template_safe()
    fig = go.Figure()
    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["text_muted"], line_width=1)

    # One bar per term (its boxplot colour); x = quartiles (the urbanity axis).
    for k in keys:
        ys = [float(agg.loc[ql, f"phi_{k}"]) if ql in agg.index else None for ql in q_labels]
        fig.add_trace(go.Bar(
            x=q_labels, y=ys, name=DIST_TERM_LABELS[k],
            marker=dict(color=DIST_TERM_COLORS[k], opacity=0.72, line=dict(color="white", width=0.5)),
            hoverinfo="skip",
        ))

    fig.update_layout(
        **layout_kwargs, template=template, barmode="group",
        title=dict(text="Contribution along urbanity", font=dict(size=13)),
        height=400, dragmode=False, hovermode=False, bargap=0.25, bargroupgap=0.04,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=10), itemclick="toggle", itemdoubleclick="toggleothers"),
        margin=dict(l=10, r=10, t=60, b=40),
        xaxis=dict(title="Urban quartile  (least → most urban)", fixedrange=True,
                   showgrid=False, linecolor=COLORS["bg_muted"]),
        yaxis=dict(title="Mean Shapley contribution (pp/yr)", fixedrange=True,
                   gridcolor=COLORS["bg_subtle"], linecolor=COLORS["bg_muted"], zeroline=False),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=key)
    caption = (
        "Each term's Shapley contribution averaged within urban quartiles (negative = favours "
        "the firm). Scanning one colour across Q1→Q4 shows its gradient: capex levelling turns "
        "more favourable toward urban firms, cable length toward rural. The slate structural "
        "terms (mechanic, input) are flat or weakly sloped; the mechanic sits far below as a "
        "large near-uniform shift. Click a legend entry to hide that term; the axis rescales "
        "to what remains."
    )
    if user_q:
        caption += f" Your firm is in **{user_q}**."
    st.caption(caption)


def _rgba(hex_color: str, alpha: float) -> str:
    """'#RRGGBB' → 'rgba(r, g, b, alpha)' for translucent fills."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
