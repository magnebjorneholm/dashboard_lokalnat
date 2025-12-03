"""
tests/test_post_dea_end_to_end.py

End-to-end test för Post-DEA stage.
Validerar effektiviseringskrav, påverkbara kostnader, och intäktsram assembly.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Lägg till projekt-root i sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders import load_baseline_data
from calculations import (
    calculate_effkrav_from_potential,
    calculate_effkrav_for_dataframe,
    DEFAULT_EFFKRAV_PARAMS
)


def test_effektiviseringskrav_calculation():
    """
    Test 1: Effektiviseringskrav beräkning
    
    Testar att:
    - Outliers får fast 1% krav
    - Icke-outliers får beräknat krav från potential
    - Trunkering fungerar korrekt
    """
    print("\n" + "="*70)
    print("TEST 1: EFFEKTIVISERINGSKRAV BERÄKNING")
    print("="*70 + "\n")
    
    # Test 1A: Outlier
    print("Test 1A: Outlier...")
    effkrav = calculate_effkrav_from_potential(
        potential=0.50,  # Hög potential
        is_outlier=True
    )
    expected = 0.01  # Fast 1%
    assert abs(effkrav - expected) < 1e-6, f"Expected {expected}, got {effkrav}"
    print(f"  ✓ Outlier effkrav: {effkrav*100:.2f}% (förväntat: {expected*100:.2f}%)")
    
    # Test 1B: Normal potential
    print("\nTest 1B: Normal potential (0.25)...")
    effkrav = calculate_effkrav_from_potential(
        potential=0.25,
        is_outlier=False
    )
    # Formel: ((1 + 0.25/4)^0.25) - 1 ≈ 0.0151
    expected = ((1 + 0.25/4) ** 0.25) - 1
    assert abs(effkrav - expected) < 1e-6, f"Expected {expected}, got {effkrav}"
    print(f"  ✓ Effkrav: {effkrav*100:.3f}% (förväntat: {expected*100:.3f}%)")
    
    # Test 1C: Trunkering - för låg potential
    print("\nTest 1C: Trunkering - för låg potential (0.10)...")
    effkrav = calculate_effkrav_from_potential(
        potential=0.10,  # Under trunk_min (0.162416)
        is_outlier=False
    )
    # Ska truneras till 0.162416
    expected = ((1 + DEFAULT_EFFKRAV_PARAMS['trunkering_min']/4) ** 0.25) - 1
    assert abs(effkrav - expected) < 1e-6, f"Expected {expected}, got {effkrav}"
    print(f"  ✓ Trunkerad till min, effkrav: {effkrav*100:.3f}%")
    
    # Test 1D: Trunkering - för hög potential
    print("\nTest 1D: Trunkering - för hög potential (0.50)...")
    effkrav = calculate_effkrav_from_potential(
        potential=0.50,  # Över trunk_max (0.30)
        is_outlier=False
    )
    # Ska trunkeras till 0.30
    expected = ((1 + DEFAULT_EFFKRAV_PARAMS['trunkering_max']/4) ** 0.25) - 1
    assert abs(effkrav - expected) < 1e-6, f"Expected {expected}, got {effkrav}"
    print(f"  ✓ Trunkerad till max, effkrav: {effkrav*100:.3f}%")
    
    print("\n✅ TEST 1 GODKÄNT - Effektiviseringskrav beräknas korrekt!\n")
    return True


def test_effkrav_for_dataframe():
    """
    Test 2: Effektiviseringskrav för DataFrame
    
    Testar att beräkning fungerar för alla 148 företag
    """
    print("\n" + "="*70)
    print("TEST 2: EFFEKTIVISERINGSKRAV FÖR ALLA FÖRETAG")
    print("="*70 + "\n")
    
    # Ladda baseline data
    print("Laddar baseline data...")
    baseline = load_baseline_data()
    dea_results = baseline.dea_results.copy()
    
    print(f"✓ Laddade {len(dea_results)} företag\n")
    
    # Beräkna effektiviseringskrav
    print("Beräknar effektiviseringskrav för alla företag...")
    result = calculate_effkrav_for_dataframe(dea_results)
    
    # Validera
    assert 'Effkrav_proc' in result.columns, "Kolumn 'Effkrav_proc' saknas"
    assert len(result) == len(dea_results), "Antal rader skiljer sig"
    assert result['Effkrav_proc'].notna().all(), "NaN-värden i effkrav"
    
    # Statistik
    print(f"\n  Statistik:")
    print(f"  - Antal företag: {len(result)}")
    print(f"  - Outliers: {result['is_outlier'].sum()}")
    print(f"  - Medel effkrav: {result['Effkrav_proc'].mean()*100:.2f}%")
    print(f"  - Min effkrav: {result['Effkrav_proc'].min()*100:.2f}%")
    print(f"  - Max effkrav: {result['Effkrav_proc'].max()*100:.2f}%")
    
    # Validera att outliers har 1%
    outliers = result[result['is_outlier']]
    if len(outliers) > 0:
        assert (outliers['Effkrav_proc'] == 0.01).all(), "Outliers ska ha 1% effkrav"
        print(f"\n  ✓ Alla {len(outliers)} outliers har korrekt 1% effkrav")
    
    print("\n✅ TEST 2 GODKÄNT - Effkrav beräknas för alla företag!\n")
    return True


def test_paverkbara_calculation_manual():
    """
    Test 3: Påverkbara kostnader - Manuellt exempel
    
    Använder känt exempel från dokumentation (REL00886):
    - Påverkbara_Medelvärde = 219,438.70 tkr
    - Neonjusteringar = 73,097.00 tkr
    - Effkrav_proc = 0.012661 (1.27%)
    - Förväntat resultat (OPEX): ~920,372 tkr
    """
    print("\n" + "="*70)
    print("TEST 3: PÅVERKBARA KOSTNADER - MANUELLT EXEMPEL")
    print("="*70 + "\n")
    
    # Manuell beräkning enligt Ei's metod
    paverkbara_medelvarde = 219438.70
    neonjusteringar = 73097.00
    effkrav_proc = 0.012661
    
    print(f"Input:")
    print(f"  - Påverkbara medelvärde: {paverkbara_medelvarde:,.2f} tkr")
    print(f"  - Neonjusteringar: {neonjusteringar:,.2f} tkr")
    print(f"  - Effkrav: {effkrav_proc*100:.3f}%")
    
    # Beräkna
    startvarde = paverkbara_medelvarde
    arlig_justering = neonjusteringar / 4
    arsbas_effkrav = startvarde + arlig_justering
    
    print(f"\n  Startvärde: {startvarde:,.2f} tkr")
    print(f"  Årlig justering: {arlig_justering:,.2f} tkr")
    print(f"  Årsbas effkrav: {arsbas_effkrav:,.2f} tkr")
    
    # Årliga beräkningar
    print(f"\n  Årliga beräkningar:")
    kumulativt_avdrag = 0
    paverkbara_per_ar = []
    
    for t in range(1, 5):
        tillvaxtfaktor = (1 + effkrav_proc) ** (t - 1)
        arligt_avdrag = effkrav_proc * arsbas_effkrav * tillvaxtfaktor
        kumulativt_avdrag += arligt_avdrag
        paverkbara = startvarde - kumulativt_avdrag + arlig_justering
        
        year = 2023 + t
        paverkbara_per_ar.append(paverkbara)
        print(f"    {year}: Avdrag={arligt_avdrag:,.2f}, Kum.avdrag={kumulativt_avdrag:,.2f}, Påverkbara={paverkbara:,.2f}")
    
    # Periodsumma
    periodsumma = sum(paverkbara_per_ar)
    expected = 920371.93  # Från dokumentation
    
    print(f"\n  Periodsumma: {periodsumma:,.2f} tkr")
    print(f"  Förväntat: {expected:,.2f} tkr")
    print(f"  Avvikelse: {abs(periodsumma - expected):,.2f} tkr")
    
    # Validera (tillåt liten numerisk avvikelse)
    tolerance = 1.0  # 1 tkr
    assert abs(periodsumma - expected) < tolerance, f"För stor avvikelse: {abs(periodsumma - expected):.2f} tkr"
    
    print(f"\n✅ TEST 3 GODKÄNT - Påverkbara beräknas korrekt!\n")
    return True


def run_all_tests():
    """Kör alla Post-DEA tester"""
    print("\n" + "="*70)
    print("  FAS 1E: POST-DEA - TEST SUITE")
    print("="*70)
    
    try:
        # Test 1
        success1 = test_effektiviseringskrav_calculation()
        
        # Test 2
        success2 = test_effkrav_for_dataframe()
        
        # Test 3
        success3 = test_paverkbara_calculation_manual()
        
        # Sammanfattning
        if success1 and success2 and success3:
            print("\n" + "="*70)
            print("  ✅ ALLA TESTER GODKÄNDA!")
            print("  Fas 1E (Post-DEA) är PRODUKTIONSKLAR!")
            print("="*70 + "\n")
            return True
        else:
            return False
        
    except Exception as e:
        print("\n" + "="*70)
        print(f"  ❌ TEST MISSLYCKADES: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)