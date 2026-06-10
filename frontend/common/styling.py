"""
Regumetrica styling.

Two layers, applied per zone:

- ``apply_base_styling()`` — fonts (Inter / IBM Plex Mono), tabular numbers,
  branding removal. Applied globally to BOTH the public landing zone and the
  authenticated tool zone.
- ``apply_tool_chrome()`` — widget refinements + the locked, always-visible
  sidebar. Applied ONLY in the "Revenue cap tool" zone. The landing zone brings
  its own look via ``frontend/common/landing_shell.py`` and must not inherit the
  locked sidebar.

Usage in streamlit_app.py:
    from frontend.common.styling import apply_base_styling, apply_tool_chrome
    st.set_page_config(...)
    apply_base_styling()          # always
    ...
    if authenticated_tool_zone:
        apply_tool_chrome()

Re-exports ``COLORS`` / ``CHART_COLORS`` / ``get_plotly_template`` from
config.colors so existing ``from frontend.common.styling import COLORS`` imports
keep working.
"""

import streamlit as st

from config.colors import COLORS, CHART_COLORS, get_plotly_template  # noqa: F401


def _font_links() -> str:
    """Google Fonts link elements."""
    return """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    """


def _base_css() -> str:
    """Typography, tabular numbers, branding removal — global to both zones."""
    return """
    <style>
        /* === TYPOGRAPHY === */
        /* Global font override - requires !important to beat Streamlit defaults */
        html, body, .stApp, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', sans-serif !important;
        }

        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        label {
            font-family: 'Inter', sans-serif !important;
        }

        .stMarkdown, .stMarkdown p,
        [data-testid="stMarkdownContainer"] p {
            font-family: 'Inter', sans-serif !important;
        }

        [data-testid="stRadio"] label,
        [data-testid="stCheckbox"] label {
            font-family: 'Inter', sans-serif !important;
        }

        [data-testid="stAlert"] p {
            font-family: 'Inter', sans-serif !important;
        }

        .stCaption, .stCaption p {
            font-family: 'Inter', sans-serif !important;
        }

        /* Tabular numbers for financial data */
        [data-testid="stMetricValue"],
        [data-testid="stDataFrame"],
        .stDataFrame {
            font-family: 'Inter', sans-serif !important;
            font-feature-settings: 'tnum' 1, 'lnum' 1;
        }

        /* Monospace for code and data cells */
        code, pre {
            font-family: 'IBM Plex Mono', 'Consolas', monospace !important;
        }

        [data-testid="stDataFrame"] [role="gridcell"] {
            font-family: 'IBM Plex Mono', monospace !important;
        }

        /* === BRANDING === */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
    </style>
    """


def _tool_chrome_css() -> str:
    """Widget refinements + locked, always-visible sidebar — tool zone only."""
    return f"""
    <style>
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

        /* === SIDEBAR === */
        /* Lock sidebar width — prevent drag-resize while keeping open/close */
        [data-testid="stSidebar"] {{
            min-width: 336px !important;
            max-width: 336px !important;
        }}
        [data-testid="stSidebar"] > div {{
            width: 336px !important;
        }}
        /* Hide the resize handle */
        [data-testid="stSidebar"]::after,
        [data-testid="stSidebarContent"]::after {{
            pointer-events: none !important;
            display: none !important;
        }}

        /* === SIDEBAR ALWAYS VISIBLE === */
        /* Hide the collapse button inside the sidebar */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebar"] button[kind="headerNoPadding"] {{
            display: none !important;
        }}
        /* Hide the expand arrow shown when sidebar is collapsed */
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
    </style>
    """


def apply_base_styling() -> None:
    """Fonts + tabular numbers + branding removal. Apply globally (both zones)."""
    st.markdown(_font_links(), unsafe_allow_html=True)
    st.markdown(_base_css(), unsafe_allow_html=True)


def apply_tool_chrome() -> None:
    """Widget refinements + locked sidebar. Apply only in the tool zone."""
    st.markdown(_tool_chrome_css(), unsafe_allow_html=True)
