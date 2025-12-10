"""
tests/test_data_loading.py

Verifierar att all data laddas korrekt med nya kolumnnamn.
Testar: Baseline data, SDF, reconciliation, kolumnvalidering.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders import load_baseline_data


# Golden test data for REL00886 (Kraftringen Nät AB)
GOLDEN_REID = "REL00886"
GOLDEN_DMU = 121
GOLDEN_KAPITALKOSTNAD_2024 = 421649.22
GOLDEN_OPEXP = 212723.32
GOLDEN_AVSKRIVNING = 231228.47
GOLDEN_AVKASTNING = 190420.75


def test_load_baseline_data():
    """Test att baseline data laddas utan fel"""
    print("\n" + "="*60)
    print("TEST: Ladda baseline data")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    assert baseline is not None, "Baseline är None"
    print(f"  Laddade baseline med {len(baseline.df_all_companies)} företag")
    print("  PASS")
    
    return baseline


def test_baseline_has_correct_columns(baseline):
    """Test att df_all_companies har rätt kolumner (nya namn)"""
    print("\n" + "="*60)
    print("TEST: Validera kolumnnamn i df_all_companies")
    print("="*60 + "\n")
    
    df = baseline.df_all_companies
    
    # Måste finnas: nya kolumnnamn
    required_cols = [
        'DMU', 'REId', 'Företag', 
        'Kapitalkostnad_2024',  # NYA NAMNET (inte CAPEX)
        'OPEXp', 'TOTEX',
        'Avskrivning', 'Avkastning',
        'CU', 'MW', 'NS', 'MWhl', 'MWhh'
    ]
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"  FAIL: Saknade kolumner: {missing}")
        raise AssertionError(f"Saknade kolumner: {missing}")
    
    print(f"  Alla {len(required_cols)} kolumner finns")
    
    # CAPEX ska INTE finnas som separat kolumn (eller vara samma som Kapitalkostnad_2024)
    if 'CAPEX' in df.columns:
        # Om CAPEX finns, ska det vara alias för Kapitalkostnad_2024
        diff = (df['CAPEX'] - df['Kapitalkostnad_2024']).abs().max()
        assert diff < 0.01, f"CAPEX och Kapitalkostnad_2024 skiljer sig: {diff}"
        print("  CAPEX finns som alias (ok)")
    
    print("  PASS")


def test_kapitalkostnad_2024_values(baseline):
    """Test att Kapitalkostnad_2024 har korrekta värden"""
    print("\n" + "="*60)
    print("TEST: Validera Kapitalkostnad_2024 värden")
    print("="*60 + "\n")
    
    df = baseline.df_all_companies
    
    # Alla värden ska vara icke-negativa
    assert (df['Kapitalkostnad_2024'] >= 0).all(), "Negativa Kapitalkostnad_2024 värden"
    print("  Alla värden >= 0")
    
    # Inga NaN
    assert df['Kapitalkostnad_2024'].notna().all(), "NaN i Kapitalkostnad_2024"
    print("  Inga NaN-värden")
    
    # Golden test: REL00886
    row = df[df['REId'] == GOLDEN_REID]
    assert len(row) == 1, f"REL00886 hittades inte"
    
    actual = row['Kapitalkostnad_2024'].values[0]
    tolerance = 1.0  # 1 tkr
    diff = abs(actual - GOLDEN_KAPITALKOSTNAD_2024)
    
    assert diff < tolerance, f"REL00886 Kapitalkostnad_2024: {actual:.2f} != {GOLDEN_KAPITALKOSTNAD_2024:.2f}"
    print(f"  REL00886 Kapitalkostnad_2024: {actual:,.2f} tkr (förväntat: {GOLDEN_KAPITALKOSTNAD_2024:,.2f})")
    print("  PASS")


def test_totex_equals_sum(baseline):
    """Test att TOTEX = OPEXp + Kapitalkostnad_2024"""
    print("\n" + "="*60)
    print("TEST: TOTEX = OPEXp + Kapitalkostnad_2024")
    print("="*60 + "\n")
    
    df = baseline.df_all_companies
    
    calculated = df['OPEXp'] + df['Kapitalkostnad_2024']
    diff = (df['TOTEX'] - calculated).abs()
    max_diff = diff.max()
    
    assert max_diff < 1.0, f"Max TOTEX-avvikelse: {max_diff:.2f} tkr"
    print(f"  Max avvikelse: {max_diff:.4f} tkr")
    print("  PASS")


def test_avskrivning_avkastning(baseline):
    """Test att Avskrivning och Avkastning finns och summerar till Kapitalkostnad_2024"""
    print("\n" + "="*60)
    print("TEST: Avskrivning + Avkastning = Kapitalkostnad_2024")
    print("="*60 + "\n")
    
    df = baseline.df_all_companies
    
    # Kolumner ska finnas
    assert 'Avskrivning' in df.columns, "Avskrivning saknas"
    assert 'Avkastning' in df.columns, "Avkastning saknas"
    
    # Summa ska vara ungefär lika med Kapitalkostnad_2024
    calculated = df['Avskrivning'] + df['Avkastning']
    diff = (df['Kapitalkostnad_2024'] - calculated).abs()
    max_diff = diff.max()
    
    assert max_diff < 1.0, f"Max avvikelse: {max_diff:.2f} tkr"
    print(f"  Max avvikelse: {max_diff:.4f} tkr")
    
    # Golden test
    row = df[df['REId'] == GOLDEN_REID].iloc[0]
    assert abs(row['Avskrivning'] - GOLDEN_AVSKRIVNING) < 1.0
    assert abs(row['Avkastning'] - GOLDEN_AVKASTNING) < 1.0
    print(f"  REL00886 Avskrivning: {row['Avskrivning']:,.2f} tkr")
    print(f"  REL00886 Avkastning: {row['Avkastning']:,.2f} tkr")
    print("  PASS")


def test_load_sdf_data(baseline):
    """Test att SDF-data laddas korrekt"""
    print("\n" + "="*60)
    print("TEST: SDF-data laddning")
    print("="*60 + "\n")
    
    # Alla SDF-attribut ska finnas
    assert hasattr(baseline, 'sdf_ir'), "sdf_ir saknas"
    assert hasattr(baseline, 'sdf_paverkbara'), "sdf_paverkbara saknas"
    assert hasattr(baseline, 'sdf_opaverkbara'), "sdf_opaverkbara saknas"
    
    # Inte tomma
    assert len(baseline.sdf_ir) > 0, "sdf_ir är tom"
    assert len(baseline.sdf_paverkbara) > 0, "sdf_paverkbara är tom"
    assert len(baseline.sdf_opaverkbara) > 0, "sdf_opaverkbara är tom"
    
    print(f"  sdf_ir: {len(baseline.sdf_ir)} rader")
    print(f"  sdf_paverkbara: {len(baseline.sdf_paverkbara)} rader")
    print(f"  sdf_opaverkbara: {len(baseline.sdf_opaverkbara)} rader")
    
    # REId ska finnas i alla
    assert 'REId' in baseline.sdf_ir.columns, "REId saknas i sdf_ir"
    print("  PASS")


def test_load_dea_results(baseline):
    """Test att DEA-resultat laddas korrekt"""
    print("\n" + "="*60)
    print("TEST: DEA-resultat laddning")
    print("="*60 + "\n")
    
    dea = baseline.dea_results
    
    # Kolumner
    required = ['REId', 'DMU', 'Effektivitet', 'potential', 'is_outlier']
    missing = [col for col in required if col not in dea.columns]
    assert not missing, f"Saknade kolumner: {missing}"
    
    # Antal
    assert len(dea) >= 140, f"För få DEA-resultat: {len(dea)}"
    print(f"  {len(dea)} DEA-resultat")
    
    # Outliers
    n_outliers = dea['is_outlier'].sum()
    print(f"  {n_outliers} outliers")
    
    print("  PASS")


def test_load_reconciliation(baseline):
    """Test att reconciliation laddas korrekt"""
    print("\n" + "="*60)
    print("TEST: Reconciliation laddning")
    print("="*60 + "\n")
    
    rec = baseline.reconciliation
    
    # Kolumner
    assert 'REId' in rec.columns, "REId saknas"
    assert 'DMU' in rec.columns, "DMU saknas"
    
    # Unika REId
    assert rec['REId'].is_unique, "REId är inte unika"
    
    print(f"  {len(rec)} mappningar")
    print("  PASS")


def test_wacc_value(baseline):
    """Test att WACC har korrekt värde"""
    print("\n" + "="*60)
    print("TEST: WACC värde")
    print("="*60 + "\n")
    
    expected_wacc = 0.0453
    
    assert baseline.wacc == expected_wacc, f"WACC: {baseline.wacc} != {expected_wacc}"
    print(f"  WACC = {baseline.wacc:.4f}")
    print("  PASS")


def test_company_count(baseline):
    """Test att vi har rätt antal företag"""
    print("\n" + "="*60)
    print("TEST: Antal företag")
    print("="*60 + "\n")
    
    n = len(baseline.df_all_companies)
    
    assert n == 148, f"Förväntar 148 företag, fick {n}"
    print(f"  {n} företag")
    print("  PASS")


def run_all_tests():
    """Kör alla data loading-tester"""
    print("\n" + "="*70)
    print("  TEST SUITE: DATA LOADING")
    print("="*70)
    
    try:
        baseline = test_load_baseline_data()
        test_baseline_has_correct_columns(baseline)
        test_kapitalkostnad_2024_values(baseline)
        test_totex_equals_sum(baseline)
        test_avskrivning_avkastning(baseline)
        test_load_sdf_data(baseline)
        test_load_dea_results(baseline)
        test_load_reconciliation(baseline)
        test_wacc_value(baseline)
        test_company_count(baseline)
        
        print("\n" + "="*70)
        print("  ALLA TESTER GODKANDA!")
        print("="*70 + "\n")
        return True
        
    except Exception as e:
        print(f"\n  TEST MISSLYCKADES: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)