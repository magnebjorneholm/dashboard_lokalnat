"""
dea_producer.py - DEA producer för efficiency-beräkning
========================================================

Återanvänd från dea_model.py.
Kör DEA (Data Envelopment Analysis) med outlier-hantering.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

try:
    from pulp import LpProblem, LpVariable, LpMinimize, lpSum, value
except ImportError:
    raise ImportError("pulp krävs för DEA-beräkning: pip install pulp")


def _run_super_efficiency_dea(inputs: np.ndarray, outputs: np.ndarray, rts: str):
    """Kör superefficiency DEA."""
    n = len(inputs)
    eff = []
    
    for i in range(n):
        if np.any(np.isnan(inputs[i])) or np.any(np.isnan(outputs[i])):
            eff.append("OUTLIER")
            continue

        model = LpProblem(name=f"DEA_SUPER_DMU_{i}", sense=LpMinimize)
        theta = LpVariable("theta", lowBound=0)
        lambdas = [LpVariable(f"lambda_{j}", lowBound=0) for j in range(n)]

        model += theta

        for r in range(outputs.shape[1]):
            model += lpSum(lambdas[j] * outputs[j][r] for j in range(n) if j != i) >= outputs[i][r]
        for k in range(inputs.shape[1]):
            model += lpSum(lambdas[j] * inputs[j][k] for j in range(n) if j != i) <= theta * inputs[i][k]
        if rts == "vrs":
            model += lpSum(lambdas[j] for j in range(n) if j != i) == 1

        try:
            model.solve()
            score = value(theta)
            if score is None or np.isnan(score):
                score = "OUTLIER"
        except:
            score = "OUTLIER"

        eff.append(score)
    return eff


def run_dea_analysis(
    df: pd.DataFrame,
    input_cols: list = ["CAPEX", "OPEXp"],
    output_cols: list = ["CU", "MW", "NS", "MWhl", "MWhh"],
    rts: str = "crs",
    outlier_filter: bool = True,
    q_lower: float = 25.0,
    q_upper: float = 75.0,
    multiplier: float = 2.0
) -> pd.DataFrame:
    """
    Kör DEA med outlier-identifikation enligt Ei:s metod.
    
    Args:
        df: DataFrame med input/output-variabler per DMU
        input_cols: Lista med input-kolumner (ex: ["CAPEX", "OPEXp"])
        output_cols: Lista med output-kolumner (ex: ["CU", "MW", "NS", "MWhl", "MWhh"])
        rts: Returns to scale - "crs" (constant) eller "vrs" (variable)
        outlier_filter: Om outliers ska identifieras
        q_lower: Nedre kvartil för outlier-detektion (default: 25)
        q_upper: Övre kvartil för outlier-detektion (default: 75)
        multiplier: IQR-multiplikator för outlier-threshold (default: 2.0)
    
    Returns:
        DataFrame med kolumner:
        - Effektivitet: Effektivitetsscore (0-1)
        - Supereffektivitet: Superefficiency score
        - potential: Förbättringspotential
        - is_outlier: Boolean om DMU är outlier
    """
    df = df.copy()
    df[input_cols] = df[input_cols].apply(pd.to_numeric, errors="coerce")

    inputs = df[input_cols].values
    outputs = df[output_cols].values

    # Första körning
    eff1 = _run_super_efficiency_dea(inputs, outputs, rts)
    df["supereff1"] = eff1

    # Identifiera outliers
    theta_valid = [e for e in eff1 if isinstance(e, (int, float)) and not np.isnan(e)]
    q_low = np.percentile(theta_valid, q_lower)
    q_high = np.percentile(theta_valid, q_upper)
    iqr = q_high - q_low
    threshold = q_high + multiplier * iqr
    df["is_outlier"] = [e > threshold if isinstance(e, (int, float)) else True for e in eff1]

    # Andra körning (exkludera outliers)
    df_clean = df[~df["is_outlier"]].reset_index(drop=True)
    inputs_clean = df_clean[input_cols].values
    outputs_clean = df_clean[output_cols].values
    eff2 = _run_super_efficiency_dea(inputs_clean, outputs_clean, rts)

    result_effektivitet = []
    result_supereffektivitet = []
    result_potential = []

    j = 0
    for i, is_outlier in enumerate(df["is_outlier"]):
        if is_outlier:
            result_effektivitet.append(min(eff1[i], 1) if isinstance(eff1[i], (int, float)) else np.nan)
            result_supereffektivitet.append(eff1[i] if isinstance(eff1[i], (int, float)) else np.nan)
            result_potential.append(1.0)
        else:
            theta = eff2[j]
            if isinstance(theta, (int, float)) and not np.isnan(theta):
                effektivitet = min(theta, 1)
                revred = 1 - effektivitet

                result_effektivitet.append(effektivitet)
                result_supereffektivitet.append(theta)
                result_potential.append(revred)
            else:
                result_effektivitet.append(np.nan)
                result_supereffektivitet.append(np.nan)
                result_potential.append(np.nan)
            j += 1

    df["Effektivitet"] = result_effektivitet
    df["Supereffektivitet"] = result_supereffektivitet
    df["potential"] = result_potential
    
    return df


def produce_efficiency_from_dea(
    capex: pd.DataFrame,
    opex: pd.DataFrame,
    volumes: pd.DataFrame,
    parameters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Producer: Beräkna efficiency från DEA.
    
    Args:
        capex: DataFrame med CAPEX per DMU (kolumner: DMU, CAPEX)
        opex: DataFrame med OPEX per DMU (kolumner: DMU, OPEXp)
        volumes: DataFrame med volumes per DMU (kolumner: DMU, CU, MW, NS, MWhl, MWhh)
        parameters: Dict med DEA-parametrar:
            - input_cols: Lista med input-variabler (default: ["CAPEX", "OPEXp"])
            - output_cols: Lista med output-variabler (default: ["CU", "MW", "NS", "MWhl", "MWhh"])
            - rts: "crs" eller "vrs" (default: "crs")
            - outlier_filter: bool (default: True)
            - q_lower: float (default: 25.0)
            - q_upper: float (default: 75.0)
            - multiplier: float (default: 2.0)
    
    Returns:
        DataFrame med efficiency per DMU
        
    Example:
        >>> efficiency = produce_efficiency_from_dea(
        ...     capex=capex_df,
        ...     opex=opex_df,
        ...     volumes=volumes_df,
        ...     parameters={'rts': 'crs', 'input_cols': ['CAPEX', 'OPEXp']}
        ... )
    """
    # Merge all data
    df = capex[['DMU', 'CAPEX']].copy()
    df = df.merge(opex[['DMU', 'OPEXp']], on='DMU', how='left')
    df = df.merge(volumes, on='DMU', how='left')
    
    # Extract parameters
    input_cols = parameters.get('input_cols', ['CAPEX', 'OPEXp'])
    output_cols = parameters.get('output_cols', ['CU', 'MW', 'NS', 'MWhl', 'MWhh'])
    rts = parameters.get('rts', 'crs')
    outlier_filter = parameters.get('outlier_filter', True)
    q_lower = parameters.get('q_lower', 25.0)
    q_upper = parameters.get('q_upper', 75.0)
    multiplier = parameters.get('multiplier', 2.0)
    
    # Run DEA
    result = run_dea_analysis(
        df,
        input_cols=input_cols,
        output_cols=output_cols,
        rts=rts,
        outlier_filter=outlier_filter,
        q_lower=q_lower,
        q_upper=q_upper,
        multiplier=multiplier
    )
    
    return result[['DMU', 'Effektivitet', 'Supereffektivitet', 'potential', 'is_outlier']]
