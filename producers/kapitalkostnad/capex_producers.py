"""
capex_producers.py - CAPEX producers
=====================================

Tre metoder för att producera CAPEX:
1. wacc_scaling - Snabb skalning baserat på WACC-förändring
2. kent_full - Full KENT-pipeline med parameterjusteringar
3. kent_upload - Läs från uppladdad KENT-fil
"""

import pandas as pd
from typing import Dict, Any, Optional

try:
    from .kent_pipeline import (
        calculate_ages_and_nuav,
        calculate_depreciation,
        calculate_returns,
        compile_capcost
    )
    from .kent_upload_processor import extract_capex_from_kent
    from .parameter_adjustments import (
        apply_normvalue_adjustments,
        apply_lifetime_adjustments
    )
except ImportError:
    from kent_pipeline import (
        calculate_ages_and_nuav,
        calculate_depreciation,
        calculate_returns,
        compile_capcost
    )
    from kent_upload_processor import extract_capex_from_kent
    from parameter_adjustments import (
        apply_normvalue_adjustments,
        apply_lifetime_adjustments
    )


def produce_capex_from_wacc_scaling(
    wacc: float,
    baseline_data: Dict[str, Any],
    parameters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Producer: Snabb CAPEX-skalning baserat på WACC-förändring.
    
    Skalar endast avkastningskomponenten proportionellt med WACC.
    Avskrivningar påverkas inte.
    
    Args:
        wacc: Ny WACC (real, före skatt)
        baseline_data: Dict med baseline CAPEX per DMU
        parameters: Oanvänd (för interface-kompatibilitet)
    
    Returns:
        DataFrame med CAPEX per DMU (kolumner: DMU, CAPEX)
        
    Example:
        >>> capex = produce_capex_from_wacc_scaling(
        ...     wacc=0.05,
        ...     baseline_data={'capex': baseline_df, 'wacc': 0.0453}
        ... )
    """
    if 'capex' not in baseline_data or 'wacc' not in baseline_data:
        raise KeyError("baseline_data måste innehålla 'capex' och 'wacc'")
    
    baseline_capex = baseline_data['capex']
    baseline_wacc = baseline_data['wacc']
    
    scaling_factor = wacc / baseline_wacc
    
    result = baseline_capex.copy()
    
    if 'Avkastning' in result.columns:
        result['Avkastning'] = result['Avkastning'] * scaling_factor
    
    if 'Avskrivningar' in result.columns and 'Avkastning' in result.columns:
        result['CAPEX'] = result['Avskrivningar'] + result['Avkastning']
    
    return result


def produce_capex_from_kent_full(
    wacc: float,
    baseline_data: Dict[str, Any],
    parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Producer: Full KENT-beräkning med parameterjusteringar.
    
    Kör hela KENT-pipelinen (steg 5-9) med möjlighet att justera:
    - Normvärden (procentuella justeringar)
    - Livslängder (ekonomiska/maximala)
    
    Args:
        wacc: WACC för avkastningsberäkning
        baseline_data: Dict med capbase_a DataFrame
        parameters: Dict med:
            - normvalue_adjustments: Optional[Dict] {level: str, adjustments: Dict[int, float]}
            - lifetime_adjustments: Optional[Dict] {level: str, adjustments: Dict[int, Dict]}
    
    Returns:
        DataFrame med CAPEX per tidsperi od och totalt
    """
    if 'capbase_a' not in baseline_data:
        raise KeyError("baseline_data måste innehålla 'capbase_a' DataFrame")
    
    capbase_a = baseline_data['capbase_a'].copy()
    
    if parameters.get('normvalue_adjustments'):
        adj = parameters['normvalue_adjustments']
        capbase_a = apply_normvalue_adjustments(
            capbase_a,
            adj['adjustments'],
            level=adj.get('level', 'cat')
        )
    
    if parameters.get('lifetime_adjustments'):
        adj = parameters['lifetime_adjustments']
        capbase_a = apply_lifetime_adjustments(
            capbase_a,
            adj['adjustments'],
            level=adj.get('level', 'cat')
        )
    
    capbase_a = calculate_ages_and_nuav(capbase_a)
    
    dep_results = calculate_depreciation(capbase_a)
    ret_results = calculate_returns(capbase_a, interest_rate=wacc)
    
    result_df = compile_capcost(dep_results, ret_results)
    
    return result_df


def produce_capex_from_kent_upload(
    wacc: float,
    kent_file,
    parameters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Producer: Läs CAPEX från uppladdad KENT-fil.
    
    Args:
        wacc: WACC för avkastningsberäkning
        kent_file: Uppladdad KENT Excel-fil (file object eller path)
        parameters: Optional[Dict] med DMU-id
    
    Returns:
        DataFrame med CAPEX per tidsperiod
    """
    dmu_id = parameters.get('dmu_id') if parameters else None
    
    capbase_a = extract_capex_from_kent(kent_file, dmu_id=dmu_id)
    
    capbase_a = calculate_ages_and_nuav(capbase_a)
    
    dep_results = calculate_depreciation(capbase_a)
    ret_results = calculate_returns(capbase_a, interest_rate=wacc)
    
    result_df = compile_capcost(dep_results, ret_results)
    
    return result_df
