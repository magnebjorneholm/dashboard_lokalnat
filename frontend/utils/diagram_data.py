"""
frontend/utils/diagram_data.py

Prepares data for revenue frame decomposition diagram.
Handles all capex_method variations, and OPEX vs TOTEX efficiency methods.

Data flow:
- Controllable costs (fore avdrag): From SDF (Medelvarde 2018-2021 * 4 + Neonjusteringar)
- Efficiency requirement: Calculated as (fore - efter), split OPEX/CAPEX for TOTEX
- Depreciation/Return: From SDF (baseline) or KENT (parameter_change)
- Capital base: Derived from return / WACC
- Other adjustments: Flexibility services + interruption compensation - state aid deduction
"""

from typing import Dict, Optional, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from pipeline.core import PipelineResult


# SDF column names (Swedish regulatory terminology)
SDF_COL_KAPITALKOSTNAD = 'Kapitalkostnad'
SDF_COL_KAPITALFORSLITNING = '-varav Kapital-fÃ¶rslitning'
SDF_COL_KAPITALBINDNING = 'varav Kapital-bindning'

BASELINE_WACC = 0.0453


def prepare_diagram_data(
    case_result: "PipelineResult",
    baseline_result: "PipelineResult",
) -> Dict[str, dict]:
    """
    Prepares data for revenue frame decomposition diagram.
    
    Handles all capex_method variations and OPEX/TOTEX efficiency methods.
    For TOTEX, provides separate OPEX/CAPEX efficiency components.
    
    Returns:
        Dict with component keys plus 'method' ('OPEX' or 'TOTEX').
    """
    user_reid = case_result.user_reid
    
    case_ir = case_result.post_dea.user_intaktsram
    baseline_ir = baseline_result.post_dea.user_intaktsram
    
    capex_method = case_result.pre_dea.capex_method
    wacc_used = case_result.pre_dea.wacc_used or BASELINE_WACC
    method = str(case_ir.get('Method_used', 'OPEX'))
    
    # Paverkbara components (OPEX-side)
    pav_data = _get_paverkbara_components(
        case_result=case_result,
        baseline_result=baseline_result,
        user_reid=user_reid
    )
    
    # Capital cost components (avskrivning/avkastning)
    capex_data = _get_capital_cost_components(
        case_result=case_result,
        baseline_result=baseline_result,
        user_reid=user_reid
    )
    
    # Ej paverkbara
    ej_paverkbara_value = float(case_ir.get('Opaverkbara_Kostnader', 0))
    ej_paverkbara_baseline = float(baseline_ir.get('Opaverkbara_Kostnader', 0))
    
    # Quality/incentive adjustment
    kvalitet_value = float(case_ir.get('Incitamentjustering_Total', 0))
    kvalitet_baseline = float(baseline_ir.get('Incitamentjustering_Total', 0))
    
    # Capital base derived from return
    kapitalbas_value = capex_data['avkastning']['value'] / wacc_used if wacc_used > 0 else 0
    kapitalbas_baseline = capex_data['avkastning']['baseline'] / BASELINE_WACC if BASELINE_WACC > 0 else 0
    
    # Other adjustments (aggregate + decomposed)
    other_adj = _get_other_adjustments(case_ir, baseline_ir)
    
    # Decomposed components for waterfall chart
    flex_case = float(case_ir.get('Flexibilitetstjanster', 0))
    flex_baseline = float(baseline_ir.get('Flexibilitetstjanster', 0))
    avbrott_case = float(case_ir.get('Avbrottsersattning_12_24h', 0))
    avbrott_baseline = float(baseline_ir.get('Avbrottsersattning_12_24h', 0))
    avdrag_case = float(case_ir.get('Avdrag_Statligt_Stod', 0))
    avdrag_baseline = float(baseline_ir.get('Avdrag_Statligt_Stod', 0))
    
    # Modification flags
    capex_modified = case_result.pre_dea.capex_modified
    effkrav_modified = _is_effkrav_modified(case_result, baseline_result, user_reid)
    
    # --- Method-dependent calculations ---
    
    if method == 'TOTEX':
        # OPEX efficiency (reduction on controllable costs)
        opex_eff_value = float(case_ir.get('OPEX_Effektivisering', 0))
        opex_eff_baseline = float(baseline_ir.get('OPEX_Effektivisering', 0))
        
        # CAPEX efficiency (reduction on capital costs)
        capex_eff_value = float(case_ir.get('CAPEX_Effektivisering', 0))
        capex_eff_baseline = float(baseline_ir.get('CAPEX_Effektivisering', 0))
        
        # Operating costs = OPEX_Efter + ej paverkbara
        opex_efter_value = float(case_ir.get('OPEX_Efter', 0))
        opex_efter_baseline = float(baseline_ir.get('OPEX_Efter', 0))
        lopande_value = opex_efter_value + ej_paverkbara_value
        lopande_baseline = opex_efter_baseline + ej_paverkbara_baseline
        
        # Capital costs = Dep + Ret - CAPEX_eff + Quality
        kapitalkostnad_value = (
            capex_data['avskrivningar']['value']
            + capex_data['avkastning']['value']
            - capex_eff_value
            + kvalitet_value
        )
        kapitalkostnad_baseline = (
            capex_data['avskrivningar']['baseline']
            + capex_data['avkastning']['baseline']
            - capex_eff_baseline
            + kvalitet_baseline
        )
    else:
        # OPEX mode: single efficiency requirement on controllable costs only
        opex_eff_value = 0
        opex_eff_baseline = 0
        capex_eff_value = 0
        capex_eff_baseline = 0
        
        # Operating costs = paverkbara_efter + ej paverkbara
        lopande_value = pav_data['paverkbara_efter']['value'] + ej_paverkbara_value
        lopande_baseline = pav_data['paverkbara_efter']['baseline'] + ej_paverkbara_baseline
        
        # Capital costs = Dep + Ret + Quality (no CAPEX reduction)
        kapitalkostnad_value = (
            capex_data['avskrivningar']['value']
            + capex_data['avkastning']['value']
            + kvalitet_value
        )
        kapitalkostnad_baseline = (
            capex_data['avskrivningar']['baseline']
            + capex_data['avkastning']['baseline']
            + kvalitet_baseline
        )
    
    # Total intaktsram
    intaktsram_value = float(case_ir.get('Intaktsram_Total', 0))
    intaktsram_baseline = float(baseline_ir.get('Intaktsram_Total', 0))
    
    result = {
        'method': method,
        'paverkbara': {
            'value': pav_data['paverkbara_fore']['value'],
            'baseline': pav_data['paverkbara_fore']['baseline'],
            'is_directly_modified': False,
            'source': 'SDF Medelvarde 2018-2021'
        },
        'ej_paverkbara': {
            'value': ej_paverkbara_value,
            'baseline': ej_paverkbara_baseline,
            'is_directly_modified': False,
            'source': 'SDF'
        },
        'kapitalbas': {
            'value': kapitalbas_value,
            'baseline': kapitalbas_baseline,
            'is_directly_modified': capex_modified,
            'source': _get_capex_source_description(capex_method, wacc_used)
        },
        'effektivisering': {
            'value': pav_data['effektivisering']['value'],
            'baseline': pav_data['effektivisering']['baseline'],
            'is_directly_modified': effkrav_modified,
            'source': 'DEA' if effkrav_modified else 'Baseline DEA'
        },
        'avskrivningar': {
            'value': capex_data['avskrivningar']['value'],
            'baseline': capex_data['avskrivningar']['baseline'],
            'is_directly_modified': capex_modified and capex_method == 'parameter_change',
            'source': _get_capex_source_description(capex_method, wacc_used)
        },
        'avkastning': {
            'value': capex_data['avkastning']['value'],
            'baseline': capex_data['avkastning']['baseline'],
            'is_directly_modified': capex_modified,
            'source': _get_capex_source_description(capex_method, wacc_used)
        },
        'kvalitet': {
            'value': kvalitet_value,
            'baseline': kvalitet_baseline,
            'is_directly_modified': False,
            'source': 'Incentive calculation'
        },
        'lopande': {
            'value': lopande_value,
            'baseline': lopande_baseline,
            'is_directly_modified': False,
            'source': 'Calculated'
        },
        'kapitalkostnader': {
            'value': kapitalkostnad_value,
            'baseline': kapitalkostnad_baseline,
            'is_directly_modified': capex_modified,
            'source': _get_capex_source_description(capex_method, wacc_used)
        },
        'other_adjustments': {
            'value': other_adj['value'],
            'baseline': other_adj['baseline'],
            'is_directly_modified': False,
            'source': 'Flexibility + Interruption - State aid'
        },
        'flexibilitetstjanster': {
            'value': flex_case,
            'baseline': flex_baseline,
            'is_directly_modified': False,
            'source': 'SDF'
        },
        'avbrottsersattning': {
            'value': avbrott_case,
            'baseline': avbrott_baseline,
            'is_directly_modified': False,
            'source': 'SDF'
        },
        'avdrag_statligt_stod': {
            'value': avdrag_case,
            'baseline': avdrag_baseline,
            'is_directly_modified': False,
            'source': 'SDF'
        },
        'intaktsram': {
            'value': intaktsram_value,
            'baseline': intaktsram_baseline,
            'is_directly_modified': False,
            'source': 'Total'
        }
    }
    
    # TOTEX-specific: separated efficiency components
    if method == 'TOTEX':
        result['opex_effektivisering'] = {
            'value': opex_eff_value,
            'baseline': opex_eff_baseline,
            'is_directly_modified': effkrav_modified,
            'source': 'TOTEX OPEX share'
        }
        result['capex_effektivisering'] = {
            'value': capex_eff_value,
            'baseline': capex_eff_baseline,
            'is_directly_modified': effkrav_modified,
            'source': 'TOTEX CAPEX share'
        }
    
    return result


def _get_other_adjustments(case_ir: pd.Series, baseline_ir: pd.Series) -> dict:
    """
    Calculate "other adjustments" = flexibility + interruption compensation - state aid.
    """
    flex_case = float(case_ir.get('Flexibilitetstjanster', 0))
    flex_baseline = float(baseline_ir.get('Flexibilitetstjanster', 0))
    
    avbrott_case = float(case_ir.get('Avbrottsersattning_12_24h', 0))
    avbrott_baseline = float(baseline_ir.get('Avbrottsersattning_12_24h', 0))
    
    avdrag_case = float(case_ir.get('Avdrag_Statligt_Stod', 0))
    avdrag_baseline = float(baseline_ir.get('Avdrag_Statligt_Stod', 0))
    
    return {
        'value': flex_case + avbrott_case - avdrag_case,
        'baseline': flex_baseline + avbrott_baseline - avdrag_baseline
    }


def _get_paverkbara_components(
    case_result: "PipelineResult",
    baseline_result: "PipelineResult",
    user_reid: str
) -> Dict[str, dict]:
    """
    Calculate paverkbara components: fore avdrag, efter avdrag, och effektivisering.
    
    Uses SDF data for base values. In both OPEX and TOTEX mode, paverkbara_fore
    represents the OPEX-only base (Medelvarde * 4 + Neonjusteringar).
    """
    case_ir = case_result.post_dea.user_intaktsram
    baseline_ir = baseline_result.post_dea.user_intaktsram
    
    case_paverkbara_efter = float(case_ir.get('Paverkbara_Periodsumma', 0))
    baseline_paverkbara_efter = float(baseline_ir.get('Paverkbara_Periodsumma', 0))
    
    sdf_paverkbara = case_result.baseline.sdf_paverkbara
    
    medelvarde_col = _find_column(sdf_paverkbara, ['medelvÃ¤rde', '2018-2021'])
    neojust_col = _find_column(sdf_paverkbara, ['separerat yrkandet', 'neojust'])
    reid_col = 'REid' if 'REid' in sdf_paverkbara.columns else 'REId'
    
    user_mask = sdf_paverkbara[reid_col] == user_reid
    
    if user_mask.any() and medelvarde_col:
        user_row = sdf_paverkbara[user_mask].iloc[0]
        medelvarde = float(user_row.get(medelvarde_col, 0) or 0)
        neonjusteringar = float(user_row.get(neojust_col, 0) or 0) if neojust_col else 0
    else:
        medelvarde = baseline_paverkbara_efter / 4
        neonjusteringar = 0
    
    paverkbara_fore = medelvarde * 4 + neonjusteringar
    
    case_effektivisering = paverkbara_fore - case_paverkbara_efter
    baseline_effektivisering = paverkbara_fore - baseline_paverkbara_efter
    
    return {
        'paverkbara_fore': {
            'value': paverkbara_fore,
            'baseline': paverkbara_fore
        },
        'paverkbara_efter': {
            'value': case_paverkbara_efter,
            'baseline': baseline_paverkbara_efter
        },
        'effektivisering': {
            'value': case_effektivisering,
            'baseline': baseline_effektivisering
        }
    }


def _get_capital_cost_components(
    case_result: "PipelineResult",
    baseline_result: "PipelineResult",
    user_reid: str
) -> Dict[str, dict]:
    """
    Get avskrivningar and avkastning based on capex_method.
    """
    capex_method = case_result.pre_dea.capex_method
    wacc_used = case_result.pre_dea.wacc_used or BASELINE_WACC
    
    baseline_avskr, baseline_avkast = _get_avskr_avkast_from_sdf(
        baseline_result.baseline.sdf_ir, user_reid
    )
    
    if capex_method == 'baseline':
        return {
            'avskrivningar': {
                'value': baseline_avskr,
                'baseline': baseline_avskr
            },
            'avkastning': {
                'value': baseline_avkast,
                'baseline': baseline_avkast
            }
        }
    
    else:  # parameter_change
        case_avskr, case_avkast = _get_avskr_avkast_from_pre_dea(
            case_result.pre_dea.df_all_companies, user_reid
        )
        
        return {
            'avskrivningar': {
                'value': case_avskr,
                'baseline': baseline_avskr
            },
            'avkastning': {
                'value': case_avkast,
                'baseline': baseline_avkast
            }
        }


def _get_avskr_avkast_from_sdf(sdf_ir: pd.DataFrame, user_reid: str) -> tuple:
    """Extract avskrivning and avkastning period sums from SDF IR sheet."""
    user_mask = sdf_ir['REId'] == user_reid
    
    if not user_mask.any():
        return 0.0, 0.0
    
    user_row = sdf_ir[user_mask].iloc[0]
    
    avkastning = 0.0
    if SDF_COL_KAPITALBINDNING in sdf_ir.columns:
        avkastning = float(pd.to_numeric(user_row.get(SDF_COL_KAPITALBINDNING, 0), errors='coerce') or 0)
    
    kapitalkostnad = 0.0
    if SDF_COL_KAPITALKOSTNAD in sdf_ir.columns:
        kapitalkostnad = float(pd.to_numeric(user_row.get(SDF_COL_KAPITALKOSTNAD, 0), errors='coerce') or 0)
    
    avskrivning = kapitalkostnad - avkastning
    
    return avskrivning, avkastning


def _get_avskr_avkast_from_pre_dea(df: pd.DataFrame, user_reid: str) -> tuple:
    """Extract avskrivning and avkastning from pre_dea DataFrame (KENT output)."""
    user_mask = df['REId'] == user_reid
    
    if not user_mask.any():
        return 0.0, 0.0
    
    user_row = df[user_mask].iloc[0]
    
    avskrivning = 0.0
    avkastning = 0.0
    
    if 'Avskrivning_Period' in df.columns:
        avskrivning = float(user_row.get('Avskrivning_Period', 0) or 0)
    elif all(f'Avskrivning_{y}' in df.columns for y in [2024, 2025, 2026, 2027]):
        avskrivning = sum(float(user_row.get(f'Avskrivning_{y}', 0) or 0) for y in [2024, 2025, 2026, 2027])
    elif 'Avskrivning' in df.columns:
        avskrivning = float(user_row.get('Avskrivning', 0) or 0) * 4
    
    if 'Avkastning_Period' in df.columns:
        avkastning = float(user_row.get('Avkastning_Period', 0) or 0)
    elif all(f'Avkastning_{y}' in df.columns for y in [2024, 2025, 2026, 2027]):
        avkastning = sum(float(user_row.get(f'Avkastning_{y}', 0) or 0) for y in [2024, 2025, 2026, 2027])
    elif 'Avkastning' in df.columns:
        avkastning = float(user_row.get('Avkastning', 0) or 0) * 4
    
    return avskrivning, avkastning


def _find_column(df: pd.DataFrame, keywords: list) -> Optional[str]:
    """Find column containing all keywords (case-insensitive)."""
    for col in df.columns:
        col_lower = col.lower()
        if all(kw.lower() in col_lower for kw in keywords):
            return col
    return None


def _is_effkrav_modified(
    case_result: "PipelineResult",
    baseline_result: "PipelineResult",
    user_reid: str
) -> bool:
    """Check if efficiency requirement differs from baseline."""
    case_effkrav = case_result.post_dea.user_effkrav_proc
    baseline_effkrav = baseline_result.post_dea.user_effkrav_proc
    
    return abs(case_effkrav - baseline_effkrav) > 0.0001


def _get_capex_source_description(capex_method: str, wacc_used: float) -> str:
    """Generate source description for capital cost components."""
    if capex_method == 'baseline':
        return 'Baseline'
    elif capex_method == 'parameter_change':
        return f'KENT (WACC {wacc_used*100:.2f}%)'
    else:
        return capex_method