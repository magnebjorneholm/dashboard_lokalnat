"""
effektivitet/backend/sfa_model.py
Backend för SFA-skattning med pySFA.
"""

import pandas as pd
import numpy as np
from typing import Dict
from pysfa import SFA


def run_sfa_model(
    df: pd.DataFrame,
    fun: str = "prod",
    input_cols: list = ["CAPEX", "OPEXp"],
    output_col: str = "CU",
    intercept: bool = True,
    lambda0: float = 1.0,
    method: str = "teJ",
    outlier_filter: bool = True,
    q_lower: float = 25.0,
    q_upper: float = 75.0,
    multiplier: float = 2.0
) -> pd.DataFrame:
    """
    Kör SFA-skattning med konfigurerbar outlier-identifikation.
    
    Args:
        df: DataFrame med data
        fun: 'prod' (produktionsfunktion) eller 'cost' (kostnadsfunktion)
        input_cols: Lista med input-kolumner
        output_col: Output-kolumn (endast en!)
        intercept: Om intercept ska inkluderas
        lambda0: Initial lambda-värde
        method: TE-metod ('teJ', 'te', 'teMod')
        outlier_filter: Om outliers ska identifieras
        q_lower: Nedre kvartil för outlier-tröskel
        q_upper: Övre kvartil för outlier-tröskel
        multiplier: IQR-multiplikator
        
    Returns:
        DataFrame med SFA-resultat inkl. TE, outlier-flagga och potential
    """
    df = df.copy()
    
    # Validera input
    all_cols = input_cols + [output_col]
    missing = [c for c in all_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Saknade kolumner: {missing}")
    
    # Rensa data
    df_clean = df[['DMU', 'REId', 'Företag'] + all_cols].copy()
    df_clean = df_clean.dropna()
    
    # Filtrera bort negativa/noll-värden
    for col in all_cols:
        df_clean = df_clean[df_clean[col] > 0]
    
    # Logaritmera data (SFA-krav)
    x_data = np.log(df_clean[input_cols].values)
    y_data = np.log(df_clean[output_col].values)
    
    # Konvertera fun och method till pySFA-konstanter
    sfa_fun = SFA.FUN_PROD if fun == "prod" else SFA.FUN_COST
    
    method_map = {
        'teJ': SFA.TE_teJ,
        'te': SFA.TE_te,
        'teMod': SFA.TE_teMod
    }
    sfa_method = method_map.get(method, SFA.TE_teJ)
    
    # Kör SFA-skattning
    sfa_model = SFA.SFA(
        y=y_data,
        x=x_data,
        fun=sfa_fun,
        intercept=intercept,
        lamda0=lambda0,
        method=sfa_method
    )
    
    sfa_model.optimize()
    
    # Extrahera resultat
    te_scores = sfa_model.get_technical_efficiency()
    
    # Skapa resultat-DataFrame
    df_result = df_clean.copy()
    df_result['TE_SFA'] = te_scores
    df_result['Effektivitet'] = te_scores
    df_result['potential'] = 1 - te_scores
    
    # Identifiera outliers baserat på TE
    if outlier_filter:
        te_valid = [e for e in te_scores if not np.isnan(e)]
        q_low = np.percentile(te_valid, q_lower)
        q_high = np.percentile(te_valid, q_upper)
        iqr = q_high - q_low
        threshold_low = q_low - multiplier * iqr
        df_result['is_outlier'] = df_result['TE_SFA'] < threshold_low
    else:
        df_result['is_outlier'] = False
    
    # Spara modellparametrar
    df_result['beta_intercept'] = sfa_model.get_beta()[0] if intercept else np.nan
    for i, col in enumerate(input_cols):
        beta_idx = i + 1 if intercept else i
        df_result[f'beta_{col}'] = sfa_model.get_beta()[beta_idx]
    
    df_result['lambda'] = sfa_model.get_lambda()
    df_result['sigma2'] = sfa_model.get_sigma2()
    df_result['sigmau2'] = sfa_model.get_sigmau2()
    df_result['sigmav2'] = sfa_model.get_sigmav2()
    
    return df_result


def get_sfa_summary_stats(sfa_result: pd.DataFrame) -> Dict:
    """Beräknar sammanfattande statistik för SFA-resultat."""
    te_scores = sfa_result['TE_SFA'].dropna()
    
    return {
        'n_total': len(sfa_result),
        'n_outliers': int(sfa_result['is_outlier'].sum()),
        'te_mean': float(te_scores.mean()),
        'te_median': float(te_scores.median()),
        'te_min': float(te_scores.min()),
        'te_max': float(te_scores.max()),
        'te_std': float(te_scores.std()),
        'lambda': float(sfa_result['lambda'].iloc[0]),
        'sigma2': float(sfa_result['sigma2'].iloc[0]),
        'sigmau2': float(sfa_result['sigmau2'].iloc[0]),
        'sigmav2': float(sfa_result['sigmav2'].iloc[0]),
        'beta_intercept': float(sfa_result['beta_intercept'].iloc[0]) if 'beta_intercept' in sfa_result.columns else None
    }


def extract_beta_coefficients(sfa_result: pd.DataFrame) -> pd.DataFrame:
    """Extraherar beta-koefficienter från SFA-resultat."""
    beta_cols = [c for c in sfa_result.columns if c.startswith('beta_')]
    
    if not beta_cols:
        return pd.DataFrame()
    
    beta_data = []
    for col in beta_cols:
        var_name = col.replace('beta_', '')
        beta_data.append({
            'Variable': var_name,
            'Coefficient': sfa_result[col].iloc[0]
        })
    
    return pd.DataFrame(beta_data)