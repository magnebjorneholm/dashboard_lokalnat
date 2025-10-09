"""
state_management.py - Helper functions for managing state in Dash beräkningskedja
==================================================================================

Hanterar stora DataFrames i flask_session och metadata i dcc.Store.
"""

import pickle
from typing import Optional, Dict, Any, List
from flask import session as flask_session
import pandas as pd


# ============================================================================
# SERVER-SIDE DATAFRAME STORAGE (Flask-Session)
# ============================================================================

def save_step_dataframe(user_dmu: int, step: int, df: pd.DataFrame) -> None:
    """
    Sparar DataFrame server-side i flask_session med pickle.
    
    Args:
        user_dmu: Användarens DMU-id
        step: Steg-nummer (5, 6, 7, 8)
        df: DataFrame att spara
    """
    key = f'step{step}_df_dmu{user_dmu}'
    flask_session[key] = pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)


def load_step_dataframe(user_dmu: int, step: int) -> Optional[pd.DataFrame]:
    """
    Laddar DataFrame från flask_session.
    
    Args:
        user_dmu: Användarens DMU-id
        step: Steg-nummer (5, 6, 7, 8)
        
    Returns:
        DataFrame eller None om inte finns
    """
    key = f'step{step}_df_dmu{user_dmu}'
    blob = flask_session.get(key)
    return pickle.loads(blob) if blob else None


def save_step_dict(user_dmu: int, step: int, data: Dict[str, Any]) -> None:
    """
    Sparar dict (små results) server-side.
    
    Args:
        user_dmu: Användarens DMU-id
        step: Steg-nummer
        data: Dict att spara
    """
    key = f'step{step}_dict_dmu{user_dmu}'
    flask_session[key] = data


def load_step_dict(user_dmu: int, step: int) -> Optional[Dict[str, Any]]:
    """
    Laddar dict från flask_session.
    
    Args:
        user_dmu: Användarens DMU-id
        step: Steg-nummer
        
    Returns:
        Dict eller None om inte finns
    """
    key = f'step{step}_dict_dmu{user_dmu}'
    return flask_session.get(key)


def clear_step_data(user_dmu: int, step: Optional[int] = None) -> None:
    """
    Rensar step-data från flask_session.
    
    Args:
        user_dmu: Användarens DMU-id
        step: Specifikt steg att rensa, eller None för alla steg
    """
    if step is not None:
        # Rensa specifikt steg
        keys_to_clear = [
            f'step{step}_df_dmu{user_dmu}',
            f'step{step}_dict_dmu{user_dmu}'
        ]
    else:
        # Rensa alla steg
        keys_to_clear = [
            f'step{s}_{t}_dmu{user_dmu}' 
            for s in [5, 6, 7, 8] 
            for t in ['df', 'dict']
        ]
    
    for key in keys_to_clear:
        flask_session.pop(key, None)


def clear_steps_from(user_dmu: int, start_step: int) -> None:
    """
    Rensar alla steg från och med start_step.
    Används när tidigare steg ändras (invalidering).
    
    Args:
        user_dmu: Användarens DMU-id
        start_step: Första steg att rensa (5, 6, 7, eller 8)
    """
    for step in range(start_step, 9):
        clear_step_data(user_dmu, step)


# ============================================================================
# DCC.STORE HELPERS (Metadata)
# ============================================================================

def update_store_step_completion(store_data: Dict, step: int) -> Dict:
    """
    Uppdaterar completed_steps i Store efter lyckad beräkning.
    
    Args:
        store_data: Nuvarande Store data
        step: Steg som slutfördes
        
    Returns:
        Uppdaterad Store data
    """
    if store_data is None:
        store_data = {}
    
    completed = set(store_data.get('completed_steps', []))
    completed.add(step)
    store_data['completed_steps'] = sorted(completed)
    store_data['current_step'] = step
    
    return store_data


def get_completed_steps(store_data: Optional[Dict]) -> List[int]:
    """
    Hämtar lista med slutförda steg.
    
    Args:
        store_data: Store data
        
    Returns:
        Lista med steg-nummer
    """
    if store_data is None:
        return []
    return store_data.get('completed_steps', [])


def is_step_accessible(store_data: Optional[Dict], step: int) -> bool:
    """
    Kontrollerar om ett steg är tillgängligt baserat på completed_steps.
    
    Logik:
    - Step 5: Alltid tillgänglig
    - Step 6: Kräver Step 5
    - Step 7: Kräver Step 5 (parallell med Step 6)
    - Step 8: Kräver Step 6 OCH Step 7
    
    Args:
        store_data: Store data
        step: Steg att kontrollera
        
    Returns:
        True om tillgänglig, False annars
    """
    completed = set(get_completed_steps(store_data))
    
    if step == 5:
        return True
    elif step == 6:
        return 5 in completed
    elif step == 7:
        return 5 in completed
    elif step == 8:
        return 6 in completed and 7 in completed
    else:
        return False


def invalidate_steps_from(store_data: Dict, start_step: int) -> Dict:
    """
    Tar bort steg från completed_steps när tidigare steg ändras.
    
    Args:
        store_data: Store data
        start_step: Första steg att invalidera
        
    Returns:
        Uppdaterad Store data
    """
    if store_data is None:
        store_data = {}
    
    completed = set(store_data.get('completed_steps', []))
    # Ta bort alla steg >= start_step
    completed = {s for s in completed if s < start_step}
    store_data['completed_steps'] = sorted(completed)
    
    return store_data


# ============================================================================
# WACC VALUE SHARING
# ============================================================================

def save_wacc_for_step7(store_data: Dict, wacc: float) -> Dict:
    """
    Sparar WACC-värde från kalkylatorn för användning i Step 7.
    
    Args:
        store_data: Store data
        wacc: WACC-värde (real, före skatt)
        
    Returns:
        Uppdaterad Store data
    """
    if store_data is None:
        store_data = {}
    
    store_data['wacc_for_step7'] = round(float(wacc), 4)
    
    return store_data


def get_wacc_for_step7(store_data: Optional[Dict], default: float = 0.0453) -> float:
    """
    Hämtar WACC-värde för Step 7.
    
    Args:
        store_data: Store data
        default: Default-värde om inget sparat
        
    Returns:
        WACC-värde
    """
    if store_data is None:
        return default
    
    return store_data.get('wacc_for_step7', default)


# ============================================================================
# LIFETIME ADJUSTMENTS
# ============================================================================

def save_lifetime_adjustments(user_dmu: int, adjustments: Dict) -> None:
    """
    Sparar lifetime-justeringar server-side.
    
    Args:
        user_dmu: Användarens DMU-id
        adjustments: Dict med justeringar
    """
    key = f'lifetime_adj_dmu{user_dmu}'
    flask_session[key] = adjustments


def load_lifetime_adjustments(user_dmu: int) -> Optional[Dict]:
    """
    Laddar lifetime-justeringar.
    
    Args:
        user_dmu: Användarens DMU-id
        
    Returns:
        Dict med justeringar eller None
    """
    key = f'lifetime_adj_dmu{user_dmu}'
    return flask_session.get(key)


def clear_lifetime_adjustments(user_dmu: int) -> None:
    """
    Rensar lifetime-justeringar.
    
    Args:
        user_dmu: Användarens DMU-id
    """
    key = f'lifetime_adj_dmu{user_dmu}'
    flask_session.pop(key, None)


# ============================================================================
# DEBUG / LOGGING
# ============================================================================

def get_session_size_info(user_dmu: int) -> Dict[str, Any]:
    """
    Returnerar info om session-storlek för debugging.
    
    Args:
        user_dmu: Användarens DMU-id
        
    Returns:
        Dict med storlekar
    """
    import sys
    
    info = {}
    
    for step in [5, 6, 7, 8]:
        df_key = f'step{step}_df_dmu{user_dmu}'
        dict_key = f'step{step}_dict_dmu{user_dmu}'
        
        df_blob = flask_session.get(df_key)
        dict_data = flask_session.get(dict_key)
        
        if df_blob:
            info[f'step{step}_df_size_mb'] = sys.getsizeof(df_blob) / (1024 * 1024)
        
        if dict_data:
            info[f'step{step}_dict_size_kb'] = sys.getsizeof(str(dict_data)) / 1024
    
    return info