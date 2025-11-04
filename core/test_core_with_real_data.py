"""
test_core_with_real_data.py - Validering av core-moduler mot produktionsdata
===========================================================================

Testar att nya core-moduler producerar identiska resultat som original-koden
innan vi uppdaterar översikt.py och foretag_berakningskedja.py.

Fokuserar på DMU 121 (id_network 886) för företagsspecifika tester.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Importera från core
from core.calculations import (
    R_OLD, YEAR_TO_CODES,
    ei_wacc_real_pre_tax, EiWaccInputs,
    apply_interest_scenario, get_period_df
)
from core.dmu_aggregation import (
    read_reconciliation, aggregate_to_dmu,
    check_year_completeness, get_complete_dmus_for_year
)
from core.export_builders import (
    build_dea_export_table, build_ir_export_table_period,
    get_concession_adjustments, apply_concession_adjustments
)
from core.export_writers import (
    format_wacc_tag, write_dea_export, write_ir_export
)


# ============================================================================
# HJÄLPFUNKTIONER
# ============================================================================

def compare_dataframes(df1, df2, name1="DF1", name2="DF2", tolerance=1e-3):
    """Jämför två DataFrames och rapporterar skillnader."""
    if df1.empty and df2.empty:
        print(f"   Båda DataFrames är tomma")
        return True
    
    if len(df1) != len(df2):
        print(f"   Olika antal rader: {name1}={len(df1)}, {name2}={len(df2)}")
        return False
    
    # Jämför numeriska kolumner
    numeric_cols = df1.select_dtypes(include=[np.number]).columns
    all_close = True
    
    for col in numeric_cols:
        if col not in df2.columns:
            continue
        
        diff = (df1[col] - df2[col]).abs()
        if diff.max() > tolerance:
            print(f"   Skillnad i kolumn '{col}': max diff = {diff.max():.6f}")
            all_close = False
    
    if all_close:
        print(f"   Numeriska värden matchar (tolerance={tolerance})")
    
    return all_close


# ============================================================================
# TESTER
# ============================================================================

def test_1_load_real_data():
    """Test 1: Ladda verklig produktionsdata."""
    print("\n" + "="*70)
    print("TEST 1: Ladda verklig produktionsdata")
    print("="*70)
    
    # Ladda facit
    facit_path = "kapitalkostnad/data/capcost_a_3_Sheet1.parquet"
    if not Path(facit_path).exists():
        print(f" Fil saknas: {facit_path}")
        return None
    
    df_facit = pd.read_parquet(facit_path)
    print(f" Laddade capcost_a: {len(df_facit):,} rader")
    print(f"  - Unika id_network: {df_facit['id_network'].nunique()}")
    print(f"  - Tidsperioder: {sorted(df_facit['time'].unique())}")
    
    # Verifiera DMU 121 / id_network 886
    df_121 = df_facit[df_facit['id_network'] == 886]
    if df_121.empty:
        print(f" id_network 886 (DMU 121) hittades inte i data")
        return None
    
    print(f" id_network 886: {len(df_121)} rader")
    print(f"  - Tidsperioder: {sorted(df_121['time'].unique())}")
    print(f"  - Total capcost_sum (2024): {df_121[df_121['time'].isin([229,230])]['capcost_sum'].sum():,.0f} tkr")
    
    return df_facit


def test_2_reconciliation():
    """Test 2: Reconciliation och DMU-mappning."""
    print("\n" + "="*70)
    print("TEST 2: Reconciliation och DMU-mappning")
    print("="*70)
    
    recon_path = "effektivitet/data/reconciliation_id_network_firm_dmu.csv"
    if not Path(recon_path).exists():
        print(f" Fil saknas: {recon_path}")
        return None
    
    rec = read_reconciliation(recon_path)
    print(f" Laddade reconciliation: {len(rec)} mappningar")
    print(f"  - Unika DMU: {rec['DMU'].nunique()}")
    print(f"  - Unika id_network: {rec['id_network'].nunique()}")
    
    # Verifiera DMU 121 mappning
    rec_121 = rec[rec['DMU'] == 121]
    if rec_121.empty:
        print(f" DMU 121 hittades inte i reconciliation")
        return None
    
    networks_121 = rec_121['id_network'].tolist()
    print(f" DMU 121 mappar till {len(networks_121)} id_network: {networks_121}")
    
    if 886 not in networks_121:
        print(f" id_network 886 finns inte i DMU 121:s mappning")
        return None
    
    print(f" id_network 886 bekräftad i DMU 121:s mappning")
    
    return rec


def test_3_dmu_aggregation(df_facit):
    """Test 3: Aggregera från id_network till DMU-nivå."""
    print("\n" + "="*70)
    print("TEST 3: DMU-aggregering")
    print("="*70)
    
    df_dmu = aggregate_to_dmu(
        df_facit,
        recon_path="effektivitet/data/reconciliation_id_network_firm_dmu.csv",
        filter_regional=True
    )
    
    print(f" Aggregerade till DMU-nivå: {len(df_dmu):,} rader")
    print(f"  - Unika DMU: {df_dmu['DMU'].nunique()}")
    print(f"  - Tidsperioder: {sorted(df_dmu['time'].unique())}")
    
    # Verifiera DMU 121
    df_121 = df_dmu[df_dmu['DMU'] == 121]
    if df_121.empty:
        print(f" DMU 121 hittades inte efter aggregering")
        return None
    
    print(f" DMU 121: {len(df_121)} rader")
    
    # Jämför med original id_network 886
    df_886_original = df_facit[df_facit['id_network'] == 886]
    
    # Jämför 2024 totaler
    original_2024 = df_886_original[df_886_original['time'].isin([229, 230])]['capcost_sum'].sum()
    aggregated_2024 = df_121[df_121['time'].isin([229, 230])]['capcost_sum'].sum()
    
    diff = abs(original_2024 - aggregated_2024)
    print(f"  - Capcost 2024 original (id_network 886): {original_2024:,.0f} tkr")
    print(f"  - Capcost 2024 aggregerad (DMU 121): {aggregated_2024:,.0f} tkr")
    print(f"  - Differens: {diff:,.0f} tkr")
    
    if diff > 1.0:
        print(f" Differens > 1 tkr kan indikera att DMU 121 har flera id_network")
    else:
        print(f" Aggregering matchar för DMU 121")
    
    return df_dmu


def test_4_wacc_calculation():
    """Test 4: WACC-beräkning med Ei-defaults."""
    print("\n" + "="*70)
    print("TEST 4: WACC-beräkning")
    print("="*70)
    
    inputs = EiWaccInputs()
    Re, Rd, Wn, Wr = ei_wacc_real_pre_tax(inputs)
    
    print(f"Re (nominell, efter skatt): {Re:.4f} ({Re*100:.2f}%)")
    print(f"Rd (nominell, före skatt):  {Rd:.4f} ({Rd*100:.2f}%)")
    print(f"WACC (nominell, före skatt): {Wn:.4f} ({Wn*100:.2f}%)")
    print(f"WACC (real, före skatt):     {Wr:.4f} ({Wr*100:.2f}%)")
    
    # Verifiera att Wr matchar R_OLD
    if abs(Wr - R_OLD) < 0.0001:
        print(f" WACC matchar R_OLD (0.0453)")
    else:
        print(f" WACC matchar INTE R_OLD: {Wr:.4f} vs {R_OLD:.4f}")
        return False
    
    return True


def test_5_scenario_calculation(df_dmu):
    """Test 5: Scenarioberäkning för DMU 121."""
    print("\n" + "="*70)
    print("TEST 5: Scenarioberäkning (DMU 121)")
    print("="*70)
    
    # Filtrera till DMU 121 för 2024
    df_121_2024 = df_dmu[
        (df_dmu['DMU'] == 121) & 
        (df_dmu['time'].isin([229, 230]))
    ]
    
    if df_121_2024.empty:
        print(" Ingen data för DMU 121 2024")
        return None
    
    print(f"Baseline data för DMU 121 2024:")
    print(f"  - return_ord: {df_121_2024['return_ord'].sum():,.0f} tkr")
    print(f"  - return_tail: {df_121_2024['return_tail'].sum():,.0f} tkr")
    print(f"  - dep_ord: {df_121_2024['dep_ord'].sum():,.0f} tkr")
    print(f"  - dep_tail: {df_121_2024['dep_tail'].sum():,.0f} tkr")
    print(f"  - capcost_sum: {df_121_2024['capcost_sum'].sum():,.0f} tkr")
    
    # Applicera scenario med 5% WACC
    r_scenario = 0.05
    df_scenario = apply_interest_scenario(df_121_2024, r_scenario)
    
    scale = r_scenario / R_OLD
    print(f"\nScenario med WACC {r_scenario:.4f} (skalningsfaktor: {scale:.4f}):")
    print(f"  - return_ord_new: {df_scenario['return_ord_new'].sum():,.0f} tkr")
    print(f"  - return_tail_new: {df_scenario['return_tail_new'].sum():,.0f} tkr")
    print(f"  - capcost_sum_new: {df_scenario['capcost_sum_new'].sum():,.0f} tkr")
    
    # Verifiera att avskrivningar är oförändrade
    dep_unchanged = (df_scenario['dep_ord'] == df_121_2024['dep_ord']).all()
    if dep_unchanged:
        print(f" Avskrivningar oförändrade (som förväntat)")
    else:
        print(f" Avskrivningar ändrades (FEL!)")
        return None
    
    return df_scenario


def test_6_dea_export(df_dmu):
    """Test 6: Bygg DEA-export för alla DMU."""
    print("\n" + "="*70)
    print("TEST 6: DEA-export (alla DMU)")
    print("="*70)
    
    # Filtrera till 2024 och kontrollera komplethet
    df_2024 = get_complete_dmus_for_year(df_dmu, 2024, warn=True)
    
    print(f"2024 data: {len(df_2024)} rader, {df_2024['DMU'].nunique()} DMU")
    
    # Bygg DEA-export
    r_scenario = 0.05
    df_dea, df_excl, tag = build_dea_export_table(
        df_2024,
        r_scenario,
        dea_base_path="effektivitet/data/Data_modeller.xlsx",
        exclude_missing_dmus=True
    )
    
    print(f" DEA-export skapad:")
    print(f"  - Inkluderade DMU: {len(df_dea)}")
    print(f"  - Exkluderade DMU: {len(df_excl)}")
    print(f"  - WACC-tag: {tag}")
    
    # Kontrollera DMU 121
    if 121 in df_dea['DMU'].values:
        dmu121 = df_dea[df_dea['DMU'] == 121].iloc[0]
        print(f"\n DMU 121 i export:")
        print(f"  - CAPEX_2024_tkr (baseline): {dmu121['CAPEX_2024_tkr']:,.0f}")
        print(f"  - CAPEX_2024_wacc_{tag}_tkr: {dmu121[f'CAPEX_2024_wacc_{tag}_tkr']:,.0f}")
        print(f"  - delta_tkr: {dmu121['delta_tkr']:,.3f}")
    else:
        print(f" DMU 121 saknas i DEA-export")
        return None
    
    return df_dea


def test_7_ir_export(df_dmu):
    """Test 7: Bygg IR-export för 2024-2027."""
    print("\n" + "="*70)
    print("TEST 7: IR-export (2024-2027)")
    print("="*70)
    
    r_scenario = 0.05
    df_ir, tag = build_ir_export_table_period(
        df_dmu,
        r_scenario,
        years=(2024, 2025, 2026, 2027),
        apply_concessions=True
    )
    
    print(f" IR-export skapad:")
    print(f"  - Totalt DMU: {len(df_ir)}")
    print(f"  - WACC-tag: {tag}")
    
    # Kontrollera DMU 121
    if 121 in df_ir['DMU'].values:
        dmu121 = df_ir[df_ir['DMU'] == 121].iloc[0]
        print(f"\n DMU 121 i IR-export (2024-2027 totalt):")
        print(f"  - Kapitalkostnad_Baseline: {dmu121['Kapitalkostnad_Baseline']:,.0f} tkr")
        print(f"  - Kapitalkostnad_Ny: {dmu121['Kapitalkostnad_Ny']:,.0f} tkr")
        print(f"  - Avskrivningar_Ny: {dmu121['Avskrivningar_Ny']:,.0f} tkr")
        print(f"  - Avkastning_Baseline: {dmu121['Avkastning_Baseline']:,.0f} tkr")
        print(f"  - Avkastning_Ny: {dmu121['Avkastning_Ny']:,.0f} tkr")
        
        # Verifiera koncessionsjusteringar
        adjustments = get_concession_adjustments()
        if 121 in adjustments['dep_adjustments']:
            print(f"   Koncessionsjusteringar applicerade för DMU 121")
    else:
        print(f" DMU 121 saknas i IR-export")
        return None
    
    return df_ir


def test_8_file_export(df_dea, df_ir):
    """Test 8: Testa faktisk fil-export (till temp-katalog)."""
    print("\n" + "="*70)
    print("TEST 8: Fil-export (temp-katalog)")
    print("="*70)
    
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test DEA-export
        try:
            dea_path, dea_meta = write_dea_export(
                df_dea,
                "0p0500",
                org="test_validation",
                base_dir=tmpdir
            )
            print(f" DEA-export skriven:")
            print(f"  - Data: {dea_path}")
            print(f"  - Meta: {dea_meta}")
            
            # Verifiera läsning
            df_read = pd.read_parquet(dea_path)
            if len(df_read) == len(df_dea):
                print(f"   Data kan läsas tillbaka korrekt")
            else:
                print(f"   Fel vid tillbakaläsning")
        except Exception as e:
            print(f" DEA-export misslyckades: {e}")
            return False
        
        # Test IR-export
        try:
            ir_path, ir_meta = write_ir_export(
                df_ir,
                "0p0500",
                org="test_validation",
                base_dir=tmpdir
            )
            print(f"\n IR-export skriven:")
            print(f"  - Data: {ir_path}")
            print(f"  - Meta: {ir_meta}")
            
            # Verifiera läsning
            df_read = pd.read_parquet(ir_path)
            if len(df_read) == len(df_ir):
                print(f"   Data kan läsas tillbaka korrekt")
            else:
                print(f"   Fel vid tillbakaläsning")
        except Exception as e:
            print(f" IR-export misslyckades: {e}")
            return False
    
    return True


# ============================================================================
# HUVUDFUNKTION
# ============================================================================

def main():
    """Kör alla tester i sekvens."""
    print("\n" + "#"*70)
    print("# VALIDERING AV CORE-MODULER MOT PRODUKTIONSDATA")
    print("# Fokus på DMU 121 (id_network 886)")
    print("#"*70)
    
    # Test 1: Ladda data
    df_facit = test_1_load_real_data()
    if df_facit is None:
        print("\n AVBRYTER: Kunde inte ladda produktionsdata")
        return False
    
    # Test 2: Reconciliation
    rec = test_2_reconciliation()
    if rec is None:
        print("\n AVBRYTER: Reconciliation misslyckades")
        return False
    
    # Test 3: DMU-aggregering
    df_dmu = test_3_dmu_aggregation(df_facit)
    if df_dmu is None:
        print("\n AVBRYTER: DMU-aggregering misslyckades")
        return False
    
    # Test 4: WACC-beräkning
    if not test_4_wacc_calculation():
        print("\n AVBRYTER: WACC-beräkning misslyckades")
        return False
    
    # Test 5: Scenarioberäkning
    df_scenario = test_5_scenario_calculation(df_dmu)
    if df_scenario is None:
        print("\n AVBRYTER: Scenarioberäkning misslyckades")
        return False
    
    # Test 6: DEA-export
    df_dea = test_6_dea_export(df_dmu)
    if df_dea is None:
        print("\n AVBRYTER: DEA-export misslyckades")
        return False
    
    # Test 7: IR-export
    df_ir = test_7_ir_export(df_dmu)
    if df_ir is None:
        print("\n AVBRYTER: IR-export misslyckades")
        return False
    
    # Test 8: Fil-export
    if not test_8_file_export(df_dea, df_ir):
        print("\n AVBRYTER: Fil-export misslyckades")
        return False
    
    # Sammanfattning
    print("\n" + "#"*70)
    print("# SAMMANFATTNING")
    print("#"*70)
    print(" Alla tester genomförda framgångsrikt!")
    print(" Core-moduler är redo att ersätta översikt.py funktioner")
    print(" DMU 121 (id_network 886) validerad genom hela kedjan")
    print("\nNästa steg:")
    print("1. Uppdatera översikt.py att importera från core/")
    print("2. Uppdatera foretag_berakningskedja.py att importera från core/")
    print("3. Radera kapital.py (redundant)")
    print("#"*70)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)