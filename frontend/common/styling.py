"""
Regumetrica Styling Module.

Minimal CSS to complement .streamlit/config.toml theme settings.
Focuses on: font loading, tabular numbers, code font, branding removal.

Usage in streamlit_app.py:
    from frontend.common.styling import apply_styling
    st.set_page_config(...)
    apply_styling()
"""

import streamlit as st


# Color constants (matching config.toml for programmatic use)
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


def _get_font_links() -> str:
    """Google Fonts link elements."""
    return """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    """


def _get_custom_css() -> str:
    """CSS rules for Regumetrica styling."""
    return f"""
    <style>
        /* === TYPOGRAPHY === */
        /* Global font override - requires !important to beat Streamlit defaults */
        html, body, .stApp, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }}
        
        /* Headings */
        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Widget labels */
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        label {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Markdown and text */
        .stMarkdown, .stMarkdown p,
        [data-testid="stMarkdownContainer"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Radio buttons and checkboxes */
        [data-testid="stRadio"] label,
        [data-testid="stCheckbox"] label {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Alerts and info boxes */
        [data-testid="stAlert"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Captions */
        .stCaption, .stCaption p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Tabular numbers for financial data */
        [data-testid="stMetricValue"],
        [data-testid="stDataFrame"],
        .stDataFrame {{
            font-family: 'Inter', sans-serif !important;
            font-feature-settings: 'tnum' 1, 'lnum' 1;
        }}
        
        /* Monospace for code and data cells */
        code, pre {{
            font-family: 'IBM Plex Mono', 'Consolas', monospace !important;
        }}
        
        [data-testid="stDataFrame"] [role="gridcell"] {{
            font-family: 'IBM Plex Mono', monospace !important;
        }}
        
        /* === REFINEMENTS === */
        /* Primary button hover */
        [data-testid="stBaseButton-primary"]:hover {{
            background-color: {COLORS["primary_hover"]};
        }}
        
        /* Input focus state */
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextInput"] input:focus {{
            border-color: {COLORS["primary"]};
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
        }}
        
        /* Expander styling */
        [data-testid="stExpander"] {{
            border: 1px solid {COLORS["bg_muted"]};
            border-radius: 8px;
        }}
        
        /* Divider color */
        hr {{
            border-color: {COLORS["bg_muted"]};
        }}
        
        /* === BRANDING === */
        #MainMenu {{
            visibility: hidden;
        }}
        
        footer {{
            visibility: hidden;
        }}
    </style>
    """


def apply_styling():
    """
    Apply Regumetrica styling.
    """
    st.markdown(_get_font_links(), unsafe_allow_html=True)
    st.markdown(_get_custom_css(), unsafe_allow_html=True)


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