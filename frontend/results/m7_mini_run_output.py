"""
M7 Benchmarking - Mini-run inline results.

Renders DEA mini-run results inside the M7 config tab.
Two views: compact metrics (always visible) and expanded details (st.expander).
"""

import streamlit as st
import plotly.graph_objects as go
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.mini_run import MiniRunResult

from config.column_names import COL_DEA_EFFICIENCY, COL_IS_OUTLIER
from config.formatting import format_percent, format_pp
from config.colors import CHART_COLORS, get_plotly_template_safe


def render_mini_results(
    result: "MiniRunResult",
    baseline: "MiniRunResult",
) -> None:
    """Render mini-run results inline in the M7 tab."""

    st.divider()
    st.markdown("**DEA results** (mini-run)")

    _render_compact(result, baseline)

    with st.expander("All companies", expanded=False):
        _render_expanded(result, baseline)


def _render_compact(result: "MiniRunResult", baseline: "MiniRunResult") -> None:
    """Compact view: 4 key metrics with delta vs baseline."""

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta = None
        if result.user_efficiency is not None and baseline.user_efficiency is not None:
            d = result.user_efficiency - baseline.user_efficiency
            if abs(d) > 0.0005:
                delta = f"{d:+.3f}".replace(".", ",")
        st.metric(
            "Efficiency score",
            f"{result.user_efficiency:.3f}".replace(".", ",")
            if result.user_efficiency is not None
            else "-",
            delta=delta,
        )

    with col2:
        delta = None
        d_pot = result.user_potential - baseline.user_potential
        if abs(d_pot) > 0.00005:
            delta = format_pp(d_pot, 1)
        st.metric(
            "Potential",
            format_percent(result.user_potential, 1),
            delta=delta,
            delta_color="inverse",
        )

    with col3:
        label_case = "Yes" if result.user_is_outlier else "No"
        label_bl = "Yes" if baseline.user_is_outlier else "No"
        st.metric(
            "Outlier",
            label_case,
            delta="Changed" if label_case != label_bl else None,
        )

    with col4:
        delta = None
        d_eff = result.user_eff_req_annual - baseline.user_eff_req_annual
        if abs(d_eff) > 0.00005:
            delta = format_pp(d_eff)
        st.metric(
            "Eff. requirement",
            format_percent(result.user_eff_req_annual),
            delta=delta,
            delta_color="inverse",
        )


def _render_expanded(result: "MiniRunResult", baseline: "MiniRunResult") -> None:
    """Expanded view: distribution stats + histogram."""

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Companies", result.n_companies)

    with col2:
        d_out = result.n_outliers - baseline.n_outliers
        st.metric(
            "Outliers",
            result.n_outliers,
            delta=f"{d_out:+d}" if d_out != 0 else None,
        )

    with col3:
        d_rank = baseline.user_rank - result.user_rank  # positive = improved
        st.metric(
            "Rank",
            f"{result.user_rank} / {result.n_companies}",
            delta=f"{d_rank:+d}" if d_rank != 0 else None,
        )

    # Histogram of efficiency scores
    eff_scores = result.dea_results[COL_DEA_EFFICIENCY].dropna()
    outlier_mask = result.dea_results[COL_IS_OUTLIER].fillna(False)

    layout_kwargs, template_name = get_plotly_template_safe()

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=eff_scores[~outlier_mask],
            nbinsx=20,
            marker_color=CHART_COLORS[0],
            marker_line_color="white",
            marker_line_width=1,
            opacity=0.85,
            name="Non-outlier",
            showlegend=False,
        )
    )

    # Mark user's position
    if result.user_efficiency is not None:
        fig.add_vline(
            x=result.user_efficiency,
            line_color=CHART_COLORS[2],
            line_width=2,
            line_dash="dash",
        )
        fig.add_annotation(
            x=result.user_efficiency,
            y=1,
            yref="paper",
            yshift=5,
            text=f"You: {result.user_efficiency:.3f}".replace(".", ","),
            showarrow=False,
            font=dict(size=11, color=CHART_COLORS[2]),
        )

    fig.update_layout(
        **layout_kwargs,
        template=template_name,
        height=260,
        xaxis_title="Efficiency score",
        yaxis_title="Companies",
        margin=dict(t=25, b=40, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
