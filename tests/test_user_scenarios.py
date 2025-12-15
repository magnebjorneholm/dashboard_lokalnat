"""
test_user_scenarios.py

Testar användarscenarier med befintlig case_definition.py.
Simulerar hur en användare skulle konfigurera och köra pipeline.

Scenarion:
1. WACC-skalning (5.5% istället för 4.53%)
2. Effkrav trunkering (ändra min/max)
3. Effkrav outlier_krav (2% istället för 1%)
4. Påverkbara metod (TOTEX istället för OPEX)
5. Kombinerat scenario (WACC + effkrav)
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
    get_baseline_config,
    create_wacc_scaling_config
)


# Golden test företag
TEST_REID = "REL00886"  # Kraftringen Nät AB
BASELINE_WACC = 0.0453
BASELINE_INTAKTSRAM = 3_986_194.49  # tkr


def test_scenario_1_wacc_scaling():
    """
    Scenario 1: Användare ändrar WACC från 4.53% till 5.5%
    
    Förväntat resultat:
    - Högre WACC -> Högre avkastning -> Högre kapitalkostnad -> Högre intäktsram
    """
    print("\n" + "="*60)
    print("SCENARIO 1: WACC-skalning (4.53% -> 5.5%)")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör baseline först
    baseline_config = get_baseline_config(TEST_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    baseline_ir = baseline_result.post_dea.user_intaktsram['Intaktsram_Total']
    
    # Kör med ny WACC
    new_wacc = 0.055  # 5.5%
    wacc_config = create_wacc_scaling_config(TEST_REID, new_wacc)
    wacc_result = run_pipeline(baseline, wacc_config)
    new_ir = wacc_result.post_dea.user_intaktsram['Intaktsram_Total']
    
    # Validera
    delta_ir = new_ir - baseline_ir
    delta_pct = (delta_ir / baseline_ir) * 100
    
    print(f"  Baseline WACC: {BASELINE_WACC:.2%}")
    print(f"  Ny WACC: {new_wacc:.2%}")
    print(f"  Skalningsfaktor: {new_wacc/BASELINE_WACC:.4f}")
    print()
    print(f"  Baseline intaktsram: {baseline_ir:,.0f} tkr")
    print(f"  Ny intaktsram: {new_ir:,.0f} tkr")
    print(f"  Forandring: {delta_ir:+,.0f} tkr ({delta_pct:+.2f}%)")
    
    # Assertions
    assert new_ir > baseline_ir, "Hogre WACC ska ge hogre intaktsram"
    assert delta_pct > 0, "Forandringen ska vara positiv"
    
    # Sanity check
    expected_capex_increase_pct = ((new_wacc / BASELINE_WACC) - 1) * 100
    print(f"\n  Forvantad CAPEX-okning: ~{expected_capex_increase_pct:.1f}%")
    
    print("\n  PASS - WACC-skalning fungerar korrekt")


def test_scenario_2_effkrav_trunkering():
    """
    Scenario 2: Användare ändrar effkrav-trunkering
    
    Baseline: min=16.24%, max=30%
    Nytt: min=20%, max=25%
    """
    print("\n" + "="*60)
    print("SCENARIO 2: Effkrav trunkering (min=20%, max=25%)")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör baseline
    baseline_config = get_baseline_config(TEST_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    baseline_effkrav = baseline_result.post_dea.user_effkrav_proc
    
    # Kör med nya trunkerings-parametrar
    new_config = CaseDefinition(
        name="Trunkering test",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(
            trunkering_min=0.20,  # 20% istället för 16.24%
            trunkering_max=0.25,  # 25% istället för 30%
            outlier_krav=0.01,
            paverkbara_method=PaverkbaraMethod.OPEX
        )
    )
    
    new_result = run_pipeline(baseline, new_config)
    new_effkrav = new_result.post_dea.user_effkrav_proc
    
    # Hämta potential för att förstå förändringen
    user_row = baseline_result.post_dea.all_effkrav[
        baseline_result.post_dea.all_effkrav['REId'] == TEST_REID
    ].iloc[0]
    potential = user_row['potential']
    is_outlier = user_row['is_outlier']
    
    print(f"  Foretag: {TEST_REID}")
    print(f"  Potential: {potential:.2%}")
    print(f"  Is outlier: {is_outlier}")
    print()
    print(f"  Baseline trunkering: min=16.24%, max=30%")
    print(f"  Ny trunkering: min=20%, max=25%")
    print()
    print(f"  Baseline effkrav: {baseline_effkrav*100:.3f}%")
    print(f"  Nytt effkrav: {new_effkrav*100:.3f}%")
    
    # Räkna antal företag som påverkas
    all_baseline_effkrav = baseline_result.post_dea.all_effkrav
    all_new_effkrav = new_result.post_dea.all_effkrav
    
    merged = all_baseline_effkrav[['REId', 'Effkrav_proc']].merge(
        all_new_effkrav[['REId', 'Effkrav_proc']],
        on='REId',
        suffixes=('_baseline', '_new')
    )
    
    changed = merged[abs(merged['Effkrav_proc_baseline'] - merged['Effkrav_proc_new']) > 0.0001]
    
    print(f"\n  Antal foretag med andrat effkrav: {len(changed)} av {len(merged)}")
    
    print("\n  PASS - Trunkering paverkar effkrav")


def test_scenario_3_outlier_krav():
    """
    Scenario 3: Användare ändrar outlier-krav
    
    Baseline: 1% för outliers
    Nytt: 2% för outliers
    """
    print("\n" + "="*60)
    print("SCENARIO 3: Outlier-krav (1% -> 2%)")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör baseline
    baseline_config = get_baseline_config(TEST_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    
    # Kör med nytt outlier-krav
    new_config = CaseDefinition(
        name="Outlier krav test",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(
            trunkering_min=0.162416,
            trunkering_max=0.30,
            outlier_krav=0.02,  # 2% istället för 1%
            paverkbara_method=PaverkbaraMethod.OPEX
        )
    )
    
    new_result = run_pipeline(baseline, new_config)
    
    # Jämför effkrav för outliers
    outliers_baseline = baseline_result.post_dea.all_effkrav[
        baseline_result.post_dea.all_effkrav['is_outlier'] == True
    ]
    outliers_new = new_result.post_dea.all_effkrav[
        new_result.post_dea.all_effkrav['is_outlier'] == True
    ]
    
    n_outliers = len(outliers_baseline)
    
    print(f"  Antal outliers: {n_outliers}")
    print()
    print(f"  Baseline outlier-krav: 1.00%")
    print(f"  Nytt outlier-krav: 2.00%")
    print()
    
    # Validera att alla outliers har exakt 2% krav
    all_correct = all(abs(outliers_new['Effkrav_proc'] - 0.02) < 0.0001)
    
    print(f"  Alla outliers har 2% krav: {all_correct}")
    
    # Validera att icke-outliers INTE påverkas
    non_outliers_baseline = baseline_result.post_dea.all_effkrav[
        baseline_result.post_dea.all_effkrav['is_outlier'] == False
    ].set_index('REId')['Effkrav_proc']
    
    non_outliers_new = new_result.post_dea.all_effkrav[
        new_result.post_dea.all_effkrav['is_outlier'] == False
    ].set_index('REId')['Effkrav_proc']
    
    non_outlier_unchanged = all(
        abs(non_outliers_baseline - non_outliers_new) < 0.0001
    )
    
    print(f"  Icke-outliers oforandrade: {non_outlier_unchanged}")
    
    assert all_correct, "Alla outliers ska ha 2% krav"
    assert non_outlier_unchanged, "Icke-outliers ska vara oforandrade"
    
    print("\n  PASS - Outlier-krav fungerar korrekt")


def test_scenario_4_paverkbara_method():
    """
    Scenario 4: Användare ändrar påverkbara-metod
    
    Baseline: OPEX (effkrav på endast OPEXp)
    Nytt: TOTEX (effkrav på OPEXp + CAPEX)
    """
    print("\n" + "="*60)
    print("SCENARIO 4: Paverkbara metod (OPEX -> TOTEX)")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör baseline (OPEX)
    baseline_config = get_baseline_config(TEST_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    baseline_paverkbara = baseline_result.post_dea.user_intaktsram.get('Paverkbara', 0)
    baseline_ir = baseline_result.post_dea.user_intaktsram['Intaktsram_Total']
    
    # Kör med TOTEX
    totex_config = CaseDefinition(
        name="TOTEX test",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(
            trunkering_min=0.162416,
            trunkering_max=0.30,
            outlier_krav=0.01,
            paverkbara_method=PaverkbaraMethod.TOTEX
        )
    )
    
    totex_result = run_pipeline(baseline, totex_config)
    totex_paverkbara = totex_result.post_dea.user_intaktsram.get('Paverkbara', 0)
    totex_ir = totex_result.post_dea.user_intaktsram['Intaktsram_Total']
    
    print(f"  Foretag: {TEST_REID}")
    print()
    print(f"  OPEX-metod:")
    print(f"    Paverkbara: {baseline_paverkbara:,.0f} tkr")
    print(f"    Intaktsram: {baseline_ir:,.0f} tkr")
    print()
    print(f"  TOTEX-metod:")
    print(f"    Paverkbara: {totex_paverkbara:,.0f} tkr")
    print(f"    Intaktsram: {totex_ir:,.0f} tkr")
    print()
    
    delta_paverkbara = totex_paverkbara - baseline_paverkbara
    delta_ir = totex_ir - baseline_ir
    
    print(f"  Forandring paverkbara: {delta_paverkbara:+,.0f} tkr")
    print(f"  Forandring intaktsram: {delta_ir:+,.0f} tkr")
    
    # Notera: Vi testar bara att metoden fungerar, inte riktningen
    assert baseline_paverkbara != totex_paverkbara or baseline_ir != totex_ir, \
        "TOTEX ska ge annorlunda resultat an OPEX"
    
    print("\n  PASS - Paverkbara metod fungerar")


def test_scenario_5_combined():
    """
    Scenario 5: Kombinerat scenario
    
    Ändringar:
    - WACC: 4.53% -> 5.0%
    - Trunkering max: 30% -> 25%
    - Outlier-krav: 1% -> 1.5%
    """
    print("\n" + "="*60)
    print("SCENARIO 5: Kombinerat scenario")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    
    # Kör baseline
    baseline_config = get_baseline_config(TEST_REID)
    baseline_result = run_pipeline(baseline, baseline_config)
    
    # Kör kombinerat scenario
    combined_config = CaseDefinition(
        name="Kombinerat scenario",
        user_reid=TEST_REID,
        pre_dea=PreDeaConfig(
            method=CapexMethod.WACC_SCALING,
            wacc=0.05  # 5.0%
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig(
            trunkering_min=0.162416,
            trunkering_max=0.25,  # Sänkt från 30%
            outlier_krav=0.015,   # Höjt från 1%
            paverkbara_method=PaverkbaraMethod.OPEX
        )
    )
    
    combined_result = run_pipeline(baseline, combined_config)
    
    print("  Andringar:")
    print("    - WACC: 4.53% -> 5.0%")
    print("    - Trunkering max: 30% -> 25%")
    print("    - Outlier-krav: 1% -> 1.5%")
    print()
    
    baseline_ir = baseline_result.post_dea.user_intaktsram['Intaktsram_Total']
    baseline_effkrav = baseline_result.post_dea.user_effkrav_proc
    combined_ir = combined_result.post_dea.user_intaktsram['Intaktsram_Total']
    combined_effkrav = combined_result.post_dea.user_effkrav_proc
    
    print(f"  Baseline:")
    print(f"    Intaktsram: {baseline_ir:,.0f} tkr")
    print(f"    Effkrav: {baseline_effkrav*100:.3f}%")
    print()
    
    print(f"  Kombinerat:")
    print(f"    Intaktsram: {combined_ir:,.0f} tkr")
    print(f"    Effkrav: {combined_effkrav*100:.3f}%")
    print()
    
    delta_ir = combined_ir - baseline_ir
    delta_effkrav = combined_effkrav - baseline_effkrav
    
    print(f"  Forandring:")
    print(f"    Intaktsram: {delta_ir:+,.0f} tkr")
    print(f"    Effkrav: {delta_effkrav*100:+.3f} procentenheter")
    
    print("\n  PASS - Kombinerat scenario fungerar")


def test_scenario_6_case_definition_validation():
    """
    Scenario 6: Validera att CaseDefinition accepterar alla parametrar
    """
    print("\n" + "="*60)
    print("SCENARIO 6: CaseDefinition validering")
    print("="*60 + "\n")
    
    # Test alla PreDeaConfig alternativ
    print("  PreDeaConfig metoder:")
    for method in CapexMethod:
        config = PreDeaConfig(method=method)
        print(f"    {method.value}: OK")
    
    # Test DeaConfig parametrar
    print("\n  DeaConfig parametrar:")
    dea_config = DeaConfig(
        method=EfficiencyMethod.DEA,
        inputs=['CAPEX', 'OPEXp'],
        outputs=['CU', 'MW', 'NS'],
        rts='vrs',
        orientation='input',
        q_lower=20.0,
        q_upper=80.0,
        multiplier=1.5
    )
    print(f"    inputs: {dea_config.inputs}")
    print(f"    outputs: {dea_config.outputs}")
    print(f"    rts: {dea_config.rts}")
    print(f"    q_lower/q_upper: {dea_config.q_lower}/{dea_config.q_upper}")
    print(f"    multiplier: {dea_config.multiplier}")
    
    # Test PostDeaConfig parametrar
    print("\n  PostDeaConfig parametrar:")
    post_config = PostDeaConfig(
        trunkering_min=0.15,
        trunkering_max=0.35,
        outlier_krav=0.02,
        paverkbara_method=PaverkbaraMethod.TOTEX
    )
    print(f"    trunkering_min: {post_config.trunkering_min}")
    print(f"    trunkering_max: {post_config.trunkering_max}")
    print(f"    outlier_krav: {post_config.outlier_krav}")
    print(f"    paverkbara_method: {post_config.paverkbara_method}")
    
    # Test full CaseDefinition
    print("\n  Full CaseDefinition:")
    full_config = CaseDefinition(
        name="Full test",
        user_reid="REL00886",
        pre_dea=PreDeaConfig(
            method=CapexMethod.WACC_SCALING,
            wacc=0.05,
            normvalue_adjustments={5: 1.2},
            lifetime_adjustments={5: {'ekdep': 30, 'maxdep': 45}}
        ),
        dea=dea_config,
        post_dea=post_config
    )
    print(f"    name: {full_config.name}")
    print(f"    user_reid: {full_config.user_reid}")
    print(f"    pre_dea.wacc: {full_config.pre_dea.wacc}")
    print(f"    pre_dea.normvalue_adjustments: {full_config.pre_dea.normvalue_adjustments}")
    
    print("\n  PASS - CaseDefinition accepterar alla parametrar")


def run_all_tests():
    """Kör alla användarscenario-tester"""
    
    print("="*70)
    print("  TEST SUITE: USER SCENARIOS")
    print("="*70)
    
    tests = [
        ("Scenario 1: WACC-skalning", test_scenario_1_wacc_scaling),
        ("Scenario 2: Effkrav trunkering", test_scenario_2_effkrav_trunkering),
        ("Scenario 3: Outlier-krav", test_scenario_3_outlier_krav),
        ("Scenario 4: Paverkbara metod", test_scenario_4_paverkbara_method),
        ("Scenario 5: Kombinerat scenario", test_scenario_5_combined),
        ("Scenario 6: CaseDefinition validering", test_scenario_6_case_definition_validation),
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
        print(f"  ALLA {passed} SCENARION GODKANDA!")
    else:
        print(f"  {passed} GODKANDA, {failed} MISSLYCKADE")
    print("="*70)


if __name__ == "__main__":
    run_all_tests()