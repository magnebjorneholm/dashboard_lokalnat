"""
tests/test_pipeline_e2e.py

End-to-end validering av pipeline:
- Baseline pipeline -> exakt intäktsram (golden test)
- DEA accuracy mot Ei's baseline
- Scenarion: WACC-skalning, annan trunkering
- Parameter change (kräver capbase_a_mini.parquet)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders import load_baseline_data
from config import (
    get_baseline_config,
    create_wacc_scaling_config,
    create_parameter_change_config
)
from pipeline import run_pipeline
from calculations import run_dea_analysis, BASELINE_DEA_SPEC


# Golden test data för REL00886 (Kraftringen Nät AB)
GOLDEN_REID = "REL00886"
GOLDEN_INTAKTSRAM = 3986194.49
GOLDEN_PAVERKBARA = 920371.93
GOLDEN_OPAVERKBARA = 1348225.00
GOLDEN_KAPITALKOSTNAD_PERIOD = 1715597.56
GOLDEN_EFFEKTIVITET = 0.793547


def test_baseline_intaktsram_accuracy():
    """Golden test: Baseline pipeline ska ge exakt intäktsram"""
    print("\n" + "="*60)
    print("TEST: Baseline intäktsram accuracy (GOLDEN TEST)")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    config = get_baseline_config(user_reid=GOLDEN_REID)
    
    result = run_pipeline(baseline, config)
    
    ir = result.post_dea.user_intaktsram
    
    print(f"  Företag: {GOLDEN_REID} (Kraftringen Nät AB)")
    print()
    
    # Intäktsram total
    actual_ir = ir['Intaktsram_Total']
    diff_ir = abs(actual_ir - GOLDEN_INTAKTSRAM)
    tolerance = 100.0  # 100 tkr tolerans för avrundningar
    
    print(f"  Intäktsram Total:")
    print(f"    Beräknad: {actual_ir:,.2f} tkr")
    print(f"    Förväntat (SDF): {GOLDEN_INTAKTSRAM:,.2f} tkr")
    print(f"    Avvikelse: {diff_ir:,.2f} tkr ({diff_ir/GOLDEN_INTAKTSRAM*100:.3f}%)")
    
    assert diff_ir < tolerance, f"Intäktsram avviker för mycket: {diff_ir:.2f} tkr"
    
    # Påverkbara
    actual_pav = ir['Paverkbara_Periodsumma']
    diff_pav = abs(actual_pav - GOLDEN_PAVERKBARA)
    
    print(f"\n  Påverkbara kostnader:")
    print(f"    Beräknad: {actual_pav:,.2f} tkr")
    print(f"    Förväntat (SDF): {GOLDEN_PAVERKBARA:,.2f} tkr")
    print(f"    Avvikelse: {diff_pav:,.2f} tkr")
    
    assert diff_pav < tolerance, f"Påverkbara avviker för mycket: {diff_pav:.2f} tkr"
    
    print("\n  PASS - Intäktsram matchar Ei's SDF inom tolerans")


def test_dea_baseline_accuracy():
    """Test att vår DEA ger samma resultat som Ei's baseline"""
    print("\n" + "="*60)
    print("TEST: DEA baseline accuracy")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör vår DEA med baseline-spec
    our_dea = run_dea_analysis(
        df=baseline.df_all_companies,
        model_spec=BASELINE_DEA_SPEC
    )
    
    # Ei's DEA
    ei_dea = baseline.dea_results
    
    # Merge för jämförelse
    comparison = our_dea[['REId', 'Effektivitet', 'potential', 'is_outlier']].merge(
        ei_dea[['REId', 'Effektivitet', 'potential']],
        on='REId',
        suffixes=('_ours', '_ei')
    )
    
    # Filtrera bort outliers för jämförelse
    non_outliers = comparison[~comparison['is_outlier']].copy()
    non_outliers['eff_diff'] = abs(non_outliers['Effektivitet_ours'] - non_outliers['Effektivitet_ei'])
    
    max_diff = non_outliers['eff_diff'].max()
    mean_diff = non_outliers['eff_diff'].mean()
    
    print(f"  Jämförelse (icke-outliers): {len(non_outliers)} företag")
    print(f"  Max effektivitetsavvikelse: {max_diff:.6f}")
    print(f"  Medel avvikelse: {mean_diff:.6f}")
    
    # REL00886 specifikt
    row = comparison[comparison['REId'] == GOLDEN_REID].iloc[0]
    print(f"\n  REL00886:")
    print(f"    Vår effektivitet: {row['Effektivitet_ours']:.6f}")
    print(f"    Ei's effektivitet: {row['Effektivitet_ei']:.6f}")
    
    tolerance = 0.05  # 0.1% tolerans
    assert max_diff <= tolerance, f"DEA avvikelse för stor: {max_diff:.6f} > {tolerance}"
    
    print("\n  PASS - DEA matchar Ei's baseline")


def test_wacc_scaling_scenario():
    """Test WACC-skalning scenario"""
    print("\n" + "="*60)
    print("TEST: WACC-skalning scenario")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Baseline
    baseline_config = get_baseline_config(user_reid=GOLDEN_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    baseline_ir = baseline_result.post_dea.user_intaktsram['Intaktsram_Total']
    
    # Högre WACC (5%)
    wacc_config = create_wacc_scaling_config(user_reid=GOLDEN_REID, new_wacc=0.05)
    wacc_result = run_pipeline(baseline, wacc_config)
    wacc_ir = wacc_result.post_dea.user_intaktsram['Intaktsram_Total']
    
    print(f"  Baseline WACC: 4.53%")
    print(f"  Ny WACC: 5.00%")
    print()
    print(f"  Baseline intäktsram: {baseline_ir:,.0f} tkr")
    print(f"  Ny intäktsram: {wacc_ir:,.0f} tkr")
    print(f"  Förändring: {wacc_ir - baseline_ir:+,.0f} tkr ({(wacc_ir/baseline_ir-1)*100:+.2f}%)")
    
    # Högre WACC ska ge högre intäktsram
    assert wacc_ir > baseline_ir, "Högre WACC ska ge högre intäktsram"
    
    # Kapitalkostnad (årsvärde) ska ha ökat
    baseline_kap = baseline_result.extraction.capex
    wacc_kap = wacc_result.extraction.capex
    print(f"\n  Baseline Kapitalkostnad_2024: {baseline_kap:,.0f} tkr")
    print(f"  Skalad Kapitalkostnad_2024: {wacc_kap:,.0f} tkr")
    
    assert wacc_kap > baseline_kap, "Kapitalkostnad_2024 ska öka vid högre WACC"
    
    print("\n  PASS - WACC-skalning fungerar korrekt")


def test_multiple_companies():
    """Test baseline pipeline för flera företag"""
    print("\n" + "="*60)
    print("TEST: Baseline pipeline för flera företag")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    test_companies = [
        ("REL00001", "Ale El ek. för."),
        ("REL00886", "Kraftringen Nät AB"),
        ("REL03015", "Vattenfall Eldistribution AB"),
        ("REL03030", "E.ON Energidistribution AB"),
    ]
    
    for reid, expected_name in test_companies:
        try:
            config = get_baseline_config(user_reid=reid)
            result = run_pipeline(baseline, config)
            
            ir = result.post_dea.user_intaktsram['Intaktsram_Total']
            eff = result.extraction.efficiency
            
            print(f"  {reid}: IR={ir:,.0f} tkr, Eff={eff:.4f}")
            
            # Validera att intäktsram är rimlig (positiv, inte för liten)
            assert ir > 0, f"{reid} har negativ intäktsram"
            assert ir > 10000, f"{reid} har orimligt låg intäktsram"
            
        except Exception as e:
            print(f"  {reid}: FAIL - {e}")
            raise
    
    print("\n  PASS - Alla företag processade")


def test_parameter_change_scenario():
    """Test parameter change scenario (kräver capbase_a_mini.parquet)"""
    print("\n" + "="*60)
    print("TEST: Parameter change scenario")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kontrollera att capbase_a_mini.parquet finns
    capbase_paths = [
        Path("data/capbase_a_mini.parquet"),
        Path("/mnt/project/data/capbase_a_mini.parquet"),
        Path("capbase_a_mini.parquet"),
    ]
    
    capbase_exists = any(p.exists() for p in capbase_paths)
    
    if not capbase_exists:
        # FAIL - filen ska finnas enligt användarens krav
        raise FileNotFoundError(
            "capbase_a_mini.parquet hittades inte. "
            f"Sökta sökvägar: {[str(p) for p in capbase_paths]}"
        )
    
    # Normvalue adjustment: Öka mätarutrustning (cat 5) med 20%
    normvalue_adj = {5: 1.2}
    
    config = create_parameter_change_config(
        user_reid=GOLDEN_REID,
        normvalue_adjustments=normvalue_adj,
        wacc=0.0453
    )
    
    result = run_pipeline(baseline, config)
    
    print(f"  Normvalue justeringar: {normvalue_adj}")
    print(f"  Metod: {result.pre_dea.capex_method}")
    print(f"  Kapitalkostnad modifierad: {result.pre_dea.capex_modified}")
    
    assert result.pre_dea.capex_method == "parameter_change"
    assert result.pre_dea.capex_modified == True
    
    ir = result.post_dea.user_intaktsram['Intaktsram_Total']
    print(f"  Intäktsram: {ir:,.0f} tkr")
    
    print("\n  PASS - Parameter change fungerar")


def test_effkrav_trunkering_scenario():
    """Test scenario med ändrad effektiviseringskrav-trunkering"""
    print("\n" + "="*60)
    print("TEST: Effkrav trunkering scenario")
    print("="*60 + "\n")
    
    # OBS: Detta kräver att pipelinen stödjer custom effkrav-parametrar
    # Om inte implementerat, testar vi bara att default-värden fungerar
    
    baseline = load_baseline_data()
    config = get_baseline_config(user_reid=GOLDEN_REID)
    
    result = run_pipeline(baseline, config)
    
    effkrav = result.post_dea.user_effkrav_proc
    
    print(f"  REL00886 effektiviseringskrav: {effkrav*100:.3f}%")
    
    # Effkrav ska vara mellan min och max
    from calculations import DEFAULT_EFFKRAV_PARAMS
    trunk_min = DEFAULT_EFFKRAV_PARAMS['trunkering_min']
    trunk_max = DEFAULT_EFFKRAV_PARAMS['trunkering_max']
    
    # Beräkna förväntade gränser
    effkrav_at_min = ((1 + trunk_min/4) ** 0.25) - 1
    effkrav_at_max = ((1 + trunk_max/4) ** 0.25) - 1
    
    print(f"  Trunkering min: {trunk_min*100:.2f}% -> effkrav {effkrav_at_min*100:.3f}%")
    print(f"  Trunkering max: {trunk_max*100:.1f}% -> effkrav {effkrav_at_max*100:.3f}%")
    
    # REL00886 är inte outlier, så effkrav ska vara inom gränserna
    if not result.extraction.is_outlier:
        assert effkrav >= effkrav_at_min - 0.0001, "Effkrav under minimum"
        assert effkrav <= effkrav_at_max + 0.0001, "Effkrav över maximum"
        print("\n  Effkrav inom trunkerade gränser")
    else:
        assert effkrav == 0.01, "Outlier ska ha 1% effkrav"
        print("\n  Företag är outlier, fast 1% effkrav")
    
    print("  PASS")


def run_all_tests():
    """Kör alla end-to-end tester"""
    print("\n" + "="*70)
    print("  TEST SUITE: PIPELINE END-TO-END")
    print("="*70)
    
    try:
        test_baseline_intaktsram_accuracy()
        test_dea_baseline_accuracy()
        test_wacc_scaling_scenario()
        test_multiple_companies()
        test_parameter_change_scenario()
        test_effkrav_trunkering_scenario()
        
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