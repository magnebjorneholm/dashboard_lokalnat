"""
calculations/dea_calculations.py

DEA (Data Envelopment Analysis) calculations with outlier handling.
Implements Ei's baseline specification: CRS, input-oriented, IQR outlier detection.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from config.column_names import (
    COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
    COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH,
)
from calculations.frontier.outliers import (
    detect_outliers_iterative, super_eff_scores,
)


def run_dea_analysis(
    df: pd.DataFrame,
    model_spec: Dict[str, Any]
) -> pd.DataFrame:
    """
    Run DEA analysis with configurable model specification.

    Args:
        df: DataFrame with all 148 companies, columns: REId, capital_cost_2024, controllable_cost_average, CU, MW, NS, MWhl, MWhh
        model_spec: Dict with DEA specification:
            - inputs: List of input columns (default: ['capital_cost_2024', 'controllable_cost_average'])
            - outputs: List of output columns (default: ['CU', 'MW', 'NS', 'MWhl', 'MWhh'])
            - rts: 'crs' or 'vrs' (default: 'crs')
            - orientation: 'input' or 'output' (default: 'input')
            - outlier_params: Dict with q_lower, q_upper, multiplier

    Returns:
        DataFrame with columns: REId, dea_efficiency, dea_super_efficiency, potential, is_outlier

    Process:
        1. Super-efficiency DEA on all companies
        2. Identify outliers with IQR method
        3. Run DEA again without outliers in reference set
        4. Calculate efficiency and potential
    """
    df = df.copy()

    # Extract model specification (defaults from BASELINE_DEA_SPEC at bottom of file)
    input_cols = model_spec.get('inputs', [COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG])
    output_cols = model_spec.get('outputs', [COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH])
    rts = model_spec.get('rts', 'crs')
    orientation = model_spec.get('orientation', 'input')
    outlier_params = model_spec.get('outlier_params', {
        'q_lower': 25.0, 'q_upper': 75.0, 'multiplier': 2.0,
    })

    # Validate that all columns exist
    missing_inputs = [col for col in input_cols if col not in df.columns]
    missing_outputs = [col for col in output_cols if col not in df.columns]

    if missing_inputs:
        raise ValueError(f"Missing input columns: {missing_inputs}")
    if missing_outputs:
        raise ValueError(f"Missing output columns: {missing_outputs}")

    # Convert to numeric values
    df[input_cols] = df[input_cols].apply(pd.to_numeric, errors='coerce')
    for col in output_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Validate that REId exists
    if 'REId' not in df.columns:
        raise ValueError("DataFrame must contain column 'REId'")

    if orientation != 'input':
        raise NotImplementedError("Only input-oriented DEA is supported")

    # Extract input/output arrays
    inputs = df[input_cols].values
    outputs = df[output_cols].values

    # Outlier detection (super-eff + IQR) and cleaned re-solve, via the shared
    # routine. `outlier_max_rounds` controls iteration: None = iterate until no
    # new outliers appear (default; reproduces Ei's published outlier set and
    # efficiencies, see eis_dea_metod.md); an int caps the rounds (e.g. 1 = a
    # single identification round, which does NOT match Ei on the full data).
    max_rounds = model_spec.get('outlier_max_rounds', None)
    res = detect_outliers_iterative(
        inputs, outputs, rts,
        q_lower=outlier_params['q_lower'],
        q_upper=outlier_params['q_upper'],
        multiplier=outlier_params['multiplier'],
        max_rounds=max_rounds,
        forced_outliers=model_spec.get('forced_outliers', None),
    )

    df[COL_IS_OUTLIER] = res.is_outlier

    # Outliers report their flag-time super-eff score and potential 1.0;
    # survivors report their score against the cleaned reference set.
    result_efficiency = []
    result_super_efficiency = []
    result_potential = []
    for i in range(len(df)):
        if res.is_outlier[i]:
            theta = res.flag_scores[i]
            result_efficiency.append(min(theta, 1) if np.isfinite(theta) else np.nan)
            result_super_efficiency.append(theta if np.isfinite(theta) else np.nan)
            result_potential.append(1.0)
        else:
            theta = res.final_scores[i]
            if np.isfinite(theta):
                efficiency = min(theta, 1)
                result_efficiency.append(efficiency)
                result_super_efficiency.append(theta)
                result_potential.append(1 - efficiency)
            else:
                result_efficiency.append(np.nan)
                result_super_efficiency.append(np.nan)
                result_potential.append(np.nan)

    df[COL_DEA_EFFICIENCY] = result_efficiency
    df[COL_DEA_SUPER_EFF] = result_super_efficiency
    df[COL_DEA_POTENTIAL] = result_potential

    # Return only relevant columns
    result_cols = ['REId', COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL, COL_IS_OUTLIER]

    # Include DMU if present (for compatibility)
    if 'DMU' in df.columns:
        result_cols = ['DMU'] + result_cols

    return df[result_cols].copy()


def _run_super_efficiency_dea(
    inputs: np.ndarray,
    outputs: np.ndarray,
    rts: str
) -> List:
    """Backward-compatible super-efficiency DEA over the full sample.

    Thin wrapper around ``calculations.frontier.outliers.super_eff_scores`` (the
    single source of truth for the LP). Each company is scored leave-one-out
    against all others. Returns a list of scores, with ``"OUTLIER"`` where the
    LP fails or data is missing (preserving the legacy return contract).
    """
    n = len(inputs)
    scores = super_eff_scores(inputs, outputs, rts, np.ones(n, dtype=bool))
    return [s if np.isfinite(s) else "OUTLIER" for s in scores]


# Baseline DEA specification (Ei's model)
BASELINE_DEA_SPEC = {
    'inputs': [COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG],
    'outputs': [COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH],
    'rts': 'crs',
    'orientation': 'input',
    'outlier_params': {
        'q_lower': 25.0,
        'q_upper': 75.0,
        'multiplier': 2.0
    }
}
