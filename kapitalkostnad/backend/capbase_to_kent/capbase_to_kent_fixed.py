"""
capbase_to_kent_with_params.py - Snabb-fix för att bevara cat_encode/ekdep/maxdep

Denna modul innehåller en modifierad version av build_capbase_a_from_kent
som bevarar kategori-parametrar från original capbase_a för att undvika
re-encoding-problem som ger fel kapitalkostnad.

ANVÄNDNING:
-----------
from capbase_to_kent_with_params import build_capbase_with_preserved_params

reconstructed = build_capbase_with_preserved_params(
    kent_file='KENT_reconstructed.xlsx',
    original_capbase_path='capbase_a.parquet',
    network_id=886
)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Lägg till capbase_prep i path
sys.path.insert(0, str(Path(__file__).parent))
from capbase_prep import build_capbase_a_from_kent


def build_capbase_with_preserved_params(
    kent_file: str,
    original_capbase_path: str,
    network_id: int
) -> pd.DataFrame:
    """
    Bygger capbase_a från KENT men bevarar cat_encode/ekdep/maxdep
    från original capbase_a.
    
    Args:
        kent_file: Path till KENT Excel-fil
        original_capbase_path: Path till original capbase_a.parquet
        network_id: Nätverks-ID
    
    Returns:
        Rekonstruerad capbase_a med korrekta parametrar
    """
    
    # 1. Bygg rekonstruerad capbase från KENT (med fel cat_encode)
    reconstructed = build_capbase_a_from_kent(kent_file, network_id)
    
    # 2. Läs original för att få rätt parametrar
    original = pd.read_parquet(original_capbase_path)
    original_filtered = original[original['id_network'] == network_id].copy()
    
    # 3. Skapa parametrar-mapping
    # För normvärde-komponenter: använd id_comptype (unik kod)
    # För övriga: använd cat+subcat+metod kombination
    
    # Skapa lookup-tabell från original
    param_lookup = {}
    
    for idx, row in original_filtered.iterrows():
        # Skapa unik nyckel
        if pd.notna(row.get('id_comptype')):
            # För normvärde: använd kod som nyckel
            key = ('kod', row['id_comptype'])
        else:
            # För övriga: använd kategori+metod
            key = ('cat', row.get('cat', ''), row.get('subcat', ''), row.get('metod', ''))
        
        # Spara parametrar
        param_lookup[key] = {
            'cat_encode': row['cat_encode'],
            'subcat_encode': row.get('subcat_encode'),
            'ekdep': row['ekdep'],
            'maxdep': row['maxdep']
        }
    
    # 4. Applicera parametrar på rekonstruerad
    for idx, row in reconstructed.iterrows():
        # Hitta rätt parametrar
        if 'kod' in row and pd.notna(row['kod']):
            key = ('kod', row['kod'])
        else:
            key = ('cat', row.get('cat', ''), row.get('subcat', ''), row.get('metod', ''))
        
        # Applicera om parametrar finns
        if key in param_lookup:
            params = param_lookup[key]
            reconstructed.at[idx, 'cat_encode'] = params['cat_encode']
            if params['subcat_encode'] is not None:
                reconstructed.at[idx, 'subcat_encode'] = params['subcat_encode']
            reconstructed.at[idx, 'ekdep'] = params['ekdep']
            reconstructed.at[idx, 'maxdep'] = params['maxdep']
    
    return reconstructed


def validate_params_preservation(
    reconstructed: pd.DataFrame,
    original: pd.DataFrame,
    network_id: int
) -> dict:
    """
    Validerar att parametrar har bevarats korrekt.
    
    Returns:
        Valideringsrapport
    """
    
    original_filtered = original[original['id_network'] == network_id]
    
    report = {
        'row_count_match': len(original_filtered) == len(reconstructed),
        'original_rows': len(original_filtered),
        'reconstructed_rows': len(reconstructed)
    }
    
    # Jämför summor
    for col in ['nuav_2022', 'cat_encode', 'ekdep', 'maxdep']:
        if col in original_filtered.columns and col in reconstructed.columns:
            orig_sum = original_filtered[col].sum()
            recon_sum = reconstructed[col].sum()
            diff_pct = abs((orig_sum - recon_sum) / orig_sum * 100) if orig_sum != 0 else 0
            
            report[f'{col}_match'] = diff_pct < 0.001
            report[f'{col}_diff_pct'] = diff_pct
    
    return report


# Exempel på användning
if __name__ == '__main__':
    
    # Paths
    kent_file = '../data/KENT_reconstructed.xlsx'
    original_capbase = '../data/capbase_a.parquet'
    network_id = 886
    
    print("=== BYGGER CAPBASE MED BEVARADE PARAMETRAR ===\n")
    
    # Bygg med bevarade parametrar
    reconstructed = build_capbase_with_preserved_params(
        kent_file,
        original_capbase,
        network_id
    )
    
    # Validera
    original = pd.read_parquet(original_capbase)
    validation = validate_params_preservation(reconstructed, original, network_id)
    
    print("VALIDERING:")
    print(f"  Antal rader match: {validation['row_count_match']}")
    print(f"  NUAV match: {validation.get('nuav_2022_match', False)} (diff: {validation.get('nuav_2022_diff_pct', 0):.6f}%)")
    print(f"  cat_encode match: {validation.get('cat_encode_match', False)} (diff: {validation.get('cat_encode_diff_pct', 0):.6f}%)")
    print(f"  ekdep match: {validation.get('ekdep_match', False)} (diff: {validation.get('ekdep_diff_pct', 0):.6f}%)")
    print(f"  maxdep match: {validation.get('maxdep_match', False)} (diff: {validation.get('maxdep_diff_pct', 0):.6f}%)")
    
    # Spara
    output_path = '../data/capbase_reconstructed_FIXED.parquet'
    reconstructed.to_parquet(output_path, index=False)
    print(f"\n✓ Sparad: {output_path}")
    
    if all([validation.get('nuav_2022_match'), validation.get('cat_encode_match'),
            validation.get('ekdep_match'), validation.get('maxdep_match')]):
        print("\n✓✓✓ PERFEKT! Nu bör kapitalkostnaden bli korrekt! ✓✓✓")
    else:
        print("\n⚠ Vissa parametrar matchar inte perfekt")