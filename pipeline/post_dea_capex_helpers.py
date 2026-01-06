"""
pipeline/post_dea_capex_helpers.py

Hjälpfunktioner för att hämta kapitalkostnad och avkastning i post_dea.

REFAKTORISERAD: Hanterar alla kombinationer av capbase_source och capex_method.

Viktigt: Dessa funktioner behöver förstå BÅDE source och method för att
korrekt avgöra var data kommer ifrån:

| Source      | Method           | Avkastning per år    | Kapitalkostnad period |
|-------------|------------------|----------------------|-----------------------|
| baseline    | baseline         | baseline df          | SDF                   |
| baseline    | wacc_scaling     | skala baseline       | skala SDF             |
| baseline    | parameter_change | KENT-output          | KENT-output           |
| kent_upload | baseline         | KENT-output          | KENT-output           |
| kent_upload | wacc_scaling     | KENT → skala         | KENT → skala          |
| kent_upload | parameter_change | KENT-output          | KENT-output           |
"""

import pandas as pd
from typing import List

from pipeline.stages.stage_outputs import PreDeaStageOutput, BaselineStageOutput


# Kolumnnamn i SDF IR-sheet
SDF_COL_KAPITALKOSTNAD = 'Kapitalkostnad'
SDF_COL_KAPITALBINDNING = 'varav Kapital-bindning'


def get_return_per_year(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Hämtar avkastning per år för alla 148 företag.
    
    Används för incitamentjusteringens 1/3-cap som appliceras per år.
    
    Logik baserat på source + method:
    - baseline + baseline: Direkt från baseline df_all_companies
    - baseline + wacc_scaling: Skala baseline per-år avkastning
    - baseline + parameter_change: Från KENT-output (pre_dea.df_all_companies)
    - kent_upload + baseline: Från KENT-output (pre_dea.df_all_companies)
    - kent_upload + wacc_scaling: Från pre_dea (redan skalat)
    - kent_upload + parameter_change: Från KENT-output
    
    Args:
        pre_dea: Output från Pre-DEA stage
        baseline: Output från Baseline stage
    
    Returns:
        DataFrame med: REId, Avkastning_2024, Avkastning_2025, 
                       Avkastning_2026, Avkastning_2027 (alla i tkr)
    """
    
    source = pre_dea.capbase_source
    method = pre_dea.capex_method
    years = [2024, 2025, 2026, 2027]
    yearly_cols = [f'Avkastning_{year}' for year in years]
    
    # Bestäm om vi behöver använda KENT-output eller baseline
    use_kent_output = (
        source != 'baseline' or  # Custom source → KENT kördes för användaren
        method == 'parameter_change'  # Parameter change → KENT kördes för alla
    )
    
    if method == 'baseline' and source == 'baseline':
        # Renodlad baseline - använd baseline df
        return _get_return_from_baseline(baseline, yearly_cols)
    
    elif method == 'wacc_scaling' and source == 'baseline':
        # WACC-skalning utan custom source - skala baseline
        return _get_return_wacc_scaled(pre_dea, baseline, yearly_cols)
    
    elif use_kent_output:
        # KENT-output finns i pre_dea.df_all_companies
        return _get_return_from_pre_dea(pre_dea, yearly_cols)
    
    else:
        # Fallback - försök med pre_dea
        return _get_return_from_pre_dea(pre_dea, yearly_cols)


def _get_return_from_baseline(
    baseline: BaselineStageOutput,
    yearly_cols: List[str]
) -> pd.DataFrame:
    """Hämtar avkastning per år direkt från baseline df_all_companies."""
    df = baseline.df_all_companies
    
    missing_cols = [col for col in yearly_cols if col not in df.columns]
    
    if missing_cols:
        print(f"    [VARNING] Per-år avkastning saknas i baseline: {missing_cols}")
        print(f"    → Använder aggregerad Avkastning för alla år")
        
        result = df[['REId']].copy()
        for col in yearly_cols:
            if 'Avkastning' in df.columns:
                result[col] = df['Avkastning']
            else:
                result[col] = 0
        return result
    
    return df[['REId'] + yearly_cols].copy()


def _get_return_wacc_scaled(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    yearly_cols: List[str]
) -> pd.DataFrame:
    """
    Skalar baseline per-år avkastning med WACC-kvot.
    
    Formel: Avkastning_ny = Avkastning_baseline × (WACC_ny / WACC_baseline)
    """
    if pre_dea.wacc_used is None:
        raise ValueError("wacc_used saknas i PreDeaStageOutput för wacc_scaling")
    
    df_baseline = baseline.df_all_companies
    
    # Kontrollera att per-år kolumner finns
    missing_cols = [col for col in yearly_cols if col not in df_baseline.columns]
    if missing_cols:
        print(f"    [VARNING] Saknade kolumner för WACC-skalning: {missing_cols}")
        # Fallback: använd aggregerad avkastning
        return _get_return_from_baseline(baseline, yearly_cols)
    
    # Beräkna skalningsfaktor
    scaling_factor = pre_dea.wacc_used / baseline.wacc
    
    result = df_baseline[['REId']].copy()
    for col in yearly_cols:
        result[col] = df_baseline[col] * scaling_factor
    
    return result


def _get_return_from_pre_dea(
    pre_dea: PreDeaStageOutput,
    yearly_cols: List[str]
) -> pd.DataFrame:
    """Hämtar avkastning per år från pre_dea.df_all_companies (KENT-output)."""
    df = pre_dea.df_all_companies
    
    missing_cols = [col for col in yearly_cols if col not in df.columns]
    
    if missing_cols:
        print(f"    [VARNING] Per-år avkastning saknas i pre_dea: {missing_cols}")
        
        # Försök med Avkastning_Period / 4 som fallback
        if 'Avkastning_Period' in df.columns:
            result = df[['REId']].copy()
            avg_return = df['Avkastning_Period'] / 4
            for col in yearly_cols:
                result[col] = avg_return
            return result
        
        # Sista fallback: 0
        result = df[['REId']].copy()
        for col in yearly_cols:
            result[col] = 0
        return result
    
    return df[['REId'] + yearly_cols].copy()


def get_capex_period_sum(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Hämtar kapitalkostnad periodsumma (4 år) för alla 148 företag.
    
    KRITISKT: Returnerar PERIODSUMMA (4 år), INTE årsvärde!
    
    Logik baserat på source + method:
    - baseline + baseline: SDF "Kapitalkostnad" (periodsumma)
    - baseline + wacc_scaling: Skala SDF periodsumma
    - övriga: KENT-output Kapitalkostnad_Period
    
    Args:
        pre_dea: Output från Pre-DEA stage
        baseline: Output från Baseline stage
    
    Returns:
        DataFrame med: REId, Kapitalkostnad_Total (periodsumma i tkr)
    """
    
    source = pre_dea.capbase_source
    method = pre_dea.capex_method
    
    # Bestäm källa
    use_sdf = (source == 'baseline' and method in ['baseline', 'wacc_scaling'])
    
    if method == 'baseline' and source == 'baseline':
        # Renodlad baseline - använd SDF
        return _get_capex_from_sdf(baseline)
    
    elif method == 'wacc_scaling' and source == 'baseline':
        # WACC-skalning - skala SDF periodsumma
        return _calculate_wacc_scaled_period_capex(pre_dea, baseline)
    
    else:
        # KENT-output finns i pre_dea.df_all_companies
        return _get_capex_from_pre_dea(pre_dea, baseline)


def _get_capex_from_sdf(baseline: BaselineStageOutput) -> pd.DataFrame:
    """Hämtar kapitalkostnad periodsumma direkt från SDF."""
    sdf = baseline.sdf_ir.copy()
    
    if SDF_COL_KAPITALKOSTNAD not in sdf.columns:
        raise ValueError(f"Kolumn '{SDF_COL_KAPITALKOSTNAD}' saknas i SDF IR")
    
    df = sdf[['REId', SDF_COL_KAPITALKOSTNAD]].copy()
    df.columns = ['REId', 'Kapitalkostnad_Total']
    df['Kapitalkostnad_Total'] = pd.to_numeric(
        df['Kapitalkostnad_Total'], errors='coerce'
    ).fillna(0)
    
    return df


def _calculate_wacc_scaled_period_capex(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Beräknar WACC-skalad periodsumma för kapitalkostnad.
    
    Metod:
    1. Hämta avskrivning och avkastning från SDF
    2. Skala endast avkastning med WACC-kvot
    3. Kapitalkostnad = Avskrivning + Skalad_Avkastning
    """
    if pre_dea.wacc_used is None:
        raise ValueError("wacc_used saknas för WACC-skalad periodsumma")
    
    sdf = baseline.sdf_ir.copy()
    
    # Hämta nödvändiga kolumner
    result = sdf[['REId']].copy()
    
    # Kapitalkostnad = Avskrivning + Avkastning
    # Vid WACC-skalning: Avskrivning konstant, Avkastning skalas
    
    if SDF_COL_KAPITALBINDNING in sdf.columns:
        avkastning_baseline = pd.to_numeric(
            sdf[SDF_COL_KAPITALBINDNING], errors='coerce'
        ).fillna(0)
        
        kapitalkostnad_baseline = pd.to_numeric(
            sdf.get(SDF_COL_KAPITALKOSTNAD, 0), errors='coerce'
        ).fillna(0)
        
        avskrivning = kapitalkostnad_baseline - avkastning_baseline
        
        # Skala avkastning
        scaling_factor = pre_dea.wacc_used / baseline.wacc
        avkastning_scaled = avkastning_baseline * scaling_factor
        
        result['Kapitalkostnad_Total'] = avskrivning + avkastning_scaled
    else:
        # Fallback: skala hela kapitalkostnaden
        kapitalkostnad = pd.to_numeric(
            sdf.get(SDF_COL_KAPITALKOSTNAD, 0), errors='coerce'
        ).fillna(0)
        
        scaling_factor = pre_dea.wacc_used / baseline.wacc
        result['Kapitalkostnad_Total'] = kapitalkostnad * scaling_factor
    
    return result


def _get_capex_from_pre_dea(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """Hämtar kapitalkostnad periodsumma från pre_dea.df_all_companies."""
    df = pre_dea.df_all_companies
    
    # Försök hitta periodsumma-kolumn
    if 'Kapitalkostnad_Period' in df.columns:
        result = df[['REId', 'Kapitalkostnad_Period']].copy()
        result.columns = ['REId', 'Kapitalkostnad_Total']
        return result
    
    elif 'Kapitalkostnad_Total' in df.columns:
        return df[['REId', 'Kapitalkostnad_Total']].copy()
    
    else:
        # Försök summera per-år kolumner
        yearly_cols = ['Kapitalkostnad_2024', 'Kapitalkostnad_2025',
                      'Kapitalkostnad_2026', 'Kapitalkostnad_2027']
        
        if all(col in df.columns for col in yearly_cols):
            result = df[['REId']].copy()
            result['Kapitalkostnad_Total'] = (
                df['Kapitalkostnad_2024'] + df['Kapitalkostnad_2025'] +
                df['Kapitalkostnad_2026'] + df['Kapitalkostnad_2027']
            )
            return result
        
        # Sista fallback: använd SDF
        print("    [VARNING] Kapitalkostnad_Period saknas i pre_dea, använder SDF")
        return _get_capex_from_sdf(baseline)