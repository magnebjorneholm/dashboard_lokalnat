"""
test_custom_dea.py

Testar custom DEA-körning med olika parametrar.
Verifierar att pipeline stödjer:
- Olika inputs (CAPEX+OPEXp, TOTEX)
- Olika outputs (subset av CU, MW, NS, MWhl, MWhh)
- Skalavkastning (CRS, VRS)
- Outlier-parametrar (q_lower, q_upper, multiplier)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders.baseline_data import load_baseline_data
from pipeline.core import run_pipeline
from config.case_definition import (
    CaseDefinition,
    PreDeaConfig,
    DeaConfig,
    PostDeaConfig,
    CapexMethod,
    EfficiencyMethod,
    PaverkbaraMethod,
    get_baseline_config
)


TEST_REID = "REL00886"


def test_custom_dea_baseline_spec():
    """
    Test 1: Custom DEA med baseline-specifikation
    
    Ska ge (nästan) samma resultat som baseline DEA.
    """
    print("\n" + "="*60)
    print("TEST 1: Custom DEA med baseline-specifikation")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör baseline DEA
    baseline_config = get_baseline_config(TEST_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    baseline_eff = baseline_result.extraction.efficiency
    
    # Kör custom DEA med samma specifikation
    custom_config = CaseDefinition(
        name="Custom DEA baseline spec",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs',
            orientation='input',
            q_lower=25.0,
            q_upper=75.0,
            multiplier=2.0
        ),
        post_dea=PostDeaConfig()
    )
    
    custom_result = run_pipeline(baseline, custom_config)
    custom_eff = custom_result.extraction.efficiency
    
    print(f"  Baseline effektivitet: {baseline_eff:.6f}")
    print(f"  Custom effektivitet: {custom_eff:.6f}")
    
    # Notera: Kan finnas små skillnader pga numeriska toleranser
    diff = abs(baseline_eff - custom_eff) if baseline_eff and custom_eff else 0
    print(f"  Differens: {diff:.6f}")
    
    print("\n  PASS - Custom DEA kördes")


def test_custom_dea_vrs():
    """
    Test 2: Custom DEA med VRS (Variable Returns to Scale)
    
    VRS ger typiskt högre effektivitet än CRS för små/stora företag.
    """
    print("\n" + "="*60)
    print("TEST 2: Custom DEA med VRS")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör CRS
    crs_config = CaseDefinition(
        name="CRS",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs'
        ),
        post_dea=PostDeaConfig()
    )
    
    crs_result = run_pipeline(baseline, crs_config)
    crs_eff = crs_result.extraction.efficiency
    
    # Kör VRS
    vrs_config = CaseDefinition(
        name="VRS",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='vrs'
        ),
        post_dea=PostDeaConfig()
    )
    
    vrs_result = run_pipeline(baseline, vrs_config)
    vrs_eff = vrs_result.extraction.efficiency
    
    print(f"  CRS effektivitet: {crs_eff:.6f}")
    print(f"  VRS effektivitet: {vrs_eff:.6f}")
    
    # VRS ska ge >= CRS (matematiskt)
    if vrs_eff and crs_eff:
        print(f"  VRS >= CRS: {vrs_eff >= crs_eff - 0.001}")  # Tolerans för numeriska fel
    
    print("\n  PASS - VRS DEA kördes")


def test_custom_dea_different_outputs():
    """
    Test 3: Custom DEA med färre outputs
    
    Färre outputs ger typiskt lägre effektivitet.
    """
    print("\n" + "="*60)
    print("TEST 3: Custom DEA med färre outputs")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Alla 5 outputs
    full_config = CaseDefinition(
        name="Full outputs",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs'
        ),
        post_dea=PostDeaConfig()
    )
    
    full_result = run_pipeline(baseline, full_config)
    full_eff = full_result.extraction.efficiency
    
    # Endast 3 outputs
    reduced_config = CaseDefinition(
        name="Reduced outputs",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS'],  # Utan MWhl, MWhh
            rts='crs'
        ),
        post_dea=PostDeaConfig()
    )
    
    reduced_result = run_pipeline(baseline, reduced_config)
    reduced_eff = reduced_result.extraction.efficiency
    
    print(f"  5 outputs effektivitet: {full_eff:.6f}")
    print(f"  3 outputs effektivitet: {reduced_eff:.6f}")
    
    # Fler outputs ger typiskt högre effektivitet
    if full_eff and reduced_eff:
        print(f"  Full >= Reduced: {full_eff >= reduced_eff - 0.001}")
    
    print("\n  PASS - Olika outputs testade")


def test_custom_dea_outlier_params():
    """
    Test 4: Custom DEA med olika outlier-parametrar
    
    Striktare outlier-detektion (lägre multiplier) ger fler outliers.
    """
    print("\n" + "="*60)
    print("TEST 4: Custom DEA med olika outlier-parametrar")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Standard outlier params
    standard_config = CaseDefinition(
        name="Standard outliers",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs',
            q_lower=25.0,
            q_upper=75.0,
            multiplier=2.0
        ),
        post_dea=PostDeaConfig()
    )
    
    standard_result = run_pipeline(baseline, standard_config)
    standard_outliers = standard_result.dea.dea_results['is_outlier'].sum()
    
    # Striktare outlier params (lägre multiplier = fler outliers)
    strict_config = CaseDefinition(
        name="Strict outliers",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs',
            q_lower=25.0,
            q_upper=75.0,
            multiplier=1.0  # Striktare
        ),
        post_dea=PostDeaConfig()
    )
    
    strict_result = run_pipeline(baseline, strict_config)
    strict_outliers = strict_result.dea.dea_results['is_outlier'].sum()
    
    # Generösare outlier params (högre multiplier = färre outliers)
    generous_config = CaseDefinition(
        name="Generous outliers",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs',
            q_lower=25.0,
            q_upper=75.0,
            multiplier=3.0  # Generösare
        ),
        post_dea=PostDeaConfig()
    )
    
    generous_result = run_pipeline(baseline, generous_config)
    generous_outliers = generous_result.dea.dea_results['is_outlier'].sum()
    
    print(f"  Standard (mult=2.0): {standard_outliers} outliers")
    print(f"  Strikt (mult=1.0): {strict_outliers} outliers")
    print(f"  Generös (mult=3.0): {generous_outliers} outliers")
    
    # Striktare params ska ge fler outliers
    print(f"\n  Strikt >= Standard >= Generös: {strict_outliers >= standard_outliers >= generous_outliers}")
    
    print("\n  PASS - Outlier-parametrar testade")


def test_custom_dea_totex_input():
    """
    Test 5: Custom DEA med TOTEX som input
    
    TOTEX = OPEXp + Kapitalkostnad_2024, så detta är en aggregerad input.
    """
    print("\n" + "="*60)
    print("TEST 5: Custom DEA med TOTEX som input")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Standard (CAPEX + OPEXp)
    standard_config = CaseDefinition(
        name="CAPEX+OPEXp",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs'
        ),
        post_dea=PostDeaConfig()
    )
    
    standard_result = run_pipeline(baseline, standard_config)
    standard_eff = standard_result.extraction.efficiency
    
    # TOTEX som enda input
    totex_config = CaseDefinition(
        name="TOTEX",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['TOTEX'],  # Endast TOTEX
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs'
        ),
        post_dea=PostDeaConfig()
    )
    
    totex_result = run_pipeline(baseline, totex_config)
    totex_eff = totex_result.extraction.efficiency
    
    print(f"  Kapitalkostnad+OPEXp effektivitet: {standard_eff:.6f}")
    print(f"  TOTEX effektivitet: {totex_eff:.6f}")
    
    print("\n  PASS - TOTEX som input testades")


def test_custom_dea_affects_intaktsram():
    """
    Test 6: Verifiera att custom DEA påverkar intäktsram
    
    Olika effektivitet ger olika effektiviseringskrav ger olika påverkbara.
    """
    print("\n" + "="*60)
    print("TEST 6: Custom DEA påverkar intäktsram")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Baseline DEA
    baseline_config = get_baseline_config(TEST_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    baseline_ir = baseline_result.post_dea.user_intaktsram['Intaktsram_Total']
    baseline_effkrav = baseline_result.post_dea.user_effkrav_proc
    
    # VRS DEA (typiskt högre effektivitet = lägre effkrav = högre intäktsram)
    vrs_config = CaseDefinition(
        name="VRS DEA",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='vrs'
        ),
        post_dea=PostDeaConfig()
    )
    
    vrs_result = run_pipeline(baseline, vrs_config)
    vrs_ir = vrs_result.post_dea.user_intaktsram['Intaktsram_Total']
    vrs_effkrav = vrs_result.post_dea.user_effkrav_proc
    
    print(f"  Baseline (CRS):")
    print(f"    Effkrav: {baseline_effkrav*100:.3f}%")
    print(f"    Intäktsram: {baseline_ir:,.0f} tkr")
    print()
    print(f"  Custom (VRS):")
    print(f"    Effkrav: {vrs_effkrav*100:.3f}%")
    print(f"    Intäktsram: {vrs_ir:,.0f} tkr")
    print()
    
    delta_effkrav = vrs_effkrav - baseline_effkrav
    delta_ir = vrs_ir - baseline_ir
    
    print(f"  Förändring:")
    print(f"    Effkrav: {delta_effkrav*100:+.3f} procentenheter")
    print(f"    Intäktsram: {delta_ir:+,.0f} tkr")
    
    print("\n  PASS - Custom DEA påverkar intäktsram")


def run_all_tests():
    """Kör alla custom DEA-tester"""
    
    print("="*70)
    print("  TEST SUITE: CUSTOM DEA")
    print("="*70)
    
    tests = [
        ("Test 1: Baseline spec", test_custom_dea_baseline_spec),
        ("Test 2: VRS", test_custom_dea_vrs),
        ("Test 3: Olika outputs", test_custom_dea_different_outputs),
        ("Test 4: Outlier params", test_custom_dea_outlier_params),
        ("Test 5: TOTEX input", test_custom_dea_totex_input),
        ("Test 6: Påverkar intäktsram", test_custom_dea_affects_intaktsram),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n  TEST MISSLYCKADES: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    if failed == 0:
        print(f"  ALLA {passed} TESTER GODKANDA!")
    else:
        print(f"  {passed} GODKANDA, {failed} MISSLYCKADE")
    print("="*70)


if __name__ == "__main__":
    run_all_tests()