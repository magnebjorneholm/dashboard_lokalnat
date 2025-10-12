"""
Moran's I-analys för masteruppsats.
Kör DEA med EI:s standardspecifikation och analyserar spatial autokorrelation
för både Effektivitet och Supereffektivitet.
"""

import sys
from pathlib import Path

# FIX: Lägg till projektroten i Python-sökvägen
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from effektiviseringskrav.backend.data_loader import load_data
from effektiviseringskrav.backend.dea_model import run_dea_model
from Moran.spatial_moran import (
    kör_komplett_spatial_analys,
    sammanfatta_lisa_resultat,
    hämta_kluster_områden
)

print("=" * 80)
print("MORAN'S I-ANALYS FÖR MASTERUPPSATS")
print("Jämför Effektivitet vs Supereffektivitet")
print("=" * 80)
print(f"Körning: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# 1. LADDA DATA OCH KÖR DEA MED EI:S STANDARDSPECIFIKATION
# ============================================================================
print("Steg 1: Laddar data och kör DEA med EI:s standardspecifikation...")
print("-" * 80)

df = load_data("effektiviseringskrav/data/Data_modeller.xlsx")

# EI:s standardspecifikation
dea_result = run_dea_model(
    df,
    rts="crs",
    trunkering_min=0.162416,
    trunkering_max=0.3,
    input_cols=["CAPEX", "OPEXp"],
    output_cols=["CU", "MW", "NS", "MWhl", "MWhh"],
    outlier_filter=True,
    outlier_krav=0.01
)

print(f" DEA klar: {len(dea_result)} företag analyserade")
print(f"  - Antal outliers: {dea_result['is_outlier'].sum()}")
print(f"  - Medel effektivitet: {dea_result['Effektivitet'].mean():.3f}")

# Kontrollera att Supereffektivitet finns
if 'Supereffektivitet' in dea_result.columns:
    print(f"  - Medel supereffektivitet: {dea_result['Supereffektivitet'].mean():.3f}")
    har_supereff = True
else:
    print("    Varning: Supereffektivitet saknas i DEA-resultat")
    har_supereff = False

# Spara DEA-resultat
output_dir = Path(__file__).parent / "resultat"
output_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M')
dea_file = output_dir / f"dea_resultat_ei_standard_{timestamp}.xlsx"
dea_result.to_excel(dea_file, index=False)
print(f" DEA-resultat sparade i: {dea_file}")

# ============================================================================
# 2A. GLOBAL MORAN'S I - EFFEKTIVITET
# ============================================================================
print("\n" + "=" * 80)
print("Steg 2A: Beräknar global Moran's I för EFFEKTIVITET")
print("-" * 80)

global_stats_eff, gdf_lisa_eff = kör_komplett_spatial_analys(
    dea_result,
    indikator="Effektivitet",
    method="knn",
    k=4
)

print(f"\nGLOBAL MORAN'S I (EFFEKTIVITET):")
print(f"  Moran's I:        {global_stats_eff['I']:.4f}")
print(f"  Förväntat värde:  {global_stats_eff['expected_I']:.4f}")
print(f"  Z-score:          {global_stats_eff['z_score']:.4f}")
print(f"  P-värde (sim):    {global_stats_eff['p_value_sim']:.4f}")
print(f"\n  Tolkning: {global_stats_eff['interpretation']}")

# ============================================================================
# 2B. GLOBAL MORAN'S I - SUPEREFFEKTIVITET
# ============================================================================
if har_supereff:
    print("\n" + "=" * 80)
    print("Steg 2B: Beräknar global Moran's I för SUPEREFFEKTIVITET")
    print("-" * 80)
    
    global_stats_super, gdf_lisa_super = kör_komplett_spatial_analys(
        dea_result,
        indikator="Supereffektivitet",
        method="knn",
        k=4
    )
    
    print(f"\nGLOBAL MORAN'S I (SUPEREFFEKTIVITET):")
    print(f"  Moran's I:        {global_stats_super['I']:.4f}")
    print(f"  Förväntat värde:  {global_stats_super['expected_I']:.4f}")
    print(f"  Z-score:          {global_stats_super['z_score']:.4f}")
    print(f"  P-värde (sim):    {global_stats_super['p_value_sim']:.4f}")
    print(f"\n  Tolkning: {global_stats_super['interpretation']}")
    
    # Jämförelse
    print("\n" + "-" * 80)
    print("JÄMFÖRELSE:")
    print(f"  Δ Moran's I:  {global_stats_super['I'] - global_stats_eff['I']:+.4f}")
    print(f"  Δ Z-score:    {global_stats_super['z_score'] - global_stats_eff['z_score']:+.4f}")
    
    if global_stats_super['I'] > global_stats_eff['I']:
        print("  → Starkare spatial autokorrelation för supereffektivitet")
    elif global_stats_super['I'] < global_stats_eff['I']:
        print("  → Svagare spatial autokorrelation för supereffektivitet")
    else:
        print("  → Liknande spatial autokorrelation")

# ============================================================================
# 3A. LOKAL MORAN'S I (LISA) - EFFEKTIVITET
# ============================================================================
print("\n" + "=" * 80)
print("Steg 3A: Identifierar lokala kluster (LISA) - EFFEKTIVITET")
print("-" * 80)

lisa_summary_eff = sammanfatta_lisa_resultat(gdf_lisa_eff)

print(f"\nLISA SAMMANFATTNING (EFFEKTIVITET):")
print(f"  Totalt antal områden:     {lisa_summary_eff['total_områden']}")
print(f"  Andel signifikanta:       {lisa_summary_eff['andel_signifikanta']:.1f}%")
print(f"\n  Kluster-fördelning:")
print(f"    HH (Högt-Högt):         {lisa_summary_eff['HH_kluster']} områden")
print(f"    LL (Lågt-Lågt):         {lisa_summary_eff['LL_kluster']} områden")
print(f"    HL (Högt-Lågt outlier): {lisa_summary_eff['HL_outliers']} områden")
print(f"    LH (Lågt-Högt outlier): {lisa_summary_eff['LH_outliers']} områden")
print(f"    NS (Ej signifikant):    {lisa_summary_eff['ej_signifikanta']} områden")

# ============================================================================
# 3B. LOKAL MORAN'S I (LISA) - SUPEREFFEKTIVITET
# ============================================================================
if har_supereff:
    print("\n" + "=" * 80)
    print("Steg 3B: Identifierar lokala kluster (LISA) - SUPEREFFEKTIVITET")
    print("-" * 80)
    
    lisa_summary_super = sammanfatta_lisa_resultat(gdf_lisa_super)
    
    print(f"\nLISA SAMMANFATTNING (SUPEREFFEKTIVITET):")
    print(f"  Totalt antal områden:     {lisa_summary_super['total_områden']}")
    print(f"  Andel signifikanta:       {lisa_summary_super['andel_signifikanta']:.1f}%")
    print(f"\n  Kluster-fördelning:")
    print(f"    HH (Högt-Högt):         {lisa_summary_super['HH_kluster']} områden")
    print(f"    LL (Lågt-Lågt):         {lisa_summary_super['LL_kluster']} områden")
    print(f"    HL (Högt-Lågt outlier): {lisa_summary_super['HL_outliers']} områden")
    print(f"    LH (Lågt-Högt outlier): {lisa_summary_super['LH_outliers']} områden")
    print(f"    NS (Ej signifikant):    {lisa_summary_super['ej_signifikanta']} områden")
    
    # Jämförelse
    print("\n" + "-" * 80)
    print("JÄMFÖRELSE AV KLUSTER:")
    print(f"  Δ Andel signifikanta: {lisa_summary_super['andel_signifikanta'] - lisa_summary_eff['andel_signifikanta']:+.1f}%")
    print(f"  Δ HH-kluster:         {lisa_summary_super['HH_kluster'] - lisa_summary_eff['HH_kluster']:+d}")
    print(f"  Δ LL-kluster:         {lisa_summary_super['LL_kluster'] - lisa_summary_eff['LL_kluster']:+d}")

# ============================================================================
# 4. DETALJERADE KLUSTER - EFFEKTIVITET
# ============================================================================
print("\n" + "=" * 80)
print("Steg 4A: Extraherar detaljerade kluster - EFFEKTIVITET")
print("-" * 80)

if lisa_summary_eff['HH_kluster'] > 0:
    print("\nHÖGT-HÖGT KLUSTER (EFFEKTIVITET):")
    print("-" * 80)
    hh_kluster_eff = hämta_kluster_områden(gdf_lisa_eff, 'HH')
    print(hh_kluster_eff.head(10).to_string(index=False))
    if len(hh_kluster_eff) > 10:
        print(f"... och {len(hh_kluster_eff) - 10} till")

if lisa_summary_eff['LL_kluster'] > 0:
    print("\nLÅGT-LÅGT KLUSTER (EFFEKTIVITET):")
    print("-" * 80)
    ll_kluster_eff = hämta_kluster_områden(gdf_lisa_eff, 'LL')
    print(ll_kluster_eff.to_string(index=False))

# ============================================================================
# 4B. DETALJERADE KLUSTER - SUPEREFFEKTIVITET
# ============================================================================
if har_supereff:
    print("\n" + "=" * 80)
    print("Steg 4B: Extraherar detaljerade kluster - SUPEREFFEKTIVITET")
    print("-" * 80)
    
    if lisa_summary_super['HH_kluster'] > 0:
        print("\nHÖGT-HÖGT KLUSTER (SUPEREFFEKTIVITET):")
        print("-" * 80)
        hh_kluster_super = hämta_kluster_områden(gdf_lisa_super, 'HH')
        print(hh_kluster_super.head(10).to_string(index=False))
        if len(hh_kluster_super) > 10:
            print(f"... och {len(hh_kluster_super) - 10} till")
    
    if lisa_summary_super['LL_kluster'] > 0:
        print("\nLÅGT-LÅGT KLUSTER (SUPEREFFEKTIVITET):")
        print("-" * 80)
        ll_kluster_super = hämta_kluster_områden(gdf_lisa_super, 'LL')
        print(ll_kluster_super.to_string(index=False))

# ============================================================================
# 5. SPARA ALLA RESULTAT
# ============================================================================
print("\n" + "=" * 80)
print("Steg 5: Sparar resultat")
print("-" * 80)

# EFFEKTIVITET
lisa_file_eff = output_dir / f"lisa_resultat_effektivitet_{timestamp}.xlsx"
gdf_lisa_eff.drop(columns='geometry').to_excel(lisa_file_eff, index=False)
print(f" LISA (Effektivitet): {lisa_file_eff}")

global_file_eff = output_dir / f"global_moran_effektivitet_{timestamp}.xlsx"
pd.DataFrame([global_stats_eff]).to_excel(global_file_eff, index=False)
print(f" Global (Effektivitet): {global_file_eff}")

summary_file_eff = output_dir / f"kluster_sammanfattning_effektivitet_{timestamp}.xlsx"
pd.DataFrame([lisa_summary_eff]).to_excel(summary_file_eff, index=False)
print(f" Sammanfattning (Effektivitet): {summary_file_eff}")

if lisa_summary_eff['HH_kluster'] > 0:
    hh_file_eff = output_dir / f"HH_kluster_effektivitet_{timestamp}.xlsx"
    hh_kluster_eff.to_excel(hh_file_eff, index=False)
    print(f" HH-kluster (Effektivitet): {hh_file_eff}")

if lisa_summary_eff['LL_kluster'] > 0:
    ll_file_eff = output_dir / f"LL_kluster_effektivitet_{timestamp}.xlsx"
    ll_kluster_eff.to_excel(ll_file_eff, index=False)
    print(f" LL-kluster (Effektivitet): {ll_file_eff}")

# SUPEREFFEKTIVITET
if har_supereff:
    print()
    lisa_file_super = output_dir / f"lisa_resultat_supereffektivitet_{timestamp}.xlsx"
    gdf_lisa_super.drop(columns='geometry').to_excel(lisa_file_super, index=False)
    print(f" LISA (Supereffektivitet): {lisa_file_super}")
    
    global_file_super = output_dir / f"global_moran_supereffektivitet_{timestamp}.xlsx"
    pd.DataFrame([global_stats_super]).to_excel(global_file_super, index=False)
    print(f" Global (Supereffektivitet): {global_file_super}")
    
    summary_file_super = output_dir / f"kluster_sammanfattning_supereffektivitet_{timestamp}.xlsx"
    pd.DataFrame([lisa_summary_super]).to_excel(summary_file_super, index=False)
    print(f" Sammanfattning (Supereffektivitet): {summary_file_super}")
    
    if lisa_summary_super['HH_kluster'] > 0:
        hh_file_super = output_dir / f"HH_kluster_supereffektivitet_{timestamp}.xlsx"
        hh_kluster_super.to_excel(hh_file_super, index=False)
        print(f" HH-kluster (Supereffektivitet): {hh_file_super}")
    
    if lisa_summary_super['LL_kluster'] > 0:
        ll_file_super = output_dir / f"LL_kluster_supereffektivitet_{timestamp}.xlsx"
        ll_kluster_super.to_excel(ll_file_super, index=False)
        print(f" LL-kluster (Supereffektivitet): {ll_file_super}")

# JÄMFÖRELSE-TABELL
if har_supereff:
    print()
    jamforelse = pd.DataFrame({
        'Mått': ['Effektivitet', 'Supereffektivitet'],
        'Morans_I': [global_stats_eff['I'], global_stats_super['I']],
        'Z_score': [global_stats_eff['z_score'], global_stats_super['z_score']],
        'P_värde': [global_stats_eff['p_value_sim'], global_stats_super['p_value_sim']],
        'HH_kluster': [lisa_summary_eff['HH_kluster'], lisa_summary_super['HH_kluster']],
        'LL_kluster': [lisa_summary_eff['LL_kluster'], lisa_summary_super['LL_kluster']],
        'Andel_signifikanta_%': [lisa_summary_eff['andel_signifikanta'], lisa_summary_super['andel_signifikanta']]
    })
    
    jamforelse_file = output_dir / f"jamforelse_eff_vs_supereff_{timestamp}.xlsx"
    jamforelse.to_excel(jamforelse_file, index=False)
    print(f" Jämförelse-tabell: {jamforelse_file}")

print("\n" + "=" * 80)
print("ANALYS KLAR! Resultat sparade i: Moran/resultat/")
print("=" * 80)

if har_supereff:
    print("\n SAMMANFATTNING AV JÄMFÖRELSE:")
    print(jamforelse.to_string(index=False))