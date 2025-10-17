"""
test_totex_validation.py
Validerar TOTEX-beräkningslogik mot OPEX-metoden

Kör denna fil direkt: python test_totex_validation.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Import från ditt projekt
try:
    from effektiviseringskrav.backend.ir_calculations import calculate_ir_paverkbara_export
    print("✓ Import lyckades från effektiviseringskrav.backend.ir_calculations")
except ImportError as e:
    print(f"✗ Kunde inte importera: {e}")
    print("Kontrollera att du kör från projektets rotkatalog")
    sys.exit(1)


def print_header(text):
    """Printar formaterad header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_subheader(text):
    """Printar formaterad subheader"""
    print(f"\n--- {text} ---")


def test_1_capex_zero():
    """
    TEST 1: CAPEX = 0
    Validerar att TOTEX = OPEX när CAPEX = 0
    """
    print_header("TEST 1: CAPEX = 0 (TOTEX ska vara identisk med OPEX)")
    
    # Skapa test-data
    test_data = pd.DataFrame({
        'REId': ['TEST001'],
        'DMU': [999],
        'Effkrav_proc': [0.02],
        'Företag': ['Test AB']
    })
    
    test_baseline = pd.DataFrame({
        'REId': ['TEST001'],
        'B_raw': [200000.0],
        'Adj': [40000.0],
        'e_base': [0.015]
    })
    
    test_working = pd.DataFrame({
        'REId': ['TEST001'],
        'Kapitalkostnad_Total': [0.0]
    })
    
    print_subheader("Input")
    print(f"DT (B_raw): 200 000 tkr")
    print(f"DU (Adj): 40 000 tkr (total Neon över 4 år)")
    print(f"Effkrav: 2.0%")
    print(f"CAPEX: 0 tkr")
    
    # Kör OPEX
    result_opex, meta_opex = calculate_ir_paverkbara_export(
        dea_result=test_data,
        ir_baseline=test_baseline,
        working_df=test_working,
        method='OPEX'
    )
    
    # Kör TOTEX
    result_totex, meta_totex = calculate_ir_paverkbara_export(
        dea_result=test_data,
        ir_baseline=test_baseline,
        working_df=test_working,
        method='TOTEX'
    )
    
    # Jämför
    opex_target = result_opex['Paverkbara_Target'].iloc[0]
    totex_target = result_totex['Paverkbara_Target'].iloc[0]
    diff = abs(opex_target - totex_target)
    
    print_subheader("Resultat")
    print(f"OPEX target (4 år): {opex_target:,.2f} tkr")
    print(f"TOTEX target (4 år): {totex_target:,.2f} tkr")
    print(f"Skillnad: {diff:.6f} tkr")
    
    # Validera
    passed = diff < 0.01
    if passed:
        print("\n✅ TEST 1 GODKÄND: TOTEX = OPEX när CAPEX = 0")
    else:
        print(f"\n❌ TEST 1 MISSLYCKAD: {diff:.2f} tkr skillnad!")
    
    return passed


def test_2_manual_calculation():
    """
    TEST 2: Manuell beräkning
    Verifierar TOTEX-logik steg-för-steg mot manuell beräkning
    """
    print_header("TEST 2: MANUELL BERÄKNING (verifierar logik)")
    
    # Input
    DT_opex = 200000
    DU_opex = 40000
    CAPEX_4yr = 80000
    e_krav = 0.02
    
    print_subheader("Input")
    print(f"DT (OPEX): {DT_opex:,} tkr")
    print(f"DU (Neon total): {DU_opex:,} tkr")
    print(f"CAPEX (4 år): {CAPEX_4yr:,} tkr")
    print(f"Effkrav: {e_krav*100:.1f}%")
    
    # Manuell beräkning
    Delta_opex = DU_opex / 4
    CAPEX_per_year = CAPEX_4yr / 4
    DT_totex = DT_opex + CAPEX_per_year
    B_totex = DT_totex + Delta_opex
    
    print_subheader("Beräknade värden")
    print(f"Delta (Neon/år): {Delta_opex:,} tkr")
    print(f"CAPEX/år: {CAPEX_per_year:,} tkr")
    print(f"DT (TOTEX): {DT_totex:,} tkr")
    print(f"B (årsbas TOTEX): {B_totex:,} tkr")
    
    # Beräkna år-för-år
    kumulativ_avdrag = 0
    year_values = []
    
    print_subheader("År-för-år beräkning")
    for t in range(1, 5):
        growth = (1 + e_krav) ** (t - 1)
        inkrement = e_krav * B_totex * growth
        kumulativ_avdrag += inkrement
        year_val_totex = DT_totex - kumulativ_avdrag + Delta_opex
        year_values.append(year_val_totex)
        
        print(f"År {2023+t}: Inkrement {inkrement:,.0f}, Kum.avdrag {kumulativ_avdrag:,.0f}, TOTEX {year_val_totex:,.0f} tkr")
    
    total_4yr_manual = sum(year_values)
    nya_opex_manual = total_4yr_manual - CAPEX_4yr
    
    print_subheader("Manuellt resultat")
    print(f"Total TOTEX (4 år): {total_4yr_manual:,.2f} tkr")
    print(f"Total CAPEX (4 år): {CAPEX_4yr:,} tkr")
    print(f"NYA OPEX (4 år): {nya_opex_manual:,.2f} tkr")
    
    # Kör faktisk beräkning
    test_data = pd.DataFrame({
        'REId': ['TEST002'],
        'DMU': [998],
        'Effkrav_proc': [e_krav],
        'Företag': ['Test2 AB']
    })
    
    test_baseline = pd.DataFrame({
        'REId': ['TEST002'],
        'B_raw': [DT_opex],
        'Adj': [DU_opex],
        'e_base': [0.015]
    })
    
    test_working = pd.DataFrame({
        'REId': ['TEST002'],
        'Kapitalkostnad_Total': [CAPEX_4yr]
    })
    
    result_totex, _ = calculate_ir_paverkbara_export(
        dea_result=test_data,
        ir_baseline=test_baseline,
        working_df=test_working,
        method='TOTEX'
    )
    
    actual_target = result_totex['Paverkbara_Target'].iloc[0]
    diff = abs(actual_target - total_4yr_manual)
    
    print_subheader("Jämförelse med faktisk beräkning")
    print(f"Manuellt: {total_4yr_manual:,.2f} tkr")
    print(f"Faktiskt: {actual_target:,.2f} tkr")
    print(f"Skillnad: {diff:.6f} tkr")
    
    passed = diff < 0.1
    if passed:
        print("\n✅ TEST 2 GODKÄND: Manuell beräkning matchar")
    else:
        print(f"\n❌ TEST 2 MISSLYCKAD: {diff:.2f} tkr skillnad!")
    
    return passed


def test_3_capex_change():
    """
    TEST 3: CAPEX-ändring
    Validerar att OPEX omberäknas korrekt när CAPEX ändras
    """
    print_header("TEST 3: CAPEX-ÄNDRING (OPEX ska kompensera)")
    
    # Initial scenario
    DT_opex = 200000
    DU_opex = 40000
    e_krav = 0.02
    initial_capex = 80000
    
    print_subheader("Scenario 1: Initial CAPEX")
    print(f"DT (OPEX): {DT_opex:,} tkr")
    print(f"DU (Neon): {DU_opex:,} tkr")
    print(f"CAPEX: {initial_capex:,} tkr")
    print(f"Effkrav: {e_krav*100:.1f}%")
    
    test_data = pd.DataFrame({
        'REId': ['TEST003'],
        'DMU': [997],
        'Effkrav_proc': [e_krav],
        'Företag': ['Test3 AB']
    })
    
    test_baseline = pd.DataFrame({
        'REId': ['TEST003'],
        'B_raw': [DT_opex],
        'Adj': [DU_opex],
        'e_base': [0.015]
    })
    
    # Kör med initial CAPEX
    test_working_1 = pd.DataFrame({
        'REId': ['TEST003'],
        'Kapitalkostnad_Total': [initial_capex]
    })
    
    result_1, _ = calculate_ir_paverkbara_export(
        dea_result=test_data,
        ir_baseline=test_baseline,
        working_df=test_working_1,
        method='TOTEX'
    )
    
    target_totex_1 = result_1['Paverkbara_Target'].iloc[0]
    target_opex_1 = target_totex_1 - initial_capex
    
    print(f"\nResultat scenario 1:")
    print(f"Target TOTEX: {target_totex_1:,.2f} tkr")
    print(f"Target OPEX: {target_opex_1:,.2f} tkr (TOTEX - CAPEX)")
    
    # Ändra CAPEX
    new_capex = 100000
    capex_change = new_capex - initial_capex
    
    print_subheader("Scenario 2: Ökad CAPEX")
    print(f"Ny CAPEX: {new_capex:,} tkr")
    print(f"Ökning: +{capex_change:,} tkr")
    
    test_working_2 = pd.DataFrame({
        'REId': ['TEST003'],
        'Kapitalkostnad_Total': [new_capex]
    })
    
    result_2, _ = calculate_ir_paverkbara_export(
        dea_result=test_data,
        ir_baseline=test_baseline,
        working_df=test_working_2,
        method='TOTEX'
    )
    
    target_totex_2 = result_2['Paverkbara_Target'].iloc[0]
    target_opex_2 = target_totex_2 - new_capex
    
    print(f"\nResultat scenario 2:")
    print(f"Target TOTEX: {target_totex_2:,.2f} tkr")
    print(f"Target OPEX: {target_opex_2:,.2f} tkr (TOTEX - CAPEX)")
    
    # Validering
    totex_diff = abs(target_totex_2 - target_totex_1)
    opex_change = target_opex_1 - target_opex_2
    expected_opex_change = capex_change
    opex_compensation_error = abs(opex_change - expected_opex_change)
    
    print_subheader("Validering")
    print(f"TOTEX förändring: {totex_diff:.2f} tkr (ska vara ~0)")
    print(f"OPEX förändring: {opex_change:,.2f} tkr")
    print(f"Förväntad OPEX-minskning: {expected_opex_change:,} tkr")
    print(f"Kompensationsfel: {opex_compensation_error:.2f} tkr")
    
    passed = totex_diff < 1.0 and opex_compensation_error < 1.0
    
    if passed:
        print("\n✅ TEST 3 GODKÄND: OPEX kompenserar korrekt för CAPEX-ändring")
        print("   → TOTEX förblir konstant")
        print("   → OPEX minskar med samma belopp som CAPEX ökar")
    else:
        print(f"\n❌ TEST 3 MISSLYCKAD:")
        if totex_diff >= 1.0:
            print(f"   → TOTEX ändrades med {totex_diff:.2f} tkr (ska vara konstant)")
        if opex_compensation_error >= 1.0:
            print(f"   → OPEX-kompensation fel med {opex_compensation_error:.2f} tkr")
    
    return passed


def run_all_tests():
    """Kör alla valideringstester"""
    print("\n" + "█" * 70)
    print("  VALIDERING AV TOTEX-BERÄKNINGSLOGIK")
    print("█" * 70)
    
    results = []
    
    # Test 1
    try:
        results.append(('Test 1: CAPEX = 0', test_1_capex_zero()))
    except Exception as e:
        print(f"\n❌ Test 1 kraschade: {e}")
        results.append(('Test 1: CAPEX = 0', False))
    
    # Test 2
    try:
        results.append(('Test 2: Manuell beräkning', test_2_manual_calculation()))
    except Exception as e:
        print(f"\n❌ Test 2 kraschade: {e}")
        results.append(('Test 2: Manuell beräkning', False))
    
    # Test 3
    try:
        results.append(('Test 3: CAPEX-ändring', test_3_capex_change()))
    except Exception as e:
        print(f"\n❌ Test 3 kraschade: {e}")
        results.append(('Test 3: CAPEX-ändring', False))
    
    # Sammanfattning
    print_header("SAMMANFATTNING")
    
    all_passed = all(result[1] for result in results)
    
    for test_name, passed in results:
        status = "✅ GODKÄND" if passed else "❌ MISSLYCKAD"
        print(f"{status}  {test_name}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALLA TESTER GODKÄNDA - TOTEX-LOGIKEN ÄR KORREKT!")
    else:
        failed_count = sum(1 for _, passed in results if not passed)
        print(f"⚠️  {failed_count} av {len(results)} tester misslyckades")
    print("=" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)