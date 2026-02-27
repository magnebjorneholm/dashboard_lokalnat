"""
config/colors.py

Color constants and Plotly template for Regumetrica.
Extracted from frontend/common/styling.py so non-Streamlit code can import
colors without pulling in Streamlit.
"""

from typing import Tuple

# ---------------------------------------------------------------------------
# Core design tokens
# ---------------------------------------------------------------------------

COLORS = {
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "bg_page": "#F8FAFC",
    "bg_card": "#FFFFFF",
    "bg_subtle": "#F1F5F9",
    "bg_muted": "#E2E8F0",
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#64748B",
    "success": "#059669",
    "warning": "#D97706",
    "warning_light": "#FEF3C7",
    "error": "#DC2626",
}

# Chart colors (colorblind-safe palette)
CHART_COLORS = [
    "#2563EB",  # Primary Blue
    "#0891B2",  # Teal
    "#7C3AED",  # Violet
    "#059669",  # Emerald
    "#EA580C",  # Orange
    "#DC2626",  # Red
    "#64748B",  # Slate
]

# ---------------------------------------------------------------------------
# Specialized visualization color groups
# ---------------------------------------------------------------------------

# Waterfall chart colors (M4, M5, results page)
WATERFALL_COLORS = {
    "base": "#3B82F6",       # Blue-500
    "deduction": "#DC2626",  # Red-600
    "total": "#1E3A5F",      # Dark navy
}

# Case/baseline comparison (M1, M2, M3 return)
COMPARISON_COLORS = {
    "case_ord": CHART_COLORS[0],  # Primary Blue
    "case_tail": "#93C5FD",       # Blue-300
    "bl_ord": "#64748B",          # Slate-500
    "bl_tail": "#CBD5E1",         # Slate-300
}

# Scatter plot (M5 frontier chart)
SCATTER_COLORS = {
    "normal": "#94A3B8",                  # Slate-400
    "efficient": "#059669",               # Emerald
    "outlier": "#EA580C",                 # Orange
    "user": COLORS["primary"],            # Primary blue
    "frontier": "rgba(5, 150, 105, 0.4)", # Emerald 40%
}

# Zone overlays (M5 histograms)
ZONE_COLORS = {
    "cap_fill": "rgba(234, 88, 12, 0.08)",
    "cap_border": "rgba(234, 88, 12, 0.25)",
    "active_fill": "rgba(37, 99, 235, 0.06)",
    "floor_fill": "rgba(5, 150, 105, 0.08)",
    "floor_border": "rgba(5, 150, 105, 0.25)",
}

# Incentive chart (M3 incentive output)
INCENTIVE_COLORS = {
    "quality": CHART_COLORS[0],   # Blue
    "netloss": CHART_COLORS[1],   # Teal
    "load": CHART_COLORS[2],      # Violet
    "cap": CHART_COLORS[4],       # Orange
    "total": CHART_COLORS[3],     # Emerald
    "positive": "#059669",        # Emerald
    "negative": "#DC2626",        # Red
}

# Geo map — muted red-green percentile gradient
GEO_COLORSCALE = [
    [0,     "#E2E8F0"],  # Slate-200 (missing data)
    [0.001, "#B91C1C"],  # Red-700
    [0.25,  "#C2410C"],  # Orange-700
    [0.5,   "#A16207"],  # Yellow-700
    [0.75,  "#15803D"],  # Green-700
    [1,     "#14532D"],  # Green-900
]

# Revenue frame diagram (HTML/CSS)
DIAGRAM_COLORS = {
    "box_bg": "#FFFFFF",
    "box_border": COLORS["bg_muted"],
    "box_hover_border": "#94A3B8",
    "box_modified_border": COLORS["primary"],
    "box_id_bg": COLORS["text_muted"],
    "box_id_modified_bg": COLORS["primary"],
    "box_title_color": COLORS["text_secondary"],
    "box_value_color": COLORS["text_primary"],
    "box_value_modified": "#1E40AF",
    "result_bg": COLORS["bg_page"],
    "result_border": "#CBD5E1",
    "flow_line": "#CBD5E1",
    "tooltip_bg": "#1E293B",
    "tooltip_text": COLORS["bg_page"],
    "sub_title_color": COLORS["text_muted"],
}

# ---------------------------------------------------------------------------
# Plotly templates
# ---------------------------------------------------------------------------


def get_plotly_template() -> dict:
    """
    Plotly layout template for consistent chart styling.
    """
    return {
        "template": "plotly_white",
        "font": {
            "family": "Inter, sans-serif",
            "size": 12,
            "color": COLORS["text_secondary"],
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
        "colorway": CHART_COLORS,
        "xaxis": {
            "showgrid": False,
            "linecolor": COLORS["bg_muted"],
        },
        "yaxis": {
            "gridcolor": COLORS["bg_subtle"],
            "linecolor": COLORS["bg_muted"],
        },
    }


def get_plotly_template_safe() -> Tuple[dict, str]:
    """Plotly template without axis/margin keys (avoids update_layout conflicts).

    Returns (layout_kwargs, template_name) so callers can do:
        kwargs, tname = get_plotly_template_safe()
        fig.update_layout(template=tname, **kwargs, ...)
    """
    tmpl = get_plotly_template()
    safe = {k: v for k, v in tmpl.items() if k not in ("xaxis", "yaxis", "margin")}
    template_name = safe.pop("template", "plotly_white")
    return safe, template_name
