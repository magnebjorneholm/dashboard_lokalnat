"""
Pending Changes Manager
Hanterar staged_modifications för scenario-parametrar.
Separerar osparade ändringar från applicerade ändringar.
"""

import streamlit as st
from typing import Any, Optional, Dict


def initialize_pending_changes():
    """Initialiserar pending changes structure i session_state om den inte finns."""
    if 'scenario_data' not in st.session_state:
        return
    
    if 'staged_modifications' not in st.session_state.scenario_data:
        st.session_state.scenario_data['staged_modifications'] = {}
    
    if 'applied_modifications' not in st.session_state.scenario_data:
        st.session_state.scenario_data['applied_modifications'] = {}


def set_staged(module: str, param: str, value: Any):
    """
    Sätter ett staged (ospart) värde för en parameter.
    
    Args:
        module: Modulnamn ('kapitalkostnad', 'paverkbara', etc)
        param: Parameternamn ('wacc', 'trunk_min', etc)
        value: Värde att spara
    """
    initialize_pending_changes()
    
    if module not in st.session_state.scenario_data['staged_modifications']:
        st.session_state.scenario_data['staged_modifications'][module] = {}
    
    st.session_state.scenario_data['staged_modifications'][module][param] = value


def get_staged(module: str, param: str, default: Any = None) -> Any:
    """
    Hämtar ett staged värde.
    
    Args:
        module: Modulnamn
        param: Parameternamn
        default: Default-värde om inte hittat
        
    Returns:
        Staged värde eller default
    """
    initialize_pending_changes()
    
    staged = st.session_state.scenario_data.get('staged_modifications', {})
    module_staged = staged.get(module, {})
    
    return module_staged.get(param, default)


def get_all_staged(module: str) -> Dict[str, Any]:
    """
    Hämtar alla staged värden för en modul.
    
    Args:
        module: Modulnamn
        
    Returns:
        Dictionary med alla staged parametrar
    """
    initialize_pending_changes()
    
    staged = st.session_state.scenario_data.get('staged_modifications', {})
    return staged.get(module, {}).copy()


def remove_staged(module: str, param: str):
    """
    Tar bort en staged parameter (reset till baseline).
    
    Args:
        module: Modulnamn
        param: Parameternamn
    """
    initialize_pending_changes()
    
    staged = st.session_state.scenario_data.get('staged_modifications', {})
    
    if module in staged and param in staged[module]:
        del staged[module][param]
        
        # Om modulen är tom, ta bort den också
        if not staged[module]:
            del staged[module]


def clear_staged(module: str):
    """
    Tar bort alla staged parametrar för en modul.
    
    Args:
        module: Modulnamn
    """
    initialize_pending_changes()
    
    staged = st.session_state.scenario_data.get('staged_modifications', {})
    
    if module in staged:
        del staged[module]


def has_staged_changes(module: str) -> bool:
    """
    Kontrollerar om det finns staged ändringar för en modul.
    
    Args:
        module: Modulnamn
        
    Returns:
        True om det finns staged ändringar
    """
    initialize_pending_changes()
    
    staged = st.session_state.scenario_data.get('staged_modifications', {})
    return module in staged and bool(staged[module])


def count_staged_changes(module: str) -> int:
    """
    Räknar antal staged parametrar för en modul.
    
    Args:
        module: Modulnamn
        
    Returns:
        Antal staged parametrar
    """
    initialize_pending_changes()
    
    staged = st.session_state.scenario_data.get('staged_modifications', {})
    return len(staged.get(module, {}))


def commit_staged_changes(module: str):
    """
    Flyttar staged ändringar till applied (efter applicering).
    
    Args:
        module: Modulnamn
    """
    initialize_pending_changes()
    
    staged = st.session_state.scenario_data.get('staged_modifications', {})
    applied = st.session_state.scenario_data.get('applied_modifications', {})
    
    if module in staged:
        # Om applied[module] redan existerar, behåll befintlig metadata
        # och lägg staged-parametrarna under en tydlig nyckel så vi
        # inte skriver över beräkningsresultat som apply-funktioner
        # redan har sparat.
        if module not in applied or not isinstance(applied[module], dict):
            # Ingen befintlig applied-data - skapa en ny struktur
            applied[module] = {}

        # Spara staged parametrar under 'staged_parameters' för spårbarhet
        applied[module].setdefault('staged_parameters', {})
        # Kopiera staged in i staged_parameters (merge)
        for k, v in staged[module].items():
            applied[module]['staged_parameters'][k] = v

        # Töm staged för denna modul
        del staged[module]


def get_applied(module: str, param: str, default: Any = None) -> Any:
    """
    Hämtar ett applicerat värde.
    
    Args:
        module: Modulnamn
        param: Parameternamn
        default: Default-värde om inte hittat
        
    Returns:
        Applicerat värde eller default
    """
    initialize_pending_changes()
    
    applied = st.session_state.scenario_data.get('applied_modifications', {})
    module_applied = applied.get(module, {})
    
    return module_applied.get(param, default)


def get_all_applied(module: str) -> Dict[str, Any]:
    """
    Hämtar alla applicerade värden för en modul.
    
    Args:
        module: Modulnamn
        
    Returns:
        Dictionary med alla applicerade parametrar
    """
    initialize_pending_changes()
    
    applied = st.session_state.scenario_data.get('applied_modifications', {})
    return applied.get(module, {}).copy()


def get_active_value(module: str, param: str, baseline_value: Any) -> Any:
    """
    Hämtar aktivt värde: staged > applied > baseline.
    
    Args:
        module: Modulnamn
        param: Parameternamn
        baseline_value: Baseline-värde från data
        
    Returns:
        Aktivt värde i prioritetsordning
    """
    # Prioritet 1: Staged (om användaren håller på att ändra)
    staged_value = get_staged(module, param)
    if staged_value is not None:
        return staged_value
    
    # Prioritet 2: Applied (om användaren har applicerat tidigare)
    applied_value = get_applied(module, param)
    if applied_value is not None:
        return applied_value
    
    # Prioritet 3: Baseline
    return baseline_value


def is_modified(module: str, param: str) -> bool:
    """
    Kontrollerar om en parameter har ändrats (staged eller applied).
    
    Args:
        module: Modulnamn
        param: Parameternamn
        
    Returns:
        True om parametern är modified
    """
    return get_staged(module, param) is not None or get_applied(module, param) is not None


def reset_parameter(module: str, param: str):
    """
    Återställer en parameter helt (både staged och applied).
    
    Args:
        module: Modulnamn
        param: Parameternamn
    """
    initialize_pending_changes()
    
    # Ta bort från staged
    remove_staged(module, param)
    
    # Ta bort från applied
    applied = st.session_state.scenario_data.get('applied_modifications', {})
    if module in applied and param in applied[module]:
        del applied[module][param]
        
        # Om modulen är tom, ta bort den också
        if not applied[module]:
            del applied[module]


def reset_all(module: str):
    """
    Återställer alla parametrar för en modul (både staged och applied).
    
    Args:
        module: Modulnamn
    """
    initialize_pending_changes()
    
    # Töm staged
    clear_staged(module)
    
    # Töm applied
    applied = st.session_state.scenario_data.get('applied_modifications', {})
    if module in applied:
        del applied[module]


def get_modifications_hash(module: str) -> str:
    """
    Genererar hash för applied modifications (för cache invalidation).
    
    Args:
        module: Modulnamn
        
    Returns:
        Hash-sträng
    """
    import json
    import pandas as pd

    applied = get_all_applied(module)

    def _serialize(obj):
        # Konvertera icke-serialiserbara objekt till JSON-vänliga representationer
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_serialize(v) for v in obj]
        if isinstance(obj, pd.DataFrame):
            # Summera DataFrame till en dict (deterministiskt)
            return obj.to_dict(orient='list')
        if isinstance(obj, pd.Series):
            return obj.to_dict()
        try:
            # Försök serialisera primitiva typer
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)

    try:
        serializable = _serialize(applied)
        s = json.dumps(serializable, sort_keys=True)
        return str(hash(s))
    except Exception:
        # Fallback: enklare, men stabil nog för cache-nyckel
        return str(hash(str(applied)))