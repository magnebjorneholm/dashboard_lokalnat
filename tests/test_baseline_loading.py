"""
tests/test_baseline_loading.py

Test för Fas 1A: Validera baseline data loading.
"""

import sys
from pathlib import Path

# Lägg till projekt-root i sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders.baseline_data import load_baseline_data, get_baseline_summary


def test_load_baseline_data():
    """Test att baseline data laddar utan fel"""
    print("\n" + "="*60)
    print("TEST: Ladda baseline data")
    print("="*60 + "\n")
    
    try:
        baseline = load_baseline_data()
        print("\n✓ Baseline data laddad framgångsrikt!")
        return baseline
    except Exception as e:
        print(f"\n✗ Fel vid laddning av baseline data: {e}")
        raise


def test_baseline_structure(baseline):
    """Test att baseline har rätt struktur"""
    print("\n" + "="*60)
    print("TEST: Validera baseline-struktur")
    print("="*60 + "\n")
    
    # Testa att alla attribut finns
    assert hasattr(baseline, 'df_all_companies'), "Saknar df_all_companies"
    assert hasattr(baseline, 'dea_results'), "Saknar dea_results"
    assert hasattr(baseline, 'sdf_data'), "Saknar sdf_data"
    assert hasattr(baseline, 'reconciliation'), "Saknar reconciliation"
    assert hasattr(baseline, 'wacc'), "Saknar wacc"
    print("✓ Alla attribut finns")
    
    # Testa WACC
    assert baseline.wacc == 0.0453, f"WACC ska vara 0.0453, är {baseline.wacc}"
    print(f"✓ WACC = {baseline.wacc:.4f}")
    
    # Testa df_all_companies
    df = baseline.df_all_companies
    print(f"\n📊 df_all_companies: {len(df)} rader × {len(df.columns)} kolumner")
    
    expected_cols = ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'NS', 'MW', 'TOTEX']
    for col in expected_cols:
        assert col in df.columns, f"Saknar kolumn: {col}"
    print(f"✓ Alla förväntade kolumner finns: {expected_cols}")
    
    # Testa DEA results
    dea = baseline.dea_results
    print(f"\n📊 dea_results: {len(dea)} rader × {len(dea.columns)} kolumner")
    
    expected_dea_cols = ['DMU', 'REId', 'Effektivitet', 'potential', 'is_outlier']
    for col in expected_dea_cols:
        assert col in dea.columns, f"Saknar kolumn i DEA: {col}"
    print(f"✓ Alla förväntade DEA-kolumner finns")
    
    # Testa SDF data
    sdf = baseline.sdf_data
    print(f"\n📊 sdf_data: Dict med {len(sdf)} sheets")
    
    # Testa att alla sheets finns
    expected_sheets = ['ir', 'opaverkbara', 'paverkbara']
    for sheet in expected_sheets:
        assert sheet in sdf, f"Saknar sheet i SDF: {sheet}"
    print(f"✓ Alla förväntade SDF-sheets finns: {expected_sheets}")
    
    # Visa storleken på varje sheet
    for sheet_name, df in sdf.items():
        print(f"  - {sheet_name}: {len(df)} rader")
    
    # Testa reconciliation
    rec = baseline.reconciliation
    print(f"\n📊 reconciliation: {len(rec)} rader × {len(rec.columns)} kolumner")
    
    expected_rec_cols = ['DMU', 'REId']
    for col in expected_rec_cols:
        assert col in rec.columns, f"Saknar kolumn i reconciliation: {col}"
    print(f"✓ Alla förväntade reconciliation-kolumner finns")
    
    print("\n✓ Baseline-struktur validerad!")


def test_baseline_data_quality(baseline):
    """Test att baseline data har rimliga värden"""
    print("\n" + "="*60)
    print("TEST: Validera data-kvalitet")
    print("="*60 + "\n")
    
    df = baseline.df_all_companies
    
    # Testa att vi har data för alla 148 företag (eller nära)
    n_companies = len(df)
    print(f"Antal företag: {n_companies}")
    assert n_companies >= 140, f"För få företag: {n_companies} (förväntar ~148)"
    print("✓ Antal företag rimligt")
    
    # Testa att CAPEX är icke-negativa
    assert (df['CAPEX'] >= 0).all(), "Alla CAPEX ska vara >= 0"
    print("✓ Alla CAPEX är icke-negativa (>= 0)")
    
    # Testa att TOTEX = OPEXp + CAPEX
    totex_check = abs(df['TOTEX'] - (df['OPEXp'] + df['CAPEX'])) < 1.0
    assert totex_check.all(), "TOTEX ska vara OPEXp + CAPEX"
    print("✓ TOTEX = OPEXp + CAPEX")
    
    # Testa att DMU är unika
    assert df['DMU'].is_unique, "DMU ska vara unika"
    print("✓ DMU är unika")
    
    # Testa DEA results
    dea = baseline.dea_results
    n_outliers = dea['is_outlier'].sum()
    n_valid = (~dea['is_outlier']).sum()
    print(f"\nDEA: {n_valid} valid, {n_outliers} outliers")
    print("✓ DEA results har outlier-flaggor")
    
    print("\n✓ Data-kvalitet validerad!")


def test_baseline_summary(baseline):
    """Test baseline summary-funktion"""
    print("\n" + "="*60)
    print("TEST: Baseline summary")
    print("="*60 + "\n")
    
    summary = get_baseline_summary(baseline)
    
    print("Baseline Summary:")
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key}: {value:,.0f}")
        else:
            print(f"  {key}: {value}")
    
    # Testa att summary innehåller förväntade nycklar
    expected_keys = ['n_dmu', 'total_capex_tsek', 'total_opex_tsek', 'baseline_wacc']
    for key in expected_keys:
        assert key in summary, f"Saknar nyckel i summary: {key}"
    
    print("\n✓ Baseline summary fungerar!")


def run_all_tests():
    """Kör alla tester för Fas 1A"""
    print("\n" + "="*70)
    print("  FAS 1A: FOUNDATION - BASELINE DATA LOADING TEST")
    print("="*70)
    
    try:
        # Test 1: Ladda data
        baseline = test_load_baseline_data()
        
        # Test 2: Validera struktur
        test_baseline_structure(baseline)
        
        # Test 3: Validera data-kvalitet
        test_baseline_data_quality(baseline)
        
        # Test 4: Test summary
        test_baseline_summary(baseline)
        
        # Sammanfattning
        print("\n" + "="*70)
        print("  ✓ ALLA TESTER GODKÄNDA!")
        print("  Fas 1A (Foundation) är klar för nästa steg.")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*70)
        print(f"  ✗ TEST MISSLYCKADES: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)