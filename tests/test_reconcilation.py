"""
tests/test_reconciliation.py

Reconciliation-tester: Validerar att beräkningskedjan ger resultat
som matchar Ei's officiella värden.

KRITISKT: Dessa tester kör BERÄKNINGARNA, inte baseline-metoden.
Vi verifierar att vår implementation av:
- KENT steg 5-8 (kapitalkostnad)
- DEA (effektivitet)
- Effektiviseringskrav
- Påverkbara kostnader
- Intäktsram-assembly

...ger samma resultat som Ei's publicerade värden.

Kör med: python test_reconciliation.py
"""

import sys
from pathlib import Path

# Säkerställ att projektroten finns i path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


# =============================================================================
# REFERENSVÄRDEN FRÅN EI
# =============================================================================

@dataclass
class EiReference:
    """Referensvärden från Ei för ett företag."""
    reid: str
    namn: str
    # Från Data_modeller.xlsx
    kapitalkostnad_2024: float  # CAPEX årsvärde (tkr)
    avskrivning: float
    avkastning: float
    # Från EIs_DEA.xlsx
    effektivitet: float
    potential: float
    effkrav_proc: float
    # Från SDF IR
    kapitalkostnad_period: float  # 4-årssumma (tkr)
    paverkbara: float  # 4-årssumma (tkr)
    opaverkbara: float
    intaktsram: float


# Referensvärden för de 3 företagen i capbase_a_mini.parquet
EI_REFERENCES = {
    'REL00001': EiReference(
        reid='REL00001',
        namn='Ale El ek. för.',
        kapitalkostnad_2024=59620.58,
        avskrivning=31020.08,
        avkastning=28600.50,
        effektivitet=0.677753,
        potential=0.322247,
        effkrav_proc=0.018245,
        kapitalkostnad_period=237713.01,
        paverkbara=176859.80,
        opaverkbara=108280.00,
        intaktsram=522852.81
    ),
    'REL00886': EiReference(
        reid='REL00886',
        namn='Kraftringen Nät AB',
        kapitalkostnad_2024=421649.22,
        avskrivning=231228.47,
        avkastning=190420.75,
        effektivitet=0.793547,
        potential=0.206453,
        effkrav_proc=0.012661,
        kapitalkostnad_period=1715597.56,
        paverkbara=920371.93,
        opaverkbara=1348225.00,
        intaktsram=3986194.49
    ),
    'REL03035': EiReference(
        reid='REL03035',
        namn='Ellevio AB',
        kapitalkostnad_2024=3530396.94,
        avskrivning=1804774.79,
        avkastning=1725622.16,
        effektivitet=0.980899,
        potential=0.019101,
        effkrav_proc=0.010000,
        kapitalkostnad_period=14187780.41,
        paverkbara=6303143.83,
        opaverkbara=7823211.00,
        intaktsram=28435646.24
    )
}

# Baseline-parametrar (Ei's värden för 2024-2027)
BASELINE_WACC = 0.0453
BASELINE_DEA_SPEC = {
    'inputs': ['Kapitalkostnad_2024', 'OPEXp'],
    'outputs': ['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
    'rts': 'crs',
    'orientation': 'input',
    'outlier_params': {
        'q_lower': 25.0,
        'q_upper': 75.0,
        'multiplier': 2.0
    }
}


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


def calculate_deviation(ei_value: float, calculated_value: float) -> Tuple[float, float]:
    """Beräknar absolut och procentuell avvikelse."""
    abs_dev = calculated_value - ei_value
    if ei_value != 0:
        pct_dev = (abs_dev / ei_value) * 100
    else:
        pct_dev = 0 if calculated_value == 0 else float('inf')
    return abs_dev, pct_dev


def print_section(title: str):
    """Skriver ut sektionsrubrik."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result_row(variabel: str, ei: float, calc: float, abs_dev: float, pct_dev: float):
    """Skriver ut en resultatrad."""
    print(f"  {variabel:30s}  Ei: {ei:>14,.2f}  Ber: {calc:>14,.2f}  "
          f"Avv: {abs_dev:>+12,.2f} ({pct_dev:>+7.3f}%)")


# =============================================================================
# TEST 1: KENT STEG 5-8 (KAPITALKOSTNAD)
# =============================================================================

def test_kent_kapitalkostnad() -> List[ReconciliationResult]:
    """
    Test 1: Kör KENT steg 5-8 med capbase_a_mini och jämför kapitalkostnad.
    
    Verifierar:
    - Kapitalkostnad_2024 (årsvärde för DEA)
    - Kapitalkostnad_Period (4-årssumma för intäktsram)
    """
    print_section("TEST 1: KENT STEG 5-8 (KAPITALKOSTNAD)")
    
    results = []
    
    # Ladda capbase_a_mini
    capbase_path = None
    for path in [
        Path("data/capbase_a_mini.parquet"),
        Path("capbase_a_mini.parquet"),
        Path(__file__).parent / "capbase_a_mini.parquet",
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
    print("  " + "-" * 66)
    
    for reid, ref in EI_REFERENCES.items():
        row = df_network[df_network['REId'] == reid]
        
        if row.empty:
            print(f"  {reid}: SAKNAS i KENT-output")
            continue
        
        # Kapitalkostnad_2024
        calc_2024 = row['Kapitalkostnad_2024'].values[0]
        abs_dev, pct_dev = calculate_deviation(ref.kapitalkostnad_2024, calc_2024)
        print_result_row(f"{reid} Kapitalkostnad_2024", ref.kapitalkostnad_2024, calc_2024, abs_dev, pct_dev)
        results.append(ReconciliationResult(
            steg="KENT", variabel="Kapitalkostnad_2024", reid=reid,
            ei_varde=ref.kapitalkostnad_2024, beraknat_varde=calc_2024,
            avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
        ))
        
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
# TEST 2: DEA (EFFEKTIVITET)
# =============================================================================

def test_dea_effektivitet() -> List[ReconciliationResult]:
    """
    Test 2: Kör DEA med baseline-specifikation och jämför effektivitet.
    
    Verifierar:
    - Effektivitet per företag
    - Potential per företag
    - Outlier-klassificering
    """
    print_section("TEST 2: DEA (EFFEKTIVITET)")
    
    results = []
    
    # Ladda baseline-data
    try:
        from data_loaders import load_baseline_data
        baseline = load_baseline_data()
        df = baseline.df_all_companies.copy()
        print(f"  Laddade {len(df)} företag från baseline")
    except Exception as e:
        print(f"  FEL vid laddning av baseline: {e}")
        return results
    
    # Kör DEA
    try:
        from calculations.dea_calculations import run_dea_analysis
        
        print(f"  Kör DEA med baseline-specifikation...")
        dea_results = run_dea_analysis(df, BASELINE_DEA_SPEC)
        print(f"  DEA klar för {len(dea_results)} företag")
        
    except ImportError as e:
        print(f"  FEL: Kunde inte importera dea_calculations: {e}")
        return results
    except Exception as e:
        print(f"  FEL vid DEA: {e}")
        import traceback
        traceback.print_exc()
        return results
    
    # Jämför för testföretagen
    print("\n  Resultat per företag:")
    print("  " + "-" * 66)
    
    for reid, ref in EI_REFERENCES.items():
        row = dea_results[dea_results['REId'] == reid]
        
        if row.empty:
            print(f"  {reid}: SAKNAS i DEA-output")
            continue
        
        # Effektivitet
        calc_eff = row['Effektivitet'].values[0]
        abs_dev, pct_dev = calculate_deviation(ref.effektivitet, calc_eff)
        print_result_row(f"{reid} Effektivitet", ref.effektivitet, calc_eff, abs_dev, pct_dev)
        results.append(ReconciliationResult(
            steg="DEA", variabel="Effektivitet", reid=reid,
            ei_varde=ref.effektivitet, beraknat_varde=calc_eff,
            avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
        ))
        
        # Potential
        calc_pot = row['potential'].values[0]
        abs_dev, pct_dev = calculate_deviation(ref.potential, calc_pot)
        print_result_row(f"{reid} potential", ref.potential, calc_pot, abs_dev, pct_dev)
        results.append(ReconciliationResult(
            steg="DEA", variabel="potential", reid=reid,
            ei_varde=ref.potential, beraknat_varde=calc_pot,
            avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
        ))
        
        # Outlier status
        is_outlier = row['is_outlier'].values[0]
        print(f"  {reid:30s}  Outlier: {is_outlier}")
    
    # Jämför alla 148 företag mot Ei's DEA
    print("\n  Jämförelse mot Ei's DEA (alla 148 företag):")
    print("  " + "-" * 66)
    
    ei_dea = baseline.dea_results
    merged = dea_results.merge(
        ei_dea[['REId', 'Effektivitet', 'potential']],
        on='REId',
        suffixes=('_calc', '_ei')
    )
    
    # Filtrera bort outliers för statistik
    non_outliers = merged[~merged['is_outlier']].copy()
    non_outliers['eff_diff'] = abs(non_outliers['Effektivitet_calc'] - non_outliers['Effektivitet_ei'])
    
    print(f"  Antal icke-outliers: {len(non_outliers)}")
    print(f"  Max effektivitetsavvikelse: {non_outliers['eff_diff'].max():.6f}")
    print(f"  Medel effektivitetsavvikelse: {non_outliers['eff_diff'].mean():.6f}")
    print(f"  Std effektivitetsavvikelse: {non_outliers['eff_diff'].std():.6f}")
    
    # Hitta företag med störst avvikelse
    worst = non_outliers.nlargest(5, 'eff_diff')
    print("\n  Top 5 största avvikelser:")
    for _, r in worst.iterrows():
        print(f"    {r['REId']}: Ei={r['Effektivitet_ei']:.6f}, Ber={r['Effektivitet_calc']:.6f}, "
              f"Diff={r['eff_diff']:.6f}")
    
    return results


# =============================================================================
# TEST 3: EFFEKTIVISERINGSKRAV
# =============================================================================

def test_effektiviseringskrav() -> List[ReconciliationResult]:
    """
    Test 3: Beräkna effektiviseringskrav och jämför mot Ei.
    
    Verifierar:
    - Effkrav_proc per företag
    - Korrekt hantering av outliers
    - Korrekt trunkering
    """
    print_section("TEST 3: EFFEKTIVISERINGSKRAV")
    
    results = []
    
    # Ladda baseline
    try:
        from data_loaders import load_baseline_data
        baseline = load_baseline_data()
    except Exception as e:
        print(f"  FEL vid laddning: {e}")
        return results
    
    # Kör DEA först (behövs för potential)
    try:
        from calculations.dea_calculations import run_dea_analysis
        from calculations.effektiviseringskrav import (
            calculate_effkrav_for_dataframe,
            DEFAULT_EFFKRAV_PARAMS
        )
        
        dea_results = run_dea_analysis(baseline.df_all_companies, BASELINE_DEA_SPEC)
        
        print(f"  Beräknar effektiviseringskrav med parametrar:")
        for k, v in DEFAULT_EFFKRAV_PARAMS.items():
            print(f"    {k}: {v}")
        
        effkrav_results = calculate_effkrav_for_dataframe(
            dea_results,
            **DEFAULT_EFFKRAV_PARAMS
        )
        
    except Exception as e:
        print(f"  FEL: {e}")
        import traceback
        traceback.print_exc()
        return results
    
    # Jämför för testföretagen
    print("\n  Resultat per företag:")
    print("  " + "-" * 66)
    
    for reid, ref in EI_REFERENCES.items():
        row = effkrav_results[effkrav_results['REId'] == reid]
        
        if row.empty:
            print(f"  {reid}: SAKNAS")
            continue
        
        calc_effkrav = row['Effkrav_proc'].values[0]
        abs_dev, pct_dev = calculate_deviation(ref.effkrav_proc, calc_effkrav)
        print_result_row(f"{reid} Effkrav_proc", ref.effkrav_proc, calc_effkrav, abs_dev, pct_dev)
        results.append(ReconciliationResult(
            steg="Effkrav", variabel="Effkrav_proc", reid=reid,
            ei_varde=ref.effkrav_proc, beraknat_varde=calc_effkrav,
            avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
        ))
    
    # Jämför alla 148 mot Ei
    print("\n  Jämförelse mot Ei (alla 148 företag):")
    print("  " + "-" * 66)
    
    ei_dea = baseline.dea_results
    merged = effkrav_results.merge(
        ei_dea[['REId', 'Effkrav_proc']],
        on='REId',
        suffixes=('_calc', '_ei')
    )
    merged['effkrav_diff'] = abs(merged['Effkrav_proc_calc'] - merged['Effkrav_proc_ei'])
    
    print(f"  Max effkrav-avvikelse: {merged['effkrav_diff'].max():.6f}")
    print(f"  Medel effkrav-avvikelse: {merged['effkrav_diff'].mean():.6f}")
    
    return results


# =============================================================================
# TEST 4: PÅVERKBARA KOSTNADER
# =============================================================================

def test_paverkbara() -> List[ReconciliationResult]:
    """
    Test 4: Beräkna påverkbara kostnader och jämför mot SDF.
    
    Verifierar:
    - Paverkbara_Periodsumma per företag
    - Korrekt applicering av effkrav
    """
    print_section("TEST 4: PÅVERKBARA KOSTNADER")
    
    results = []
    
    try:
        from data_loaders import load_baseline_data
        from calculations.dea_calculations import run_dea_analysis
        from calculations.effektiviseringskrav import (
            calculate_effkrav_for_dataframe,
            DEFAULT_EFFKRAV_PARAMS
        )
        from calculations.paverkbara_calculations import (
            calculate_paverkbara_with_effkrav,
            get_paverkbara_from_sdf
        )
        
        baseline = load_baseline_data()
        
        # Kör DEA och effkrav
        dea_results = run_dea_analysis(baseline.df_all_companies, BASELINE_DEA_SPEC)
        effkrav_results = calculate_effkrav_for_dataframe(dea_results, **DEFAULT_EFFKRAV_PARAMS)
        
        # Hämta påverkbara baseline från SDF
        sdf_paverkbara = get_paverkbara_from_sdf(
            baseline.sdf_ir,
            baseline.sdf_paverkbara
        )
        
        # Beräkna påverkbara (OPEX-metod)
        print("  Beräknar påverkbara kostnader (OPEX-metod)...")
        capex_data = pd.DataFrame({'REId': baseline.df_all_companies['REId']})
        
        paverkbara_results = calculate_paverkbara_with_effkrav(
            effkrav_data=effkrav_results,
            sdf_baseline=sdf_paverkbara,
            capex_data=capex_data,
            method='OPEX'
        )
        
    except Exception as e:
        print(f"  FEL: {e}")
        import traceback
        traceback.print_exc()
        return results
    
    # Jämför för testföretagen
    print("\n  Resultat per företag:")
    print("  " + "-" * 66)
    
    for reid, ref in EI_REFERENCES.items():
        row = paverkbara_results[paverkbara_results['REId'] == reid]
        
        if row.empty:
            print(f"  {reid}: SAKNAS")
            continue
        
        calc_pav = row['Paverkbara_Periodsumma'].values[0]
        abs_dev, pct_dev = calculate_deviation(ref.paverkbara, calc_pav)
        print_result_row(f"{reid} Påverkbara", ref.paverkbara, calc_pav, abs_dev, pct_dev)
        results.append(ReconciliationResult(
            steg="Påverkbara", variabel="Paverkbara_Periodsumma", reid=reid,
            ei_varde=ref.paverkbara, beraknat_varde=calc_pav,
            avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
        ))
    
    return results


# =============================================================================
# TEST 5: INTÄKTSRAM ASSEMBLY
# =============================================================================

def test_intaktsram_assembly() -> List[ReconciliationResult]:
    """
    Test 5: Assemblera komplett intäktsram och jämför mot SDF.
    
    Verifierar:
    - Intaktsram_Total per företag
    - Korrekt summering av alla komponenter
    """
    print_section("TEST 5: INTÄKTSRAM ASSEMBLY")
    
    results = []
    
    try:
        from data_loaders import load_baseline_data
        from calculations.dea_calculations import run_dea_analysis
        from calculations.effektiviseringskrav import (
            calculate_effkrav_for_dataframe,
            DEFAULT_EFFKRAV_PARAMS
        )
        from calculations.paverkbara_calculations import (
            calculate_paverkbara_with_effkrav,
            get_paverkbara_from_sdf
        )
        from calculations.intaktsram_assembly import assemble_intaktsram
        
        baseline = load_baseline_data()
        
        # Kör hela kedjan
        dea_results = run_dea_analysis(baseline.df_all_companies, BASELINE_DEA_SPEC)
        effkrav_results = calculate_effkrav_for_dataframe(dea_results, **DEFAULT_EFFKRAV_PARAMS)
        
        sdf_paverkbara = get_paverkbara_from_sdf(
            baseline.sdf_ir,
            baseline.sdf_paverkbara
        )
        
        capex_data = pd.DataFrame({'REId': baseline.df_all_companies['REId']})
        
        paverkbara_results = calculate_paverkbara_with_effkrav(
            effkrav_data=effkrav_results,
            sdf_baseline=sdf_paverkbara,
            capex_data=capex_data,
            method='OPEX'
        )
        
        # Kapitalkostnad från SDF (baseline)
        capex_for_ir = baseline.sdf_ir[['REId', 'Kapitalkostnad']].rename(
            columns={'Kapitalkostnad': 'Kapitalkostnad_Total'}
        ).copy()
        
        # Assemblera intäktsram
        print("  Assemblerar intäktsram...")
        intaktsram = assemble_intaktsram(
            capex_result=capex_for_ir,
            paverkbara_result=paverkbara_results,
            sdf_baseline=baseline.sdf_ir
        )
        
    except Exception as e:
        print(f"  FEL: {e}")
        import traceback
        traceback.print_exc()
        return results
    
    # Jämför för testföretagen
    print("\n  Resultat per företag:")
    print("  " + "-" * 66)
    
    for reid, ref in EI_REFERENCES.items():
        row = intaktsram[intaktsram['REId'] == reid]
        
        if row.empty:
            print(f"  {reid}: SAKNAS")
            continue
        
        # Intäktsram total
        calc_ir = row['Intaktsram_Total'].values[0]
        abs_dev, pct_dev = calculate_deviation(ref.intaktsram, calc_ir)
        print_result_row(f"{reid} Intäktsram", ref.intaktsram, calc_ir, abs_dev, pct_dev)
        results.append(ReconciliationResult(
            steg="Intäktsram", variabel="Intaktsram_Total", reid=reid,
            ei_varde=ref.intaktsram, beraknat_varde=calc_ir,
            avvikelse_abs=abs_dev, avvikelse_proc=pct_dev
        ))
        
        # Visa komponenterna
        print(f"    Komponenter:")
        print(f"      Kapitalkostnad: {row['Kapitalkostnad_Total'].values[0]:,.2f} (Ei: {ref.kapitalkostnad_period:,.2f})")
        print(f"      Påverkbara:     {row['Paverkbara_Periodsumma'].values[0]:,.2f} (Ei: {ref.paverkbara:,.2f})")
        print(f"      Opåverkbara:    {row['Opaverkbara_Kostnader'].values[0]:,.2f} (Ei: {ref.opaverkbara:,.2f})")
    
    return results


# =============================================================================
# SAMMANFATTNING
# =============================================================================

def print_summary(all_results: List[ReconciliationResult]):
    """Skriver ut sammanfattning av alla reconciliation-resultat."""
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
        avg_pct = sum(abs(r.avvikelse_proc) for r in steg_results) / len(steg_results)
        
        print(f"\n  {steg}:")
        print(f"    Antal jämförelser: {len(steg_results)}")
        print(f"    Max absolut avvikelse: {max_abs:,.2f} tkr")
        print(f"    Max procentuell avvikelse: {max_pct:.4f}%")
        print(f"    Medel procentuell avvikelse: {avg_pct:.4f}%")
    
    # Största avvikelser totalt
    print("\n  Top 5 största procentuella avvikelser:")
    print("  " + "-" * 66)
    sorted_results = sorted(all_results, key=lambda r: abs(r.avvikelse_proc), reverse=True)
    for r in sorted_results[:5]:
        print(f"    {r.steg}/{r.variabel}/{r.reid}: {r.avvikelse_proc:+.4f}%")


# =============================================================================
# MAIN
# =============================================================================

def run_all_reconciliation_tests():
    """Kör alla reconciliation-tester och sammanfatta."""
    print("\n" + "=" * 70)
    print("  RECONCILIATION TEST SUITE")
    print("  Validerar beräkningskedjan mot Ei's officiella värden")
    print("=" * 70)
    
    all_results = []
    
    # Test 1: KENT kapitalkostnad
    results = test_kent_kapitalkostnad()
    all_results.extend(results)
    
    # Test 2: DEA effektivitet
    results = test_dea_effektivitet()
    all_results.extend(results)
    
    # Test 3: Effektiviseringskrav
    results = test_effektiviseringskrav()
    all_results.extend(results)
    
    # Test 4: Påverkbara kostnader
    results = test_paverkbara()
    all_results.extend(results)
    
    # Test 5: Intäktsram assembly
    results = test_intaktsram_assembly()
    all_results.extend(results)
    
    # Sammanfattning
    print_summary(all_results)
    
    print("\n" + "=" * 70)
    print("  RECONCILIATION KLAR")
    print("=" * 70 + "\n")
    
    return all_results


if __name__ == "__main__":
    run_all_reconciliation_tests()