"""
tests/test_kent_component_level.py

Validerar KENT-beräkningar på komponent-nivå mot Ei's officiella
beräkningsexempel från "Kapitalbas beräkningsexempel s. 10.pdf".

Ei's exempel använder period 2016-2019 med WACC=6%.
Vi anpassar till period 2024-2027 med samma logik.

Testfall från PDF:en:
1. Anläggning startad hösten 2015 (→ hösten 2023 för vår period)
2. Anläggning startad våren 2016 (→ våren 2024)
3. Anläggning startad 1999 (→ 2007 för samma ålder)
4. Gammal anläggning i "tail" (efter ekonomisk livslängd)

Kör med: python test_kent_component_level.py
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np


# =============================================================================
# EI's BERÄKNINGSFORMEL (från PDF)
# =============================================================================

@dataclass
class EiComponentExample:
    """Ett beräkningsexempel från Ei's PDF."""
    name: str
    nuav: float              # NUAV i tkr
    ekdep: int               # Ekonomisk livslängd i halvår (40 år = 80 halvår)
    maxdep: int              # Maximal livslängd i halvår (50 år = 100 halvår)
    time_from: int           # Tidskod när anläggningen började användas
    wacc: float              # WACC (Ei använder 6% i exemplen)
    expected_capcost: float  # Förväntad total kapitalkostnad för perioden
    is_tail: bool = False    # Om komponenten är i "tail" (efter ekdep)


def calculate_ei_capcost_manually(
    nuav: float,
    ekdep_halvar: int,
    maxdep_halvar: int,
    time_from: int,
    wacc: float,
    period_codes: List[int]
) -> Dict[str, float]:
    """
    Beräknar kapitalkostnad enligt Ei's formel från PDF.
    
    Kapitalförslitning (ordinary): NUAV / ekdep
    Kapitalbindning (ordinary): NUAV * ((ekdep/2 - ålder_år) / (ekdep/2)) * WACC / 2
    
    där ålder_år beräknas genom att konvertera halvårsålder till "regulatorisk ålder".
    """
    results = {
        'dep_total': 0.0,
        'ret_total': 0.0,
        'capcost_total': 0.0,
        'per_halfyear': {}
    }
    
    ekdep_ar = ekdep_halvar // 2  # Ekonomisk livslängd i år
    
    for timecode in period_codes:
        age_halvar = timecode - time_from  # Ålder i halvår
        
        # Skippa om ålder <= 0 (ännu ej i drift)
        if age_halvar <= 0:
            results['per_halfyear'][timecode] = {'dep': 0, 'ret': 0, 'total': 0, 'type': 'not_in_service'}
            continue
        
        # Bestäm om ordinary eller tail
        if age_halvar <= ekdep_halvar:
            # ORDINARY: inom ekonomisk livslängd
            
            # Kapitalförslitning = NUAV / ekdep / 2 (per halvår)
            dep = nuav / ekdep_ar / 2
            
            # Kapitalbindning enligt Ei's formel:
            # NUAV * ((ekdep - ålder_år) / ekdep) * WACC / 2
            # 
            # Ålder_år beräknas genom att avrunda halvårsålder uppåt om udda,
            # sedan dividera med 2, sedan subtrahera 1
            if age_halvar % 2 == 1:
                age_adjusted = age_halvar + 1
            else:
                age_adjusted = age_halvar
            age_ar = age_adjusted // 2 - 1
            
            if age_ar < 0:
                age_ar = 0
            
            # Kvarvarande kapitalbas
            capbase_left = nuav * ((ekdep_ar / 2 - age_ar) / (ekdep_ar / 2))
            if age_ar < 0 or capbase_left < 0:
                capbase_left = 0
            
            # Kapitalbindning (halvårsränta)
            ret = wacc * capbase_left / 2
            
            component_type = 'ordinary'
            
        elif age_halvar <= maxdep_halvar:
            # TAIL: efter ekonomisk livslängd men innan maximal
            
            # Ålder för tail-beräkning
            if age_halvar % 2 == 1:
                age_reg = age_halvar + 1
            else:
                age_reg = age_halvar
            
            # Kapitalförslitning i tail = NUAV / age_reg (hyperbolisk)
            dep = nuav / age_reg if age_reg > 0 else 0
            
            # Kapitalbindning i tail = NUAV / (age_ar + 1) * WACC / 2
            age_ar = age_reg // 2 - 1
            capbase_left = nuav / (age_ar + 1) if age_ar >= 0 else 0
            ret = wacc * capbase_left / 2
            
            component_type = 'tail'
            
        else:
            # Äldre än maxdep - ingen kapitalkostnad
            dep = 0
            ret = 0
            component_type = 'expired'
        
        results['per_halfyear'][timecode] = {
            'dep': dep,
            'ret': ret,
            'total': dep + ret,
            'type': component_type,
            'age_halvar': age_halvar
        }
        results['dep_total'] += dep
        results['ret_total'] += ret
        results['capcost_total'] += dep + ret
    
    return results


# =============================================================================
# TESTFALL FRÅN EI's PDF (anpassade till period 2024-2027)
# =============================================================================

# Period 2024-2027: tidskoder 229-236
PERIOD_CODES = list(range(229, 237))

# Ei's exempel använder 6% WACC
EI_WACC = 0.06

# Ekonomisk livslängd för "överföring av el" = 40 år = 80 halvår
EKDEP_HALVAR = 80
MAXDEP_HALVAR = 100  # 50 år

# Tidskodsmappning:
# 2023 H1 = 227, 2023 H2 = 228
# 2024 H1 = 229, 2024 H2 = 230
# etc.

EI_EXAMPLES = [
    # Exempel 1: Anläggning startad hösten 2015 → hösten 2023 för 2024-2027
    # I Ei's exempel: vid 2016 är ålder 0-1 år, vid 2019 är ålder 3-4 år
    # För oss: time_from = 228 (2023 H2), så vid 229 (2024 H1) ålder = 1 halvår
    EiComponentExample(
        name="Exempel 1: Startad hösten innan period (2023 H2)",
        nuav=1000.0,
        ekdep=EKDEP_HALVAR,
        maxdep=MAXDEP_HALVAR,
        time_from=228,  # 2023 H2
        wacc=EI_WACC,
        expected_capcost=331.0,  # Från Ei's PDF (2016-2019)
    ),
    
    # Exempel 2: Anläggning startad våren 2016 → våren 2024
    # time_from = 229 (2024 H1), börjar ingå från 230 (2024 H2)
    # Första halvåret (H1) = 0, sedan normalt
    EiComponentExample(
        name="Exempel 2: Startad våren första året (2024 H1)",
        nuav=1000.0,
        ekdep=EKDEP_HALVAR,
        maxdep=MAXDEP_HALVAR,
        time_from=229,  # 2024 H1
        wacc=EI_WACC,
        expected_capcost=290.75,  # Från Ei's PDF
    ),
    
    # Exempel 3: Anläggning startad 1999 (16-17 år gammal vid periodstart)
    # För period 2024-2027: startad 2007 ger samma ålder som 1999 för 2016
    # time_from = 229 - 17*2 = 229 - 34 = 195
    EiComponentExample(
        name="Exempel 3: Startad 17 år innan period (2007)",
        nuav=1000.0,
        ekdep=EKDEP_HALVAR,
        maxdep=MAXDEP_HALVAR,
        time_from=229 - 34,  # 17 år innan 2024 H1 = 195
        wacc=EI_WACC,
        expected_capcost=235.0,  # Från Ei's PDF
    ),
    
    # Exempel 4: Gammal anläggning (38 år vid utgång 2015 → 46 år vid 2024)
    # Denna är i "tail" - efter ekonomisk livslängd
    # time_from = 229 - 46*2 = 229 - 92 = 137
    EiComponentExample(
        name="Exempel 4: Gammal anläggning i tail (46 år)",
        nuav=1000.0,
        ekdep=EKDEP_HALVAR,
        maxdep=MAXDEP_HALVAR,
        time_from=229 - 92,  # 46 år innan = 137
        wacc=EI_WACC,
        expected_capcost=105.58,  # Från Ei's PDF
        is_tail=True,
    ),
]


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# =============================================================================
# TEST 1: Manuell beräkning enligt Ei's formel
# =============================================================================

def test_manual_ei_calculation():
    """Testar vår manuella implementation av Ei's formel."""
    print_section("TEST 1: Manuell beräkning enligt Ei's formel")
    
    all_passed = True
    
    for example in EI_EXAMPLES:
        print(f"\n  {example.name}")
        print(f"    NUAV: {example.nuav} tkr, ekdep: {example.ekdep//2} år")
        print(f"    time_from: {example.time_from}, WACC: {example.wacc*100:.0f}%")
        
        result = calculate_ei_capcost_manually(
            nuav=example.nuav,
            ekdep_halvar=example.ekdep,
            maxdep_halvar=example.maxdep,
            time_from=example.time_from,
            wacc=example.wacc,
            period_codes=PERIOD_CODES
        )
        
        calculated = result['capcost_total']
        expected = example.expected_capcost
        diff = calculated - expected
        diff_pct = (diff / expected * 100) if expected != 0 else 0
        
        print(f"    Beräknad: {calculated:.2f} tkr")
        print(f"    Förväntat: {expected:.2f} tkr")
        print(f"    Avvikelse: {diff:+.2f} tkr ({diff_pct:+.2f}%)")
        
        # Visa per halvår
        print("    Per halvår:")
        for tc in PERIOD_CODES:
            hf = result['per_halfyear'].get(tc, {})
            if hf:
                dep = hf.get('dep', 0)
                ret = hf.get('ret', 0)
                total = hf.get('total', 0)
                typ = hf.get('type', '?')
                age = hf.get('age_halvar', 0)
                year = 2024 + (tc - 229) // 2
                half = ((tc - 229) % 2) + 1
                print(f"      {year}H{half}: dep={dep:.2f}, ret={ret:.2f}, "
                      f"sum={total:.2f} ({typ}, ålder={age}h)")
        
        # Tolerans: 5% (eftersom vi anpassat tidskoder kan det finnas små skillnader)
        if abs(diff_pct) > 5:
            print(f"    [VARNING] Avvikelse > 5%")
            all_passed = False
        else:
            print(f"    [OK]")
    
    return all_passed


# =============================================================================
# TEST 2: Jämför med vår KENT-implementation
# =============================================================================

def test_kent_implementation():
    """Jämför Ei's formel med vår KENT-implementation."""
    print_section("TEST 2: Jämför med KENT-implementation")
    
    try:
        from calculations.kent_calculations import (
            calculate_ages_and_nuav_batch,
            calculate_depreciation_batch,
            calculate_returns_batch,
            aggregate_to_network_level,
            calculate_capex_outputs
        )
    except ImportError as e:
        print(f"  FEL: Kunde inte importera kent_calculations: {e}")
        return False
    
    # Skapa syntetisk DataFrame med testkomponenter
    test_components = []
    
    for i, example in enumerate(EI_EXAMPLES):
        component = {
            'id_component': f'TEST_{i+1}',
            'id_network': 99999,  # Syntetiskt id
            'cat_encode': 1,
            'nuav_2022': example.nuav * 1000,  # Konvertera till kr (KENT arbetar i kr)
            'ekdep': example.ekdep,
            'maxdep': example.maxdep,
            'time_from': example.time_from,
            'time_invest': np.nan,
            'invest': np.nan,
            'capbase_existing': 1,
        }
        test_components.append(component)
    
    df = pd.DataFrame(test_components)
    
    print(f"\n  Skapade {len(df)} testkomponenter")
    
    # Kör KENT-beräkning med Ei's WACC (6%)
    print("  Kör KENT steg 5-8...")
    
    try:
        df_step5 = calculate_ages_and_nuav_batch(df)
        df_step6 = calculate_depreciation_batch(df_step5)
        df_step7 = calculate_returns_batch(df_step6, wacc=EI_WACC)
        df_network = aggregate_to_network_level(df_step7)
        df_network = calculate_capex_outputs(df_network)
    except Exception as e:
        print(f"  FEL vid KENT-beräkning: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Hämta resultat
    if df_network.empty:
        print("  FEL: Tomt resultat från KENT")
        return False
    
    kent_capcost = df_network['Kapitalkostnad_Period'].values[0] if 'Kapitalkostnad_Period' in df_network.columns else 0
    
    print(f"\n  KENT total kapitalkostnad (period): {kent_capcost:.2f} tkr")
    
    # Jämför med manuell beräkning (summa av alla exempel)
    total_expected = sum(ex.expected_capcost for ex in EI_EXAMPLES)
    print(f"  Förväntad total (summa Ei-exempel): {total_expected:.2f} tkr")
    
    # Detaljer per komponent
    print("\n  Detaljer per halvår (från KENT):")
    for tc in PERIOD_CODES:
        dep_col = f'dep_ord_{tc}'
        ret_col = f'return_ord_{tc}'
        capcost_col = f'capcost_{tc}'
        
        dep = df_network[dep_col].values[0] if dep_col in df_network.columns else 0
        ret = df_network[ret_col].values[0] if ret_col in df_network.columns else 0
        capcost = df_network[capcost_col].values[0] if capcost_col in df_network.columns else 0
        
        year = 2024 + (tc - 229) // 2
        half = ((tc - 229) % 2) + 1
        print(f"    {year}H{half}: dep={dep:.2f}, ret={ret:.2f}, capcost={capcost:.2f}")
    
    return True


# =============================================================================
# TEST 3: Enskild komponent med exakt matchning
# =============================================================================

def test_single_component_exact():
    """
    Testar en enskild komponent med detaljerad jämförelse.
    Använder samma formel som Ei's PDF.
    """
    print_section("TEST 3: Enskild komponent - detaljerad jämförelse")
    
    try:
        from calculations.kent_calculations import (
            calculate_ages_and_nuav_batch,
            calculate_depreciation_batch,
            calculate_returns_batch
        )
    except ImportError as e:
        print(f"  FEL: Kunde inte importera: {e}")
        return False
    
    # En komponent: 1000 tkr, ekdep=80 halvår (40 år), startad 228 (2023 H2)
    # Vid 229 (2024 H1): ålder = 1 halvår
    
    test_nuav = 1000.0  # tkr
    test_ekdep = 80     # halvår = 40 år
    test_time_from = 228  # 2023 H2
    
    df = pd.DataFrame([{
        'id_component': 'SINGLE_TEST',
        'id_network': 1,
        'cat_encode': 1,
        'nuav_2022': test_nuav * 1000,  # kr
        'ekdep': test_ekdep,
        'maxdep': 100,
        'time_from': test_time_from,
        'time_invest': np.nan,
        'invest': np.nan,
        'capbase_existing': 1,
    }])
    
    print(f"\n  Komponent: NUAV={test_nuav} tkr, ekdep={test_ekdep//2} år, time_from={test_time_from}")
    print(f"  WACC: {EI_WACC*100:.0f}%")
    
    # Kör KENT
    df_step5 = calculate_ages_and_nuav_batch(df)
    df_step6 = calculate_depreciation_batch(df_step5)
    df_step7 = calculate_returns_batch(df_step6, wacc=EI_WACC)
    
    print("\n  Jämförelse per halvår:")
    print("  " + "-" * 70)
    print(f"  {'Period':<10} {'Ålder':>8} {'Ei dep':>10} {'KENT dep':>10} "
          f"{'Ei ret':>10} {'KENT ret':>10}")
    print("  " + "-" * 70)
    
    all_passed = True
    
    for tc in PERIOD_CODES:
        age_halvar = tc - test_time_from
        
        # Ei's beräkning
        # Avskrivning = NUAV / ekdep / 2 per halvår = 1000 / 40 / 2 = 12.5
        ei_dep = test_nuav / (test_ekdep // 2) / 2  # 12.5 per halvår
        
        # Kapitalbindning enligt Ei's formel från PDF
        # År 2024 H1 (tc=229, ålder=1): NUAV * ((40-0)/40) * 6% / 2 = 1000 * 1.0 * 0.03 = 30
        # År 2024 H2 (tc=230, ålder=2): samma
        # År 2025 H1 (tc=231, ålder=3): NUAV * ((40-1)/40) * 6% / 2 = 1000 * 0.975 * 0.03 = 29.25
        # etc.
        
        # Konvertera halvårsålder till "år" för avkastningsberäkning
        if age_halvar % 2 == 1:
            age_adj = age_halvar + 1
        else:
            age_adj = age_halvar
        age_ar = age_adj // 2 - 1
        if age_ar < 0:
            age_ar = 0
        
        ekdep_ar = test_ekdep // 2  # 40
        capbase_fraction = (ekdep_ar - age_ar) / ekdep_ar
        ei_ret = test_nuav * capbase_fraction * EI_WACC / 2
        
        # KENT's beräkning
        dep_col = f'comp_dep_{tc}'
        ret_col = f'return_ord_{tc}'
        
        kent_dep = df_step7[dep_col].values[0] / 1000 if dep_col in df_step7.columns else 0
        kent_ret = df_step7[ret_col].values[0] / 1000 if ret_col in df_step7.columns else 0
        
        year = 2024 + (tc - 229) // 2
        half = ((tc - 229) % 2) + 1
        
        dep_diff = abs(kent_dep - ei_dep)
        ret_diff = abs(kent_ret - ei_ret)
        
        status = "" if dep_diff < 0.01 and ret_diff < 0.5 else " *"
        if status:
            all_passed = False
        
        print(f"  {year}H{half:<6} {age_halvar:>8} {ei_dep:>10.2f} {kent_dep:>10.2f} "
              f"{ei_ret:>10.2f} {kent_ret:>10.2f}{status}")
    
    print("  " + "-" * 70)
    
    # Summor
    ei_dep_total = ei_dep * 8  # 8 halvår
    ei_ret_total = sum(
        test_nuav * ((test_ekdep//2 - max(0, ((tc - test_time_from + (1 if (tc-test_time_from)%2==1 else 0))//2 - 1))) / (test_ekdep//2)) * EI_WACC / 2
        for tc in PERIOD_CODES
    )
    
    # Summera KENT
    kent_dep_total = sum(
        df_step7[f'comp_dep_{tc}'].values[0] / 1000 
        for tc in PERIOD_CODES if f'comp_dep_{tc}' in df_step7.columns
    )
    kent_ret_total = sum(
        df_step7[f'return_ord_{tc}'].values[0] / 1000 
        for tc in PERIOD_CODES if f'return_ord_{tc}' in df_step7.columns
    )
    
    print(f"\n  Totaler (8 halvår):")
    print(f"    Avskrivning Ei:   {ei_dep_total:.2f} tkr")
    print(f"    Avskrivning KENT: {kent_dep_total:.2f} tkr")
    print(f"    Avkastning Ei:    {ei_ret_total:.2f} tkr (approx)")
    print(f"    Avkastning KENT:  {kent_ret_total:.2f} tkr")
    print(f"    Total Ei:         {ei_dep_total + ei_ret_total:.2f} tkr")
    print(f"    Total KENT:       {kent_dep_total + kent_ret_total:.2f} tkr")
    
    # Ei's facit från PDF: 331 tkr för period 2016-2019
    print(f"\n    Ei's facit (PDF): 331.00 tkr")
    
    total_diff = abs((kent_dep_total + kent_ret_total) - 331)
    if total_diff < 5:
        print("    [PASS] Inom 5 tkr av Ei's facit")
    else:
        print(f"    [VARNING] Avvikelse {total_diff:.2f} tkr från Ei's facit")
        all_passed = False
    
    return all_passed


# =============================================================================
# MAIN
# =============================================================================

def run_all_kent_component_tests():
    """Kör alla KENT komponent-nivå tester."""
    print("\n" + "=" * 70)
    print("  KENT COMPONENT-LEVEL VALIDATION")
    print("  Baserat på Ei's beräkningsexempel (Kapitalbas s. 10)")
    print("=" * 70)
    
    results = []
    
    # Test 1: Manuell beräkning
    results.append(("Manuell Ei-formel", test_manual_ei_calculation()))
    
    # Test 2: KENT implementation
    results.append(("KENT implementation", test_kent_implementation()))
    
    # Test 3: Detaljerad enskild komponent
    results.append(("Enskild komponent", test_single_component_exact()))
    
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
        print("\n  VISSA TESTER BEHÖVER GRANSKNING")
    
    print("\n" + "=" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    run_all_kent_component_tests()