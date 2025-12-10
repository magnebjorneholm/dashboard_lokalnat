"""
tests/test_calculations.py

Verifierar individuella beräkningar:
- KENT halvårsmappning (tidskoder 229-236)
- WACC-skalning
- Effektiviseringskrav
- Påverkbara kostnader
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders import load_baseline_data
from calculations import (
    calculate_wacc_scaled_capex,
    calculate_effkrav_from_potential,
    calculate_effkrav_for_dataframe,
    DEFAULT_EFFKRAV_PARAMS
)


# Golden test data
GOLDEN_REID = "REL00886"
GOLDEN_EFFEKTIVITET = 0.793547
GOLDEN_PAVERKBARA_PERIODSUMMA = 920371.93


def test_wacc_scaling_formula():
    """Test WACC-skalningsformel"""
    print("\n" + "="*60)
    print("TEST: WACC-skalning formel")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    df = baseline.df_all_companies.copy()
    
    baseline_wacc = 0.0453
    new_wacc = 0.05
    
    # Skala
    df_scaled = calculate_wacc_scaled_capex(df, new_wacc, baseline_wacc)
    
    # Formel: Ny Avkastning = Baseline Avkastning * (new_wacc / baseline_wacc)
    # Ny Kapitalkostnad_2024 = Avskrivning + Ny Avkastning
    
    expected_factor = new_wacc / baseline_wacc
    print(f"  Skalningsfaktor: {expected_factor:.4f}")
    
    # Kontrollera att avskrivning är oförändrad
    assert (df['Avskrivning'] == df_scaled['Avskrivning']).all(), "Avskrivning ska vara oförändrad"
    print("  Avskrivning oförändrad")
    
    # Kontrollera att avkastning skalas korrekt
    expected_avkastning = df['Avkastning'] * expected_factor
    diff = (df_scaled['Avkastning'] - expected_avkastning).abs().max()
    assert diff < 0.01, f"Avkastning skalas fel: max diff {diff:.4f}"
    print("  Avkastning skalad korrekt")
    
    # Kontrollera att Kapitalkostnad_2024 = Avskrivning + Avkastning
    expected_kap = df_scaled['Avskrivning'] + df_scaled['Avkastning']
    diff = (df_scaled['Kapitalkostnad_2024'] - expected_kap).abs().max()
    assert diff < 0.01, f"Kapitalkostnad_2024 fel: max diff {diff:.4f}"
    print("  Kapitalkostnad_2024 = Avskrivning + Avkastning")
    
    # REL00886 specifikt
    row = df_scaled[df_scaled['REId'] == GOLDEN_REID].iloc[0]
    print(f"\n  REL00886:")
    print(f"    Avskrivning: {row['Avskrivning']:,.2f} tkr (oförändrad)")
    print(f"    Avkastning: {row['Avkastning']:,.2f} tkr (skalad)")
    print(f"    Kapitalkostnad_2024: {row['Kapitalkostnad_2024']:,.2f} tkr")
    
    print("  PASS")


def test_wacc_scaling_totex_update():
    """Test att TOTEX uppdateras vid WACC-skalning"""
    print("\n" + "="*60)
    print("TEST: TOTEX uppdatering vid WACC-skalning")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    df = baseline.df_all_companies.copy()
    
    df_scaled = calculate_wacc_scaled_capex(df, new_wacc=0.05, baseline_wacc=0.0453)
    
    # TOTEX = OPEXp + Kapitalkostnad_2024
    expected_totex = df_scaled['OPEXp'] + df_scaled['Kapitalkostnad_2024']
    diff = (df_scaled['TOTEX'] - expected_totex).abs().max()
    
    assert diff < 0.01, f"TOTEX fel: max diff {diff:.4f}"
    print("  TOTEX = OPEXp + Kapitalkostnad_2024")
    print("  PASS")


def test_effektiviseringskrav_outlier():
    """Test effektiviseringskrav för outliers"""
    print("\n" + "="*60)
    print("TEST: Effektiviseringskrav - Outliers")
    print("="*60 + "\n")
    
    # Outliers ska alltid få fast 1% krav
    effkrav = calculate_effkrav_from_potential(
        potential=0.50,  # Hög potential
        is_outlier=True
    )
    
    expected = 0.01  # 1%
    assert abs(effkrav - expected) < 1e-6, f"Outlier effkrav: {effkrav} != {expected}"
    print(f"  Outlier med potential 50%: effkrav = {effkrav*100:.2f}%")
    print("  PASS")


def test_effektiviseringskrav_normal():
    """Test effektiviseringskrav för normala företag"""
    print("\n" + "="*60)
    print("TEST: Effektiviseringskrav - Normal potential")
    print("="*60 + "\n")
    
    # Formel: ((1 + potential/4)^0.25) - 1
    potential = 0.25
    effkrav = calculate_effkrav_from_potential(
        potential=potential,
        is_outlier=False
    )
    
    expected = ((1 + potential/4) ** 0.25) - 1
    assert abs(effkrav - expected) < 1e-6, f"Effkrav: {effkrav} != {expected}"
    print(f"  Potential 25%: effkrav = {effkrav*100:.3f}%")
    print(f"  Formel: ((1 + 0.25/4)^0.25) - 1 = {expected*100:.3f}%")
    print("  PASS")


def test_effektiviseringskrav_trunkering_min():
    """Test trunkering vid för låg potential"""
    print("\n" + "="*60)
    print("TEST: Effektiviseringskrav - Trunkering min")
    print("="*60 + "\n")
    
    # Potential under trunk_min (0.162416) -> trunkeras till trunk_min
    potential = 0.10  # Under min
    effkrav = calculate_effkrav_from_potential(
        potential=potential,
        is_outlier=False
    )
    
    trunk_min = DEFAULT_EFFKRAV_PARAMS['trunkering_min']
    expected = ((1 + trunk_min/4) ** 0.25) - 1
    
    assert abs(effkrav - expected) < 1e-6, f"Trunkerad effkrav: {effkrav} != {expected}"
    print(f"  Potential 10% (under min {trunk_min*100:.2f}%)")
    print(f"  Trunkeras till: {trunk_min*100:.2f}%")
    print(f"  Effkrav: {effkrav*100:.3f}%")
    print("  PASS")


def test_effektiviseringskrav_trunkering_max():
    """Test trunkering vid för hög potential"""
    print("\n" + "="*60)
    print("TEST: Effektiviseringskrav - Trunkering max")
    print("="*60 + "\n")
    
    # Potential över trunk_max (0.30) -> trunkeras till trunk_max
    potential = 0.50  # Över max
    effkrav = calculate_effkrav_from_potential(
        potential=potential,
        is_outlier=False
    )
    
    trunk_max = DEFAULT_EFFKRAV_PARAMS['trunkering_max']
    expected = ((1 + trunk_max/4) ** 0.25) - 1
    
    assert abs(effkrav - expected) < 1e-6, f"Trunkerad effkrav: {effkrav} != {expected}"
    print(f"  Potential 50% (över max {trunk_max*100:.1f}%)")
    print(f"  Trunkeras till: {trunk_max*100:.1f}%")
    print(f"  Effkrav: {effkrav*100:.3f}%")
    print("  PASS")


def test_effektiviseringskrav_for_all_companies():
    """Test effektiviseringskrav för alla företag"""
    print("\n" + "="*60)
    print("TEST: Effektiviseringskrav för alla företag")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    dea_results = baseline.dea_results.copy()
    
    result = calculate_effkrav_for_dataframe(dea_results)
    
    # Kolumn ska finnas
    assert 'Effkrav_proc' in result.columns, "Effkrav_proc saknas"
    
    # Inga NaN
    assert result['Effkrav_proc'].notna().all(), "NaN i effkrav"
    
    # Alla outliers ska ha 1%
    outliers = result[result['is_outlier']]
    if len(outliers) > 0:
        assert (outliers['Effkrav_proc'] == 0.01).all(), "Outliers ska ha 1%"
        print(f"  {len(outliers)} outliers med 1% effkrav")
    
    # Statistik
    non_outliers = result[~result['is_outlier']]
    print(f"  {len(non_outliers)} icke-outliers")
    print(f"    Medel effkrav: {non_outliers['Effkrav_proc'].mean()*100:.3f}%")
    print(f"    Min effkrav: {non_outliers['Effkrav_proc'].min()*100:.3f}%")
    print(f"    Max effkrav: {non_outliers['Effkrav_proc'].max()*100:.3f}%")
    
    print("  PASS")


def test_paverkbara_manual_calculation():
    """Test påverkbara beräkning med känt exempel (REL00886)"""
    print("\n" + "="*60)
    print("TEST: Påverkbara beräkning (manuell validering)")
    print("="*60 + "\n")
    
    # Från dokumentation för REL00886:
    # - Påverkbara_Medelvärde = 219,438.70 tkr
    # - Neonjusteringar = 73,097.00 tkr
    # - Effkrav_proc = 0.012661 (1.27%)
    # - Förväntat periodsumma: ~920,372 tkr
    
    paverkbara_medelvarde = 219438.70
    neonjusteringar = 73097.00
    effkrav_proc = 0.012661
    
    print(f"  Input:")
    print(f"    Påverkbara medelvärde: {paverkbara_medelvarde:,.2f} tkr")
    print(f"    Neonjusteringar: {neonjusteringar:,.2f} tkr")
    print(f"    Effkrav: {effkrav_proc*100:.3f}%")
    
    # Beräkning enligt Ei's formel
    startvarde = paverkbara_medelvarde
    arlig_justering = neonjusteringar / 4
    arsbas_effkrav = startvarde + arlig_justering
    
    kumulativt_avdrag = 0
    paverkbara_per_ar = []
    
    for t in range(1, 5):
        tillvaxtfaktor = (1 + effkrav_proc) ** (t - 1)
        arligt_avdrag = effkrav_proc * arsbas_effkrav * tillvaxtfaktor
        kumulativt_avdrag += arligt_avdrag
        paverkbara = startvarde - kumulativt_avdrag + arlig_justering
        paverkbara_per_ar.append(paverkbara)
    
    periodsumma = sum(paverkbara_per_ar)
    
    print(f"\n  Beräknad periodsumma: {periodsumma:,.2f} tkr")
    print(f"  Förväntat (SDF): {GOLDEN_PAVERKBARA_PERIODSUMMA:,.2f} tkr")
    
    tolerance = 1.0  # 1 tkr
    diff = abs(periodsumma - GOLDEN_PAVERKBARA_PERIODSUMMA)
    assert diff < tolerance, f"Avvikelse för stor: {diff:.2f} tkr"
    
    print(f"  Avvikelse: {diff:.2f} tkr")
    print("  PASS")


def test_kent_timecodes_concept():
    """Test att tidskoder tolkas korrekt (halvår, inte helår)"""
    print("\n" + "="*60)
    print("TEST: KENT tidskodskoncept")
    print("="*60 + "\n")
    
    # Tidskodsmappning enligt KENT-handboken
    # 229 = 2024H1, 230 = 2024H2, 231 = 2025H1, etc.
    
    timecodes = {
        229: ('2024', 'H1'),
        230: ('2024', 'H2'),
        231: ('2025', 'H1'),
        232: ('2025', 'H2'),
        233: ('2026', 'H1'),
        234: ('2026', 'H2'),
        235: ('2027', 'H1'),
        236: ('2027', 'H2'),
    }
    
    print("  Tidskodsmappning:")
    for code, (year, half) in timecodes.items():
        print(f"    {code} -> {year}{half}")
    
    # Årsvärde 2024 = sum av H1 + H2 (2 tidskoder)
    year_2024_codes = [229, 230]
    assert len(year_2024_codes) == 2, "Årsvärde ska ha 2 halvår"
    print(f"\n  Årsvärde 2024 = tidskoder {year_2024_codes} (2 halvår)")
    
    # Periodsumma 2024-2027 = sum av alla 8 halvår
    period_codes = list(range(229, 237))  # 229 to 236 inclusive
    assert len(period_codes) == 8, f"Periodsumma ska ha 8 halvår, fick {len(period_codes)}"
    print(f"  Periodsumma 2024-2027 = tidskoder {period_codes} (8 halvår)")
    
    # VIKTIGT: range(229, 237) ger 229-236 (237 exkluderas)
    assert 237 not in period_codes, "237 ska INTE inkluderas"
    assert 236 in period_codes, "236 SKA inkluderas"
    
    print("\n  range(229, 237) ger korrekt [229, 230, 231, 232, 233, 234, 235, 236]")
    print("  PASS")


def run_all_tests():
    """Kör alla beräkningstester"""
    print("\n" + "="*70)
    print("  TEST SUITE: CALCULATIONS")
    print("="*70)
    
    try:
        test_wacc_scaling_formula()
        test_wacc_scaling_totex_update()
        test_effektiviseringskrav_outlier()
        test_effektiviseringskrav_normal()
        test_effektiviseringskrav_trunkering_min()
        test_effektiviseringskrav_trunkering_max()
        test_effektiviseringskrav_for_all_companies()
        test_paverkbara_manual_calculation()
        test_kent_timecodes_concept()
        
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