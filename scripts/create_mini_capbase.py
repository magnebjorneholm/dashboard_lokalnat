#!/usr/bin/env python3
"""
scripts/create_mini_capbase.py

Standalone script för att skapa mini capbase_a.parquet med 3-4 företag.
Används för att testa KENT-beräkningar utan att kräva 4GB+ RAM.

Usage:
    python scripts/create_mini_capbase.py
"""

import pandas as pd
from pathlib import Path
import sys


def create_mini_capbase():
    """
    Skapar mini capbase_a.parquet med endast 3 företag:
    - REL00886 (Kraftringen Nät AB)
    - REL03035 (Ellevio AB)  
    - REL00001 (Ale El ek. för.)
    """
    
    print("\n" + "="*70)
    print("  SKAPA MINI CAPBASE_A.PARQUET")
    print("="*70 + "\n")
    
    # Företag att inkludera
    target_companies = ['REL00886', 'REL03035', 'REL00001']
    print(f"Målföretag: {', '.join(target_companies)}\n")
    
    # Sökvägar
    project_root = Path(__file__).parent.parent
    reconciliation_path = project_root / "reconciliation_id_network_firm_dmu.csv"
    capbase_full_path = project_root / "capbase_a.parquet"
    capbase_mini_path = project_root / "capbase_a_mini.parquet"
    
    # Alternativa sökvägar
    alt_paths = [
        project_root / "data" / "capbase_a.parquet",
        Path("/mnt/project/capbase_a.parquet"),
        Path("capbase_a.parquet")
    ]
    
    # Steg 1: Hitta capbase_a.parquet
    print("Steg 1: Söker efter capbase_a.parquet...")
    
    if not capbase_full_path.exists():
        for alt_path in alt_paths:
            if alt_path.exists():
                capbase_full_path = alt_path
                break
    
    if not capbase_full_path.exists():
        print("❌ ERROR: Kunde inte hitta capbase_a.parquet")
        print(f"\nProvade:")
        print(f"  - {project_root / 'capbase_a.parquet'}")
        for p in alt_paths:
            print(f"  - {p}")
        print(f"\nPlacera capbase_a.parquet i någon av ovanstående platser.")
        sys.exit(1)
    
    print(f"✓ Hittade capbase_a.parquet: {capbase_full_path}")
    
    # Steg 2: Hitta reconciliation
    print("\nSteg 2: Söker efter reconciliation...")
    
    alt_rec_paths = [
        project_root / "data" / "reconciliation_id_network_firm_dmu.csv",
        Path("/mnt/project/reconciliation_id_network_firm_dmu.csv"),
        Path("reconciliation_id_network_firm_dmu.csv")
    ]
    
    if not reconciliation_path.exists():
        for alt_path in alt_rec_paths:
            if alt_path.exists():
                reconciliation_path = alt_path
                break
    
    if not reconciliation_path.exists():
        print("❌ ERROR: Kunde inte hitta reconciliation_id_network_firm_dmu.csv")
        print(f"\nProvade:")
        print(f"  - {project_root / 'reconciliation_id_network_firm_dmu.csv'}")
        for p in alt_rec_paths:
            print(f"  - {p}")
        sys.exit(1)
    
    print(f"✓ Hittade reconciliation: {reconciliation_path}")
    
    # Steg 3: Ladda reconciliation och hitta id_network
    print("\nSteg 3: Mappar REId → id_network...")
    
    rec = pd.read_csv(reconciliation_path)
    
    # Hitta id_network för våra företag
    target_rows = rec[rec['REId'].isin(target_companies)]
    
    if len(target_rows) == 0:
        print("❌ ERROR: Inga av target-företagen hittades i reconciliation")
        print(f"Target: {target_companies}")
        print(f"Tillgängliga REId: {rec['REId'].head(10).tolist()}...")
        sys.exit(1)
    
    id_networks = target_rows['id_network'].tolist()
    
    print(f"✓ Hittade {len(id_networks)} företag:")
    for _, row in target_rows.iterrows():
        print(f"  - {row['REId']}: id_network={row['id_network']}")
    
    # Steg 4: Ladda och filtrera capbase_a
    print("\nSteg 4: Laddar full capbase_a.parquet...")
    
    try:
        capbase_full = pd.read_parquet(capbase_full_path)
        print(f"✓ Laddade capbase: {len(capbase_full):,} rader, {len(capbase_full.columns)} kolumner")
        
        # Visa storlek
        size_mb = capbase_full_path.stat().st_size / (1024**2)
        print(f"  Filstorlek: {size_mb:.1f} MB")
        
    except Exception as e:
        print(f"❌ ERROR: Kunde inte ladda capbase_a.parquet: {e}")
        sys.exit(1)
    
    # Steg 5: Filtrera till mini version
    print("\nSteg 5: Filtrerar till mini version...")
    
    if 'id_network' not in capbase_full.columns:
        print("❌ ERROR: Kolumn 'id_network' saknas i capbase_a")
        print(f"Tillgängliga kolumner: {capbase_full.columns.tolist()[:10]}...")
        sys.exit(1)
    
    capbase_mini = capbase_full[capbase_full['id_network'].isin(id_networks)].copy()
    
    if len(capbase_mini) == 0:
        print("❌ ERROR: Inga rader matchade id_networks")
        print(f"Target id_networks: {id_networks}")
        print(f"Tillgängliga id_networks: {capbase_full['id_network'].unique()[:10]}...")
        sys.exit(1)
    
    print(f"✓ Filtrerade: {len(capbase_mini):,} rader behållna")
    
    # Visa statistik
    reduction_pct = (1 - len(capbase_mini)/len(capbase_full)) * 100
    print(f"  Reduktion: {reduction_pct:.1f}%")
    
    # Steg 6: Spara mini version
    print("\nSteg 6: Sparar capbase_a_mini.parquet...")
    
    try:
        capbase_mini.to_parquet(capbase_mini_path)
        
        # Visa storlek
        mini_size_mb = capbase_mini_path.stat().st_size / (1024**2)
        print(f"✓ Sparad: {capbase_mini_path}")
        print(f"  Filstorlek: {mini_size_mb:.1f} MB (från {size_mb:.1f} MB)")
        print(f"  Rader: {len(capbase_mini):,} (från {len(capbase_full):,})")
        
    except Exception as e:
        print(f"❌ ERROR: Kunde inte spara mini version: {e}")
        sys.exit(1)
    
    # Sammanfattning
    print("\n" + "="*70)
    print("  ✅ MINI CAPBASE_A SKAPAD!")
    print("="*70)
    print(f"\nFil: {capbase_mini_path}")
    print(f"Storlek: {mini_size_mb:.1f} MB")
    print(f"Rader: {len(capbase_mini):,}")
    print(f"Företag: {', '.join(target_companies)}")
    print("\nAnvänd denna fil för att testa KENT-beräkningar utan memory issues.")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        create_mini_capbase()
    except KeyboardInterrupt:
        print("\n\n❌ Avbrutet av användare")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Oväntat fel: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)