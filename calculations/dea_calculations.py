"""
calculations/dea_calculations.py

DEA (Data Envelopment Analysis) beräkningar med outlier-hantering.
Implementerar Ei's baseline-specifikation: CRS, input-oriented, IQR outlier detection.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import pulp


def run_dea_analysis(
    df: pd.DataFrame,
    model_spec: Dict[str, Any]
) -> pd.DataFrame:
    """
    Kör DEA-analys med konfigurerbar modellspecifikation.
    
    Args:
        df: DataFrame med alla 148 företag, kolumner: REId, CAPEX, OPEXp, CU, MW, NS, MWhl, MWhh
        model_spec: Dict med DEA-specifikation:
            - inputs: Lista med input-kolumner (default: ['CAPEX', 'OPEXp'])
            - outputs: Lista med output-kolumner (default: ['CU', 'MW', 'NS', 'MWhl', 'MWhh'])
            - rts: 'crs' eller 'vrs' (default: 'crs')
            - orientation: 'input' eller 'output' (default: 'input')
            - outlier_params: Dict med q_lower, q_upper, multiplier
    
    Returns:
        DataFrame med kolumner: REId, Effektivitet, Supereffektivitet, potential, is_outlier
        
    Process:
        1. Super-efficiency DEA på alla företag
        2. Identifiera outliers med IQR-metod
        3. Kör DEA igen utan outliers i referensset
        4. Beräkna effektivitet och potential
    """
    df = df.copy()
    
    # Extrahera modellspecifikation
    input_cols = model_spec.get('inputs', ['CAPEX', 'OPEXp'])
    output_cols = model_spec.get('outputs', ['CU', 'MW', 'NS', 'MWhl', 'MWhh'])
    rts = model_spec.get('rts', 'crs')
    orientation = model_spec.get('orientation', 'input')
    outlier_params = model_spec.get('outlier_params', {
        'q_lower': 25.0,
        'q_upper': 75.0,
        'multiplier': 2.0
    })
    
    # Validera att alla kolumner finns
    missing_inputs = [col for col in input_cols if col not in df.columns]
    missing_outputs = [col for col in output_cols if col not in df.columns]
    
    if missing_inputs:
        raise ValueError(f"Saknade input-kolumner: {missing_inputs}")
    if missing_outputs:
        raise ValueError(f"Saknade output-kolumner: {missing_outputs}")
    
    # Konvertera till numeriska värden
    df[input_cols] = df[input_cols].apply(pd.to_numeric, errors='coerce')
    for col in output_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Validera att REId finns
    if 'REId' not in df.columns:
        raise ValueError("DataFrame måste innehålla kolumn 'REId'")
    
    if orientation != 'input':
        raise NotImplementedError("Endast input-oriented DEA stöds för tillfället")
    
    # Extrahera input/output arrays
    inputs = df[input_cols].values
    outputs = df[output_cols].values
    
    # STEG 1: Första körning - Super-efficiency DEA
    eff1 = _run_super_efficiency_dea(inputs, outputs, rts)
    df["supereff1"] = eff1
    
    # STEG 2: Identifiera outliers
    theta_valid = [e for e in eff1 if isinstance(e, (int, float)) and not np.isnan(e)]
    q_low = np.percentile(theta_valid, outlier_params['q_lower'])
    q_high = np.percentile(theta_valid, outlier_params['q_upper'])
    iqr = q_high - q_low
    threshold = q_high + outlier_params['multiplier'] * iqr
    
    df["is_outlier"] = [
        e > threshold if isinstance(e, (int, float)) else True 
        for e in eff1
    ]
    
    # STEG 3: Andra körning - Exkludera outliers från referensset
    df_clean = df[~df["is_outlier"]].reset_index(drop=True)
    inputs_clean = df_clean[input_cols].values
    outputs_clean = df_clean[output_cols].values
    eff2 = _run_super_efficiency_dea(inputs_clean, outputs_clean, rts)
    
    # STEG 4: Beräkna resultat
    result_effektivitet = []
    result_supereffektivitet = []
    result_potential = []
    
    j = 0
    for i, is_outlier in enumerate(df["is_outlier"]):
        if is_outlier:
            # För outliers: använd första körningen
            result_effektivitet.append(min(eff1[i], 1) if isinstance(eff1[i], (int, float)) else np.nan)
            result_supereffektivitet.append(eff1[i] if isinstance(eff1[i], (int, float)) else np.nan)
            result_potential.append(1.0)
        else:
            # För icke-outliers: använd andra körningen
            theta = eff2[j]
            if isinstance(theta, (int, float)) and not np.isnan(theta):
                effektivitet = min(theta, 1)
                potential = 1 - effektivitet
                
                result_effektivitet.append(effektivitet)
                result_supereffektivitet.append(theta)
                result_potential.append(potential)
            else:
                result_effektivitet.append(np.nan)
                result_supereffektivitet.append(np.nan)
                result_potential.append(np.nan)
            j += 1
    
    df["Effektivitet"] = result_effektivitet
    df["Supereffektivitet"] = result_supereffektivitet
    df["potential"] = result_potential
    
    # Returnera endast relevanta kolumner
    result_cols = ['REId', 'Effektivitet', 'Supereffektivitet', 'potential', 'is_outlier']
    
    # Lägg till DMU om den finns (för kompatibilitet)
    if 'DMU' in df.columns:
        result_cols = ['DMU'] + result_cols
    
    return df[result_cols].copy()


def _run_super_efficiency_dea(
    inputs: np.ndarray,
    outputs: np.ndarray,
    rts: str
) -> List:
    """
    Kör super-efficiency DEA.
    
    För varje företag i löses en LP-modell där företaget exkluderas från referensset.
    
    Args:
        inputs: numpy array med inputs (n_companies × n_inputs)
        outputs: numpy array med outputs (n_companies × n_outputs)
        rts: 'crs' eller 'vrs'
    
    Returns:
        Lista med super-efficiency scores (eller "OUTLIER" om optimization misslyckas)
    """
    n = len(inputs)
    eff = []
    
    for i in range(n):
        # Kontrollera missing data
        if np.any(np.isnan(inputs[i])) or np.any(np.isnan(outputs[i])):
            eff.append("OUTLIER")
            continue
        
        # Skapa LP-problem
        model = pulp.LpProblem(name=f"DEA_SUPER_DMU_{i}", sense=pulp.LpMinimize)
        
        # Decision variable: theta (efficiency score)
        theta = pulp.LpVariable("theta", lowBound=0)
        
        # Decision variables: lambdas för ALLA företag (inte n-1)
        lambdas = [pulp.LpVariable(f"lambda_{j}", lowBound=0) for j in range(n)]
        
        # Objective: minimize theta (input-oriented)
        model += theta
        
        # Output constraints: Σλⱼ·yⱼ ≥ y₀ (exkludera företag i)
        for r in range(outputs.shape[1]):
            model += (
                pulp.lpSum(lambdas[j] * outputs[j][r] for j in range(n) if j != i) 
                >= outputs[i][r]
            )
        
        # Input constraints: Σλⱼ·xⱼ ≤ θ·x₀ (exkludera företag i)
        for k in range(inputs.shape[1]):
            model += (
                pulp.lpSum(lambdas[j] * inputs[j][k] for j in range(n) if j != i) 
                <= theta * inputs[i][k]
            )
        
        # RTS constraint
        if rts == "vrs":
            # Variable Returns to Scale: Σλⱼ = 1 (exkludera företag i)
            model += pulp.lpSum(lambdas[j] for j in range(n) if j != i) == 1
        # else: CRS har ingen constraint
        
        # Lös problem
        try:
            model.solve(pulp.PULP_CBC_CMD(msg=0))
            score = pulp.value(theta)
            
            if score is None or np.isnan(score):
                score = "OUTLIER"
        except:
            score = "OUTLIER"
        
        eff.append(score)
    
    return eff


# Baseline DEA-specifikation (Ei's modell)
BASELINE_DEA_SPEC = {
    'inputs': ['CAPEX', 'OPEXp'],
    'outputs': ['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
    'rts': 'crs',
    'orientation': 'input',
    'outlier_params': {
        'q_lower': 25.0,
        'q_upper': 75.0,
        'multiplier': 2.0
    }
}