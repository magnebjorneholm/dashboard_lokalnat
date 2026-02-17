"""
calculations/dea_calculations.py

DEA (Data Envelopment Analysis) calculations with outlier handling.
Implements Ei's baseline specification: CRS, input-oriented, IQR outlier detection.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import pulp

from config.column_names import (
    COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
    COL_CU, COL_MW, COL_NS, COL_MWH_LOW, COL_MWH_HIGH,
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

    # STEP 1: First run - Super-efficiency DEA
    eff1 = _run_super_efficiency_dea(inputs, outputs, rts)
    df["supereff1"] = eff1

    # STEP 2: Identify outliers
    theta_valid = [e for e in eff1 if isinstance(e, (int, float)) and not np.isnan(e)]
    q_low = np.percentile(theta_valid, outlier_params['q_lower'])
    q_high = np.percentile(theta_valid, outlier_params['q_upper'])
    iqr = q_high - q_low
    threshold = q_high + outlier_params['multiplier'] * iqr

    df[COL_IS_OUTLIER] = [
        e > threshold if isinstance(e, (int, float)) else True
        for e in eff1
    ]

    # STEP 3: Second run - Exclude outliers from reference set
    df_clean = df[~df[COL_IS_OUTLIER]].reset_index(drop=True)
    inputs_clean = df_clean[input_cols].values
    outputs_clean = df_clean[output_cols].values
    eff2 = _run_super_efficiency_dea(inputs_clean, outputs_clean, rts)

    # STEP 4: Calculate results
    result_efficiency = []
    result_super_efficiency = []
    result_potential = []

    j = 0
    for i, is_outlier in enumerate(df[COL_IS_OUTLIER]):
        if is_outlier:
            # For outliers: use first run
            result_efficiency.append(min(eff1[i], 1) if isinstance(eff1[i], (int, float)) else np.nan)
            result_super_efficiency.append(eff1[i] if isinstance(eff1[i], (int, float)) else np.nan)
            result_potential.append(1.0)
        else:
            # For non-outliers: use second run
            theta = eff2[j]
            if isinstance(theta, (int, float)) and not np.isnan(theta):
                efficiency = min(theta, 1)
                potential = 1 - efficiency

                result_efficiency.append(efficiency)
                result_super_efficiency.append(theta)
                result_potential.append(potential)
            else:
                result_efficiency.append(np.nan)
                result_super_efficiency.append(np.nan)
                result_potential.append(np.nan)
            j += 1

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
    """
    Run super-efficiency DEA.

    For each company i, an LP model is solved where the company is excluded from the reference set.

    Args:
        inputs: numpy array with inputs (n_companies * n_inputs)
        outputs: numpy array with outputs (n_companies * n_outputs)
        rts: 'crs' or 'vrs'

    Returns:
        List with super-efficiency scores (or "OUTLIER" if optimization fails)
    """
    n = len(inputs)
    eff = []

    for i in range(n):
        # Check for missing data
        if np.any(np.isnan(inputs[i])) or np.any(np.isnan(outputs[i])):
            eff.append("OUTLIER")
            continue

        # Create LP problem
        model = pulp.LpProblem(name=f"DEA_SUPER_DMU_{i}", sense=pulp.LpMinimize)

        # Decision variable: theta (efficiency score)
        theta = pulp.LpVariable("theta", lowBound=0)

        # Decision variables: lambdas for ALL companies (not n-1)
        lambdas = [pulp.LpVariable(f"lambda_{j}", lowBound=0) for j in range(n)]

        # Objective: minimize theta (input-oriented)
        model += theta

        # Output constraints: sum(lambda_j * y_j) >= y_0 (exclude company i)
        for r in range(outputs.shape[1]):
            model += (
                pulp.lpSum(lambdas[j] * outputs[j][r] for j in range(n) if j != i)
                >= outputs[i][r]
            )

        # Input constraints: sum(lambda_j * x_j) <= theta * x_0 (exclude company i)
        for k in range(inputs.shape[1]):
            model += (
                pulp.lpSum(lambdas[j] * inputs[j][k] for j in range(n) if j != i)
                <= theta * inputs[i][k]
            )

        # RTS constraint
        if rts == "vrs":
            # Variable Returns to Scale: sum(lambda_j) = 1 (exclude company i)
            model += pulp.lpSum(lambdas[j] for j in range(n) if j != i) == 1
        # else: CRS has no constraint

        # Solve problem
        try:
            model.solve(pulp.PULP_CBC_CMD(msg=0))
            score = pulp.value(theta)

            if score is None or np.isnan(score):
                score = "OUTLIER"
        except:
            score = "OUTLIER"

        eff.append(score)

    return eff


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
