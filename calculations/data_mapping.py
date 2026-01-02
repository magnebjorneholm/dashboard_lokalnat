"""
calculations/data_mapping.py

Funktioner för att mappa mellan id_network, REId och företagsdata.
Efter RER-filtrering har vi 1:1 mapping: id_network <-> REId.

Uppdaterad med ny merge-strategi:
- Baseline har nu Avkastning_2024-2027, Avkastning_Period
- KENT uppdaterar ENDAST de företag som faktiskt omberäknats
- Övriga företag behåller sina baseline-värden intakta
- DEV FALLBACK: Företag utan Kapitalkostnad_Period får värde från SDF
"""

import pandas as pd
from typing import Dict, List, Optional

# Korrekt halvårsmappning
YEAR_TO_TIMECODES = {
    2024: [229, 230],  # H1 + H2
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236],
}


def merge_kent_with_baseline(
    df_network: pd.DataFrame,
    df_all_companies: pd.DataFrame,
    sdf_ir: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Mergar KENT-beräknad CAPEX med baseline företagsdata.
    
    NY STRATEGI (med utökad baseline):
    - Baseline har redan Avkastning_2024-2027, Avkastning_Period
    - KENT uppdaterar ENDAST de företag som faktiskt omberäknats
    - Övriga företag behåller sina baseline-värden intakta
    - DEV FALLBACK: Om sdf_ir tillhandahålls, används SDF-data för företag
      som saknar Kapitalkostnad_Period (typiskt under utveckling med mini-parquet)
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId från KENT
            Förväntar: REId, Kapitalkostnad_2024, och eventuellt per-år kolumner
        df_all_companies: Baseline företagsdata med OPEXp, volumes, per-år avkastning
        sdf_ir: (Valfri) SDF intäktsram-data med 'Kapitalkostnad' periodsumma.
            Om angiven används som fallback för företag utan KENT-beräknad period.
        
    Returns:
        DataFrame med 148 företag och uppdaterad CAPEX/TOTEX för KENT-beräknade företag
    """
    
    # 1. Verifiera att REId finns i KENT-output
    if 'REId' not in df_network.columns:
        raise ValueError(
            "df_network saknar REId-kolumn! "
            "Kör aggregate_to_network_level först."
        )
    
    # 2. Starta med en kopia av baseline (behåll ALLA kolumner)
    df_result = df_all_companies.copy()
    
    # 3. Identifiera vilka REIds som KENT har omberäknat
    kent_reids = set(df_network['REId'].unique())
    baseline_reids = set(df_all_companies['REId'].unique())
    
    n_kent = len(kent_reids)
    n_baseline = len(baseline_reids)
    
    # Logga täckning
    missing_in_kent = baseline_reids - kent_reids
    if missing_in_kent:
        print(f"  ℹ KENT har {n_kent}/{n_baseline} företag. "
              f"{len(missing_in_kent)} företag behåller baseline-värden.")
    
    # 4. Definiera kolumner som ska uppdateras från KENT (om de finns)
    update_cols = [
        # Kapitalkostnader
        'Kapitalkostnad_2024', 'Kapitalkostnad_2025', 
        'Kapitalkostnad_2026', 'Kapitalkostnad_2027',
        'Kapitalkostnad_Period',
        'CAPEX',
        
        # Avskrivningar och avkastning (aggregat)
        'Avskrivning', 'Avkastning',
        
        # Per-år avkastning
        'Avkastning_2024', 'Avkastning_2025', 
        'Avkastning_2026', 'Avkastning_2027',
        'Avkastning_Period',
        
        # Per-år avskrivningar (om KENT producerar dem)
        'Avskrivning_2024', 'Avskrivning_2025',
        'Avskrivning_2026', 'Avskrivning_2027',
        'Avskrivning_Period',
    ]
    
    # Filtrera till kolumner som faktiskt finns i KENT-output
    available_update_cols = [col for col in update_cols if col in df_network.columns]
    
    if not available_update_cols:
        print("  ⚠ KENT-output saknar uppdateringsbara kolumner!")
        return df_result
    
    print(f"  ℹ Uppdaterar {len(available_update_cols)} kolumner från KENT")
    
    # 5. Säkerställ att alla uppdateringskolumner finns i result
    for col in available_update_cols:
        if col not in df_result.columns:
            df_result[col] = pd.NA
    
    # 6. Uppdatera ENDAST de rader som finns i KENT-output
    df_network_indexed = df_network.set_index('REId')
    
    updated_count = 0
    for reid in kent_reids:
        if reid in df_result['REId'].values:
            mask = df_result['REId'] == reid
            
            for col in available_update_cols:
                if col in df_network_indexed.columns:
                    value = df_network_indexed.loc[reid, col]
                    df_result.loc[mask, col] = value
            
            updated_count += 1
    
    print(f"  ✓ Uppdaterade {updated_count} företag med KENT-värden")
    
    # 7. Synkronisera CAPEX med Kapitalkostnad_2024 om CAPEX saknas
    if 'CAPEX' not in available_update_cols and 'Kapitalkostnad_2024' in available_update_cols:
        for reid in kent_reids:
            if reid in df_result['REId'].values:
                mask = df_result['REId'] == reid
                df_result.loc[mask, 'CAPEX'] = df_result.loc[mask, 'Kapitalkostnad_2024']
    
    # 8. Beräkna TOTEX för alla (inklusive uppdaterade)
    df_result['TOTEX'] = df_result['OPEXp'] + df_result['Kapitalkostnad_2024']
    
    # 9. DEV FALLBACK: Fyll i Kapitalkostnad_Period från SDF för företag utan KENT-data
    df_result = _apply_kapitalkostnad_period_fallback(df_result, sdf_ir, kent_reids)
    
    # 10. Verifiera resultat
    n_result = len(df_result)
    if n_result != n_baseline:
        print(f"  ⚠ VARNING: Resultat har {n_result} rader, förväntat {n_baseline}")
    
    return df_result


def _apply_kapitalkostnad_period_fallback(
    df_result: pd.DataFrame,
    sdf_ir: Optional[pd.DataFrame],
    kent_reids: set
) -> pd.DataFrame:
    """
    DEV FALLBACK: Fyller i Kapitalkostnad_Period från SDF för företag som saknar KENT-data.
    
    Under utveckling med capbase_a_mini.parquet har endast ett fåtal företag
    beräknad Kapitalkostnad_Period. Denna funktion fyller i från SDF för övriga.
    
    Args:
        df_result: DataFrame med merge-resultat
        sdf_ir: SDF intäktsram-data (valfri)
        kent_reids: Set med REIds som har KENT-data
        
    Returns:
        DataFrame med ifylld Kapitalkostnad_Period
    """
    # Säkerställ att kolumnen finns
    if 'Kapitalkostnad_Period' not in df_result.columns:
        df_result['Kapitalkostnad_Period'] = pd.NA
    
    # Identifiera företag som saknar Kapitalkostnad_Period
    missing_period_mask = df_result['Kapitalkostnad_Period'].isna()
    n_missing = missing_period_mask.sum()
    
    if n_missing == 0:
        # Alla företag har Kapitalkostnad_Period, ingen fallback behövs
        return df_result
    
    # Om SDF inte tillhandahålls, logga varning och returnera
    if sdf_ir is None:
        print(f"  ⚠ {n_missing} företag saknar Kapitalkostnad_Period och ingen SDF-fallback tillgänglig")
        return df_result
    
    # Hitta kolumnnamn för kapitalkostnad i SDF (kan vara 'Kapitalkostnad' eller liknande)
    sdf_capex_col = None
    for col_name in ['Kapitalkostnad', 'Kapitalkostnad_Total', 'Kapitalkostnad_Period']:
        if col_name in sdf_ir.columns:
            sdf_capex_col = col_name
            break
    
    if sdf_capex_col is None:
        print(f"  ⚠ Kunde inte hitta kapitalkostnad-kolumn i SDF. "
              f"Tillgängliga kolumner: {list(sdf_ir.columns)[:10]}...")
        return df_result
    
    # Skapa lookup från SDF
    sdf_lookup = sdf_ir.set_index('REId')[sdf_capex_col].to_dict()
    
    # Fyll i saknade värden
    filled_count = 0
    for idx, row in df_result[missing_period_mask].iterrows():
        reid = row['REId']
        if reid in sdf_lookup:
            sdf_value = sdf_lookup[reid]
            if pd.notna(sdf_value):
                df_result.loc[idx, 'Kapitalkostnad_Period'] = sdf_value
                filled_count += 1
    
    # Logga tydligt för utvecklaren
    n_total = len(df_result)
    n_from_kent = len(kent_reids)
    print(f"  [DEV FALLBACK] {n_missing} av {n_total} företag saknade Kapitalkostnad_Period från KENT.")
    print(f"                 Använde SDF-baseline för {filled_count} företag.")
    
    # Verifiera att alla nu har värden
    still_missing = df_result['Kapitalkostnad_Period'].isna().sum()
    if still_missing > 0:
        print(f"  ⚠ {still_missing} företag saknar fortfarande Kapitalkostnad_Period efter fallback")
    
    return df_result


def get_yearly_return_columns(df: pd.DataFrame) -> List[str]:
    """
    Returnerar lista med per-år avkastningskolumner som finns i DataFrame.
    
    Args:
        df: DataFrame att kontrollera
        
    Returns:
        Lista med kolumnnamn
    """
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    return [col for col in yearly_cols if col in df.columns]


def has_yearly_returns(df: pd.DataFrame) -> bool:
    """
    Kontrollerar om DataFrame har alla per-år avkastningskolumner.
    
    Args:
        df: DataFrame att kontrollera
        
    Returns:
        True om alla per-år kolumner finns
    """
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    return all(col in df.columns for col in yearly_cols)


def extract_yearly_returns(
    df: pd.DataFrame,
    reid_col: str = 'REId'
) -> pd.DataFrame:
    """
    Extraherar per-år avkastning från DataFrame.
    
    Args:
        df: DataFrame med per-år avkastningskolumner
        reid_col: Namn på REId-kolumn
        
    Returns:
        DataFrame med REId och Avkastning_2024-2027
    """
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    
    available_cols = [col for col in yearly_cols if col in df.columns]
    
    if not available_cols:
        raise ValueError("DataFrame saknar per-år avkastningskolumner")
    
    return df[[reid_col] + available_cols].copy()


def scale_yearly_returns(
    df: pd.DataFrame,
    scaling_factor: float,
    reid_col: str = 'REId'
) -> pd.DataFrame:
    """
    Skalar per-år avkastning med en faktor.
    
    Används för WACC-skalning där avkastning är proportionell mot WACC.
    
    Args:
        df: DataFrame med per-år avkastningskolumner
        scaling_factor: Faktor att multiplicera med (ny_WACC / baseline_WACC)
        reid_col: Namn på REId-kolumn
        
    Returns:
        DataFrame med skalad per-år avkastning
    """
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    
    result = df[[reid_col]].copy()
    
    for col in yearly_cols:
        if col in df.columns:
            result[col] = df[col] * scaling_factor
        else:
            raise ValueError(f"Kolumn {col} saknas i DataFrame")
    
    # Beräkna ny periodsumma
    result['Avkastning_Period'] = (
        result['Avkastning_2024'] + result['Avkastning_2025'] +
        result['Avkastning_2026'] + result['Avkastning_2027']
    )
    
    return result


def get_reconciliation_mapping(reconciliation_df: pd.DataFrame) -> Dict[str, int]:
    """
    Skapar mapping från REId till id_network.
    
    Args:
        reconciliation_df: DataFrame med REId och id_network kolumner
        
    Returns:
        Dict {REId: id_network}
    """
    if 'REId' not in reconciliation_df.columns:
        raise ValueError("reconciliation_df saknar REId-kolumn")
    
    if 'id_network' not in reconciliation_df.columns:
        raise ValueError("reconciliation_df saknar id_network-kolumn")
    
    return dict(zip(reconciliation_df['REId'], reconciliation_df['id_network']))


def get_reid_from_id_network(
    id_network: int, 
    reconciliation_df: pd.DataFrame
) -> Optional[str]:
    """
    Hämtar REId för ett givet id_network.
    
    Args:
        id_network: Nätverk-ID
        reconciliation_df: Reconciliation DataFrame
        
    Returns:
        REId eller None om ej hittat
    """
    mask = reconciliation_df['id_network'] == id_network
    
    if mask.any():
        return reconciliation_df.loc[mask, 'REId'].iloc[0]
    
    return None


def get_id_network_from_reid(
    reid: str, 
    reconciliation_df: pd.DataFrame
) -> Optional[int]:
    """
    Hämtar id_network för ett givet REId.
    
    Args:
        reid: REId (ex: "REL00001")
        reconciliation_df: Reconciliation DataFrame
        
    Returns:
        id_network eller None om ej hittat
    """
    mask = reconciliation_df['REId'] == reid
    
    if mask.any():
        return int(reconciliation_df.loc[mask, 'id_network'].iloc[0])
    
    return None