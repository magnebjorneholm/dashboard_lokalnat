"""
test_incentive_calculations.py

Verifierar att Python-implementationen matchar Stata-output.
"""

import pandas as pd
import numpy as np
import sys
import pathlib

from calculations.incentive_calculations import calculate_all_incentives
from calculations.incentive_parameters import MISSING_DATA_IDS


def load_and_prepare_input(filepath: str) -> pd.DataFrame:
    """Laddar input-data och byter namn pa capcost till ret_period."""
    df = pd.read_csv(filepath)
    
    # Byt namn pa capcost till ret_period (mer beskrivande)
    if 'capcost' in df.columns:
        df = df.rename(columns={'capcost': 'ret_period'})
    
    return df


def compare_results(df_calc: pd.DataFrame, df_facit: pd.DataFrame) -> dict:
    """
    Jamfor beraknade resultat mot facit.
    Merge pa (reid, year) for korrekt jamforelse.
    
    Returns:
        Dict med jamforelsemetrik
    """
    results = {}
    
    # Kolumner att jamfora
    compare_cols = [
        'inter_incentive_a',
        'loss_incentive_a', 
        'util_incentive_a',
        'inter_incentive',
        'loss_incentive',
        'util_incentive',
        'incentive_total_year',
        'incentive_total',
        'inter_incentive_sum',
        'loss_incentive_sum',
        'util_incentive_sum',
    ]
    
    # Merge pa reid+year for korrekt jamforelse
    df_merged = df_calc[['reid', 'year'] + [c for c in compare_cols if c in df_calc.columns]].merge(
        df_facit[['reid', 'year'] + [c for c in compare_cols if c in df_facit.columns]],
        on=['reid', 'year'],
        suffixes=('_calc', '_facit')
    )
    
    for col in compare_cols:
        calc_col = f'{col}_calc'
        facit_col = f'{col}_facit'
        
        if calc_col not in df_merged.columns:
            results[col] = {'status': 'MISSING', 'error': 'Kolumn saknas i berakning'}
            continue
        if facit_col not in df_merged.columns:
            results[col] = {'status': 'MISSING', 'error': 'Kolumn saknas i facit'}
            continue
        
        # Jamfor varden (exklusive NaN)
        calc_vals = df_merged[calc_col].values
        facit_vals = df_merged[facit_col].values
        
        # Mask for icke-NaN i bada
        valid_mask = ~(np.isnan(calc_vals) | np.isnan(facit_vals))
        
        if valid_mask.sum() == 0:
            results[col] = {'status': 'NO_DATA', 'error': 'Inga jamforbara varden'}
            continue
        
        calc_valid = calc_vals[valid_mask]
        facit_valid = facit_vals[valid_mask]
        
        # Berakna skillnad
        abs_diff = np.abs(calc_valid - facit_valid)
        rel_diff = np.abs(abs_diff / np.where(facit_valid != 0, facit_valid, 1))
        
        max_abs_diff = abs_diff.max()
        max_rel_diff = rel_diff.max()
        mean_abs_diff = abs_diff.mean()
        
        # Tolerans: 10 kr absolut (avrundningsfel mellan Python/Stata)
        is_match = max_abs_diff < 10.0
        
        results[col] = {
            'status': 'PASS' if is_match else 'FAIL',
            'max_abs_diff': max_abs_diff,
            'max_rel_diff': max_rel_diff,
            'mean_abs_diff': mean_abs_diff,
            'n_compared': valid_mask.sum(),
        }
    
    return results


def verify_missing_data_handling(df_calc: pd.DataFrame) -> dict:
    """Verifierar att MISSING_DATA_IDS har NaN."""
    results = {}
    
    incentive_cols = [c for c in df_calc.columns if 'incentive' in c]
    
    for reid in MISSING_DATA_IDS:
        mask = df_calc['reid'] == reid
        if mask.sum() == 0:
            results[reid] = {'status': 'NOT_FOUND'}
            continue
        
        all_nan = df_calc.loc[mask, incentive_cols].isna().all().all()
        results[reid] = {'status': 'PASS' if all_nan else 'FAIL', 'all_nan': all_nan}
    
    return results


def main():
    print("=" * 60)
    print("TEST: Incitamentberakningar mot facitfil")
    print("=" * 60)
    
    # Ladda data
    input_path = '/mnt/user-data/uploads/all_adjust_vars.csv'
    facit_path = '/mnt/user-data/uploads/adjustment_final__1_.csv'

    # Fallback: om filerna inte finns på /mnt/user-data, använd repo/data
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    data_dir = repo_root / 'data'
    if not pathlib.Path(input_path).exists():
        candidate = data_dir / 'all_adjust_vars.csv'
        if candidate.exists():
            input_path = str(candidate)

    if not pathlib.Path(facit_path).exists():
        # Leta efter en fil i data-mappen som innehåller 'adjustment_final'
        if data_dir.exists():
            for f in data_dir.iterdir():
                if 'adjustment_final' in f.name:
                    facit_path = str(f)
                    break
    
    print(f"\nLaddar input: {input_path}")
    df_input = load_and_prepare_input(input_path)
    print(f"  Rader: {len(df_input)}, Kolumner: {len(df_input.columns)}")
    
    print(f"\nLaddar facit: {facit_path}")
    df_facit = pd.read_csv(facit_path)
    print(f"  Rader: {len(df_facit)}, Kolumner: {len(df_facit.columns)}")
    
    # Kor berakning
    print("\nKor berakning...")
    df_calc = calculate_all_incentives(df_input, ret_period_col='ret_period')
    print(f"  Resultat: {len(df_calc)} rader")
    
    # Jamfor resultat
    print("\n" + "-" * 60)
    print("JAMFORELSE MOT FACIT")
    print("-" * 60)
    
    comparison = compare_results(df_calc, df_facit)
    
    all_pass = True
    for col, result in comparison.items():
        status = result['status']
        if status == 'PASS':
            print(f"  [PASS] {col}")
        elif status == 'FAIL':
            all_pass = False
            print(f"  [FAIL] {col}")
            print(f"         max_abs_diff: {result['max_abs_diff']:.6f}")
            print(f"         max_rel_diff: {result['max_rel_diff']:.6%}")
        else:
            print(f"  [{status}] {col}: {result.get('error', '')}")
    
    # Verifiera missing data
    print("\n" + "-" * 60)
    print("MISSING DATA HANTERING")
    print("-" * 60)
    
    missing_results = verify_missing_data_handling(df_calc)
    for reid, result in missing_results.items():
        status = result['status']
        print(f"  reid {reid}: [{status}]")
        if status == 'FAIL':
            all_pass = False
    
    # Detaljerad jamforelse for ett foretag
    print("\n" + "-" * 60)
    print("DETALJERAD JAMFORELSE (reid=38, year=2024)")
    print("-" * 60)
    
    reid, year = 38, 2024
    calc_row = df_calc[(df_calc['reid'] == reid) & (df_calc['year'] == year)].iloc[0]
    facit_row = df_facit[(df_facit['reid'] == reid) & (df_facit['year'] == year)].iloc[0]
    
    detail_cols = [
        'inc_inter', 'cemi4_diff', 'cemi4_adj_factor',
        'inter_incentive_a', 'loss_incentive_a', 'util_incentive_a',
        'max_adj',
        'inter_incentive', 'loss_incentive', 'util_incentive',
        'incentive_total_year', 'incentive_total'
    ]
    
    print(f"  {'Kolumn':25s}  {'Calc':>15s}  {'Facit':>15s}  {'Diff':>12s}")
    print("  " + "-" * 72)
    for col in detail_cols:
        calc_val = calc_row.get(col, np.nan)
        facit_val = facit_row.get(col, np.nan)
        
        if pd.notna(calc_val) and pd.notna(facit_val):
            diff = calc_val - facit_val
            print(f"  {col:25s}: {calc_val:>15.2f}  {facit_val:>15.2f}  {diff:>12.4f}")
        elif pd.notna(calc_val):
            print(f"  {col:25s}: {calc_val:>15.2f}  {'N/A':>15s}  {'':>12s}")
        elif pd.notna(facit_val):
            print(f"  {col:25s}: {'N/A':>15s}  {facit_val:>15.2f}  {'':>12s}")
        else:
            print(f"  {col:25s}: {'N/A':>15s}  {'N/A':>15s}  {'':>12s}")
    
    # Sammanfattning
    print("\n" + "=" * 60)
    if all_pass:
        print("RESULTAT: ALLA TESTER PASSERADE")
    else:
        print("RESULTAT: NAGRA TESTER MISSLYCKADES")
    print("=" * 60)
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())