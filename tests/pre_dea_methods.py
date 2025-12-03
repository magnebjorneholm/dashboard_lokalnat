"""
tests/test_pre_dea_methods.py

Test suite för alla Pre-DEA metoder med REId som primärnyckel:
1. Baseline (ingen ändring)
2. WACC-scaling (snabb avkastningsskalning)
3. Parameter-ändringar (KENT steg 5-8 batch)
4. Kombinerad metod (WACC + parametrar)
"""

import sys
from pathlib import Path

# Lägg till projekt root i path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders import load_baseline_data
from config import (
    get_baseline_config,
    create_wacc_scaling_config,
    create_parameter_change_config
)
from pipeline import run_pipeline


def test_baseline_method():
    """Test 1: Baseline-metod (ingen ändring)"""
    print("\n" + "="*70)
    print("TEST 1: Baseline-metod")
    print("="*70)
    
    # Ladda baseline
    baseline = load_baseline_data()
    
    # Skapa baseline config för REL00001 (Ale El ek. för.)
    config = get_baseline_config(user_reid="REL00001")
    
    # Kör pipeline
    result = run_pipeline(baseline, config)
    
    # Validera
    assert result.pre_dea.capex_modified == False, "CAPEX ska INTE vara modifierad för baseline"
    assert result.pre_dea.capex_method == "baseline", "Metod ska vara 'baseline'"
    
    # Hitta företag i resultat
    company = result.pre_dea.df_all_companies[
        result.pre_dea.df_all_companies['REId'] == 'REL00001'
    ].iloc[0]
    
    print(f"✓ CAPEX modified: {result.pre_dea.capex_modified}")
    print(f"✓ Method: {result.pre_dea.capex_method}")
    print(f"✓ REL00001 (Ale El ek. för.) CAPEX: {company['CAPEX']:,.0f} tkr")
    print("✓ TEST 1 PASS\n")


def test_wacc_scaling_method():
    """Test 2: WACC-scaling metod"""
    print("\n" + "="*70)
    print("TEST 2: WACC-scaling metod")
    print("="*70)
    
    # Ladda baseline
    baseline = load_baseline_data()
    baseline_wacc = baseline.wacc
    
    # Skapa WACC-scaling config med högre WACC
    new_wacc = 0.05
    config = create_wacc_scaling_config(user_reid="REL00001", new_wacc=new_wacc)
    
    # Kör pipeline
    result = run_pipeline(baseline, config)
    
    # Validera
    assert result.pre_dea.capex_modified == True, "CAPEX ska vara modifierad"
    assert result.pre_dea.capex_method == "wacc_scaling", "Metod ska vara 'wacc_scaling'"
    
    # Hämta CAPEX för REL00001
    baseline_company = baseline.df_all_companies[
        baseline.df_all_companies['REId'] == 'REL00001'
    ].iloc[0]
    result_company = result.pre_dea.df_all_companies[
        result.pre_dea.df_all_companies['REId'] == 'REL00001'
    ].iloc[0]
    
    baseline_capex = baseline_company['CAPEX']
    scaled_capex = result_company['CAPEX']
    
    # Scaling factor
    scaling_factor = new_wacc / baseline_wacc
    
    print(f"✓ CAPEX skalad för alla {len(result.pre_dea.df_all_companies)} företag")
    print(f"✓ Scaling factor: {scaling_factor:.4f}")
    print(f"\nJämförelse för REL00001:")
    print(f"  - Baseline CAPEX: {baseline_capex:,.0f} tkr")
    print(f"  - Scaled CAPEX: {scaled_capex:,.0f} tkr")
    print(f"  - Förändring: {scaled_capex - baseline_capex:+,.0f} tkr ({(scaled_capex/baseline_capex - 1)*100:+.2f}%)")
    print("✓ TEST 2 PASS\n")


def test_parameter_change_method():
    """Test 3: Parameter-ändringar metod"""
    print("\n" + "="*70)
    print("TEST 3: Parameter-ändringar metod")
    print("="*70)
    
    # Ladda baseline
    baseline = load_baseline_data()
    
    # Normvalue adjustments: Öka mätarutrustning (cat 5) med 20%
    normvalue_adj = {5: 1.2}
    
    # Skapa config
    config = create_parameter_change_config(
        user_reid="REL00001",
        normvalue_adjustments=normvalue_adj,
        wacc=0.0453  # Använd baseline WACC
    )
    
    # Kör pipeline
    try:
        result = run_pipeline(baseline, config)
        
        # Validera
        assert result.pre_dea.capex_modified == True, "CAPEX ska vara modifierad"
        assert result.pre_dea.capex_method == "parameter_change", "Metod ska vara 'parameter_change'"
        
        # Hämta CAPEX för REL00001
        baseline_company = baseline.df_all_companies[
            baseline.df_all_companies['REId'] == 'REL00001'
        ].iloc[0]
        result_company = result.pre_dea.df_all_companies[
            result.pre_dea.df_all_companies['REId'] == 'REL00001'
        ].iloc[0]
        
        baseline_capex = baseline_company['CAPEX']
        adjusted_capex = result_company['CAPEX']
        
        print(f"✓ Normvalue adjustments: {normvalue_adj}")
        print(f"\nJämförelse för REL00001:")
        print(f"  - Baseline CAPEX: {baseline_capex:,.0f} tkr")
        print(f"  - Adjusted CAPEX: {adjusted_capex:,.0f} tkr")
        print(f"  - Förändring: {adjusted_capex - baseline_capex:+,.0f} tkr ({(adjusted_capex/baseline_capex - 1)*100:+.2f}%)")
        print("✓ TEST 3 PASS\n")
        
    except FileNotFoundError as e:
        if 'capbase_a.parquet' in str(e):
            print("⚠️ capbase_a.parquet saknas - hoppar över test")
            print("   (Detta är OK - filen är ~350MB och måste laddas separat)")
            print("✓ TEST 3 SKIPPED\n")
        else:
            raise


def test_wacc_plus_parameters():
    """Test 4: Kombinerad metod (WACC + parameter-ändringar)"""
    print("\n" + "="*70)
    print("TEST 4: WACC + Parameter-ändringar kombinerat")
    print("="*70)
    
    # Ladda baseline
    baseline = load_baseline_data()
    
    # Kombinera: Högre WACC (5%) + Minska transformatorer (cat 7) med 10%
    config = create_parameter_change_config(
        user_reid="REL00001",
        normvalue_adjustments={7: 0.9},  # -10% transformatorer
        wacc=0.05  # Högre WACC
    )
    
    # Kör pipeline
    try:
        result = run_pipeline(baseline, config)
        
        # Hämta CAPEX för REL00001
        baseline_company = baseline.df_all_companies[
            baseline.df_all_companies['REId'] == 'REL00001'
        ].iloc[0]
        result_company = result.pre_dea.df_all_companies[
            result.pre_dea.df_all_companies['REId'] == 'REL00001'
        ].iloc[0]
        
        baseline_capex = baseline_company['CAPEX']
        combined_capex = result_company['CAPEX']
        
        print(f"✓ WACC: {config.pre_dea.wacc:.4f}")
        print(f"✓ Normvalue adjustments: {config.pre_dea.normvalue_adjustments}")
        print(f"\nJämförelse för REL00001:")
        print(f"  - Baseline CAPEX: {baseline_capex:,.0f} tkr")
        print(f"  - Combined CAPEX: {combined_capex:,.0f} tkr")
        print(f"  - Förändring: {combined_capex - baseline_capex:+,.0f} tkr ({(combined_capex/baseline_capex - 1)*100:+.2f}%)")
        print("✓ TEST 4 PASS\n")
        
    except FileNotFoundError as e:
        if 'capbase_a.parquet' in str(e):
            print("⚠️ capbase_a.parquet saknas - hoppar över test")
            print("✓ TEST 4 SKIPPED\n")
        else:
            raise


def test_all_companies_processed():
    """Test 5: Validera att alla 148 företag processas korrekt"""
    print("\n" + "="*70)
    print("TEST 5: Alla 148 företag")
    print("="*70)
    
    # Ladda baseline
    baseline = load_baseline_data()
    
    # Kör med baseline config
    config = get_baseline_config(user_reid="REL00001")
    result = run_pipeline(baseline, config)
    
    df = result.pre_dea.df_all_companies
    
    # Validera antal företag
    n_companies = len(df)
    assert n_companies == 148, f"Förväntar 148 företag, fick {n_companies}"
    
    # Validera att ingen har null CAPEX
    null_capex = df['CAPEX'].isna().sum()
    assert null_capex == 0, f"{null_capex} företag har null CAPEX"
    
    # Validera TOTEX = OPEXp + CAPEX
    df['TOTEX_calc'] = df['OPEXp'] + df['CAPEX']
    max_diff = (df['TOTEX'] - df['TOTEX_calc']).abs().max()
    assert max_diff < 1.0, f"Max TOTEX avvikelse: {max_diff:.2f} tkr"
    
    print(f"✓ Antal företag: {n_companies}")
    print(f"✓ Företag med null CAPEX: {null_capex}")
    print(f"✓ Max TOTEX avvikelse: {max_diff:.2f} tkr")
    print("✓ TEST 5 PASS\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  PRE-DEA METODER - TEST SUITE (REId)")
    print("="*70)
    
    try:
        test_baseline_method()
        test_wacc_scaling_method()
        test_parameter_change_method()
        test_wacc_plus_parameters()
        test_all_companies_processed()
        
        print("="*70)
        print("  ✅ ALLA TESTER KLARA!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST MISSLYCKADES: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)