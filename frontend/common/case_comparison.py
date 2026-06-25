"""
Case Comparison Table.

Renders a side-by-side KPI comparison of saved cases using their
result snapshots.  Baseline values come from snapshot baseline_* fields.
"""

from typing import List

import streamlit as st

from config.colors import COLORS
from config.formatting import format_tkr, format_percent
from frontend.utils.case_storage import SavedCase


# (label, snapshot_key, format_type, highlight)
_COMPARISON_KPIS = [
    ("Revenue cap", "revenue_frame", "tkr", True),
    ("Capital cost (period)", "capital_cost_period", "tkr", False),
    ("Capital cost in RF", "capital_cost_in_rf", "tkr", False),
    ("Controllable (period)", "controllable_period", "tkr", False),
    ("Controllable in RF", "controllable_in_rf", "tkr", False),
    ("Non-controllable", "non_controllable_period", "tkr", False),
    ("Flexibility", "flexibility_period", "tkr", False),
    ("Efficiency deduction", "efficiency_deduction", "tkr", False),
    ("Incentive total", "incentive_total", "tkr", False),
    ("DEA efficiency", "dea_efficiency", "percent", False),
    ("Eff. req. (annual)", "efficiency_req_annual", "percent", False),
]


def _fmt(value, fmt_type: str) -> str:
    """Format a snapshot value for display."""
    if value is None:
        return "—"
    if fmt_type == "tkr":
        return format_tkr(value)
    if fmt_type == "percent":
        return format_percent(value)
    return str(value)


def _delta_html(case_val, baseline_val, fmt_type: str) -> str:
    """Return a small HTML delta string (colored)."""
    if case_val is None or baseline_val is None:
        return ""
    delta = case_val - baseline_val
    if abs(delta) < 0.5 and fmt_type == "tkr":
        return ""
    if abs(delta) < 1e-6 and fmt_type == "percent":
        return ""

    color = COLORS["success"] if delta >= 0 else COLORS["error"]
    arrow = "&#9650;" if delta > 0 else "&#9660;"

    if fmt_type == "tkr":
        sign = "+" if delta >= 0 else ""
        text = f"{sign}{delta:,.0f}".replace(",", " ") + " tkr"
    else:
        sign = "+" if delta >= 0 else ""
        text = f"{sign}{delta * 100:.2f}%"

    return (
        f'<span style="color:{color};font-size:0.8em;font-weight:500;">'
        f'{arrow}&nbsp;{text}</span>'
    )


def render_comparison_table(cases: List[SavedCase]) -> None:
    """Render an inline HTML comparison table for selected cases."""
    if not cases:
        return

    # --- Baseline from first case's snapshot ---
    baseline_snap = cases[0].result_snapshot or {}

    # --- Build HTML ---
    n_cases = len(cases)
    col_width = max(140, 600 // (n_cases + 2))

    header_cells = (
        f'<th style="text-align:left;padding:8px 12px;border-bottom:2px solid {COLORS["bg_muted"]};">'
        f'KPI</th>'
        f'<th style="text-align:right;padding:8px 12px;background:{COLORS["bg_subtle"]};'
        f'border-bottom:2px solid {COLORS["bg_muted"]};min-width:{col_width}px;">'
        f'Baseline</th>'
    )
    for c in cases:
        header_cells += (
            f'<th style="text-align:right;padding:8px 12px;'
            f'border-bottom:2px solid {COLORS["bg_muted"]};min-width:{col_width}px;">'
            f'{c.name}</th>'
        )

    rows_html = ""
    for label, key, fmt_type, highlight in _COMPARISON_KPIS:
        baseline_val = baseline_snap.get(f"baseline_{key}")
        label_weight = "600" if highlight else "400"
        label_style = (
            f'padding:6px 12px;font-weight:{label_weight};'
            f'color:{COLORS["text_secondary"]};white-space:nowrap;'
            f'border-bottom:1px solid {COLORS["bg_muted"]};'
        )
        baseline_style = (
            f'text-align:right;padding:6px 12px;'
            f'background:{COLORS["bg_subtle"]};'
            f'border-bottom:1px solid {COLORS["bg_muted"]};'
        )

        row = f'<td style="{label_style}">{label}</td>'
        row += f'<td style="{baseline_style}">{_fmt(baseline_val, fmt_type)}</td>'

        for c in cases:
            snap = c.result_snapshot or {}
            case_val = snap.get(key)
            cell_weight = "600" if highlight else "400"
            delta = _delta_html(case_val, baseline_val, fmt_type)
            delta_block = f'<br>{delta}' if delta else ""
            row += (
                f'<td style="text-align:right;padding:6px 12px;'
                f'font-weight:{cell_weight};'
                f'border-bottom:1px solid {COLORS["bg_muted"]};">'
                f'{_fmt(case_val, fmt_type)}{delta_block}</td>'
            )

        rows_html += f"<tr>{row}</tr>\n"

    table_html = f"""
    <div style="overflow-x:auto;margin-top:8px;">
    <table style="border-collapse:collapse;width:100%;
        font-family:'IBM Plex Mono','Courier New',monospace;
        font-feature-settings:'tnum';font-size:0.9em;">
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{rows_html}</tbody>
    </table>
    </div>
    """

    st.markdown("##### Case comparison")
    st.markdown(table_html, unsafe_allow_html=True)
