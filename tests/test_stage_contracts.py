"""
tests/test_stage_contracts.py

Verifierar input/output-kontrakt mellan pipeline stages.
Säkerställer att kolumnnamn (Kapitalkostnad_2024, Kapitalkostnad_Period) 
hanteras konsekvent genom hela pipelinen.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_loaders import load_baseline_data
from config import get_baseline_config, create_wacc_scaling_config
from pipeline import run_pipeline
from pipeline.stages import stage_baseline, stage_pre_dea, stage_dea


def test_baseline_stage_output():
    """Test att baseline stage output har rätt struktur"""
    print("\n" + "="*60)
    print("TEST: Baseline stage output kontrakt")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    output = stage_baseline(baseline)
    
    # df_all_companies
    df = output.df_all_companies
    assert 'Kapitalkostnad_2024' in df.columns, "Kapitalkostnad_2024 saknas i baseline output"
    assert 'OPEXp' in df.columns, "OPEXp saknas"
    assert 'REId' in df.columns, "REId saknas"
    print("  df_all_companies: Kapitalkostnad_2024, OPEXp, REId finns")
    
    # dea_baseline
    assert hasattr(output, 'dea_baseline'), "dea_baseline attribut saknas"
    assert len(output.dea_baseline) > 0, "dea_baseline är tom"
    print(f"  dea_baseline: {len(output.dea_baseline)} rader")
    
    # sdf_ir ska ha Kapitalkostnad (periodsumma)
    assert hasattr(output, 'sdf_ir'), "sdf_ir attribut saknas"
    assert 'Kapitalkostnad' in output.sdf_ir.columns, "Kapitalkostnad saknas i sdf_ir"
    print("  sdf_ir: Kapitalkostnad (periodsumma) finns")
    
    # wacc
    assert output.wacc == 0.0453, f"WACC fel: {output.wacc}"
    print(f"  wacc: {output.wacc}")
    
    print("  PASS")
    return output


def test_pre_dea_baseline_output(baseline_output):
    """Test att pre_dea stage med baseline-metod har rätt output"""
    print("\n" + "="*60)
    print("TEST: Pre-DEA stage output (baseline)")
    print("="*60 + "\n")
    
    config = get_baseline_config(user_reid="REL00886")
    output = stage_pre_dea(baseline_output, config.pre_dea)
    
    df = output.df_all_companies
    
    # Måste ha Kapitalkostnad_2024 för DEA
    assert 'Kapitalkostnad_2024' in df.columns, "Kapitalkostnad_2024 saknas"
    print("  Kapitalkostnad_2024 finns (för DEA)")
    
    # Måste ha OPEXp
    assert 'OPEXp' in df.columns, "OPEXp saknas"
    print("  OPEXp finns")
    
    # Alla företag
    assert len(df) == 148, f"Förväntar 148 företag, fick {len(df)}"
    print(f"  {len(df)} företag")
    
    # capex_method
    assert output.capex_method == "baseline", f"Metod: {output.capex_method}"
    assert output.capex_modified == False, "capex_modified ska vara False för baseline"
    print(f"  capex_method: {output.capex_method}")
    print(f"  capex_modified: {output.capex_modified}")
    
    print("  PASS")
    return output


def test_pre_dea_wacc_scaling_output(baseline_output):
    """Test att pre_dea stage med WACC-skalning har rätt output"""
    print("\n" + "="*60)
    print("TEST: Pre-DEA stage output (WACC-skalning)")
    print("="*60 + "\n")
    
    config = create_wacc_scaling_config(user_reid="REL00886", new_wacc=0.05)
    output = stage_pre_dea(baseline_output, config.pre_dea)
    
    df = output.df_all_companies
    
    # Måste ha Kapitalkostnad_2024 för DEA
    assert 'Kapitalkostnad_2024' in df.columns, "Kapitalkostnad_2024 saknas"
    print("  Kapitalkostnad_2024 finns (skalad)")
    
    # capex_modified ska vara True
    assert output.capex_method == "wacc_scaling", f"Metod: {output.capex_method}"
    assert output.capex_modified == True, "capex_modified ska vara True för wacc_scaling"
    print(f"  capex_method: {output.capex_method}")
    print(f"  capex_modified: {output.capex_modified}")
    
    # Kontrollera att värden faktiskt ändrats
    baseline_kap = baseline_output.df_all_companies['Kapitalkostnad_2024'].sum()
    scaled_kap = df['Kapitalkostnad_2024'].sum()
    assert scaled_kap > baseline_kap, "Skalad kapitalkostnad borde vara högre vid högre WACC"
    print(f"  Baseline sum: {baseline_kap:,.0f} tkr")
    print(f"  Skalad sum: {scaled_kap:,.0f} tkr (+{(scaled_kap/baseline_kap-1)*100:.1f}%)")
    
    print("  PASS")
    return output


def test_dea_stage_input_requirements():
    """Test att DEA stage kräver rätt kolumner"""
    print("\n" + "="*60)
    print("TEST: DEA stage input krav")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    baseline_output = stage_baseline(baseline)
    config = get_baseline_config(user_reid="REL00886")
    pre_dea_output = stage_pre_dea(baseline_output, config.pre_dea)
    
    df = pre_dea_output.df_all_companies
    
    # DEA förväntar sig dessa kolumner (från BASELINE_DEA_SPEC)
    dea_inputs = ['Kapitalkostnad_2024', 'OPEXp']
    dea_outputs = ['CU', 'MW', 'NS', 'MWhl', 'MWhh']
    
    for col in dea_inputs:
        assert col in df.columns, f"DEA input '{col}' saknas"
    print(f"  DEA inputs: {dea_inputs}")
    
    for col in dea_outputs:
        assert col in df.columns, f"DEA output '{col}' saknas"
    print(f"  DEA outputs: {dea_outputs}")
    
    print("  PASS")


def test_dea_stage_output():
    """Test att DEA stage output har rätt struktur"""
    print("\n" + "="*60)
    print("TEST: DEA stage output kontrakt")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    baseline_output = stage_baseline(baseline)
    config = get_baseline_config(user_reid="REL00886")
    pre_dea_output = stage_pre_dea(baseline_output, config.pre_dea)
    
    dea_output = stage_dea(pre_dea_output, config.dea, baseline=baseline_output)
    
    # Resultat
    dea_results = dea_output.dea_results
    
    required = ['REId', 'Effektivitet', 'potential', 'is_outlier']
    for col in required:
        assert col in dea_results.columns, f"DEA output saknar '{col}'"
    print(f"  DEA output kolumner: {required}")
    
    # Alla företag
    assert len(dea_results) == 148, f"Förväntar 148, fick {len(dea_results)}"
    print(f"  {len(dea_results)} DEA-resultat")
    
    # Method
    assert dea_output.dea_method == "baseline", f"Metod: {dea_output.dea_method}"
    print(f"  dea_method: {dea_output.dea_method}")
    
    print("  PASS")


def test_post_dea_input_requirements():
    """Test att post_dea förväntar sig rätt kolumner för intäktsram"""
    print("\n" + "="*60)
    print("TEST: Post-DEA input krav")
    print("="*60 + "\n")
    
    # Post-DEA behöver:
    # 1. DEA-resultat (Effektivitet, potential, is_outlier)
    # 2. Kapitalkostnad för intäktsram
    #    - Baseline: Kapitalkostnad från SDF (periodsumma)
    #    - WACC-skalning: Kapitalkostnad_2024 * 4 (approximation)
    #    - KENT: Kapitalkostnad_Period (exakt periodsumma)
    
    baseline = load_baseline_data()
    
    # SDF IR ska ha periodsumma
    assert 'Kapitalkostnad' in baseline.sdf_ir.columns, "SDF saknar Kapitalkostnad"
    print("  SDF IR har 'Kapitalkostnad' (periodsumma för baseline)")
    
    # sdf_paverkbara för påverkbara beräkningar
    assert len(baseline.sdf_paverkbara) > 0, "sdf_paverkbara tom"
    print(f"  sdf_paverkbara: {len(baseline.sdf_paverkbara)} rader")
    
    print("  PASS")


def test_full_pipeline_contracts():
    """Test att hela pipelinen följer kontrakten"""
    print("\n" + "="*60)
    print("TEST: Full pipeline kontrakt")
    print("="*60 + "\n")
    
    baseline = load_baseline_data()
    config = get_baseline_config(user_reid="REL00886")
    
    result = run_pipeline(baseline, config)
    
    # Baseline stage
    assert result.baseline is not None, "Baseline saknas"
    assert 'Kapitalkostnad_2024' in result.baseline.df_all_companies.columns
    print("  Baseline: OK")
    
    # Pre-DEA stage
    assert result.pre_dea is not None, "Pre-DEA saknas"
    assert 'Kapitalkostnad_2024' in result.pre_dea.df_all_companies.columns
    print("  Pre-DEA: OK")
    
    # DEA stage
    assert result.dea is not None, "DEA saknas"
    assert 'Effektivitet' in result.dea.dea_results.columns
    print("  DEA: OK")
    
    # Extraction stage
    assert result.extraction is not None, "Extraction saknas"
    assert result.extraction.user_reid == "REL00886"
    print("  Extraction: OK")
    
    # Post-DEA stage
    assert result.post_dea is not None, "Post-DEA saknas"
    assert 'Intaktsram_Total' in result.post_dea.user_intaktsram
    print("  Post-DEA: OK")
    
    print("  PASS")


def run_all_tests():
    """Kör alla stage contract-tester"""
    print("\n" + "="*70)
    print("  TEST SUITE: STAGE CONTRACTS")
    print("="*70)
    
    try:
        baseline_output = test_baseline_stage_output()
        test_pre_dea_baseline_output(baseline_output)
        test_pre_dea_wacc_scaling_output(baseline_output)
        test_dea_stage_input_requirements()
        test_dea_stage_output()
        test_post_dea_input_requirements()
        test_full_pipeline_contracts()
        
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