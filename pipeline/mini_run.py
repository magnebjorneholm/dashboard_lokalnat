"""
pipeline/mini_run.py

Isolated DEA "mini-run": runs only the DEA stage + efficiency requirement
calculation, without the full 5-stage pipeline.

Used by the M7 benchmarking tab for instant feedback on DEA specification changes.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

import pandas as pd

from config.case_definition import DeaConfig
from config.column_names import (
    COL_REID,
    COL_DEA_EFFICIENCY,
    COL_DEA_SUPER_EFF,
    COL_DEA_POTENTIAL,
    COL_IS_OUTLIER,
    COL_EFF_REQ_ANNUAL,
)
from data_loaders import BaselineData
from pipeline.stages.baseline import stage_baseline
from pipeline.stages.dea import stage_dea
from calculations.efficiency.efficiency_requirement import calculate_eff_req_for_dataframe


@dataclass(frozen=True)
class MiniRunResult:
    """Result from an isolated DEA mini-run."""

    # Full 148-company DEA results
    dea_results: pd.DataFrame
    dea_method: str
    dea_executed: bool

    # User-specific extracted values
    user_reid: str
    user_efficiency: Optional[float]
    user_super_efficiency: Optional[float]
    user_potential: float
    user_is_outlier: bool
    user_eff_req_annual: float

    # Distribution stats
    n_companies: int
    n_outliers: int
    user_rank: int  # 1 = best efficiency score


def run_dea_mini(
    baseline_data: BaselineData,
    dea_config: DeaConfig,
    user_reid: str,
    eff_req_params: Optional[Dict[str, Any]] = None,
) -> MiniRunResult:
    """
    Run DEA in isolation with baseline data.

    Args:
        baseline_data: Cached baseline data (148 companies).
        dea_config: DEA specification (inputs, outputs, RTS, outlier params).
        user_reid: User's company REId.
        eff_req_params: M5 parameters for efficiency requirement calculation.
            Keys: truncation_max, outlier_req, customer_sharing,
            realization_time, supervision_period.
            None = baseline defaults from calculate_eff_req_for_dataframe().

    Returns:
        MiniRunResult with DEA results and user-specific extraction.
    """
    # Stage 1: baseline conversion (format only, fast)
    baseline_output = stage_baseline(baseline_data)

    # Stage 3: DEA (skips stage 2 — stage_dea never uses pre_dea)
    dea_output = stage_dea(config=dea_config, baseline=baseline_output)

    # Efficiency requirement with caller-provided M5 params (or defaults)
    eff_kwargs = eff_req_params if eff_req_params else {}
    dea_with_eff = calculate_eff_req_for_dataframe(
        df=dea_output.dea_results,
        **eff_kwargs,
    )

    # Extract user's company
    user_mask = dea_with_eff[COL_REID] == user_reid
    if not user_mask.any():
        raise ValueError(f"REId {user_reid} not found in DEA results")

    row = dea_with_eff.loc[user_mask].iloc[0]
    user_efficiency = (
        float(row[COL_DEA_EFFICIENCY])
        if pd.notna(row[COL_DEA_EFFICIENCY])
        else None
    )
    user_super_eff = (
        float(row[COL_DEA_SUPER_EFF])
        if COL_DEA_SUPER_EFF in row.index and pd.notna(row[COL_DEA_SUPER_EFF])
        else None
    )
    user_potential = float(row[COL_DEA_POTENTIAL])
    user_is_outlier = bool(row[COL_IS_OUTLIER])
    user_eff_req = float(row[COL_EFF_REQ_ANNUAL])

    # Distribution stats
    n_companies = len(dea_with_eff)
    n_outliers = int(dea_with_eff[COL_IS_OUTLIER].sum())

    # Rank by efficiency score (1 = best, highest score)
    eff_scores = dea_with_eff[COL_DEA_EFFICIENCY].dropna()
    user_rank = int((eff_scores > user_efficiency).sum()) + 1 if user_efficiency is not None else n_companies

    return MiniRunResult(
        dea_results=dea_with_eff,
        dea_method=dea_output.dea_method,
        dea_executed=dea_output.dea_executed,
        user_reid=user_reid,
        user_efficiency=user_efficiency,
        user_super_efficiency=user_super_eff,
        user_potential=user_potential,
        user_is_outlier=user_is_outlier,
        user_eff_req_annual=user_eff_req,
        n_companies=n_companies,
        n_outliers=n_outliers,
        user_rank=user_rank,
    )
