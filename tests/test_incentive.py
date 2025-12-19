"""
tests/test_incentive_integration.py

INTEGRATIONSTEST för incitamentjusteringar i pipelinen.

Testar att:
1. run_pipeline() inkluderar incitamentberäkning
2. PostDeaStageOutput.all_incentives är korrekt ifylld
3. Intaktsram_Total inkluderar Incitamentjustering_Total
4. Formeln är korrekt för alla capex_methods

Kör med: python test_incentive_integration.py
"""

import sys
from pathlib import Path

# Säkerställ att projektroten finns i path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from typing import List, Tuple
from dataclasses import dataclass


# =============================================================================
# TEST RESULT STRUCTURE
# =============================================================================

@dataclass
class IntegrationTestResult:
    """Resultat från ett integrationstest."""
    test_namn: str
    status: str  # PASS, FAIL, SKIP
    detaljer: str = ""


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(result: IntegrationTestResult):
    status_symbol = {"PASS": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}
    symbol = status_symbol.get(result.status, "[?]")
    print(f"  {symbol} {result.test_namn}")
    if result.detaljer:
        for line in result.detaljer.split("\n"):
            print(f"       {line}")


# =============================================================================
# TEST 1: PIPELINE MED BASELINE METOD
# =============================================================================

def test_pipeline_baseline_method() -> IntegrationTestResult:
    """
    Test 1: Kör hela pipelinen med baseline capex_method.
    
    Verifierar:
    - PostDeaStageOutput.all_incentives är inte None
    - Incitamentjustering_Total finns i intäktsram
    - Intaktsram_Total = summa av alla komponenter inkl. incitament
    """
    print_section("TEST 1: PIPELINE MED BASELINE METOD")
    
    try:
        from data_loaders import load_baseline_data
        from pipeline.core import run_pipeline
        from config import CaseDefinition
        from config.case_definition import (
            PreDeaConfig, DeaConfig, PostDeaConfig,
            CapexMethod, EfficiencyMethod
        )
        
        # Ladda baseline
        print("  Laddar baseline data...")
        baseline = load_baseline_data()
        
        # Skapa case config med baseline metod
        case_config = CaseDefinition(
            name="test_baseline_incentives",
            user_reid="REL00001",
            pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
            dea=DeaConfig(method=EfficiencyMethod.BASELINE),
            post_dea=PostDeaConfig()
        )
        
        # Kör pipelinen
        print("  Kör run_pipeline()...")
        result = run_pipeline(baseline, case_config)
        
        # Verifiera att all_incentives finns
        print("  Verifierar PostDeaStageOutput.all_incentives...")
        if result.post_dea.all_incentives is None:
            return IntegrationTestResult(
                "Pipeline baseline - incitament", "FAIL",
                "all_incentives är None - incitament inte integrerat i pipeline"
            )
        
        all_inc = result.post_dea.all_incentives
        n_companies = len(all_inc)
        print(f"    Incitament beräknat för {n_companies} företag")
        
        # Verifiera kolumner
        required_cols = ['REId', 'Incitamentjustering_Total', 'Missing_Incentive_Data']
        missing_cols = [c for c in required_cols if c not in all_inc.columns]
        if missing_cols:
            return IntegrationTestResult(
                "Pipeline baseline - incitament", "FAIL",
                f"Saknade kolumner i all_incentives: {missing_cols}"
            )
        
        # Verifiera att intäktsram inkluderar incitament
        print("  Verifierar intäktsram-integration...")
        ir = result.post_dea.all_intaktsram
        
        if 'Incitamentjustering_Total' not in ir.columns:
            return IntegrationTestResult(
                "Pipeline baseline - incitament", "FAIL",
                "Incitamentjustering_Total saknas i all_intaktsram"
            )
        
        # Verifiera formeln för ett företag
        print("  Verifierar intäktsram-formeln för REL00001...")
        user_ir = result.post_dea.user_intaktsram
        
        # Beräkna förväntad total
        expected_total = (
            user_ir.get('Kapitalkostnad_Total', 0) +
            user_ir.get('Paverkbara_Periodsumma', 0) +
            user_ir.get('Opaverkbara_Kostnader', 0) +
            user_ir.get('Flexibilitetstjanster', 0) +
            user_ir.get('Avbrottsersattning_12_24h', 0) -
            user_ir.get('Avdrag_Statligt_Stod', 0) +
            user_ir.get('Incitamentjustering_Total', 0)
        )
        
        actual_total = user_ir.get('Intaktsram_Total', 0)
        diff = abs(expected_total - actual_total)
        
        print(f"    Förväntad total: {expected_total:,.0f} tkr")
        print(f"    Faktisk total:   {actual_total:,.0f} tkr")
        print(f"    Differens:       {diff:,.2f} tkr")
        
        # Tolerans för avrundning
        if diff > 1.0:
            return IntegrationTestResult(
                "Pipeline baseline - incitament", "FAIL",
                f"Intaktsram_Total ({actual_total:,.0f}) != beräknad summa ({expected_total:,.0f})"
            )
        
        # Visa incitamentjusteringen
        inc_total = user_ir.get('Incitamentjustering_Total', 0)
        print(f"\n    REL00001 Incitamentjustering: {inc_total:,.0f} tkr")
        
        return IntegrationTestResult(
            "Pipeline baseline - incitament", "PASS",
            f"all_incentives OK ({n_companies} företag), formel verifierad"
        )
        
    except ImportError as e:
        return IntegrationTestResult(
            "Pipeline baseline - incitament", "FAIL",
            f"Import error: {e}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return IntegrationTestResult(
            "Pipeline baseline - incitament", "FAIL",
            f"Exception: {e}"
        )


# =============================================================================
# TEST 2: PIPELINE MED WACC_SCALING METOD
# =============================================================================

def test_pipeline_wacc_scaling_method() -> IntegrationTestResult:
    """
    Test 2: Kör hela pipelinen med wacc_scaling capex_method.
    
    Verifierar:
    - Incitament beräknas med korrekt avkastning per år (skalad)
    - Intäktsram inkluderar incitament
    """
    print_section("TEST 2: PIPELINE MED WACC_SCALING METOD")
    
    try:
        from data_loaders import load_baseline_data
        from pipeline.core import run_pipeline
        from config import CaseDefinition
        from config.case_definition import (
            PreDeaConfig, DeaConfig, PostDeaConfig,
            CapexMethod, EfficiencyMethod
        )
        
        # Ladda baseline
        print("  Laddar baseline data...")
        baseline = load_baseline_data()
        
        # Skapa case config med wacc_scaling (5.5% istället för 4.53%)
        new_wacc = 0.055
        case_config = CaseDefinition(
            name="test_wacc_scaling_incentives",
            user_reid="REL00001",
            pre_dea=PreDeaConfig(
                method=CapexMethod.WACC_SCALING,
                wacc=new_wacc
            ),
            dea=DeaConfig(method=EfficiencyMethod.DEA),  # Måste köra ny DEA
            post_dea=PostDeaConfig()
        )
        
        # Kör pipelinen
        print(f"  Kör run_pipeline() med WACC={new_wacc}...")
        result = run_pipeline(baseline, case_config)
        
        # Verifiera att incitament finns
        if result.post_dea.all_incentives is None:
            return IntegrationTestResult(
                "Pipeline wacc_scaling - incitament", "FAIL",
                "all_incentives är None"
            )
        
        all_inc = result.post_dea.all_incentives
        print(f"    Incitament beräknat för {len(all_inc)} företag")
        
        # Verifiera att wacc_used är korrekt
        print(f"    capex_method: {result.pre_dea.capex_method}")
        print(f"    wacc_used: {result.pre_dea.wacc_used}")
        
        if result.pre_dea.wacc_used != new_wacc:
            return IntegrationTestResult(
                "Pipeline wacc_scaling - incitament", "FAIL",
                f"wacc_used ({result.pre_dea.wacc_used}) != förväntad ({new_wacc})"
            )
        
        # Verifiera formeln
        user_ir = result.post_dea.user_intaktsram
        
        expected_total = (
            user_ir.get('Kapitalkostnad_Total', 0) +
            user_ir.get('Paverkbara_Periodsumma', 0) +
            user_ir.get('Opaverkbara_Kostnader', 0) +
            user_ir.get('Flexibilitetstjanster', 0) +
            user_ir.get('Avbrottsersattning_12_24h', 0) -
            user_ir.get('Avdrag_Statligt_Stod', 0) +
            user_ir.get('Incitamentjustering_Total', 0)
        )
        
        actual_total = user_ir.get('Intaktsram_Total', 0)
        diff = abs(expected_total - actual_total)
        
        print(f"    Intaktsram_Total: {actual_total:,.0f} tkr")
        print(f"    Incitamentjustering: {user_ir.get('Incitamentjustering_Total', 0):,.0f} tkr")
        
        if diff > 1.0:
            return IntegrationTestResult(
                "Pipeline wacc_scaling - incitament", "FAIL",
                f"Formelverifiering misslyckades: diff={diff:,.2f}"
            )
        
        return IntegrationTestResult(
            "Pipeline wacc_scaling - incitament", "PASS",
            f"WACC={new_wacc}, incitament integrerat, formel OK"
        )
        
    except ImportError as e:
        return IntegrationTestResult(
            "Pipeline wacc_scaling - incitament", "FAIL",
            f"Import error: {e}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return IntegrationTestResult(
            "Pipeline wacc_scaling - incitament", "FAIL",
            f"Exception: {e}"
        )


# =============================================================================
# TEST 3: VERIFIERA ATT INCITAMENT PÅVERKAR INTÄKTSRAM
# =============================================================================

def test_incentive_affects_intaktsram() -> IntegrationTestResult:
    """
    Test 3: Verifiera att incitamentjustering faktiskt påverkar Intaktsram_Total.
    
    Jämför intäktsram med och utan incitament för att säkerställa
    att Incitamentjustering_Total adderas korrekt.
    """
    print_section("TEST 3: INCITAMENT PÅVERKAR INTÄKTSRAM")
    
    try:
        from data_loaders import load_baseline_data
        from pipeline.core import run_pipeline
        from config import CaseDefinition
        from config.case_definition import (
            PreDeaConfig, DeaConfig, PostDeaConfig,
            CapexMethod, EfficiencyMethod
        )
        
        # Ladda baseline
        baseline = load_baseline_data()
        
        # Kör pipeline
        case_config = CaseDefinition(
            name="test_incentive_effect",
            user_reid="REL00001",
            pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
            dea=DeaConfig(method=EfficiencyMethod.BASELINE),
            post_dea=PostDeaConfig()
        )
        
        print("  Kör pipeline...")
        result = run_pipeline(baseline, case_config)
        
        # Hämta intäktsram-data
        ir = result.post_dea.all_intaktsram
        
        # Verifiera att icke-noll incitament påverkar intäktsram
        print("  Analyserar incitamenteffekt...")
        
        # Hitta företag med signifikant incitament (> 1000 tkr eller < -1000 tkr)
        ir_with_inc = ir[ir['Incitamentjustering_Total'].abs() > 1000]
        
        if len(ir_with_inc) == 0:
            return IntegrationTestResult(
                "Incitament påverkar intäktsram", "SKIP",
                "Inga företag med signifikant incitament (>1000 tkr) hittades"
            )
        
        print(f"    Företag med |incitament| > 1000 tkr: {len(ir_with_inc)}")
        
        # För varje sådant företag, verifiera formeln
        errors = []
        for _, row in ir_with_inc.head(5).iterrows():
            reid = row['REId']
            inc = row['Incitamentjustering_Total']
            
            # Beräkna summa utan incitament
            sum_without_inc = (
                row.get('Kapitalkostnad_Total', 0) +
                row.get('Paverkbara_Periodsumma', 0) +
                row.get('Opaverkbara_Kostnader', 0) +
                row.get('Flexibilitetstjanster', 0) +
                row.get('Avbrottsersattning_12_24h', 0) -
                row.get('Avdrag_Statligt_Stod', 0)
            )
            
            expected_with_inc = sum_without_inc + inc
            actual = row['Intaktsram_Total']
            diff = abs(expected_with_inc - actual)
            
            print(f"    {reid}: Inc={inc:+,.0f}, Total={actual:,.0f}, diff={diff:.2f}")
            
            if diff > 1.0:
                errors.append(f"{reid}: diff={diff:.2f}")
        
        if errors:
            return IntegrationTestResult(
                "Incitament påverkar intäktsram", "FAIL",
                f"Formelfel för: {', '.join(errors)}"
            )
        
        return IntegrationTestResult(
            "Incitament påverkar intäktsram", "PASS",
            f"Verifierade {min(5, len(ir_with_inc))} företag - formel korrekt"
        )
        
    except ImportError as e:
        return IntegrationTestResult(
            "Incitament påverkar intäktsram", "FAIL",
            f"Import error: {e}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return IntegrationTestResult(
            "Incitament påverkar intäktsram", "FAIL",
            f"Exception: {e}"
        )


# =============================================================================
# TEST 4: VERIFIERA MISSING_INCENTIVE_DATA FLAGGA
# =============================================================================

def test_missing_data_handling() -> IntegrationTestResult:
    """
    Test 4: Verifiera att företag med saknad incitamentdata hanteras korrekt.
    
    REL00139, REL00168, REL00177, REL03050 ska ha:
    - Missing_Incentive_Data = True
    - Incitamentjustering_Total = 0 eller NaN
    """
    print_section("TEST 4: HANTERING AV SAKNAD DATA")
    
    try:
        from data_loaders import load_baseline_data
        from pipeline.core import run_pipeline
        from config import CaseDefinition
        from config.case_definition import (
            PreDeaConfig, DeaConfig, PostDeaConfig,
            CapexMethod, EfficiencyMethod
        )
        
        MISSING_REIDS = ['REL00139', 'REL00168', 'REL00177', 'REL03050']
        
        # Ladda och kör pipeline
        baseline = load_baseline_data()
        case_config = CaseDefinition(
            name="test_missing_data",
            user_reid="REL00001",
            pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
            dea=DeaConfig(method=EfficiencyMethod.BASELINE),
            post_dea=PostDeaConfig()
        )
        
        print("  Kör pipeline...")
        result = run_pipeline(baseline, case_config)
        
        if result.post_dea.all_incentives is None:
            return IntegrationTestResult(
                "Hantering av saknad data", "SKIP",
                "all_incentives är None"
            )
        
        all_inc = result.post_dea.all_incentives
        
        # Kontrollera varje företag med saknad data
        print("  Kontrollerar företag med saknad data...")
        errors = []
        
        for reid in MISSING_REIDS:
            row = all_inc[all_inc['REId'] == reid]
            
            if row.empty:
                print(f"    {reid}: Finns inte i data (OK om företaget saknas)")
                continue
            
            missing_flag = row['Missing_Incentive_Data'].iloc[0]
            inc_total = row['Incitamentjustering_Total'].iloc[0]
            
            print(f"    {reid}: Missing={missing_flag}, Inc={inc_total}")
            
            if not missing_flag:
                errors.append(f"{reid}: Missing_Incentive_Data borde vara True")
            
            # Incitament ska vara 0 eller NaN
            if pd.notna(inc_total) and abs(inc_total) > 0.01:
                errors.append(f"{reid}: Incitament borde vara 0 eller NaN, är {inc_total}")
        
        if errors:
            return IntegrationTestResult(
                "Hantering av saknad data", "FAIL",
                "\n".join(errors)
            )
        
        return IntegrationTestResult(
            "Hantering av saknad data", "PASS",
            f"Alla {len(MISSING_REIDS)} företag hanteras korrekt"
        )
        
    except ImportError as e:
        return IntegrationTestResult(
            "Hantering av saknad data", "FAIL",
            f"Import error: {e}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return IntegrationTestResult(
            "Hantering av saknad data", "FAIL",
            f"Exception: {e}"
        )


# =============================================================================
# TEST 5: JÄMFÖR INTÄKTSRAM MED OCH UTAN INCITAMENT
# =============================================================================

def test_intaktsram_decomposition() -> IntegrationTestResult:
    """
    Test 5: Detaljerad dekomposition av intäktsram för verifiering.
    
    Visar alla komponenter och verifierar att summan stämmer.
    """
    print_section("TEST 5: INTÄKTSRAM DEKOMPOSITION")
    
    try:
        from data_loaders import load_baseline_data
        from pipeline.core import run_pipeline
        from config import CaseDefinition
        from config.case_definition import (
            PreDeaConfig, DeaConfig, PostDeaConfig,
            CapexMethod, EfficiencyMethod
        )
        
        baseline = load_baseline_data()
        case_config = CaseDefinition(
            name="test_decomposition",
            user_reid="REL00001",
            pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
            dea=DeaConfig(method=EfficiencyMethod.BASELINE),
            post_dea=PostDeaConfig()
        )
        
        print("  Kör pipeline för REL00001...")
        result = run_pipeline(baseline, case_config)
        
        user_ir = result.post_dea.user_intaktsram
        
        # Visa dekomposition
        print("\n  INTÄKTSRAM DEKOMPOSITION (REL00001):")
        print("  " + "-" * 50)
        
        components = [
            ('Kapitalkostnad', 'Kapitalkostnad_Total', 1),
            ('Påverkbara kostnader', 'Paverkbara_Periodsumma', 1),
            ('Opåverkbara kostnader', 'Opaverkbara_Kostnader', 1),
            ('Flexibilitetstjänster', 'Flexibilitetstjanster', 1),
            ('Avbrottsersättning 12-24h', 'Avbrottsersattning_12_24h', 1),
            ('Avdrag statligt stöd', 'Avdrag_Statligt_Stod', -1),
            ('Incitamentjustering', 'Incitamentjustering_Total', 1),
        ]
        
        calculated_sum = 0
        for label, col, sign in components:
            val = user_ir.get(col, 0) * sign
            calculated_sum += val
            print(f"    {label:30s} {val:>15,.0f} tkr")
        
        print("  " + "-" * 50)
        print(f"    {'BERÄKNAD SUMMA':30s} {calculated_sum:>15,.0f} tkr")
        print(f"    {'INTÄKTSRAM_TOTAL':30s} {user_ir['Intaktsram_Total']:>15,.0f} tkr")
        
        diff = abs(calculated_sum - user_ir['Intaktsram_Total'])
        print(f"    {'DIFFERENS':30s} {diff:>15,.2f} tkr")
        
        # Visa incitamentdetaljer om tillgängliga
        if result.post_dea.all_incentives is not None:
            inc_row = result.post_dea.all_incentives[
                result.post_dea.all_incentives['REId'] == 'REL00001'
            ]
            if not inc_row.empty:
                print("\n  INCITAMENT DETALJER:")
                print("  " + "-" * 50)
                for col in ['Kvalitetsjustering_Total', 'Natforlustjustering_Total', 
                           'Belastningsjustering_Total']:
                    if col in inc_row.columns:
                        val = inc_row[col].iloc[0]
                        label = col.replace('_Total', '').replace('justering', '')
                        print(f"    {label:30s} {val:>15,.0f} tkr")
        
        if diff > 1.0:
            return IntegrationTestResult(
                "Intäktsram dekomposition", "FAIL",
                f"Summa stämmer inte: diff={diff:.2f}"
            )
        
        return IntegrationTestResult(
            "Intäktsram dekomposition", "PASS",
            "Alla komponenter summerar till Intaktsram_Total"
        )
        
    except ImportError as e:
        return IntegrationTestResult(
            "Intäktsram dekomposition", "FAIL",
            f"Import error: {e}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return IntegrationTestResult(
            "Intäktsram dekomposition", "FAIL",
            f"Exception: {e}"
        )


# =============================================================================
# SAMMANFATTNING
# =============================================================================

def print_summary(results: List[IntegrationTestResult]):
    print_section("SAMMANFATTNING")
    
    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_skip = sum(1 for r in results if r.status == "SKIP")
    
    print(f"\n  Totalt: {len(results)} tester")
    print(f"    PASS: {n_pass}")
    print(f"    FAIL: {n_fail}")
    print(f"    SKIP: {n_skip}")
    
    if n_fail > 0:
        print("\n  Misslyckade tester:")
        for r in results:
            if r.status == "FAIL":
                print(f"    - {r.test_namn}")
                if r.detaljer:
                    print(f"      {r.detaljer[:100]}...")


# =============================================================================
# MAIN
# =============================================================================

def run_all_integration_tests():
    """Kör alla integrationstester."""
    print("\n" + "=" * 70)
    print("  INCITAMENT INTEGRATIONSTEST")
    print("  Testar att incitament är korrekt integrerat i pipelinen")
    print("=" * 70)
    
    results = []
    
    # Test 1: Pipeline med baseline
    result = test_pipeline_baseline_method()
    print_result(result)
    results.append(result)
    
    # Test 2: Pipeline med wacc_scaling
    result = test_pipeline_wacc_scaling_method()
    print_result(result)
    results.append(result)
    
    # Test 3: Incitament påverkar intäktsram
    result = test_incentive_affects_intaktsram()
    print_result(result)
    results.append(result)
    
    # Test 4: Hantering av saknad data
    result = test_missing_data_handling()
    print_result(result)
    results.append(result)
    
    # Test 5: Intäktsram dekomposition
    result = test_intaktsram_decomposition()
    print_result(result)
    results.append(result)
    
    # Sammanfattning
    print_summary(results)
    
    print("\n" + "=" * 70)
    print("  INTEGRATIONSTEST KLART")
    print("=" * 70 + "\n")
    
    return results


if __name__ == "__main__":
    results = run_all_integration_tests()
    
    # Exit med felkod om något misslyckades
    n_fail = sum(1 for r in results if r.status == "FAIL")
    sys.exit(1 if n_fail > 0 else 0)