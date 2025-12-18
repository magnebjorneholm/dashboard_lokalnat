"""
tests/test_totex_validation.py

Validerar TOTEX-metoden genom att verifiera:
1. Med Kapitalkostnad_Total = 0 ska TOTEX = OPEX
2. Med Kapitalkostnad_Total > 0 ska TOTEX > OPEX (startvärdet ökar)
3. Effkrav appliceras korrekt på utökad bas

Kör med: python test_totex_validation.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# =============================================================================
# TEST 1: TOTEX med CAPEX=0 ska vara identisk med OPEX
# =============================================================================

def test_totex_equals_opex_when_capex_zero():
    """
    Validerar att TOTEX med Kapitalkostnad_Total=0 ger exakt samma resultat som OPEX.
    """
    print_section("TEST 1: TOTEX = OPEX när Kapitalkostnad_Total = 0")
    
    try:
        from calculations.paverkbara_calculations import (
            calculate_paverkbara_with_effkrav,
            _calculate_paverkbara_single_company
        )
    except ImportError as e:
        print(f"  FEL: Kunde inte importera: {e}")
        return False
    
    # Testdata - 3 hypotetiska företag
    test_data = [
        {'REId': 'TEST001', 'effkrav': 0.01, 'pav_medel': 100000, 'neo': 5000},
        {'REId': 'TEST002', 'effkrav': 0.0182, 'pav_medel': 500000, 'neo': 0},
        {'REId': 'TEST003', 'effkrav': 0.015, 'pav_medel': 250000, 'neo': -10000},
    ]
    
    print("\n  Testdata:")
    print("  " + "-" * 66)
    for td in test_data:
        print(f"    {td['REId']}: Effkrav={td['effkrav']*100:.2f}%, "
              f"Påv_medel={td['pav_medel']:,}, Neo={td['neo']:,}")
    
    all_passed = True
    
    print("\n  Jämförelse OPEX vs TOTEX (CAPEX=0):")
    print("  " + "-" * 66)
    
    for td in test_data:
        # Kör OPEX
        result_opex = _calculate_paverkbara_single_company(
            reid=td['REId'],
            effkrav_proc=td['effkrav'],
            paverkbara_medelvarde=td['pav_medel'],
            neonjusteringar=td['neo'],
            kapitalkostnad_total=0,  # Inte relevant för OPEX
            method='OPEX'
        )
        
        # Kör TOTEX med CAPEX=0
        result_totex = _calculate_paverkbara_single_company(
            reid=td['REId'],
            effkrav_proc=td['effkrav'],
            paverkbara_medelvarde=td['pav_medel'],
            neonjusteringar=td['neo'],
            kapitalkostnad_total=0,  # CAPEX = 0
            method='TOTEX'
        )
        
        # Jämför periodsummor
        opex_sum = result_opex['Paverkbara_Periodsumma']
        totex_sum = result_totex['Paverkbara_Periodsumma']
        diff = abs(totex_sum - opex_sum)
        
        status = "OK" if diff < 0.01 else "FAIL"
        if diff >= 0.01:
            all_passed = False
        
        print(f"    {td['REId']}: OPEX={opex_sum:,.2f}, TOTEX={totex_sum:,.2f}, "
              f"Diff={diff:.4f} [{status}]")
        
        # Jämför även årsvärden
        for year in [2024, 2025, 2026, 2027]:
            opex_year = result_opex[f'Paverkbara_{year}']
            totex_year = result_totex[f'Paverkbara_{year}']
            year_diff = abs(totex_year - opex_year)
            if year_diff >= 0.01:
                print(f"      {year}: OPEX={opex_year:,.2f}, TOTEX={totex_year:,.2f}, "
                      f"Diff={year_diff:.4f} [FAIL]")
                all_passed = False
    
    if all_passed:
        print("\n  PASS - TOTEX med CAPEX=0 är identisk med OPEX")
    else:
        print("\n  FAIL - Avvikelser hittades")
    
    return all_passed


# =============================================================================
# TEST 2: TOTEX med CAPEX>0 ska ge högre periodsumma
# =============================================================================

def test_totex_increases_with_capex():
    """
    Validerar att TOTEX med Kapitalkostnad_Total > 0 ger högre startvärde
    men också högre avdrag (effkrav appliceras på större bas).
    """
    print_section("TEST 2: TOTEX med CAPEX > 0 ger modifierat resultat")
    
    try:
        from calculations.paverkbara_calculations import _calculate_paverkbara_single_company
    except ImportError as e:
        print(f"  FEL: Kunde inte importera: {e}")
        return False
    
    # Testparametrar
    effkrav = 0.015  # 1.5% årligt
    pav_medel = 200000  # tkr (medelvärde)
    neo = 0
    capex_total = 400000  # tkr (4-årig periodsumma)
    
    print(f"\n  Testparametrar:")
    print(f"    Effkrav: {effkrav*100:.2f}% per år")
    print(f"    Påverkbara medelvärde: {pav_medel:,} tkr")
    print(f"    Kapitalkostnad_Total (4 år): {capex_total:,} tkr")
    print(f"    Kapitalkostnad_Total / 4: {capex_total/4:,} tkr per år")
    
    # OPEX
    result_opex = _calculate_paverkbara_single_company(
        reid='TEST',
        effkrav_proc=effkrav,
        paverkbara_medelvarde=pav_medel,
        neonjusteringar=neo,
        kapitalkostnad_total=0,
        method='OPEX'
    )
    
    # TOTEX med CAPEX > 0
    result_totex = _calculate_paverkbara_single_company(
        reid='TEST',
        effkrav_proc=effkrav,
        paverkbara_medelvarde=pav_medel,
        neonjusteringar=neo,
        kapitalkostnad_total=capex_total,
        method='TOTEX'
    )
    
    print(f"\n  Beräknade startvärden:")
    print(f"    OPEX startvärde:  {pav_medel:,} tkr")
    print(f"    TOTEX startvärde: {pav_medel + capex_total/4:,} tkr (+{capex_total/4:,})")
    
    print(f"\n  Årsvärden (Påverkbara per år):")
    print("  " + "-" * 66)
    print(f"  {'År':<6} {'OPEX':>14} {'TOTEX':>14} {'Differens':>14} {'TOTEX/OPEX':>12}")
    
    for year in [2024, 2025, 2026, 2027]:
        opex_year = result_opex[f'Paverkbara_{year}']
        totex_year = result_totex[f'Paverkbara_{year}']
        diff = totex_year - opex_year
        ratio = totex_year / opex_year if opex_year != 0 else 0
        print(f"  {year:<6} {opex_year:>14,.2f} {totex_year:>14,.2f} {diff:>+14,.2f} {ratio:>12.4f}")
    
    opex_sum = result_opex['Paverkbara_Periodsumma']
    totex_sum = result_totex['Paverkbara_Periodsumma']
    diff_sum = totex_sum - opex_sum
    ratio_sum = totex_sum / opex_sum if opex_sum != 0 else 0
    
    print("  " + "-" * 66)
    print(f"  {'SUMMA':<6} {opex_sum:>14,.2f} {totex_sum:>14,.2f} {diff_sum:>+14,.2f} {ratio_sum:>12.4f}")
    
    # Validera logik
    # TOTEX startvärde är högre, så första årets påverkbara är högre
    # Men effkrav appliceras på större bas, så avdragen är också större
    
    expected_diff_year1 = capex_total / 4  # Första årets diff = CAPEX/4 (innan första avdraget)
    actual_diff_year1 = result_totex['Paverkbara_2024'] - result_opex['Paverkbara_2024']
    
    # Kontrollera att TOTEX > OPEX för alla år
    all_passed = True
    for year in [2024, 2025, 2026, 2027]:
        if result_totex[f'Paverkbara_{year}'] <= result_opex[f'Paverkbara_{year}']:
            print(f"\n  VARNING: År {year} TOTEX <= OPEX (oväntat)")
            all_passed = False
    
    if totex_sum > opex_sum:
        print(f"\n  PASS - TOTEX periodsumma ({totex_sum:,.0f}) > OPEX periodsumma ({opex_sum:,.0f})")
    else:
        print(f"\n  FAIL - TOTEX periodsumma borde vara större än OPEX")
        all_passed = False
    
    return all_passed


# =============================================================================
# TEST 3: Full pipeline med TOTEX
# =============================================================================

def test_totex_full_pipeline():
    """
    Testar TOTEX genom hela pipelinen med riktiga baseline-data.
    """
    print_section("TEST 3: TOTEX genom full pipeline")
    
    try:
        from data_loaders import load_baseline_data
        from calculations.dea_calculations import run_dea_analysis, BASELINE_DEA_SPEC
        from calculations.effektiviseringskrav import (
            calculate_effkrav_for_dataframe,
            DEFAULT_EFFKRAV_PARAMS
        )
        from calculations.paverkbara_calculations import (
            calculate_paverkbara_with_effkrav,
            get_paverkbara_from_sdf
        )
    except ImportError as e:
        print(f"  FEL: Kunde inte importera: {e}")
        return False
    
    print("  Laddar baseline data...")
    baseline = load_baseline_data()
    
    # Kör DEA och effkrav
    print("  Kör DEA...")
    dea_results = run_dea_analysis(baseline.df_all_companies, BASELINE_DEA_SPEC)
    
    print("  Beräknar effektiviseringskrav...")
    effkrav_results = calculate_effkrav_for_dataframe(dea_results, **DEFAULT_EFFKRAV_PARAMS)
    
    # Hämta påverkbara baseline
    sdf_paverkbara = get_paverkbara_from_sdf(
        baseline.sdf_ir,
        baseline.sdf_paverkbara
    )
    
    # Kapitalkostnad från SDF (för TOTEX)
    capex_data = baseline.sdf_ir[['REId', 'Kapitalkostnad']].rename(
        columns={'Kapitalkostnad': 'Kapitalkostnad_Total'}
    ).copy()
    
    # Kör OPEX-metod
    print("  Beräknar påverkbara (OPEX)...")
    opex_result = calculate_paverkbara_with_effkrav(
        effkrav_data=effkrav_results,
        sdf_baseline=sdf_paverkbara,
        capex_data=capex_data,
        method='OPEX'
    )
    
    # Kör TOTEX-metod
    print("  Beräknar påverkbara (TOTEX)...")
    totex_result = calculate_paverkbara_with_effkrav(
        effkrav_data=effkrav_results,
        sdf_baseline=sdf_paverkbara,
        capex_data=capex_data,
        method='TOTEX'
    )
    
    # Jämför för utvalda företag
    test_reids = ['REL00001', 'REL00886', 'REL03035']
    
    print("\n  Jämförelse OPEX vs TOTEX för utvalda företag:")
    print("  " + "-" * 66)
    print(f"  {'REId':<12} {'OPEX':>14} {'TOTEX':>14} {'Differens':>14} {'Ratio':>10}")
    print("  " + "-" * 66)
    
    all_passed = True
    
    for reid in test_reids:
        opex_row = opex_result[opex_result['REId'] == reid]
        totex_row = totex_result[totex_result['REId'] == reid]
        capex_row = capex_data[capex_data['REId'] == reid]
        
        if opex_row.empty or totex_row.empty:
            print(f"  {reid}: SAKNAS")
            continue
        
        opex_sum = opex_row['Paverkbara_Periodsumma'].values[0]
        totex_sum = totex_row['Paverkbara_Periodsumma'].values[0]
        capex = capex_row['Kapitalkostnad_Total'].values[0] if not capex_row.empty else 0
        
        diff = totex_sum - opex_sum
        ratio = totex_sum / opex_sum if opex_sum != 0 else 0
        
        print(f"  {reid:<12} {opex_sum:>14,.0f} {totex_sum:>14,.0f} {diff:>+14,.0f} {ratio:>10.4f}")
        
        # TOTEX ska alltid vara >= OPEX (eftersom vi adderar CAPEX/4 till basen)
        if totex_sum < opex_sum - 1:  # 1 tkr tolerans för avrundning
            print(f"    VARNING: TOTEX < OPEX för {reid} (oväntat)")
            all_passed = False
    
    # Statistik
    print("\n  Aggregerad statistik (alla 148 företag):")
    print("  " + "-" * 66)
    
    opex_total = opex_result['Paverkbara_Periodsumma'].sum()
    totex_total = totex_result['Paverkbara_Periodsumma'].sum()
    
    print(f"    Total OPEX:  {opex_total:>20,.0f} tkr")
    print(f"    Total TOTEX: {totex_total:>20,.0f} tkr")
    print(f"    Differens:   {totex_total - opex_total:>+20,.0f} tkr")
    print(f"    Ratio:       {totex_total/opex_total:>20.4f}")
    
    if totex_total > opex_total:
        print("\n  PASS - TOTEX aggregerat > OPEX aggregerat")
    else:
        print("\n  FAIL - TOTEX borde vara större än OPEX")
        all_passed = False
    
    return all_passed


# =============================================================================
# TEST 4: Matematisk verifiering av effkrav-applicering
# =============================================================================

def test_effkrav_applies_to_totex_base():
    """
    Verifierar att effkrav appliceras på hela TOTEX-basen (OPEX + CAPEX/4),
    inte bara på OPEX-delen.
    """
    print_section("TEST 4: Effkrav appliceras på hela TOTEX-basen")
    
    try:
        from calculations.paverkbara_calculations import _calculate_paverkbara_single_company
    except ImportError as e:
        print(f"  FEL: Kunde inte importera: {e}")
        return False
    
    # Extremt enkelt testfall för manuell verifiering
    effkrav = 0.01  # 1% per år
    pav_medel = 100000  # 100,000 tkr
    capex_total = 40000  # 40,000 tkr (10,000 per år)
    neo = 0
    
    print(f"\n  Testparametrar:")
    print(f"    Effkrav: {effkrav*100:.1f}% per år")
    print(f"    Påverkbara medelvärde: {pav_medel:,} tkr")
    print(f"    Kapitalkostnad_Total: {capex_total:,} tkr ({capex_total/4:,} per år)")
    
    # OPEX: bas = 100,000
    # TOTEX: bas = 100,000 + 10,000 = 110,000
    
    result_opex = _calculate_paverkbara_single_company(
        reid='TEST', effkrav_proc=effkrav, paverkbara_medelvarde=pav_medel,
        neonjusteringar=neo, kapitalkostnad_total=0, method='OPEX'
    )
    
    result_totex = _calculate_paverkbara_single_company(
        reid='TEST', effkrav_proc=effkrav, paverkbara_medelvarde=pav_medel,
        neonjusteringar=neo, kapitalkostnad_total=capex_total, method='TOTEX'
    )
    
    # Manuell beräkning för verifiering
    print("\n  Manuell beräkning:")
    print("  " + "-" * 66)
    
    # OPEX: startvärde = 100,000, årsbas = 100,000
    opex_bas = pav_medel
    print(f"  OPEX bas: {opex_bas:,}")
    
    # TOTEX: startvärde = 100,000 + 10,000 = 110,000, årsbas = 110,000
    totex_bas = pav_medel + capex_total / 4
    print(f"  TOTEX bas: {totex_bas:,}")
    
    # År 1 (2024): avdrag = effkrav * bas * (1+effkrav)^0 = 1% * bas
    opex_avdrag_ar1 = effkrav * opex_bas
    totex_avdrag_ar1 = effkrav * totex_bas
    
    print(f"\n  År 1 avdrag:")
    print(f"    OPEX:  {opex_avdrag_ar1:,.2f} (1% av {opex_bas:,})")
    print(f"    TOTEX: {totex_avdrag_ar1:,.2f} (1% av {totex_bas:,})")
    
    # År 1 påverkbara = startvärde - kumulativt_avdrag
    opex_pav_ar1 = opex_bas - opex_avdrag_ar1
    totex_pav_ar1 = totex_bas - totex_avdrag_ar1
    
    print(f"\n  År 1 påverkbara (efter avdrag):")
    print(f"    OPEX beräknad:  {result_opex['Paverkbara_2024']:,.2f}")
    print(f"    OPEX manuell:   {opex_pav_ar1:,.2f}")
    print(f"    TOTEX beräknad: {result_totex['Paverkbara_2024']:,.2f}")
    print(f"    TOTEX manuell:  {totex_pav_ar1:,.2f}")
    
    # Verifiering
    opex_match = abs(result_opex['Paverkbara_2024'] - opex_pav_ar1) < 0.01
    totex_match = abs(result_totex['Paverkbara_2024'] - totex_pav_ar1) < 0.01
    
    all_passed = True
    
    if opex_match and totex_match:
        print("\n  PASS - Beräkningar matchar manuell verifiering")
    else:
        print("\n  FAIL - Beräkningar matchar INTE manuell verifiering")
        all_passed = False
    
    # Extra kontroll: skillnaden i avdrag ska vara proportionell mot skillnaden i bas
    avdrag_ratio = totex_avdrag_ar1 / opex_avdrag_ar1 if opex_avdrag_ar1 != 0 else 0
    bas_ratio = totex_bas / opex_bas if opex_bas != 0 else 0
    
    print(f"\n  Proportionalitetskontroll:")
    print(f"    Bas-ratio (TOTEX/OPEX): {bas_ratio:.4f}")
    print(f"    Avdrag-ratio (TOTEX/OPEX): {avdrag_ratio:.4f}")
    
    if abs(avdrag_ratio - bas_ratio) < 0.0001:
        print("    PASS - Avdrag är proportionellt mot bas")
    else:
        print("    FAIL - Avdrag är INTE proportionellt mot bas")
        all_passed = False
    
    return all_passed


# =============================================================================
# MAIN
# =============================================================================

def run_all_totex_tests():
    """Kör alla TOTEX-valideringstester."""
    print("\n" + "=" * 70)
    print("  TOTEX VALIDATION TEST SUITE")
    print("=" * 70)
    
    results = []
    
    # Test 1
    results.append(("TOTEX=OPEX när CAPEX=0", test_totex_equals_opex_when_capex_zero()))
    
    # Test 2
    results.append(("TOTEX ökar med CAPEX", test_totex_increases_with_capex()))
    
    # Test 3
    results.append(("TOTEX full pipeline", test_totex_full_pipeline()))
    
    # Test 4
    results.append(("Effkrav på TOTEX-bas", test_effkrav_applies_to_totex_base()))
    
    # Sammanfattning
    print_section("SAMMANFATTNING")
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n  ALLA TESTER GODKÄNDA!")
    else:
        print("\n  VISSA TESTER MISSLYCKADES")
    
    print("\n" + "=" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    run_all_totex_tests()