"""
Regumetrica Styling Module.

Centralized CSS styling for professional Nordic Blue design profile.
Import and call apply_styling() in streamlit_app.py.

Version: 1.2 - Fixed expander icon rendering (Material Icons preservation)
"""

import streamlit as st

# === COLOR PALETTE ===
# Nordic Blue - consulting/finance inspired

COLORS = {
    # Primary brand colors
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "primary_light": "#60A5FA",
    
    # Secondary colors
    "secondary": "#475569",
    "accent": "#0891B2",
    
    # Backgrounds
    "bg_page": "#F8FAFC",
    "bg_card": "#FFFFFF",
    "bg_subtle": "#F1F5F9",
    "bg_muted": "#E2E8F0",
    
    # Text
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#64748B",
    
    # Semantic colors
    "success": "#059669",
    "warning": "#D97706",
    "error": "#DC2626",
    "info": "#0284C7",
    
    # Sidebar (dark variant)
    "sidebar_bg": "#1E293B",
    "sidebar_text": "#F1F5F9",
    "sidebar_muted": "#94A3B8",
}

# Chart colors (colorblind-safe)
CHART_COLORS = [
    "#2563EB",  # Primary Blue
    "#0891B2",  # Teal
    "#7C3AED",  # Violet
    "#059669",  # Emerald
    "#EA580C",  # Orange
    "#DC2626",  # Red
    "#64748B",  # Slate
    "#A855F7",  # Purple
]


def _get_font_links() -> str:
    """
    Returns HTML link elements for Google Fonts.
    
    Using <link> elements instead of @import ensures fonts load correctly
    regardless of where Streamlit injects the HTML.
    """
    return """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    """


def _get_custom_css() -> str:
    """
    Returns CSS rules for Regumetrica styling.
    
    Note: Font loading is handled separately via _get_font_links().
    Extended selectors for Streamlit 1.52.2 compatibility.
    Version 1.2: Fixed Material Icons preservation for expander arrows.
    """
    return f"""
    <style>
        /* === MATERIAL ICONS PRESERVATION === */
        /* Must come first to establish baseline for icon fonts */
        .material-symbols-rounded,
        .material-symbols-outlined,
        .material-icons,
        [data-testid="stExpander"] summary svg,
        [data-testid="stExpander"] summary span[class*="icon"],
        [data-testid="stExpander"] summary > span:first-child,
        [class*="icon"],
        [class*="Icon"] {{
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        }}
        
        /* === MATHJAX / KATEX PRESERVATION === */
        /* Preserve math fonts for LaTeX rendering */
        .MathJax,
        .MathJax *,
        .MathJax_Display,
        .MathJax_Preview,
        .MJXc-display,
        .mjx-chtml,
        .mjx-chtml *,
        .mjx-math,
        .mjx-math *,
        .mjx-mrow,
        .mjx-mi,
        .mjx-mo,
        .mjx-mn,
        .mjx-mfrac,
        .mjx-msup,
        .mjx-msub,
        .katex,
        .katex *,
        .katex-display,
        .katex-html,
        .katex-mathml,
        [class*="MathJax"],
        [class*="mjx-"],
        [class*="katex"] {{
            font-family: inherit !important;
        }}
        
        /* Ensure math containers don't get Inter */
        .element-container:has(.MathJax),
        .element-container:has(.katex),
        .stMarkdown:has(.MathJax),
        .stMarkdown:has(.katex) {{
            font-family: inherit;
        }}
        
        /* === GLOBAL TYPOGRAPHY === */
        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }}
        
        /* Selective catch-all - excludes icon elements */
        .stApp {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        
        /* Tabular numbers for numeric data */
        .stMetric, .stDataFrame, [data-testid="stMetricValue"] {{
            font-feature-settings: 'tnum' 1, 'lnum' 1;
        }}
        
        /* Monospace for code blocks and technical values */
        code, pre, .stCodeBlock {{
            font-family: 'IBM Plex Mono', 'Consolas', monospace !important;
        }}
        
        /* === HEADINGS === */
        h1 {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_primary"]};
            font-weight: 600;
            font-size: 1.875rem;
            letter-spacing: -0.025em;
        }}
        
        h2 {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_primary"]};
            font-weight: 600;
            font-size: 1.5rem;
        }}
        
        h3 {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_primary"]};
            font-weight: 500;
            font-size: 1.25rem;
        }}
        
        /* === WIDGET LABELS (Streamlit 1.52.2 extended selectors) === */
        /* Primary label selectors */
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] > div,
        [data-testid="stWidgetLabel"] > div > p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Number input specific */
        [data-testid="stNumberInput"] label,
        [data-testid="stNumberInput"] [data-testid="stWidgetLabel"],
        [data-testid="stNumberInput"] [data-testid="stWidgetLabel"] p,
        .stNumberInput label,
        .stNumberInput [data-testid="stWidgetLabel"],
        .stNumberInput [data-testid="stWidgetLabel"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Text input specific */
        [data-testid="stTextInput"] label,
        [data-testid="stTextInput"] [data-testid="stWidgetLabel"],
        [data-testid="stTextInput"] [data-testid="stWidgetLabel"] p,
        .stTextInput label,
        .stTextInput [data-testid="stWidgetLabel"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Select box specific */
        [data-testid="stSelectbox"] label,
        [data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
        [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p,
        .stSelectbox label,
        .stSelectbox [data-testid="stWidgetLabel"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Multiselect specific */
        [data-testid="stMultiSelect"] label,
        [data-testid="stMultiSelect"] [data-testid="stWidgetLabel"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Slider specific */
        [data-testid="stSlider"] label,
        [data-testid="stSlider"] [data-testid="stWidgetLabel"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Checkbox and radio specific */
        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label,
        [data-testid="stRadio"] [data-testid="stWidgetLabel"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* BaseWeb components (underlying UI library) */
        [data-baseweb="input"] {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        [data-baseweb="select"] {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        [data-baseweb="textarea"] {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Form labels fallback */
        label {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Paragraph text in widgets - but not in expanders */
        .stApp > div > div > div > div > p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* === SIDEBAR === */
        [data-testid="stSidebar"] {{
            background-color: {COLORS["sidebar_bg"]};
        }}
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
            color: {COLORS["sidebar_text"]};
        }}
        
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
            color: {COLORS["sidebar_text"]};
            font-family: 'Inter', sans-serif !important;
        }}
        
        [data-testid="stSidebar"] hr {{
            border-color: {COLORS["secondary"]};
        }}
        
        [data-testid="stSidebar"] .stCaption {{
            color: {COLORS["sidebar_muted"]};
        }}
        
        /* === METRICS === */
        [data-testid="stMetric"] {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["bg_muted"]};
            border-radius: 8px;
            padding: 16px 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }}
        
        [data-testid="stMetricValue"] {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_primary"]};
            font-weight: 600;
        }}
        
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_secondary"]};
            font-weight: 500;
        }}
        
        /* Positive/negative delta colors */
        [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Up"] {{
            fill: {COLORS["success"]};
        }}
        
        [data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Down"] {{
            fill: {COLORS["error"]};
        }}
        
        /* === BUTTONS === */
        .stButton > button {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 500;
            border-radius: 6px;
            transition: all 0.15s ease;
        }}
        
        .stButton > button[kind="primary"] {{
            background-color: {COLORS["primary"]};
            border: none;
        }}
        
        .stButton > button[kind="primary"]:hover {{
            background-color: {COLORS["primary_hover"]};
        }}
        
        .stButton > button[kind="secondary"] {{
            background-color: transparent;
            border: 1px solid {COLORS["bg_muted"]};
            color: {COLORS["text_primary"]};
        }}
        
        .stButton > button[kind="secondary"]:hover {{
            background-color: {COLORS["bg_subtle"]};
            border-color: {COLORS["secondary"]};
        }}
        
        /* === TABS === */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: transparent;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 500;
            color: {COLORS["text_secondary"]};
            border-radius: 6px 6px 0 0;
            padding: 10px 16px;
        }}
        
        .stTabs [aria-selected="true"] {{
            color: {COLORS["primary"]};
            background-color: {COLORS["bg_card"]};
        }}
        
        /* === EXPANDERS === */
        /* Header styling - target text only, preserve icons */
        .streamlit-expanderHeader {{
            font-weight: 500;
            color: {COLORS["text_primary"]};
            background-color: {COLORS["bg_subtle"]};
            border-radius: 6px;
        }}
        
        /* Target only paragraph text in expander header */
        .streamlit-expanderHeader > div > p,
        .streamlit-expanderHeader p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Expander summary - only the text div, not the icon */
        [data-testid="stExpander"] summary > div:not(:first-child) {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Expander text content */
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Ensure expander icons retain Material Icons font */
        [data-testid="stExpander"] summary > span:first-child,
        [data-testid="stExpander"] summary > div:first-child > span,
        .streamlit-expanderHeader span[data-testid],
        [data-testid="stExpanderToggleIcon"] {{
            font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        }}
        
        .streamlit-expanderContent {{
            border: 1px solid {COLORS["bg_muted"]};
            border-top: none;
            border-radius: 0 0 6px 6px;
        }}
        
        /* === DATA EDITOR / TABLES === */
        [data-testid="stDataFrame"] {{
            border: 1px solid {COLORS["bg_muted"]};
            border-radius: 8px;
            overflow: hidden;
        }}
        
        [data-testid="stDataFrameResizable"] {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 13px;
        }}
        
        /* Data editor cells */
        [data-testid="stDataFrame"] [role="gridcell"] {{
            font-family: 'IBM Plex Mono', monospace !important;
        }}
        
        /* Data editor headers */
        [data-testid="stDataFrame"] [role="columnheader"] {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 500;
        }}
        
        /* === INPUTS === */
        .stNumberInput input,
        .stTextInput input,
        .stSelectbox select,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input {{
            font-family: 'Inter', sans-serif !important;
            border-radius: 6px;
            border: 1px solid {COLORS["bg_muted"]};
        }}
        
        .stNumberInput input:focus,
        .stTextInput input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextInput"] input:focus {{
            border-color: {COLORS["primary"]};
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
        }}
        
        /* === ALERTS === */
        .stAlert {{
            border-radius: 8px;
            border-left-width: 4px;
        }}
        
        [data-testid="stAlert"][data-baseweb="notification"] {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        [data-testid="stAlert"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* === STATUS === */
        [data-testid="stStatusWidget"] {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        [data-testid="stStatusWidget"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* === DIVIDERS === */
        hr {{
            border-color: {COLORS["bg_muted"]};
            margin: 1.5rem 0;
        }}
        
        /* === CAPTIONS === */
        .stCaption, .stCaption p {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_muted"]};
            font-size: 0.875rem;
        }}
        
        /* === MARKDOWN TEXT === */
        .stMarkdown p, 
        [data-testid="stMarkdownContainer"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* === FILE UPLOADER === */
        [data-testid="stFileUploader"] label,
        [data-testid="stFileUploader"] [data-testid="stWidgetLabel"] p {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* === HIDE STREAMLIT BRANDING === */
        #MainMenu {{
            visibility: hidden;
        }}
        
        footer {{
            visibility: hidden;
        }}
        
        /* === CUSTOM UTILITY CLASSES === */
        .metric-card {{
            background: {COLORS["bg_card"]};
            border: 1px solid {COLORS["bg_muted"]};
            border-radius: 12px;
            padding: 20px 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }}
        
        .section-header {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_primary"]};
            font-weight: 600;
            font-size: 1.125rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid {COLORS["primary"]};
        }}
        
        .data-label {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["text_secondary"]};
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .highlight-value {{
            font-family: 'Inter', sans-serif !important;
            color: {COLORS["primary"]};
            font-weight: 600;
            font-feature-settings: 'tnum' 1;
        }}
        
        .change-positive {{
            color: {COLORS["success"]};
        }}
        
        .change-negative {{
            color: {COLORS["error"]};
        }}
    </style>
    """


def apply_styling():
    """
    Apply Regumetrica design profile.
    
    Call this function FIRST in streamlit_app.py, after st.set_page_config():
    
        from frontend.common.styling import apply_styling
        st.set_page_config(...)
        apply_styling()
    
    The function injects Google Fonts via <link> elements and CSS rules
    via <style> block. Using !important ensures styles override Streamlit defaults.
    """
    st.markdown(_get_font_links(), unsafe_allow_html=True)
    st.markdown(_get_custom_css(), unsafe_allow_html=True)


def get_plotly_template() -> dict:
    """
    Returns Plotly layout template for consistent chart styling.
    
    Usage:
        fig.update_layout(**get_plotly_template())
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
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        "xaxis": {
            "showgrid": False,
            "linecolor": COLORS["bg_muted"],
            "tickfont": {"size": 11},
        },
        "yaxis": {
            "gridcolor": COLORS["bg_subtle"],
            "linecolor": COLORS["bg_muted"],
            "tickfont": {"size": 11},
        },
        "colorway": CHART_COLORS,
    }


def styled_metric_card(label: str, value: str, delta: str = None, delta_color: str = None):
    """
    Render a styled metric card with HTML.
    
    Args:
        label: Metric label
        value: Main value
        delta: Change (optional)
        delta_color: 'positive', 'negative' or None
    """
    delta_html = ""
    if delta:
        color_class = f"change-{delta_color}" if delta_color else ""
        delta_html = f'<div class="{color_class}" style="font-size: 0.875rem; margin-top: 4px;">{delta}</div>'
    
    html = f"""
    <div class="metric-card">
        <div class="data-label">{label}</div>
        <div class="highlight-value" style="font-size: 1.5rem; margin-top: 8px;">{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def section_header(text: str):
    """Render a styled section header."""
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)