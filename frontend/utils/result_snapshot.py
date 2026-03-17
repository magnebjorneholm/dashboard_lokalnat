"""
Result snapshot extraction for case comparison.

Extracts a lightweight dict of ~15 aggregated KPIs from a PipelineResult,
suitable for Firestore persistence and instant cross-case comparison
without re-running the pipeline.
"""

from datetime import datetime
from typing import Dict, Any

from config.column_names import (
    COL_REVENUE_FRAME,
    COL_CAPITAL_COST_PERIOD,
    COL_CAPITAL_COST_IN_RF,
    COL_CONTROLLABLE_PERIOD,
    COL_CONTROLLABLE_IN_RF,
    COL_NON_CONTROLLABLE,
    COL_FLEXIBILITY,
    COL_DEPRECIATION_PERIOD,
    COL_RETURN_PERIOD,
    COL_EFFICIENCY_DEDUCTION,
    COL_INCENTIVE_TOTAL,
    COL_INTERRUPTION,
    COL_STATE_DEDUCTION,
    COL_METHOD_USED,
)
from pipeline.core import PipelineResult


# Maps snapshot key -> column name in user_revenue_frame (pd.Series)
_RF_FIELDS = {
    "revenue_frame": COL_REVENUE_FRAME,
    "capital_cost_period": COL_CAPITAL_COST_PERIOD,
    "capital_cost_in_rf": COL_CAPITAL_COST_IN_RF,
    "controllable_period": COL_CONTROLLABLE_PERIOD,
    "controllable_in_rf": COL_CONTROLLABLE_IN_RF,
    "non_controllable_period": COL_NON_CONTROLLABLE,
    "flexibility_period": COL_FLEXIBILITY,
    "depreciation_period": COL_DEPRECIATION_PERIOD,
    "return_period": COL_RETURN_PERIOD,
    "efficiency_deduction": COL_EFFICIENCY_DEDUCTION,
    "incentive_total": COL_INCENTIVE_TOTAL,
    "interruption_period": COL_INTERRUPTION,
    "state_deduction_period": COL_STATE_DEDUCTION,
}


def _safe_float(series, key: str) -> float | None:
    """Extract a float from a Series, returning None if the key is missing."""
    try:
        val = series[key]
        return float(val)
    except (KeyError, TypeError, ValueError):
        return None


def extract_result_snapshot(
    case_result: PipelineResult,
    baseline_result: PipelineResult,
    config_hash: str,
) -> Dict[str, Any]:
    """Extract a lightweight KPI snapshot from pipeline results.

    The snapshot contains ~15 case values, their baseline equivalents,
    and metadata.  All values are plain Python float/str — Firestore-safe.
    """
    case_rf = case_result.post_dea.user_revenue_frame
    baseline_rf = baseline_result.post_dea.user_revenue_frame

    snapshot: Dict[str, Any] = {
        "computed_at": datetime.now().isoformat(),
        "config_hash": config_hash,
        "company_name": case_result.extraction.company_name,
        "user_reid": case_result.user_reid,
        "method_used": str(case_rf.get(COL_METHOD_USED, "")),
    }

    # Case KPIs from revenue frame
    for key, col in _RF_FIELDS.items():
        snapshot[key] = _safe_float(case_rf, col)

    # Baseline equivalents for delta calculation in comparison view
    for key, col in _RF_FIELDS.items():
        snapshot[f"baseline_{key}"] = _safe_float(baseline_rf, col)

    # DEA / efficiency (from extraction + post_dea)
    snapshot["dea_efficiency"] = (
        float(case_result.extraction.efficiency)
        if case_result.extraction.efficiency is not None
        else None
    )
    snapshot["efficiency_req_annual"] = float(
        case_result.post_dea.user_eff_req_pct
    )

    return snapshot
