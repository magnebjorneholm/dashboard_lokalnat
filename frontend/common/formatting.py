"""
Number Formatting for Regumetrica UI.

Handles thousand separators, percentages, and currency formats.
Includes HTML formatting for delta values with color coding.

Note: Uses European number format (comma as decimal separator, space as 
thousand separator) as per Swedish regulatory standards, but with English labels.
"""

from typing import Optional


def format_tkr(value: float) -> str:
    """
    Format value with thousand separators in tkr (thousand SEK).
    
    Args:
        value: Value in tkr
        
    Returns:
        Formatted string, e.g. "1 234 567 tkr"
    """
    return f"{value:,.0f}".replace(",", " ") + " tkr"


def format_percent(value: float, decimals: int = 2) -> str:
    """
    Format as percentage with European decimal comma.
    
    Args:
        value: Value as decimal (e.g. 0.0453 for 4.53%)
        decimals: Number of decimal places
        
    Returns:
        Formatted string, e.g. "4.53%"
    """
    formatted = f"{value * 100:.{decimals}f}"
    return formatted.replace(".", ",") + "%"


def format_number(value: float, decimals: int = 0) -> str:
    """
    Format number with European conventions.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
        
    Returns:
        Formatted string with European conventions
    """
    if decimals == 0:
        return f"{value:,.0f}".replace(",", " ")
    else:
        formatted = f"{value:,.{decimals}f}"
        parts = formatted.split(".")
        integer_part = parts[0].replace(",", " ")
        decimal_part = parts[1] if len(parts) > 1 else ""
        return f"{integer_part},{decimal_part}" if decimal_part else integer_part


def format_delta(value: float, unit: str = "tkr") -> str:
    """
    Format delta value with +/- prefix.
    
    Args:
        value: Delta value
        unit: Unit (default "tkr")
        
    Returns:
        Formatted string, e.g. "+1 234 tkr" or "-567 tkr"
    """
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:,.0f}".replace(",", " ") + f" {unit}"


def format_delta_html(
    value: float, 
    unit: str = "tkr",
    show_arrow: bool = True
) -> str:
    """
    Format delta value as HTML with color coding.
    
    Positive values shown in green, negative in red.
    
    Args:
        value: Delta value
        unit: Unit (default "tkr")
        show_arrow: Show arrow before value
        
    Returns:
        HTML string with color coding
    """
    try:
        from frontend.common.styling import COLORS
        color = COLORS["success"] if value >= 0 else COLORS["error"]
    except ImportError:
        color = "#059669" if value >= 0 else "#DC2626"
    
    sign = "+" if value >= 0 else ""
    arrow = "↑ " if value > 0 else ("↓ " if value < 0 else "")
    arrow_str = arrow if show_arrow else ""
    
    formatted_value = f"{value:,.0f}".replace(",", " ")
    
    return f'<span style="color: {color}; font-weight: 500;">{arrow_str}{sign}{formatted_value} {unit}</span>'


def format_delta_percent_html(
    value: float,
    decimals: int = 1,
    show_arrow: bool = True
) -> str:
    """
    Format percentage change as HTML with color coding.
    
    Args:
        value: Delta in percentage points (e.g. 0.05 for +5%)
        decimals: Number of decimal places
        show_arrow: Show arrow before value
        
    Returns:
        HTML string with color coding
    """
    try:
        from frontend.common.styling import COLORS
        color = COLORS["success"] if value >= 0 else COLORS["error"]
    except ImportError:
        color = "#059669" if value >= 0 else "#DC2626"
    
    sign = "+" if value >= 0 else ""
    arrow = "↑ " if value > 0 else ("↓ " if value < 0 else "")
    arrow_str = arrow if show_arrow else ""
    
    formatted_value = f"{value * 100:.{decimals}f}".replace(".", ",")
    
    return f'<span style="color: {color}; font-weight: 500;">{arrow_str}{sign}{formatted_value}%</span>'


def format_comparison(
    current: float,
    baseline: float,
    unit: str = "tkr",
    decimals: int = 0
) -> str:
    """
    Format value with comparison to baseline.
    
    Args:
        current: Current value
        baseline: Baseline value
        unit: Unit
        decimals: Number of decimal places
        
    Returns:
        HTML string with value and delta
    """
    delta = current - baseline
    
    if decimals == 0:
        current_str = f"{current:,.0f}".replace(",", " ")
    else:
        current_str = format_number(current, decimals)
    
    if abs(delta) < 0.01:
        return f"{current_str} {unit}"
    
    delta_html = format_delta_html(delta, unit)
    return f"{current_str} {unit} ({delta_html})"


def format_variance(
    current: float,
    baseline: float,
    as_percent: bool = False
) -> str:
    """
    Format variance between current and baseline values.
    
    Args:
        current: Current value
        baseline: Baseline value
        as_percent: If True, show as percentage change
        
    Returns:
        HTML string with formatted variance
    """
    try:
        from frontend.common.styling import COLORS
    except ImportError:
        COLORS = {"success": "#059669", "error": "#DC2626", "text_muted": "#64748B"}
    
    delta = current - baseline
    
    if abs(delta) < 1e-9:
        return f'<span style="color: {COLORS["text_muted"]};">No change</span>'
    
    if as_percent and baseline != 0:
        pct_change = (delta / baseline) * 100
        color = COLORS["success"] if delta >= 0 else COLORS["error"]
        sign = "+" if delta >= 0 else ""
        return f'<span style="color: {color}; font-weight: 500;">{sign}{pct_change:.1f}%</span>'
    else:
        color = COLORS["success"] if delta >= 0 else COLORS["error"]
        sign = "+" if delta >= 0 else ""
        formatted = f"{delta:,.0f}".replace(",", " ")
        return f'<span style="color: {color}; font-weight: 500;">{sign}{formatted}</span>'


def status_badge(status: str) -> str:
    """
    Return HTML badge for status indication.
    
    Args:
        status: One of 'baseline', 'modified', 'error', 'success'
        
    Returns:
        HTML string with styled badge
    """
    styles = {
        "baseline": ("background: #E2E8F0; color: #475569;", "BASELINE"),
        "modified": ("background: #FEF3C7; color: #92400E;", "MODIFIED"),
        "error": ("background: #FEE2E2; color: #991B1B;", "ERROR"),
        "success": ("background: #D1FAE5; color: #065F46;", "SUCCESS"),
        "pending": ("background: #E0E7FF; color: #3730A3;", "PENDING"),
    }
    
    style, label = styles.get(status.lower(), styles["baseline"])
    
    return (
        f'<span style="{style} padding: 2px 8px; border-radius: 4px; '
        f'font-size: 0.75rem; font-weight: 500; text-transform: uppercase;">'
        f'{label}</span>'
    )