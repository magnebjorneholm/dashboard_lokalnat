"""
visualization/diagram_data.py

Prepares data for revenue frame decomposition diagram.
Handles all capex_method variations, and OPEX vs TOTEX efficiency methods.

Data flow:
- Controllable costs: From user_revenue_frame (pipeline output)
- Efficiency requirement: Calculated as (before - after), split OPEX/CAPEX for TOTEX
- Depreciation/Return: From pipeline (capital_cost_period - return_on_assets_period)
- Capital base: Derived from return / WACC
- Other adjustments: Flexibility services + interruption compensation - state aid deduction
"""

from typing import Dict, TYPE_CHECKING
import pandas as pd

if TYPE_CHECKING:
    from pipeline.core import PipelineResult

from config.column_names import (
    COL_METHOD_USED, COL_OPEX_BEFORE, COL_CONTROLLABLE_BEFORE,
    COL_OPEX_AFTER, COL_CONTROLLABLE_PERIOD,
    COL_OPEX_EFF_DEDUCTION, COL_EFFICIENCY_DEDUCTION,
    COL_NON_CONTROLLABLE, COL_INCENTIVE_TOTAL,
    COL_FLEXIBILITY, COL_INTERRUPTION, COL_STATE_DEDUCTION,
    COL_CAPEX_EFF_DEDUCTION, COL_REVENUE_FRAME,
    COL_RETURN_PERIOD, COL_CAPITAL_COST_PERIOD,
)
from calculations.capex.wacc_calculations import BASELINE_WACC


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

    case_ir = case_result.post_dea.user_revenue_frame
    baseline_ir = baseline_result.post_dea.user_revenue_frame

    capex_method = case_result.pre_dea.capex_method
    wacc_used = case_result.pre_dea.wacc_used or BASELINE_WACC
    method = str(case_ir.get(COL_METHOD_USED, 'OPEX'))

    # Controllable components - read directly from revenue frame
    paverkbara_fore_value = float(case_ir.get(COL_OPEX_BEFORE, case_ir.get(COL_CONTROLLABLE_BEFORE, 0)))
    paverkbara_fore_baseline = float(baseline_ir.get(COL_OPEX_BEFORE, baseline_ir.get(COL_CONTROLLABLE_BEFORE, 0)))
    paverkbara_efter_value = float(case_ir.get(COL_OPEX_AFTER, case_ir.get(COL_CONTROLLABLE_PERIOD, 0)))
    paverkbara_efter_baseline = float(baseline_ir.get(COL_OPEX_AFTER, baseline_ir.get(COL_CONTROLLABLE_PERIOD, 0)))
    effektivisering_value = float(case_ir.get(COL_OPEX_EFF_DEDUCTION, case_ir.get(COL_EFFICIENCY_DEDUCTION, 0)))
    effektivisering_baseline = float(baseline_ir.get(COL_OPEX_EFF_DEDUCTION, baseline_ir.get(COL_EFFICIENCY_DEDUCTION, 0)))

    # Capital cost components (depreciation/return)
    capex_data = _get_capital_cost_components(
        case_result=case_result,
        baseline_result=baseline_result,
        user_reid=user_reid
    )

    # Non-controllable
    ej_paverkbara_value = float(case_ir.get(COL_NON_CONTROLLABLE, 0))
    ej_paverkbara_baseline = float(baseline_ir.get(COL_NON_CONTROLLABLE, 0))

    # Quality/incentive adjustment
    kvalitet_value = float(case_ir.get(COL_INCENTIVE_TOTAL, 0))
    kvalitet_baseline = float(baseline_ir.get(COL_INCENTIVE_TOTAL, 0))

    # Capital base derived from return
    kapitalbas_value = capex_data['avkastning']['value'] / wacc_used if wacc_used > 0 else 0
    kapitalbas_baseline = capex_data['avkastning']['baseline'] / BASELINE_WACC if BASELINE_WACC > 0 else 0

    # Other adjustments (aggregate + decomposed)
    other_adj = _get_other_adjustments(case_ir, baseline_ir)

    # Decomposed components for waterfall chart
    flex_case = float(case_ir.get(COL_FLEXIBILITY, 0))
    flex_baseline = float(baseline_ir.get(COL_FLEXIBILITY, 0))
    avbrott_case = float(case_ir.get(COL_INTERRUPTION, 0))
    avbrott_baseline = float(baseline_ir.get(COL_INTERRUPTION, 0))
    avdrag_case = float(case_ir.get(COL_STATE_DEDUCTION, 0))
    avdrag_baseline = float(baseline_ir.get(COL_STATE_DEDUCTION, 0))

    # Modification flags
    capex_modified = case_result.pre_dea.capex_modified
    effkrav_modified = _is_effkrav_modified(case_result, baseline_result, user_reid)

    # OPEX modification flags (compare case vs baseline values, tolerance 1 tkr)
    _TOL = 1.0
    paverkbara_modified = abs(paverkbara_fore_value - paverkbara_fore_baseline) > _TOL
    ej_paverkbara_modified = abs(ej_paverkbara_value - ej_paverkbara_baseline) > _TOL
    flex_modified = abs(flex_case - flex_baseline) > _TOL
    avbrott_modified = abs(avbrott_case - avbrott_baseline) > _TOL
    avdrag_modified = abs(avdrag_case - avdrag_baseline) > _TOL

    # --- Method-dependent calculations ---

    if method == 'TOTEX':
        # OPEX efficiency (reduction on controllable costs)
        opex_eff_value = float(case_ir.get(COL_OPEX_EFF_DEDUCTION, 0))
        opex_eff_baseline = float(baseline_ir.get(COL_OPEX_EFF_DEDUCTION, 0))

        # CAPEX efficiency (reduction on capital costs)
        capex_eff_value = float(case_ir.get(COL_CAPEX_EFF_DEDUCTION, 0))
        capex_eff_baseline = float(baseline_ir.get(COL_CAPEX_EFF_DEDUCTION, 0))

        # Operating costs = OPEX_After + non-controllable
        opex_efter_value = float(case_ir.get(COL_OPEX_AFTER, 0))
        opex_efter_baseline = float(baseline_ir.get(COL_OPEX_AFTER, 0))
        lopande_value = opex_efter_value + ej_paverkbara_value
        lopande_baseline = opex_efter_baseline + ej_paverkbara_baseline

        # Capital costs = Dep + Ret - CAPEX_eff (matches COL_CAPITAL_COST_IN_RF)
        kapitalkostnad_value = (
            capex_data['avskrivningar']['value']
            + capex_data['avkastning']['value']
            - capex_eff_value
        )
        kapitalkostnad_baseline = (
            capex_data['avskrivningar']['baseline']
            + capex_data['avkastning']['baseline']
            - capex_eff_baseline
        )
    else:
        # OPEX mode: single efficiency requirement on controllable costs only
        opex_eff_value = 0
        opex_eff_baseline = 0
        capex_eff_value = 0
        capex_eff_baseline = 0

        # Operating costs = controllable_after + non-controllable
        lopande_value = paverkbara_efter_value + ej_paverkbara_value
        lopande_baseline = paverkbara_efter_baseline + ej_paverkbara_baseline

        # Capital costs = Dep + Ret (matches COL_CAPITAL_COST_PERIOD)
        kapitalkostnad_value = (
            capex_data['avskrivningar']['value']
            + capex_data['avkastning']['value']
        )
        kapitalkostnad_baseline = (
            capex_data['avskrivningar']['baseline']
            + capex_data['avkastning']['baseline']
        )

    # Total revenue frame
    intaktsram_value = float(case_ir.get(COL_REVENUE_FRAME, 0))
    intaktsram_baseline = float(baseline_ir.get(COL_REVENUE_FRAME, 0))

    result = {
        'method': method,
        'paverkbara': {
            'value': paverkbara_fore_value,
            'baseline': paverkbara_fore_baseline,
            'is_directly_modified': paverkbara_modified,
            'source': 'Revenue frame (opex_before)'
        },
        'ej_paverkbara': {
            'value': ej_paverkbara_value,
            'baseline': ej_paverkbara_baseline,
            'is_directly_modified': ej_paverkbara_modified,
            'source': 'SDF'
        },
        'kapitalbas': {
            'value': kapitalbas_value,
            'baseline': kapitalbas_baseline,
            'is_directly_modified': capex_modified,
            'source': _get_capex_source_description(capex_method, wacc_used)
        },
        'effektivisering': {
            'value': effektivisering_value,
            'baseline': effektivisering_baseline,
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
            'is_directly_modified': abs(kvalitet_value - kvalitet_baseline) > _TOL,
            'source': 'Incentive calculation'
        },
        'lopande': {
            'value': lopande_value,
            'baseline': lopande_baseline,
            'is_directly_modified': paverkbara_modified or ej_paverkbara_modified or effkrav_modified,
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
            'is_directly_modified': flex_modified or avbrott_modified or avdrag_modified,
            'source': 'Flexibility + Interruption - State aid'
        },
        'flexibilitetstjanster': {
            'value': flex_case,
            'baseline': flex_baseline,
            'is_directly_modified': flex_modified,
            'source': 'SDF'
        },
        'avbrottsersattning': {
            'value': avbrott_case,
            'baseline': avbrott_baseline,
            'is_directly_modified': avbrott_modified,
            'source': 'SDF'
        },
        'avdrag_statligt_stod': {
            'value': avdrag_case,
            'baseline': avdrag_baseline,
            'is_directly_modified': avdrag_modified,
            'source': 'SDF'
        },
        'intaktsram': {
            'value': intaktsram_value,
            'baseline': intaktsram_baseline,
            'is_directly_modified': abs(intaktsram_value - intaktsram_baseline) > _TOL,
            'source': 'Total'
        }
    }

    # Always provide separated OPEX/CAPEX efficiency components.
    # In OPEX mode: OPEX eff = full deduction, CAPEX eff = 0.
    # In TOTEX mode: Both are non-zero based on allocation shares.
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
    else:
        result['opex_effektivisering'] = {
            'value': effektivisering_value,
            'baseline': effektivisering_baseline,
            'is_directly_modified': effkrav_modified,
            'source': 'OPEX efficiency deduction'
        }
        result['capex_effektivisering'] = {
            'value': 0.0,
            'baseline': 0.0,
            'is_directly_modified': False,
            'source': 'N/A (OPEX method)'
        }

    return result


def _get_other_adjustments(case_ir: pd.Series, baseline_ir: pd.Series) -> dict:
    """
    Calculate "other adjustments" = flexibility + interruption compensation - state aid.
    """
    flex_case = float(case_ir.get(COL_FLEXIBILITY, 0))
    flex_baseline = float(baseline_ir.get(COL_FLEXIBILITY, 0))

    avbrott_case = float(case_ir.get(COL_INTERRUPTION, 0))
    avbrott_baseline = float(baseline_ir.get(COL_INTERRUPTION, 0))

    avdrag_case = float(case_ir.get(COL_STATE_DEDUCTION, 0))
    avdrag_baseline = float(baseline_ir.get(COL_STATE_DEDUCTION, 0))

    return {
        'value': flex_case + avbrott_case - avdrag_case,
        'baseline': flex_baseline + avbrott_baseline - avdrag_baseline
    }



def _get_capital_cost_components(
    case_result: "PipelineResult",
    baseline_result: "PipelineResult",
    user_reid: str
) -> Dict[str, dict]:
    """
    Get depreciation and return on assets from pipeline data.

    Uses the same data sources as the revenue frame assembly:
    - capital_cost_period from user_revenue_frame (matches KPI)
    - return_on_assets_period from pre_dea.df_all_companies
    - depreciation = capital_cost_period - return_on_assets_period
    """
    case_ir = case_result.post_dea.user_revenue_frame
    baseline_ir = baseline_result.post_dea.user_revenue_frame

    # Capital cost period from revenue frame (same source as KPI)
    case_capkost = float(case_ir.get(COL_CAPITAL_COST_PERIOD, 0))
    baseline_capkost = float(baseline_ir.get(COL_CAPITAL_COST_PERIOD, 0))

    # Return from pre_dea.df_all_companies (available for all capex methods)
    case_avkast = _get_return_from_pre_dea(
        case_result.pre_dea.df_all_companies, user_reid
    )
    baseline_avkast = _get_return_from_pre_dea(
        baseline_result.pre_dea.df_all_companies, user_reid
    )

    # Derive depreciation so dep + return = capital_cost_period (by construction)
    case_avskr = case_capkost - case_avkast
    baseline_avskr = baseline_capkost - baseline_avkast

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


def _get_return_from_pre_dea(df: pd.DataFrame, user_reid: str) -> float:
    """Extract return on assets period sum from pre_dea DataFrame."""
    user_mask = df['REId'] == user_reid

    if not user_mask.any():
        return 0.0

    user_row = df[user_mask].iloc[0]

    if COL_RETURN_PERIOD in df.columns:
        return float(user_row.get(COL_RETURN_PERIOD, 0) or 0)

    # Fallback: sum per-year columns
    yearly_cols = [f'return_on_assets_{y}' for y in [2024, 2025, 2026, 2027]]
    if all(c in df.columns for c in yearly_cols):
        return sum(float(user_row.get(c, 0) or 0) for c in yearly_cols)

    return 0.0



def _is_effkrav_modified(
    case_result: "PipelineResult",
    baseline_result: "PipelineResult",
    user_reid: str
) -> bool:
    """Check if efficiency requirement differs from baseline."""
    case_effkrav = case_result.post_dea.user_eff_req_pct
    baseline_effkrav = baseline_result.post_dea.user_eff_req_pct

    return abs(case_effkrav - baseline_effkrav) > 0.0001


def _get_capex_source_description(capex_method: str, wacc_used: float) -> str:
    """Generate source description for capital cost components."""
    if capex_method == 'baseline':
        return 'Baseline'
    elif capex_method == 'parameter_change':
        return f'KENT (WACC {wacc_used*100:.2f}%)'
    else:
        return capex_method
