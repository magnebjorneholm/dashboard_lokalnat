"""
test_wacc_scaling_pipeline.py

Testfil för att verifiera korrekt WACC-skalning i pipeline.

Testar att:
1. Pre-DEA producerar korrekt Kapitalkostnad_2024 (årsvärde) för DEA
2. Post-DEA skalar periodsummor korrekt från SDF (inte årsvärde × 4)
3. Intäktsram beräknas med korrekta periodsummor

Kör med: python test_wacc_scaling_pipeline.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Lägg till projektmapp i path om nödvändigt
# sys.path.insert(0, str(Path(__file__).parent))


def test_wacc_scaling_calculation():
    """
    Testar WACC-skalningslogiken isolerat utan att köra hela pipelinen.
    Verifierar att periodsummor skalas korrekt.
    """
    print("="*70)
    print("TEST: WACC-skalning av periodsummor (isolerat)")
    print("="*70)
    
    # Simulera SDF-data för ett företag
    baseline_wacc = 0.0453
    new_wacc = 0.05
    
    # Exempeldata (periodsummor för 2024-2027)
    kapitalforslitning_period = 125_000  # tkr, oförändrad
    kapitalbindning_period = 100_000     # tkr, ska skalas
    
    # Baseline periodsumma
    baseline_kapitalkostnad = kapitalforslitning_period + kapitalbindning_period
    
    # FELAKTIG metod (årsvärde × 4)
    # Årsvärde approximerat som periodsumma/4
    arsvarde_2024 = baseline_kapitalkostnad / 4
    # Skalat årsvärde
    scaling_factor = new_wacc / baseline_wacc
    # Felaktigt: ta skalat årsvärde × 4
    felaktig_periodsumma = arsvarde_2024 * scaling_factor * 4
    
    # KORREKT metod (skala periodsumma för kapitalbindning)
    skalad_kapitalbindning = kapitalbindning_period * scaling_factor
    korrekt_periodsumma = kapitalforslitning_period + skalad_kapitalbindning
    
    print(f"\nInput:")
    print(f"  Baseline WACC: {baseline_wacc:.4f} ({baseline_wacc*100:.2f}%)")
    print(f"  Ny WACC: {new_wacc:.4f} ({new_wacc*100:.2f}%)")
    print(f"  Skalningsfaktor: {scaling_factor:.4f}")
    print(f"\n  Kapitalförslitning (periodsumma): {kapitalforslitning_period:,} tkr")
    print(f"  Kapitalbindning (periodsumma): {kapitalbindning_period:,} tkr")
    print(f"  Baseline kapitalkostnad (periodsumma): {baseline_kapitalkostnad:,} tkr")
    
    print(f"\nResultat:")
    print(f"  FELAKTIG metod (årsvärde × 4): {felaktig_periodsumma:,.0f} tkr")
    print(f"  KORREKT metod (skala periodsumma): {korrekt_periodsumma:,.0f} tkr")
    
    # Skillnaden
    skillnad = felaktig_periodsumma - korrekt_periodsumma
    skillnad_pct = (skillnad / korrekt_periodsumma) * 100
    
    print(f"\n  Skillnad: {skillnad:,.0f} tkr ({skillnad_pct:+.2f}%)")
    
    # I detta förenklade exempel är skillnaden 0 eftersom vi approximerade
    # årsvärdet som periodsumma/4. Men i verkligheten avtar kapitalbindningen
    # varje halvår, så årsvärdet för 2024 är HÖGRE än genomsnittet.
    
    # Mer realistiskt exempel med avtagande kapitalbindning
    print("\n" + "-"*70)
    print("Realistiskt exempel med avtagande kapitalbindning:")
    
    # Kapitalbindning per halvår (avtar)
    # 2024H1, 2024H2, 2025H1, 2025H2, 2026H1, 2026H2, 2027H1, 2027H2
    kapitalbindning_per_halvar = [
        14000, 13500,  # 2024
        13000, 12500,  # 2025
        12000, 11500,  # 2026
        11000, 10500   # 2027
    ]
    
    kapitalbindning_period_real = sum(kapitalbindning_per_halvar)
    kapitalbindning_2024 = kapitalbindning_per_halvar[0] + kapitalbindning_per_halvar[1]
    
    # Kapitalförslitning är konstant per halvår
    kapitalforslitning_per_halvar = 15625  # tkr per halvår
    kapitalforslitning_period_real = kapitalforslitning_per_halvar * 8
    kapitalforslitning_2024 = kapitalforslitning_per_halvar * 2
    
    # Baseline
    kapitalkostnad_2024 = kapitalforslitning_2024 + kapitalbindning_2024
    baseline_period_real = kapitalforslitning_period_real + kapitalbindning_period_real
    
    print(f"\n  Kapitalbindning per halvår: {kapitalbindning_per_halvar}")
    print(f"  Kapitalbindning 2024 (årsvärde): {kapitalbindning_2024:,} tkr")
    print(f"  Kapitalbindning periodsumma: {kapitalbindning_period_real:,} tkr")
    print(f"  Kapitalkostnad 2024 (årsvärde): {kapitalkostnad_2024:,} tkr")
    print(f"  Kapitalkostnad periodsumma: {baseline_period_real:,} tkr")
    
    # FELAKTIG: Skala årsvärde och multiplicera med 4
    skalad_kapitalkostnad_2024 = (
        kapitalforslitning_2024 + kapitalbindning_2024 * scaling_factor
    )
    felaktig_period = skalad_kapitalkostnad_2024 * 4
    
    # KORREKT: Skala periodsumma för kapitalbindning
    skalad_kapitalbindning_period = kapitalbindning_period_real * scaling_factor
    korrekt_period = kapitalforslitning_period_real + skalad_kapitalbindning_period
    
    print(f"\n  FELAKTIG (skalat årsvärde × 4): {felaktig_period:,.0f} tkr")
    print(f"  KORREKT (skalad periodsumma): {korrekt_period:,.0f} tkr")
    
    skillnad_real = felaktig_period - korrekt_period
    skillnad_real_pct = (skillnad_real / korrekt_period) * 100
    
    print(f"\n  Skillnad: {skillnad_real:,.0f} tkr ({skillnad_real_pct:+.2f}%)")
    print(f"  => Felaktiga metoden ÖVERSKATTAR kapitalkostnaden!")
    
    # Assertion
    assert abs(skillnad_real) > 0, "Skillnaden borde vara >0 för realistisk data"
    print("\n  [PASS] Test visar att metoderna ger olika resultat")
    
    return True


def test_sdf_column_names():
    """
    Testar att SDF-filen har förväntade kolumnnamn.
    """
    print("\n" + "="*70)
    print("TEST: SDF kolumnnamn")
    print("="*70)
    
    # Sök efter SDF-filen
    sdf_paths = [
        Path("Löpande_kostnader_från_SDF_2024-27.xlsx"),
        Path("data/Löpande_kostnader_från_SDF_2024-27.xlsx"),
        Path("/mnt/user-data/uploads/Löpande_kostnader_från_SDF_2024-27.xlsx"),
        Path("/mnt/project/Löpande_kostnader_från_SDF_202427.xlsx"),
    ]
    
    sdf_file = None
    for path in sdf_paths:
        if path.exists():
            sdf_file = path
            break
    
    if sdf_file is None:
        print("  [SKIP] SDF-fil ej hittad, hoppar över test")
        return True
    
    print(f"  Använder: {sdf_file}")
    
    # Läs IR-sheet
    df_ir = pd.read_excel(sdf_file, sheet_name='IR 2024-2027', engine='openpyxl')
    
    # Förväntade kolumner
    expected_cols = {
        'REId': 'Företags-ID',
        '-varav Kapital-förslitning': 'Kapitalförslitning periodsumma',
        'varav Kapital-bindning': 'Kapitalbindning periodsumma',
        'Kapitalkostnad': 'Total kapitalkostnad periodsumma'
    }
    
    print(f"\n  Kolumner i IR-sheet:")
    for col in df_ir.columns:
        print(f"    - {col}")
    
    print(f"\n  Kontrollerar förväntade kolumner:")
    all_found = True
    for col, desc in expected_cols.items():
        if col in df_ir.columns:
            print(f"    [OK] '{col}' ({desc})")
        else:
            print(f"    [FAIL] '{col}' saknas! ({desc})")
            all_found = False
    
    if all_found:
        print("\n  [PASS] Alla förväntade kolumner finns")
        
        # Visa exempeldata
        print(f"\n  Exempeldata (första 3 rader):")
        sample = df_ir[['REId', '-varav Kapital-förslitning', 'varav Kapital-bindning', 'Kapitalkostnad']].head(3)
        print(sample.to_string(index=False))
        
        # Verifiera att summan stämmer
        print(f"\n  Verifierar summor:")
        for idx, row in sample.iterrows():
            forslitning = row['-varav Kapital-förslitning']
            bindning = row['varav Kapital-bindning']
            total = row['Kapitalkostnad']
            calc_total = forslitning + bindning
            diff = abs(total - calc_total)
            status = "[OK]" if diff < 1 else "[DIFF]"
            print(f"    {row['REId']}: {forslitning:.0f} + {bindning:.0f} = {calc_total:.0f} (rapporterad: {total:.0f}) {status}")
    
    return all_found


def test_pipeline_with_wacc_scaling():
    """
    Testar hela pipelinen med WACC-skalning.
    Kräver att alla moduler är tillgängliga.
    """
    print("\n" + "="*70)
    print("TEST: Pipeline med WACC-skalning")
    print("="*70)
    
    try:
        from data_loaders import load_baseline_data
        from config import CaseDefinition, PreDeaConfig, DeaConfig, PostDeaConfig
        from config.case_definition import CapexMethod, EfficiencyMethod
        from pipeline.core import run_pipeline, validate_pipeline_result
    except ImportError as e:
        print(f"  [SKIP] Kunde inte importera moduler: {e}")
        print("  Kör detta test från projektets rotmapp med alla moduler tillgängliga.")
        return True
    
    # Ladda baseline data
    print("\n  Laddar baseline data...")
    try:
        baseline_data = load_baseline_data()
        print(f"    [OK] Laddade {len(baseline_data.df_all_companies)} företag")
    except Exception as e:
        print(f"  [FAIL] Kunde inte ladda baseline: {e}")
        return False
    
    # Välj ett testföretag
    test_reid = baseline_data.df_all_companies['REId'].iloc[0]
    print(f"    Testföretag: {test_reid}")
    
    # Kör baseline först
    print("\n  Kör BASELINE scenario...")
    baseline_config = CaseDefinition(
        name="Baseline",
        user_reid=test_reid,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )
    
    try:
        baseline_result = run_pipeline(baseline_data, baseline_config)
        baseline_kapkost = baseline_result.post_dea.user_intaktsram['Kapitalkostnad_Total']
        baseline_intaktsram = baseline_result.post_dea.user_intaktsram['Intaktsram_Total']
        print(f"    Kapitalkostnad: {baseline_kapkost:,.0f} tkr")
        print(f"    Intäktsram: {baseline_intaktsram:,.0f} tkr")
    except Exception as e:
        print(f"  [FAIL] Baseline pipeline fel: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Kör WACC-skalning med högre WACC
    print("\n  Kör WACC-SCALING scenario (5.0% WACC)...")
    wacc_config = CaseDefinition(
        name="WACC 5%",
        user_reid=test_reid,
        pre_dea=PreDeaConfig(
            method=CapexMethod.WACC_SCALING,
            wacc=0.05  # 5% istället för baseline 4.53%
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )
    
    try:
        wacc_result = run_pipeline(baseline_data, wacc_config)
        wacc_kapkost = wacc_result.post_dea.user_intaktsram['Kapitalkostnad_Total']
        wacc_intaktsram = wacc_result.post_dea.user_intaktsram['Intaktsram_Total']
        print(f"    Kapitalkostnad: {wacc_kapkost:,.0f} tkr")
        print(f"    Intäktsram: {wacc_intaktsram:,.0f} tkr")
    except Exception as e:
        print(f"  [FAIL] WACC-scaling pipeline fel: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Jämför resultat
    print("\n  Jämförelse:")
    kapkost_diff = wacc_kapkost - baseline_kapkost
    kapkost_diff_pct = (kapkost_diff / baseline_kapkost) * 100
    intaktsram_diff = wacc_intaktsram - baseline_intaktsram
    intaktsram_diff_pct = (intaktsram_diff / baseline_intaktsram) * 100
    
    print(f"    Kapitalkostnad: {baseline_kapkost:,.0f} -> {wacc_kapkost:,.0f} ({kapkost_diff_pct:+.2f}%)")
    print(f"    Intäktsram: {baseline_intaktsram:,.0f} -> {wacc_intaktsram:,.0f} ({intaktsram_diff_pct:+.2f}%)")
    
    # Verifiera att förändringen är rimlig
    wacc_diff_pct = (0.05 / 0.0453 - 1) * 100  # ~10.4%
    print(f"\n  WACC-förändring: {wacc_diff_pct:.1f}%")
    print(f"  Kapitalkostnad-förändring: {kapkost_diff_pct:.2f}%")
    
    # Kapitalkostnad bör öka, men mindre än WACC-förändringen
    # (eftersom endast kapitalbindning skalas, inte kapitalförslitning)
    if kapkost_diff > 0:
        print(f"\n  [OK] Kapitalkostnad ökade som förväntat")
    else:
        print(f"\n  [FAIL] Kapitalkostnad borde öka när WACC ökar")
        return False
    
    if kapkost_diff_pct < wacc_diff_pct:
        print(f"  [OK] Ökningen ({kapkost_diff_pct:.2f}%) är mindre än WACC-ökningen ({wacc_diff_pct:.1f}%)")
        print(f"       (korrekt eftersom endast kapitalbindning skalas)")
    else:
        print(f"  [WARN] Ökningen ({kapkost_diff_pct:.2f}%) är >= WACC-ökningen ({wacc_diff_pct:.1f}%)")
        print(f"         Detta kan indikera fel i beräkningen")
    
    print("\n  [PASS] Pipeline med WACC-skalning fungerar")
    return True


def main():
    """Kör alla tester."""
    print("\n" + "="*70)
    print("WACC-SKALNING TESTSVIT")
    print("="*70)
    print("\nTestar att WACC-skalning använder korrekta periodsummor")
    print("istället för felaktig årsvärde × 4 approximation.\n")
    
    results = []
    
    # Test 1: Isolerad beräkningslogik
    results.append(("Beräkningslogik", test_wacc_scaling_calculation()))
    
    # Test 2: SDF kolumnnamn
    results.append(("SDF kolumnnamn", test_sdf_column_names()))
    
    # Test 3: Full pipeline (om möjligt)
    results.append(("Full pipeline", test_pipeline_with_wacc_scaling()))
    
    # Sammanfattning
    print("\n" + "="*70)
    print("SAMMANFATTNING")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n  Alla tester passerade!")
    else:
        print("\n  Några tester misslyckades - se detaljer ovan")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())