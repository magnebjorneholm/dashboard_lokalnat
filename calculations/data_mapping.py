"""
calculations/data_mapping.py

Funktioner för att mappa mellan id_network, REId och företagsdata.
Efter RER-filtrering har vi 1:1 mapping: id_network <-> REId.

Merge-strategi:
- Baseline har Avkastning_2024-2027, Avkastning_Period
- KENT uppdaterar ENDAST de företag som faktiskt omberäknats
- Övriga företag behåller sina baseline-värden intakta
- SDF-fallback för företag utan Kapitalkostnad_Period
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple

TEST_MODE = True  # Flagga för testläge (mini-dataset)

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
    sdf_ir: Optional[pd.DataFrame] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Mergar KENT-beräknad CAPEX med baseline företagsdata.
    
    Strategi:
    - Baseline har redan Avkastning_2024-2027, Avkastning_Period
    - KENT uppdaterar ENDAST de företag som faktiskt omberäknats
    - Övriga företag behåller sina baseline-värden intakta
    - Om sdf_ir tillhandahålls: SDF-data används som fallback för företag
      som saknar Kapitalkostnad_Period (partiell KENT-täckning)
    
    Args:
        df_network: DataFrame med kapitalkostnader per REId från KENT
        df_all_companies: Baseline företagsdata med OPEXp, volumes, per-år avkastning
        sdf_ir: (Valfri) SDF intäktsram-data för fallback
        verbose: Om True, skriv ut detaljerad debug-info
        
    Returns:
        DataFrame med 148 företag och uppdaterad CAPEX/TOTEX för KENT-beräknade företag
    """
    
    def log(msg: str, indent: int = 0):
        if verbose:
            prefix = "  " * indent
            print(f"{prefix}{msg}")
    
    log("â”€â”€ merge_kent_with_baseline() â”€â”€", indent=1)
    
    # 1. Verifiera att REId finns i KENT-output
    if 'REId' not in df_network.columns:
        raise ValueError(
            "df_network saknar REId-kolumn! "
            "Kör aggregate_to_network_level först."
        )
    
    # 2. Starta med en kopia av baseline
    df_result = df_all_companies.copy()
    
    # 3. Identifiera vilka REIds som KENT har omberäknat
    kent_reids = set(df_network['REId'].unique())
    baseline_reids = set(df_all_companies['REId'].unique())
    
    n_kent = len(kent_reids)
    n_baseline = len(baseline_reids)
    
    log(f"Indata: KENT={n_kent} företag, Baseline={n_baseline} företag", indent=2)
    
    # Logga täckning
    missing_in_kent = baseline_reids - kent_reids
    if missing_in_kent:
        log(f"KENT-täckning: {n_kent}/{n_baseline} ({100*n_kent/n_baseline:.1f}%)", indent=2)
        log(f"Utan KENT-data: {len(missing_in_kent)} företag behåller baseline-värden", indent=2)
    else:
        log(f"KENT-täckning: Fullständig ({n_kent}/{n_baseline})", indent=2)
    
    # 4. Definiera kolumner som ska uppdateras från KENT
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
        # Per-år avskrivningar
        'Avskrivning_2024', 'Avskrivning_2025',
        'Avskrivning_2026', 'Avskrivning_2027',
        'Avskrivning_Period',
    ]
    
    # Filtrera till kolumner som faktiskt finns i KENT-output
    available_update_cols = [col for col in update_cols if col in df_network.columns]
    
    if not available_update_cols:
        log("[VARNING] KENT-output saknar uppdateringsbara kolumner!", indent=2)
        return df_result
    
    log(f"Kolumner från KENT: {len(available_update_cols)} st", indent=2)
    
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
    
    log(f"Uppdaterade: {updated_count} företag med KENT-värden", indent=2)
    
    # 7. Synkronisera CAPEX med Kapitalkostnad_2024 om CAPEX saknas
    if 'CAPEX' not in available_update_cols and 'Kapitalkostnad_2024' in available_update_cols:
        for reid in kent_reids:
            if reid in df_result['REId'].values:
                mask = df_result['REId'] == reid
                df_result.loc[mask, 'CAPEX'] = df_result.loc[mask, 'Kapitalkostnad_2024']
    
    # 8. Beräkna TOTEX för alla
    df_result['TOTEX'] = df_result['OPEXp'] + df_result['Kapitalkostnad_2024']
    
    # 9. Fyll i Kapitalkostnad_Period från SDF för företag utan KENT-data
    df_result, fallback_stats = _apply_kapitalkostnad_period_fallback(
        df_result, sdf_ir, kent_reids, verbose
    )
    
    # 10. Verifiera resultat
    n_result = len(df_result)
    if n_result != n_baseline:
        log(f"[VARNING] Resultat har {n_result} rader, förväntat {n_baseline}", indent=2)
    
    # Sammanfattning
    log("â”€â”€ Resultat â”€â”€", indent=1)
    log(f"Kapitalkostnad_2024: {(~df_result['Kapitalkostnad_2024'].isna()).sum()}/{n_result} företag", indent=2)
    
    if 'Kapitalkostnad_Period' in df_result.columns:
        n_period = (~df_result['Kapitalkostnad_Period'].isna()).sum()
        log(f"Kapitalkostnad_Period: {n_period}/{n_result} företag "
            f"(KENT: {fallback_stats['from_kent']}, SDF-fallback: {fallback_stats['from_sdf']})", indent=2)
    
    return df_result


def _apply_kapitalkostnad_period_fallback(
    df_result: pd.DataFrame,
    sdf_ir: Optional[pd.DataFrame],
    kent_reids: set,
    verbose: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    Fyller i Kapitalkostnad_Period från SDF för företag som saknar KENT-data.
    
    Vid partiell KENT-täckning (t.ex. capbase_a_mini med 3 företag) behöver
    övriga företag periodsumma för intäktsram-beräkning. SDF innehåller
    baseline-värden som används som fallback.
    
    Returns:
        Tuple: (DataFrame med ifylld Kapitalkostnad_Period, dict med statistik)
    """
    
    def log(msg: str, indent: int = 0):
        if verbose:
            prefix = "  " * indent
            print(f"{prefix}{msg}")
    
    stats = {
        'from_kent': len(kent_reids),
        'from_sdf': 0,
        'still_missing': 0
    }
    
    # Säkerställ att kolumnen finns
    if 'Kapitalkostnad_Period' not in df_result.columns:
        df_result['Kapitalkostnad_Period'] = pd.NA
    
    # Identifiera företag som saknar Kapitalkostnad_Period
    missing_period_mask = df_result['Kapitalkostnad_Period'].isna()
    n_missing = missing_period_mask.sum()
    
    if n_missing == 0:
        log("Kapitalkostnad_Period: Fullständig täckning, ingen fallback behövs", indent=2)
        return df_result, stats
    
    # Om SDF inte tillhandahålls
    if sdf_ir is None:
        log(f"[VARNING] {n_missing} företag saknar Kapitalkostnad_Period, ingen SDF tillgänglig", indent=2)
        stats['still_missing'] = n_missing
        return df_result, stats
    
    # Hitta kolumnnamn för kapitalkostnad i SDF
    sdf_capex_col = None
    for col_name in ['Kapitalkostnad', 'Kapitalkostnad_Total', 'Kapitalkostnad_Period']:
        if col_name in sdf_ir.columns:
            sdf_capex_col = col_name
            break
    
    if sdf_capex_col is None:
        log(f"[VARNING] Ingen kapitalkostnad-kolumn i SDF. Kolumner: {list(sdf_ir.columns)[:5]}...", indent=2)
        stats['still_missing'] = n_missing
        return df_result, stats
    
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
    
    stats['from_sdf'] = filled_count
    
    # Kontrollera om några fortfarande saknas
    still_missing = df_result['Kapitalkostnad_Period'].isna().sum()
    stats['still_missing'] = still_missing
    
    # Logga resultat
    n_total = len(df_result)
    log(f"[FALLBACK: SDF] {n_missing}/{n_total} företag saknade Kapitalkostnad_Period från KENT", indent=2)
    log(f"                Fyllde i {filled_count} från SDF (kolumn: '{sdf_capex_col}')", indent=2)
    
    if still_missing > 0:
        log(f"[VARNING] {still_missing} företag saknar fortfarande Kapitalkostnad_Period", indent=2)
    
    return df_result, stats


# =============================================================================
# HJÄLPFUNKTIONER
# =============================================================================

def get_yearly_return_columns(df: pd.DataFrame) -> List[str]:
    """Returnerar lista med per-år avkastningskolumner som finns i DataFrame."""
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    return [col for col in yearly_cols if col in df.columns]


def has_yearly_returns(df: pd.DataFrame) -> bool:
    """Kontrollerar om DataFrame har alla per-år avkastningskolumner."""
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    return all(col in df.columns for col in yearly_cols)


def extract_yearly_returns(
    df: pd.DataFrame,
    reid_col: str = 'REId'
) -> pd.DataFrame:
    """Extraherar per-år avkastning från DataFrame."""
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
    """Skalar per-år avkastning med en faktor (för WACC-skalning)."""
    yearly_cols = ['Avkastning_2024', 'Avkastning_2025', 
                   'Avkastning_2026', 'Avkastning_2027']
    
    result = df[[reid_col]].copy()
    
    for col in yearly_cols:
        if col in df.columns:
            result[col] = df[col] * scaling_factor
        else:
            raise ValueError(f"Kolumn {col} saknas i DataFrame")
    
    result['Avkastning_Period'] = (
        result['Avkastning_2024'] + result['Avkastning_2025'] +
        result['Avkastning_2026'] + result['Avkastning_2027']
    )
    
    return result


def get_reconciliation_mapping(reconciliation_df: pd.DataFrame) -> Dict[str, int]:
    """Skapar mapping från REId till id_network."""
    if 'REId' not in reconciliation_df.columns:
        raise ValueError("reconciliation_df saknar REId-kolumn")
    if 'id_network' not in reconciliation_df.columns:
        raise ValueError("reconciliation_df saknar id_network-kolumn")
    return dict(zip(reconciliation_df['REId'], reconciliation_df['id_network']))


def get_reid_from_id_network(
    id_network: int, 
    reconciliation_df: pd.DataFrame
) -> Optional[str]:
    """Hämtar REId för ett givet id_network."""
    mask = reconciliation_df['id_network'] == id_network
    if mask.any():
        return reconciliation_df.loc[mask, 'REId'].iloc[0]
    return None


def get_id_network_from_reid(
    reid: str, 
    reconciliation_df: pd.DataFrame
) -> Optional[int]:
    """Hämtar id_network för ett givet REId."""
    mask = reconciliation_df['REId'] == reid
    if mask.any():
        return int(reconciliation_df.loc[mask, 'id_network'].iloc[0])
    return None