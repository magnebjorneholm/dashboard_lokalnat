"""
Parameter Input Component for Regumetrica UI.

Reusable component for parameter input with baseline comparison.
Values are always displayed and compared against baseline to determine changes.
"""

import streamlit as st
from typing import Tuple, Optional

from config.formatting import format_percent, format_number
from config.colors import COLORS


def parameter_input(
    module_key: str,
    param_id: str,
    label: str,
    baseline: float,
    value: Optional[float] = None,
    unit: str = "",
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    step: Optional[float] = None,
    format_str: Optional[str] = None,
    help_text: str = "",
    format_as_percent: bool = False
) -> Tuple[float, bool]:
    """
    Render parameter input with baseline comparison.
    
    Args:
        module_key: Unique key for the module (widget-key prefix)
        param_id: Parameter ID from User Manual (e.g. "3.2.5")
        label: Display name
        baseline: Baseline value (used for comparison and Modified flag)
        value: Initial widget value. If None, uses baseline.
        unit: Unit (e.g. "%", "years")
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        step: Step size for input
        format_str: Display format (e.g. "%.4f" for 4 decimals)
        help_text: Help text
        format_as_percent: If True, format as percentage in help text
    
    Returns:
        Tuple of (current_value, is_changed)
    """
    input_key = f"{module_key}_input_{param_id}"
    initial_value = value if value is not None else baseline
    
    # Layout: ID | Label | Input | Baseline/Status
    col_id, col_label, col_input, col_baseline = st.columns([1, 2.5, 2, 1.5])
    
    with col_id:
        st.markdown(
            f'<span style="font-family: \'IBM Plex Mono\', monospace; '
            f'color: {COLORS["text_secondary"]}; font-size: 0.875rem;">'
            f'{param_id}</span>',
            unsafe_allow_html=True
        )
    
    with col_label:
        st.markdown(
            f'<span style="color: {COLORS["text_primary"]};">{label}</span>',
            unsafe_allow_html=True
        )
    
    with col_input:
        current = st.number_input(
            label,
            value=initial_value,
            min_value=min_val,
            max_value=max_val,
            step=step,
            format=format_str,
            key=input_key,
            help=help_text,
            label_visibility="collapsed"
        )
    
    with col_baseline:
        # Compare with tolerance for floating point
        is_changed = abs(current - baseline) > 1e-9
        
        if format_as_percent:
            baseline_str = format_percent(baseline)
        elif unit:
            baseline_str = f"{baseline} {unit}"
        else:
            baseline_str = str(baseline)
        
        if is_changed:
            st.markdown(
                f'<div style="font-size: 0.8rem;">'
                f'<span style="color: {COLORS["warning"]}; font-weight: 500;">Modified</span>'
                f'<br><span style="color: {COLORS["text_muted"]};">baseline: {baseline_str}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    
    return current, is_changed


def parameter_select(
    module_key: str,
    param_id: str,
    label: str,
    options: list,
    baseline: str,
    value: Optional[str] = None,
    help_text: str = ""
) -> Tuple[str, bool]:
    """
    Render parameter select with baseline comparison.
    
    Args:
        module_key: Unique key for the module
        param_id: Parameter ID from User Manual
        label: Display name
        options: List of selectable options
        baseline: Baseline option (used for comparison and Modified flag)
        value: Initial selection. If None, uses baseline.
        help_text: Help text
    
    Returns:
        Tuple of (selected_value, is_changed)
    """
    input_key = f"{module_key}_select_{param_id}"
    initial_value = value if value is not None else baseline
    
    col_id, col_label, col_input, col_baseline = st.columns([1, 2.5, 2, 1.5])
    
    with col_id:
        st.markdown(
            f'<span style="font-family: \'IBM Plex Mono\', monospace; '
            f'color: {COLORS["text_secondary"]}; font-size: 0.875rem;">'
            f'{param_id}</span>',
            unsafe_allow_html=True
        )
    
    with col_label:
        st.markdown(
            f'<span style="color: {COLORS["text_primary"]};">{label}</span>',
            unsafe_allow_html=True
        )
    
    with col_input:
        default_idx = options.index(initial_value) if initial_value in options else 0
        selected = st.selectbox(
            label,
            options=options,
            index=default_idx,
            key=input_key,
            help=help_text,
            label_visibility="collapsed"
        )
    
    with col_baseline:
        is_changed = selected != baseline
        
        if is_changed:
            st.markdown(
                f'<div style="font-size: 0.8rem;">'
                f'<span style="color: {COLORS["warning"]}; font-weight: 500;">Modified</span>'
                f'<br><span style="color: {COLORS["text_muted"]};">baseline: {baseline}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    
    return selected, is_changed


def parameter_header(title: str, param_range: str = ""):
    """
    Render a section header for parameters.
    
    Args:
        title: Section title
        param_range: Parameter range, e.g. "3.1.X - 3.2.X"
    """
    if param_range:
        st.markdown(
            f'<div style="display: flex; justify-content: space-between; align-items: baseline; '
            f'border-bottom: 2px solid {COLORS["primary"]}; padding-bottom: 8px; margin: 1.5rem 0 1rem 0;">'
            f'<span style="font-weight: 600; color: {COLORS["text_primary"]};">{title}</span>'
            f'<span style="font-family: \'IBM Plex Mono\', monospace; color: {COLORS["text_muted"]}; font-size: 0.75rem;">{param_range}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div style="font-weight: 600; color: {COLORS["text_primary"]}; '
            f'border-bottom: 2px solid {COLORS["primary"]}; padding-bottom: 8px; margin: 1.5rem 0 1rem 0;">'
            f'{title}</div>',
            unsafe_allow_html=True
        )


def parameter_info(text: str):
    """
    Render informational text for parameters section.
    
    Args:
        text: Information text to display
    """
    st.markdown(
        f'<p style="color: {COLORS["text_muted"]}; font-size: 0.875rem; margin: 0.5rem 0 1rem 0;">'
        f'{text}</p>',
        unsafe_allow_html=True
    )


def baseline_badge(is_baseline: bool) -> str:
    """
    Return HTML badge indicating baseline status.
    
    Args:
        is_baseline: True if value matches baseline
        
    Returns:
        HTML string with badge
    """
    if is_baseline:
        return (
            f'<span style="background: {COLORS["bg_muted"]}; color: {COLORS["text_secondary"]}; '
            f'padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500;">'
            f'BASELINE</span>'
        )
    else:
        return (
            f'<span style="background: #FEF3C7; color: #92400E; '
            f'padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500;">'
            f'MODIFIED</span>'
        )