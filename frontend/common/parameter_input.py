"""
Parameter Input komponent för Regumetrica UI.

Återanvändbar komponent för baseline-first parameter-input med override-möjlighet.
"""

import streamlit as st
from typing import Tuple, Optional
from frontend.common.formatting import format_percent, format_number


def parameter_input(
    module_key: str,
    param_id: str,
    label: str,
    baseline: float,
    unit: str = "",
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    step: Optional[float] = None,
    help_text: str = "",
    format_as_percent: bool = False
) -> Tuple[float, bool]:
    """
    Renderar parameter-input med override-möjlighet.
    
    Visar baseline-värde som default. Användaren kan välja att ändra
    genom att checka i "Ändra"-checkboxen.
    
    Args:
        module_key: Unik nyckel för modulen (för widget-key prefix)
        param_id: Parameter-ID från User Manual (t.ex. "3.2.5")
        label: Visningsnamn
        baseline: Baseline-värde
        unit: Enhet (t.ex. "%", "år")
        min_val: Minsta tillåtna värde
        max_val: Största tillåtna värde
        step: Stegstorlek för input
        help_text: Hjälptext
        format_as_percent: Om True, formatera baseline som procent
    
    Returns:
        Tuple med (current_value, is_overridden)
    """
    # Unika keys med module-prefix för att undvika kollisioner
    override_key = f"{module_key}_override_{param_id}"
    value_key = f"{module_key}_value_{param_id}"
    
    # Initialisera state om det inte finns
    if override_key not in st.session_state:
        st.session_state[override_key] = False
        st.session_state[value_key] = baseline
    
    # Layout: ID | Label | Input/Baseline
    col_id, col_label, col_checkbox, col_input = st.columns([1, 2, 1, 2])
    
    with col_id:
        st.markdown(f"**{param_id}**")
    
    with col_label:
        st.markdown(label)
    
    with col_checkbox:
        is_overridden = st.checkbox(
            "Ändra",
            key=override_key,
            help="Kryssa i för att ändra från baseline"
        )
    
    with col_input:
        if is_overridden:
            current = st.number_input(
                f"{label} (ny)",
                value=st.session_state[value_key],
                min_value=min_val,
                max_value=max_val,
                step=step,
                key=f"{module_key}_input_{param_id}",
                help=help_text,
                label_visibility="collapsed"
            )
            st.session_state[value_key] = current
        else:
            # Visa baseline-värde formaterat
            if format_as_percent:
                display_val = format_percent(baseline)
            elif unit:
                display_val = f"{baseline} {unit}"
            else:
                display_val = str(baseline)
            st.markdown(f"*{display_val} (baseline)*")
            current = baseline
    
    return current, is_overridden


def parameter_select(
    module_key: str,
    param_id: str,
    label: str,
    options: list,
    baseline: str,
    help_text: str = ""
) -> Tuple[str, bool]:
    """
    Renderar parameter-select med override-möjlighet.
    
    Args:
        module_key: Unik nyckel för modulen
        param_id: Parameter-ID
        label: Visningsnamn
        options: Lista med valbara alternativ
        baseline: Baseline-alternativ
        help_text: Hjälptext
    
    Returns:
        Tuple med (selected_value, is_overridden)
    """
    override_key = f"{module_key}_override_{param_id}"
    value_key = f"{module_key}_value_{param_id}"
    
    if override_key not in st.session_state:
        st.session_state[override_key] = False
        st.session_state[value_key] = baseline
    
    col_id, col_label, col_checkbox, col_input = st.columns([1, 2, 1, 2])
    
    with col_id:
        st.markdown(f"**{param_id}**")
    
    with col_label:
        st.markdown(label)
    
    with col_checkbox:
        is_overridden = st.checkbox(
            "Ändra",
            key=override_key,
            help="Kryssa i för att ändra från baseline"
        )
    
    with col_input:
        if is_overridden:
            idx = options.index(st.session_state[value_key]) if st.session_state[value_key] in options else 0
            current = st.selectbox(
                f"{label} (ny)",
                options=options,
                index=idx,
                key=f"{module_key}_select_{param_id}",
                help=help_text,
                label_visibility="collapsed"
            )
            st.session_state[value_key] = current
        else:
            st.markdown(f"*{baseline} (baseline)*")
            current = baseline
    
    return current, is_overridden
