"""
tests/test_pipeline_flow.py

Test för Fas 1B: Validera att pipeline kör igenom med REId.
"""

import sys
from pathlib import Path

# Lägg till projekt-root i sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders import load_baseline_data
from config import get_baseline_config
from pipeline import run_pipeline, validate_pipeline_result


def test_load_baseline():
    """Test att baseline laddar"""
    print("\n" + "="*60)
    print("TEST: Ladda baseline data")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    print(f"✓ Laddade baseline med {len(baseline.df_all_companies)} företag")
    
    return baseline


def test_create_baseline_config():
    """Test att skapa baseline config"""
    print("\n" + "="*60)
    print("TEST: Skapa baseline config")
    print("="*60 + "\n")
    
    # Använd REL00001 (Ale El ek. för.) som test
    config = get_baseline_config(user_reid="REL00001")
    
    print(f"✓ Skapade config för {config.user_reid}")
    print(f"  - Name: {config.name}")
    print(f"  - Pre-DEA method: {config.pre_dea.method}")
    print(f"  - DEA method: {config.dea.method}")
    print(f"  - Påverkbara method: {config.post_dea.paverkbara_method}")
    
    return config


def test_run_pipeline(baseline, config):
    """Test att köra hela pipeline"""
    print("\n" + "="*60)
    print("TEST: Kör pipeline")
    print("="*60 + "\n")
    
    result = run_pipeline(baseline, config)
    
    print(f"✓ Pipeline körde framgångsrikt!")
    print(f"  - Case: {result.case_name}")
    print(f"  - User REId: {result.user_reid}")
    
    return result


def test_validate_stages(result):
    """Test att alla stages har rätt output"""
    print("\n" + "="*60)
    print("TEST: Validera stage outputs")
    print("="*60 + "\n")
    
    # Stage 1: Baseline
    print("Stage 1: Baseline")
    print(f"  - Companies: {len(result.baseline.df_all_companies)} rader")
    print(f"  - DEA baseline: {len(result.baseline.dea_baseline)} rader")
    print(f"  - WACC: {result.baseline.wacc:.4f}")
    assert len(result.baseline.df_all_companies) >= 140, "För få företag i baseline"
    print("  ✓ Baseline OK")
    
    # Stage 2: Pre-DEA
    print("\nStage 2: Pre-DEA")
    print(f"  - Companies: {len(result.pre_dea.df_all_companies)} rader")
    print(f"  - Method: {result.pre_dea.capex_method}")
    print(f"  - Modified: {result.pre_dea.capex_modified}")
    assert len(result.pre_dea.df_all_companies) == len(result.baseline.df_all_companies)
    print("  ✓ Pre-DEA OK")
    
    # Stage 3: DEA
    print("\nStage 3: DEA")
    print(f"  - Results: {len(result.dea.dea_results)} rader")
    print(f"  - Method: {result.dea.dea_method}")
    print(f"  - Executed: {result.dea.dea_executed}")
    assert len(result.dea.dea_results) == len(result.baseline.df_all_companies)
    print("  ✓ DEA OK")
    
    # Stage 4: Extraction
    print("\nStage 4: Extraction")
    print(f"  - REId: {result.extraction.user_reid}")
    print(f"  - Företag: {result.extraction.foretag}")
    print(f"  - CAPEX: {result.extraction.capex:,.0f} tkr")
    print(f"  - OPEX: {result.extraction.opex:,.0f} tkr")
    print(f"  - Efficiency: {result.extraction.efficiency}")
    print(f"  - Potential: {result.extraction.potential:.4f}")
    print(f"  - Is outlier: {result.extraction.is_outlier}")
    assert result.extraction.user_reid == result.user_reid
    print("  ✓ Extraction OK")
    
    # Stage 5: Post-DEA
    print("\nStage 5: Post-DEA")
    print(f"  - Effkrav: {result.post_dea.effkrav_proc:.2%}")
    print(f"  - Effkrav method: {result.post_dea.effkrav_method}")
    print(f"  - Påverkbara baseline: {result.post_dea.paverkbara_baseline:,.0f} tkr")
    print(f"  - Påverkbara efter effkrav: {result.post_dea.paverkbara_efter_effkrav:,.0f} tkr")
    if result.post_dea.intaktsram_total is not None:
        print(f"  - Intäktsram total: {result.post_dea.intaktsram_total:,.0f} tkr")
    assert result.post_dea.user_reid == result.user_reid
    print("  ✓ Post-DEA OK")
    
    print("\n✓ Alla stages validerade!")


def test_validate_result(result):
    """Test pipeline result validation"""
    print("\n" + "="*60)
    print("TEST: Validera pipeline result")
    print("="*60 + "\n")
    
    is_valid = validate_pipeline_result(result)
    
    print(f"✓ Pipeline result är valid: {is_valid}")


def test_multiple_companies(baseline):
    """Test att köra pipeline för flera företag"""
    print("\n" + "="*60)
    print("TEST: Testa flera företag")
    print("="*60 + "\n")
    
    # Testa med några olika REId
    test_reids = ["REL00001", "REL00043", "REL03015", "REL03030"]
    
    for reid in test_reids:
        try:
            config = get_baseline_config(user_reid=reid)
            result = run_pipeline(baseline, config)
            print(f"✓ {reid}: {result.extraction.foretag}")
        except Exception as e:
            print(f"✗ {reid}: {e}")
            raise
    
    print("\n✓ Alla företag testade framgångsrikt!")


def run_all_tests():
    """Kör alla tester för Fas 1B"""
    print("\n" + "="*70)
    print("  FAS 1B: PIPELINE SKELETT - FLOW TEST (REId)")
    print("="*70)
    
    try:
        # Test 1: Ladda baseline
        baseline = test_load_baseline()
        
        # Test 2: Skapa config
        config = test_create_baseline_config()
        
        # Test 3: Kör pipeline
        result = test_run_pipeline(baseline, config)
        
        # Test 4: Validera stages
        test_validate_stages(result)
        
        # Test 5: Validera result
        test_validate_result(result)
        
        # Test 6: Testa flera företag
        test_multiple_companies(baseline)
        
        # Sammanfattning
        print("\n" + "="*70)
        print("  ✓ ALLA TESTER GODKÄNDA!")
        print("  Fas 1B (Pipeline Skelett) är klar för nästa steg.")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*70)
        print(f"  ✗ TEST MISSLYCKADES: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)