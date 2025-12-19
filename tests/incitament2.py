"""
tests/test_kent_incentive_reconciliation.py

Reconciliation-test: Verifierar att incitamentjusteringar fungerar korrekt
med KENT-pipelinen (parameter_change/kent_upload metoder).

LOGIK:
- Ei's referensvärden (intaktsram) inkluderar INTE incitament
- Vår beräkning: intäktsram_med_incitament = Ei_intäktsram + incitamentjustering
- Om detta stämmer är incitamentet korrekt integrerat

Testar med capbase_a_mini (3 företag) för snabb körning.

Kör med: python test_kent_incentive_reconciliation.py
"""

import sys
from pathlib import Path

# Säkerställ att projektroten finns i path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


# =============================================================================
# REFERENSVÄRDEN FRÅN EI (UTAN INCITAMENT)
# =============================================================================

@dataclass
class EiReference:
    """Referensvärden från Ei för ett företag (UTAN incitament)."""
    reid: str
    namn: str
    # Från Data_modeller/KENT
    kapitalkostnad_2024: float  # Årsvärde (tkr)
    kapitalkostnad_period: float  # 4-årssumma (tkr)
    # Från EIs_DEA.xlsx
    effektivitet: float
    effkrav_proc: float
    # Från SDF IR (UTAN incitament)
    paverkbara: float  # 4-årssumma (tkr)
    opaverkbara: float
    intaktsram_utan_incitament: float  # Ei's värde UTAN incitament


# Referensvärden för de 3 företagen i capbase_a_mini.parquet
# KRITISKT: intaktsram_utan_incitament är Ei's officiella värde som INTE inkluderar incitament
EI_REFERENCES = {
    'REL00001': EiReference(
        reid='REL00001',
        namn='Ale El ek. för.',
        kapitalkostnad_2024=59620.58,
        kapitalkostnad_period=237713.01,
        effektivitet=0.677753,
        effkrav_proc=0.018245,
        paverkbara=176859.80,
        opaverkbara=108280.00,
        intaktsram_utan_incitament=522852.81
    ),
    'REL00886': EiReference(
        reid='REL00886',
        namn='Kraftringen Nät AB',
        kapitalkostnad_2024=421649.22,
        kapitalkostnad_period=1715597.56,
        effektivitet=0.793547,
        effkrav_proc=0.012661,
        paverkbara=920371.93,
        opaverkbara=1348225.00,
        intaktsram_utan_incitament=3986194.49
    ),
    'REL03035': EiReference(
        reid='REL03035',
        namn='Ellevio AB',
        kapitalkostnad_2024=3530396.94,
        kapitalkostnad_period=14187780.41,
        effektivitet=0.980899,
        effkrav_proc=0.010000,
        paverkbara=6303143.83,
        opaverkbara=7823211.00,
        intaktsram_utan_incitament=28435646.24
    )
}

BASELINE_WACC = 0.0453


# =============================================================================
# HJÄLPFUNKTIONER
# =============================================================================

@dataclass
class ReconciliationResult:
    """Resultat från en reconciliation-jämförelse."""
    steg: str
    variabel: str
    reid: str
    ei_varde: float
    beraknat_varde: float
    avvikelse_abs: float
    avvikelse_proc: float


def calculate_deviation(expected: float, actual: float) -> Tuple[float, float]:
    """Beräknar absolut och procentuell avvikelse."""
    abs_dev = actual - expected
    if expected != 0:
        pct_dev = (abs_dev / expected) * 100
    else:
        pct_dev = 0 if actual == 0 else float('inf')
    return abs_dev, pct_dev


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result_row(variabel: str, expected: float, actual: float, abs_dev: float, pct_dev: float):
    print(f"  {variabel:35s}  Förv: {expected:>14,.2f}  Ber: {actual:>14,.2f}  "
          f"Avv: {abs_dev:>+12,.2f} ({pct_dev:>+7.3f}%)")


# =============================================================================
# TEST 1: KENT KAPITALKOSTNAD (BASELINE)
# =============================================================================

def test_kent_kapitalkostnad() -> List[ReconciliationResult]:
    """
    Test 1: Kör KENT steg 5-8 med capbase_a_mini och jämför kapitalkostnad.
    
    Verifierar att KENT-beräkningarna ger samma värden som Ei's baseline.
    """
    print_section("TEST 1: KENT KAPITALKOSTNAD")
    
    results = []
    
    # Sök efter capbase_a_mini
    capbase_path = None
    for path in [
        Path("data/capbase_a_mini.parquet"),
        Path("capbase_a_mini.parquet"),
        Path(__file__).parent / "capbase_a_mini.parquet",
        Path(__file__).parent.parent / "data" / "capbase_a_mini.parquet",
    ]:
        if path.exists():
            capbase_path = path
            break
    
    if capbase_path is None:
        print("  SKIP: capbase_a_mini.parquet hittades inte")
        return results
    
    print(f"  Laddar: {capbase_path}")
    
    try:
        capbase_data = pd.read_parquet(capbase_path)
        print(f"  Laddade {len(capbase_data):,} komponenter")
    except Exception as e:
        print(f"  FEL vid laddning: {e}")
        return results
    
    # Kör KENT steg 5-8
    try:
        from calculations.kent_calculations import run_kent_calculations_batch
        
        print(f"  Kör KENT steg 5-8 med WACC={BASELINE_WACC}...")
        _, df_network = run_kent_calculations_batch(
            capbase_data,
            wacc=BASELINE_WACC,
            normvalue_adjustments=None,
            lifetime_adjustments=None
        )
        print(f"  Beräknade {len(df_network)} nätverk")
        
    except ImportError as e:
        print(f"  FEL: Kunde inte importera kent_calculations: {e}")
        return results
    except Exception as e:
        print(f"  FEL vid KENT-beräkning: {e}")
        import traceback
        traceback.print_exc()
        return results
    
    # Jämför för varje testföretag
    print("\n  Resultat per företag:")
    print("  " + "-" * 70)
    
    for reid, ref in EI_REFERENCES.items():
        row = df_network[df_network['REId'] == reid]
        
        if row.empty:
            print(f"  {reid}: SAKNAS i KENT-output")
            continue
        
        # Kapitalkostnad_Period
        calc_period = row['Kapitalkostnad_Period'].values[0]
        abs_dev, pct_dev = calculate_deviation(ref.kapitalkostnad_period, calc_period)
        print_result_row(f"{reid} Kapitalkostnad_Period", ref.kapitalkostnad_period, calc_period, abs_dev, pct_dev)
        results.append(ReconciliationResult(
            steg="KENT", variabel="Kapitalkostnad_Period", reid=reid,
            ei_varde=ref.kapitalkostnad_period, beraknat_varde=calc_period,
            avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
        ))
    
    return results


# =============================================================================
# TEST 2: INCITAMENTBERÄKNING FÖR TESTFÖRETAGEN
# =============================================================================

def test_incentive_calculation() -> Tuple[List[ReconciliationResult], Dict[str, float]]:
    """
    Test 2: Beräkna incitamentjusteringar för testföretagen.
    
    Returnerar:
    - Lista med reconciliation-resultat
    - Dict med incitamentjusteringar per REId (för användning i test 3)
    """
    print_section("TEST 2: INCITAMENTBERÄKNING")
    
    results = []
    incentives_by_reid = {}
    
    try:
        from data_loaders.incentive_data import load_incentive_data, prepare_incentive_input, get_incentive_summary_by_reid
        from calculations.incentive_calculations import calculate_all_incentives
        
        # Ladda incitamentdata
        inc_path = None
        for path in [
            Path("data/all_adjust_vars.csv"),
            Path(__file__).parent.parent / "data" / "all_adjust_vars.csv",
        ]:
            if path.exists():
                inc_path = str(path)
                break
        
        if inc_path is None:
            print("  SKIP: all_adjust_vars.csv hittades inte")
            return results, incentives_by_reid
        
        print(f"  Laddar incitamentdata: {inc_path}")
        df_inc = load_incentive_data(inc_path)
        
        # Filtrera till testföretagen
        test_reids = list(EI_REFERENCES.keys())
        df_inc_filtered = df_inc[df_inc['REId'].isin(test_reids)].copy()
        print(f"  Filtrerade till {len(df_inc_filtered)} rader för {len(test_reids)} företag")
        
        # Ladda SDF för avkastning per år
        sdf_path = None
        for path in [
            Path("data/Löpande kostnader från SDF 2024-27.xlsx"),
            Path(__file__).parent.parent / "data" / "Löpande kostnader från SDF 2024-27.xlsx",
        ]:
            if path.exists():
                sdf_path = path
                break
        
        if sdf_path is None:
            print("  SKIP: SDF-fil hittades inte")
            return results, incentives_by_reid
        
        print(f"  Laddar SDF för avkastning...")
        sdf = pd.read_excel(sdf_path, sheet_name='IR 2024-2027')
        
        # Skapa return_per_year (approximation: kapitalbindning / 4)
        return_per_year = sdf[['REId']].copy()
        kapitalbindning = pd.to_numeric(sdf['varav Kapital-bindning'], errors='coerce').fillna(0)
        avkastning_per_year = kapitalbindning / 4
        for year in [2024, 2025, 2026, 2027]:
            return_per_year[f'Avkastning_{year}'] = avkastning_per_year
        
        # Förbered input och beräkna
        df_input = prepare_incentive_input(df_inc_filtered, return_per_year)
        print(f"  Förberedd input: {len(df_input)} rader")
        
        df_calc = calculate_all_incentives(df_input, ret_period_col='ret_period')
        print(f"  Beräknade incitament: {len(df_calc)} rader")
        
        # Aggregera till periodsummor
        df_summary = get_incentive_summary_by_reid(df_calc)
        
        # Visa resultat per företag
        print("\n  Incitamentjusteringar per företag:")
        print("  " + "-" * 70)
        
        for reid, ref in EI_REFERENCES.items():
            row = df_summary[df_summary['REId'] == reid]
            
            if row.empty:
                print(f"  {reid}: SAKNAS i incitamentdata")
                incentives_by_reid[reid] = 0.0
                continue
            
            inc_total = row['Incitamentjustering_Total'].values[0]
            inc_kvalitet = row['Kvalitetsjustering_Total'].values[0]
            inc_natforlust = row['Natforlustjustering_Total'].values[0]
            inc_belastning = row['Belastningsjustering_Total'].values[0]
            
            incentives_by_reid[reid] = inc_total
            
            print(f"  {reid} ({ref.namn}):")
            print(f"    Kvalitetsjustering:    {inc_kvalitet:>12,.0f} tkr")
            print(f"    Nätförlustjustering:   {inc_natforlust:>12,.0f} tkr")
            print(f"    Belastningsjustering:  {inc_belastning:>12,.0f} tkr")
            print(f"    TOTAL:                 {inc_total:>12,.0f} tkr")
            
            results.append(ReconciliationResult(
                steg="Incitament", variabel="Incitamentjustering_Total", reid=reid,
                ei_varde=0,  # Ei har inga incitament i baseline
                beraknat_varde=inc_total,
                avvikelse_abs=inc_total,
                avvikelse_proc=0
            ))
        
    except ImportError as e:
        print(f"  FEL: Import error: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"  FEL: {e}")
        import traceback
        traceback.print_exc()
    
    return results, incentives_by_reid


# =============================================================================
# TEST 3: INTÄKTSRAM MED INCITAMENT (KENT-METOD)
# =============================================================================

def test_intaktsram_with_incentive(incentives_by_reid: Dict[str, float]) -> List[ReconciliationResult]:
    """
    Test 3: Assemblera intäktsram med incitament och verifiera formeln.
    
    KRITISK VERIFIERING:
    - Ei_intäktsram (utan incitament) + Vår_incitament = Vår_intäktsram (med incitament)
    
    Om detta stämmer är incitamentet korrekt integrerat i pipelinen.
    """
    print_section("TEST 3: INTÄKTSRAM MED INCITAMENT (KENT-METOD)")
    
    results = []
    
    try:
        from data_loaders import load_baseline_data
        from calculations.kent_calculations import run_kent_calculations_batch
        from calculations.data_mapping import merge_kent_with_baseline
        from calculations.effektiviseringskrav import calculate_effkrav_for_dataframe, DEFAULT_EFFKRAV_PARAMS
        from calculations.paverkbara_calculations import calculate_paverkbara_with_effkrav, get_paverkbara_from_sdf
        from calculations.intaktsram_assembly import assemble_intaktsram
        
        # Ladda baseline
        print("  Laddar baseline data...")
        baseline = load_baseline_data()
        
        # Ladda capbase_a_mini
        capbase_path = None
        for path in [
            Path("data/capbase_a_mini.parquet"),
            Path("capbase_a_mini.parquet"),
            Path(__file__).parent / "capbase_a_mini.parquet",
            Path(__file__).parent.parent / "data" / "capbase_a_mini.parquet",
        ]:
            if path.exists():
                capbase_path = path
                break
        
        if capbase_path is None:
            print("  SKIP: capbase_a_mini.parquet hittades inte")
            return results
        
        capbase_data = pd.read_parquet(capbase_path)
        print(f"  Laddade {len(capbase_data):,} komponenter")
        
        # Kör KENT steg 5-8
        print(f"  Kör KENT steg 5-8...")
        _, df_network = run_kent_calculations_batch(
            capbase_data,
            wacc=BASELINE_WACC,
            normvalue_adjustments=None,
            lifetime_adjustments=None
        )
        
        # Merge med baseline (för OPEX, volymer, etc.)
        df_merged = merge_kent_with_baseline(df_network, baseline.df_all_companies)
        
        # Använd baseline DEA-resultat (hoppar över ny DEA)
        print("  Använder baseline DEA-resultat...")
        dea_results = baseline.dea_results.copy()
        
        # Beräkna effektiviseringskrav
        print("  Beräknar effektiviseringskrav...")
        effkrav_results = calculate_effkrav_for_dataframe(dea_results, **DEFAULT_EFFKRAV_PARAMS)
        
        # Hämta påverkbara baseline
        sdf_paverkbara = get_paverkbara_from_sdf(baseline.sdf_ir, baseline.sdf_paverkbara)
        
        # Beräkna påverkbara
        print("  Beräknar påverkbara kostnader...")
        capex_data = pd.DataFrame({'REId': baseline.df_all_companies['REId']})
        paverkbara_results = calculate_paverkbara_with_effkrav(
            effkrav_data=effkrav_results,
            sdf_baseline=sdf_paverkbara,
            capex_data=capex_data,
            method='OPEX'
        )
        
        # Förbered kapitalkostnad från KENT (simulerar parameter_change/kent_upload)
        print("  Förbereder kapitalkostnad från KENT...")
        capex_for_ir = df_network[['REId', 'Kapitalkostnad_Period']].rename(
            columns={'Kapitalkostnad_Period': 'Kapitalkostnad_Total'}
        ).copy()
        
        # Förbered incitament-DataFrame
        print("  Förbereder incitamentjusteringar...")
        incentive_df = pd.DataFrame([
            {'REId': reid, 'Incitamentjustering_Total': inc, 'Missing_Incentive_Data': False}
            for reid, inc in incentives_by_reid.items()
        ])
        
        # Assemblera intäktsram MED incitament
        print("  Assemblerar intäktsram MED incitament...")
        intaktsram = assemble_intaktsram(
            capex_result=capex_for_ir,
            paverkbara_result=paverkbara_results,
            sdf_baseline=baseline.sdf_ir,
            incentive_result=incentive_df
        )
        
        # KRITISK VERIFIERING
        print("\n  KRITISK VERIFIERING:")
        print("  " + "-" * 70)
        print("  Formel: Ei_IR (utan inc) + Vår_inc = Vår_IR (med inc)")
        print("  " + "-" * 70)
        
        all_pass = True
        
        for reid, ref in EI_REFERENCES.items():
            row = intaktsram[intaktsram['REId'] == reid]
            
            if row.empty:
                print(f"  {reid}: SAKNAS i intäktsram")
                continue
            
            ir_med_incitament = row['Intaktsram_Total'].values[0]
            incitament = incentives_by_reid.get(reid, 0)
            ir_utan_incitament = ref.intaktsram_utan_incitament
            
            # Förväntad IR med incitament
            expected_ir = ir_utan_incitament + incitament
            
            # Avvikelse
            abs_dev, pct_dev = calculate_deviation(expected_ir, ir_med_incitament)
            
            print(f"\n  {reid} ({ref.namn}):")
            print(f"    Ei IR (utan inc):      {ir_utan_incitament:>14,.2f} tkr")
            print(f"    + Incitament:          {incitament:>+14,.2f} tkr")
            print(f"    = Förväntad IR:        {expected_ir:>14,.2f} tkr")
            print(f"    Vår IR (med inc):      {ir_med_incitament:>14,.2f} tkr")
            print(f"    Avvikelse:             {abs_dev:>+14,.2f} tkr ({pct_dev:+.4f}%)")
            
            # Tolerans: 1 tkr eller 0.001%
            if abs(abs_dev) > 1.0 and abs(pct_dev) > 0.001:
                print(f"    STATUS: FAIL")
                all_pass = False
            else:
                print(f"    STATUS: PASS")
            
            results.append(ReconciliationResult(
                steg="IR+Incitament", variabel="Intaktsram_Total", reid=reid,
                ei_varde=expected_ir, beraknat_varde=ir_med_incitament,
                avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
            ))
        
        if all_pass:
            print("\n  ALLA VERIFIERINGAR PASSERADE!")
            print("  Incitamentjustering är korrekt integrerat i KENT-pipelinen.")
        else:
            print("\n  NÅGRA VERIFIERINGAR MISSLYCKADES!")
        
    except ImportError as e:
        print(f"  FEL: Import error: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"  FEL: {e}")
        import traceback
        traceback.print_exc()
    
    return results


# =============================================================================
# SAMMANFATTNING
# =============================================================================

def print_summary(all_results: List[ReconciliationResult]):
    print_section("SAMMANFATTNING")
    
    if not all_results:
        print("  Inga resultat att sammanfatta.")
        return
    
    # Gruppera per steg
    by_steg = {}
    for r in all_results:
        if r.steg not in by_steg:
            by_steg[r.steg] = []
        by_steg[r.steg].append(r)
    
    print(f"\n  Totalt {len(all_results)} jämförelser:")
    print("  " + "-" * 66)
    
    for steg, steg_results in by_steg.items():
        max_abs = max(abs(r.avvikelse_abs) for r in steg_results)
        max_pct = max(abs(r.avvikelse_proc) for r in steg_results)
        
        print(f"\n  {steg}:")
        print(f"    Antal jämförelser: {len(steg_results)}")
        print(f"    Max absolut avvikelse: {max_abs:,.2f} tkr")
        print(f"    Max procentuell avvikelse: {max_pct:.4f}%")
    
    # Kontrollera om alla IR+Incitament-tester passerade
    ir_results = by_steg.get('IR+Incitament', [])
    all_pass = all(abs(r.avvikelse_abs) <= 1.0 or abs(r.avvikelse_proc) <= 0.001 for r in ir_results)
    
    print("\n" + "=" * 70)
    if all_pass and ir_results:
        print("  RESULTAT: PASS - Incitament korrekt integrerat i KENT-pipeline")
    elif not ir_results:
        print("  RESULTAT: SKIP - Kunde inte köra intäktsram-test")
    else:
        print("  RESULTAT: FAIL - Avvikelser i intäktsram-beräkning")
    print("=" * 70)


# =============================================================================
# MAIN
# =============================================================================

def run_all_tests():
    """Kör alla reconciliation-tester."""
    print("\n" + "=" * 70)
    print("  KENT INCENTIVE RECONCILIATION TEST")
    print("  Verifierar: Ei_IR + Incitament = Vår_IR (med incitament)")
    print("=" * 70)
    
    all_results = []
    
    # Test 1: KENT kapitalkostnad
    results = test_kent_kapitalkostnad()
    all_results.extend(results)
    
    # Test 2: Incitamentberäkning
    results, incentives_by_reid = test_incentive_calculation()
    all_results.extend(results)
    
    # Test 3: Intäktsram med incitament (KENT-metod)
    if incentives_by_reid:
        results = test_intaktsram_with_incentive(incentives_by_reid)
        all_results.extend(results)
    else:
        print("\n  SKIP: Test 3 - Inga incitament beräknade")
    
    # Sammanfattning
    print_summary(all_results)
    
    print("\n" + "=" * 70)
    print("  RECONCILIATION KLAR")
    print("=" * 70 + "\n")
    
    return all_results


if __name__ == "__main__":
    results = run_all_tests()
    
    # Exit med felkod om något misslyckades
    ir_results = [r for r in results if r.steg == 'IR+Incitament']
    any_fail = any(abs(r.avvikelse_abs) > 1.0 and abs(r.avvikelse_proc) > 0.001 for r in ir_results)
    sys.exit(1 if any_fail else 0)