"""
Parameter Input komponent för Regumetrica UI.

Återanvändbar komponent för parameter-input med baseline-jämförelse.
Värdet visas alltid och jämförs mot baseline för att avgöra om det ändrats.
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
    Renderar parameter-input med baseline-jämförelse.
    
    Visar alltid inputfält med baseline som default. Returnerar om värdet
    skiljer sig från baseline.
    
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
        format_as_percent: Om True, formatera som procent i hjälptext
    
    Returns:
        Tuple med (current_value, is_changed)
    """
    input_key = f"{module_key}_input_{param_id}"
    
    # Layout: ID | Label | Input | Baseline
    col_id, col_label, col_input, col_baseline = st.columns([1, 2, 2, 1.5])
    
    with col_id:
        st.markdown(f"**{param_id}**")
    
    with col_label:
        st.markdown(label)
    
    with col_input:
        current = st.number_input(
            label,
            value=baseline,
            min_value=min_val,
            max_value=max_val,
            step=step,
            key=input_key,
            help=help_text,
            label_visibility="collapsed"
        )
    
    with col_baseline:
        # Visa baseline och ändringsstatus
        if format_as_percent:
            baseline_str = format_percent(baseline)
        elif unit:
            baseline_str = f"{baseline} {unit}"
        else:
            baseline_str = str(baseline)
        
        # Jämför med tolerans för flyttal
        is_changed = abs(current - baseline) > 1e-9
        
        if is_changed:
            delta = current - baseline
            if format_as_percent:
                delta_str = f"{delta*100:+.2f}pp"
            else:
                delta_str = f"{delta:+.2g}"
            st.caption(f":orange[{delta_str}] från {baseline_str}")
        else:
            st.caption(f"= {baseline_str}")
    
    return current, is_changed


def parameter_select(
    module_key: str,
    param_id: str,
    label: str,
    options: list,
    baseline: str,
    help_text: str = ""
) -> Tuple[str, bool]:
    """
    Renderar parameter-select med baseline-jämförelse.
    
    Visar alltid selectbox med baseline som default. Returnerar om värdet
    skiljer sig från baseline.
    
    Args:
        module_key: Unik nyckel för modulen
        param_id: Parameter-ID
        label: Visningsnamn
        options: Lista med valbara alternativ
        baseline: Baseline-alternativ
        help_text: Hjälptext
    
    Returns:
        Tuple med (selected_value, is_changed)
    """
    select_key = f"{module_key}_select_{param_id}"
    
    # Layout: ID | Label | Select | Baseline
    col_id, col_label, col_select, col_baseline = st.columns([1, 2, 2, 1.5])
    
    with col_id:
        st.markdown(f"**{param_id}**")
    
    with col_label:
        st.markdown(label)
    
    with col_select:
        # Hitta baseline-index
        baseline_idx = options.index(baseline) if baseline in options else 0
        
        current = st.selectbox(
            label,
            options=options,
            index=baseline_idx,
            key=select_key,
            help=help_text,
            label_visibility="collapsed"
        )
    
    with col_baseline:
        is_changed = (current != baseline)
        
        if is_changed:
            st.caption(f":orange[Ändrat] från {baseline}")
        else:
            st.caption(f"= {baseline}")
    
    return current, is_changed