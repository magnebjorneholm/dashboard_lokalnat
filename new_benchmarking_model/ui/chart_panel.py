"""
chart_panel.py — generic thematic-group panel for the new-benchmarking result view.

Related charts are grouped into themes shown at one vertical position and switched
horizontally. The horizontal switcher is deliberately isolated here (currently st.tabs)
so swapping it for st.segmented_control / st.pills / st.radio later is a one-function
change that no caller has to know about.

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
    """Render the thematic groups behind a horizontal switcher.

    Currently a tab strip: each group occupies the same vertical position and the user
    moves between them horizontally. To switch the mechanic (e.g. to a segmented control
    that renders only the active group), change only this function.
    """
    if not groups:
        return
    tabs = st.tabs([g.title for g in groups])
    for tab, group in zip(tabs, groups):
        with tab:
            group.render(ctx)
