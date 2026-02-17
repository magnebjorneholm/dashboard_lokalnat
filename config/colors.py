"""
config/colors.py

Color constants and Plotly template for Regumetrica.
Extracted from frontend/common/styling.py so non-Streamlit code can import
colors without pulling in Streamlit.
"""

# Color constants (matching .streamlit/config.toml for programmatic use)
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
