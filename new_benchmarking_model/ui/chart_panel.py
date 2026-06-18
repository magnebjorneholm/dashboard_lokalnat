"""
chart_panel.py — generic thematic-group panel for the new-benchmarking result view.

Related charts are grouped into themes. The themes are currently stacked vertically (the
user reads the whole result by scrolling), each under its own heading. The layout
mechanic is deliberately isolated here so swapping the vertical stack for a horizontal
switcher (st.tabs / st.segmented_control / st.pills) later is a one-function change that
no caller has to know about.

A "group" is just a title plus a render callback that takes whatever context object the
caller passes through (this module never inspects it), so the panel stays decoupled from
the specific result type it happens to display.

Add a new theme where the groups are defined (company_view.CHART_GROUPS), not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

import streamlit as st


@dataclass(frozen=True)
class ChartGroup:
    """One thematic group of charts.

    key:    stable identifier (handy for widget keys / future deep-linking).
    title:  the label shown on the horizontal switcher.
    render: callback that draws the group, given the shared context object.
    """
    key: str
    title: str
    render: Callable[[Any], None]


def render_chart_panel(groups: Sequence[ChartGroup], ctx: Any) -> None:
    """Render the thematic groups stacked vertically, one after another.

    Each group gets its title as a section heading and is separated from the previous one
    by a divider, so the user reads the whole result by scrolling. The grouping
    abstraction is kept so a horizontal switcher (st.tabs / st.segmented_control /
    st.pills) can be restored later by changing only this function.
    """
    for i, group in enumerate(groups):
        if i > 0:
            st.divider()
        st.markdown(f"#### {group.title}")
        group.render(ctx)
