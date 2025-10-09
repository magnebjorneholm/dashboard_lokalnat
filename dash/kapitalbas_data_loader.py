"""
kapitalbas_data_loader.py - Dash-version
=========================================

Företagsspecifik data loader för kapitalbas-modulen.
Filtrerar all data till inloggat företags DMU och aggregerar till DMU-nivå.

Använder Flask session via auth.py för session management.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from pathlib import Path
from flask import session as flask_session


# ============================================================================
# SESSION UTILITIES
# ============================================================================

def get_user_dmu() -> Optional[int]:
    """
    Hämtar inloggat företags DMU från Flask session.
    
    Returns:
        DMU ID eller None
    """
    return flask_session.get('user_dmu', None)


def get_user_org() -> str:
    """
    Hämtar organisations-ID från Flask session.
    
    Returns:
        Organisation ID (str)
    """
    return flask_session.get('org', 'default')


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_reconciliation_foretag() -> pd.DataFrame:
    """
    Laddar reconciliation-mappning mellan id_network, DMU och REId.
    Ingen caching - Flask-cache kan läggas till senare om behövs.
    
    Returns:
        DataFrame med kolumner [id_network, DMU, Företag, REId]
    """
    try:
        # Försök läsa new_recon.csv först (används i andra moduler)
        recon_path = "effektiviseringskrav/data/new_recon.csv"
        if Path(recon_path).exists():
            rec = pd.read_csv(recon_path)
        else:
            # Fallback till den gamla filen
            recon_path = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"
            rec = pd.read_csv(recon_path)
            
        # Standardisera kolumnnamn (case-insensitive mapping)
        cols = {c.lower(): c for c in rec.columns}
        
        mapping = {}
        mapping['id_network'] = cols.get("id_network", "id_network")
        mapping['DMU'] = cols.get("dmu", "DMU") 
        mapping['Företag'] = cols.get("företag", cols.get("foretag", cols.get("id_firm", "Företag")))
        mapping['REId'] = cols.get("reid", cols.get("id_network_string", "REId"))
        
        # Byt namn på kolumner
        rec = rec.rename(columns={
            mapping['id_network']: "id_network",
            mapping['DMU']: "DMU", 
            mapping['Företag']: "Företag",
            mapping['REId']: "REId"
        })
        
        # Behåll endast relevanta kolumner
        keep_cols = [c for c in ["id_network", "DMU", "Företag", "REId"] if c in rec.columns]
        rec = rec[keep_cols].drop_duplicates()
        
        # Konvertera datatyper
        rec["DMU"] = rec["DMU"].astype("Int64")
        if "REId" in rec.columns:
            rec["REId"] = rec["REId"].astype("string").str.strip()
            
        return rec
        
    except Exception as e:
        print(f"ERROR: Kunde inte ladda reconciliation-fil: {e}")
        return pd.DataFrame()


def get_company_id_networks(dmu: int) -> List[int]:
    """
    Hämtar alla id_network som tillhör ett specifikt DMU.
    Filtrerar till endast lokalnät (REId börjar med REL).
    
    Args:
        dmu: DMU-nummer
        
    Returns:
        Lista med id_network
    """
    rec = load_reconciliation_foretag()
    if rec.empty:
        return []
    
    # Filtrera till specifikt DMU
    dmu_data = rec[rec['DMU'] == dmu]
    
    # Filtrera till endast lokalnät (REId börjar med REL)
    if 'REId' in dmu_data.columns:
        dmu_data = dmu_data[
            dmu_data['REId'].astype(str).str.startswith('REL', na=False) &
            ~dmu_data['REId'].astype(str).str.startswith('RER', na=False)
        ]
    
    # Returnera lista med id_network
    return dmu_data['id_network'].tolist()


def load_capcost_a_foretag() -> pd.DataFrame:
    """
    Laddar kapitalkostnad-data filtrerat för inloggat företags DMU.
    Aggregerar från id_network-nivå till DMU-nivå.
    
    Returns:
        DataFrame med kapitalkostnader för företaget
    """
    user_dmu = get_user_dmu()
    
    if user_dmu is None:
        return pd.DataFrame()
    
    try:
        # Ladda full kapitalkostnad-data
        capcost_path = "kapitalbas/datafiler/slutdata/capcost_a_3_Sheet1.parquet"
        df_full = pd.read_parquet(capcost_path)
        
        # Hämta företagets id_networks
        company_networks = get_company_id_networks(user_dmu)
        
        if not company_networks:
            print(f"WARNING: Inga id_networks hittades för DMU {user_dmu}")
            return pd.DataFrame()
        
        # Filtrera till företagets nätverk
        df_company = df_full[df_full['id_network'].isin(company_networks)].copy()
        
        # Aggregera till DMU-nivå (summera över id_network)
        numeric_cols = df_company.select_dtypes(include=[np.number]).columns
        exclude_cols = ['id_network', 'time', 'DMU']
        agg_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        if 'time' in df_company.columns:
            group_by = ['time']
            if 'cat_encode' in df_company.columns:
                group_by.append('cat_encode')
            
            df_aggregated = df_company.groupby(group_by, as_index=False)[agg_cols].sum()
        else:
            df_aggregated = pd.DataFrame([df_company[agg_cols].sum()]).T
            df_aggregated.columns = ['value']
            df_aggregated = df_aggregated.reset_index()
        
        return df_aggregated
        
    except Exception as e:
        print(f"ERROR: Kunde inte ladda capcost data: {e}")
        return pd.DataFrame()


def load_dmu_volymer_foretag() -> pd.DataFrame:
    """
    Laddar DMU-volymer för inloggat företag.
    
    Returns:
        DataFrame med volymer för företaget
    """
    user_dmu = get_user_dmu()
    
    if user_dmu is None:
        return pd.DataFrame()
    
    try:
        df_full = pd.read_csv("effektiviseringskrav/data/dmu_volymer.csv")
        # Filtrera till användarens DMU
        df_company = df_full[df_full['DMU'] == user_dmu].copy()
        return df_company
    except Exception as e:
        print(f"ERROR: Kunde inte ladda DMU-volymer: {e}")
        return pd.DataFrame()


def load_reconciliation_foretag_info() -> Dict[str, Any]:
    """
    Returnerar information om användarens DMU och dess id_network-mappning.
    Användbar för debugging och information till användaren.
    
    Returns:
        Dictionary med företagsinformation
    """
    user_dmu = get_user_dmu()
    
    if user_dmu is None:
        return {'error': 'Ingen DMU hittades för inloggad användare'}
    
    rec = load_reconciliation_foretag()
    if rec.empty:
        return {'error': 'Kunde inte ladda reconciliation-data'}
    
    # Hämta information för användarens DMU
    dmu_data = rec[rec['DMU'] == user_dmu]
    
    if dmu_data.empty:
        return {
            'user_dmu': user_dmu,
            'error': f'DMU {user_dmu} hittades inte i reconciliation'
        }
    
    # Filtrera till lokalnät
    local_nets = dmu_data[
        dmu_data['REId'].astype(str).str.startswith('REL', na=False) &
        ~dmu_data['REId'].astype(str).str.startswith('RER', na=False)
    ] if 'REId' in dmu_data.columns else dmu_data
    
    company_name = dmu_data['Företag'].iloc[0] if 'Företag' in dmu_data.columns and not dmu_data.empty else 'Okänt företag'
    
    return {
        'user_dmu': user_dmu,
        'company_name': company_name,
        'total_networks': len(dmu_data),
        'local_networks': len(local_nets),
        'id_networks': local_nets['id_network'].tolist() if not local_nets.empty else [],
        'reid_list': local_nets['REId'].tolist() if 'REId' in local_nets.columns and not local_nets.empty else []
    }


def validate_company_data() -> Dict[str, Any]:
    """
    Validerar att företagsdata kan laddas korrekt.
    Returnerar valideringsresultat för debugging.
    
    Returns:
        Dictionary med valideringsresultat
    """
    validation = {
        'user_authenticated': False,
        'dmu_found': False,
        'reconciliation_loaded': False,
        'networks_found': False,
        'capcost_data_available': False,
        'details': {}
    }
    
    # Kontrollera användar-autentisering
    user_dmu = get_user_dmu()
    validation['user_authenticated'] = user_dmu is not None
    validation['details']['user_dmu'] = user_dmu
    
    if not validation['user_authenticated']:
        return validation
    
    # Kontrollera reconciliation
    rec = load_reconciliation_foretag()
    validation['reconciliation_loaded'] = not rec.empty
    validation['details']['reconciliation_rows'] = len(rec)
    
    if not validation['reconciliation_loaded']:
        return validation
    
    # Kontrollera DMU finns
    dmu_data = rec[rec['DMU'] == user_dmu]
    validation['dmu_found'] = not dmu_data.empty
    validation['details']['dmu_networks'] = len(dmu_data)
    
    if not validation['dmu_found']:
        return validation
    
    # Kontrollera id_network
    company_networks = get_company_id_networks(user_dmu)
    validation['networks_found'] = len(company_networks) > 0
    validation['details']['company_networks'] = company_networks
    
    if not validation['networks_found']:
        return validation
    
    # Kontrollera capcost data
    try:
        df_capcost = load_capcost_a_foretag()
        validation['capcost_data_available'] = not df_capcost.empty
        validation['details']['capcost_rows'] = len(df_capcost)
        validation['details']['capcost_periods'] = df_capcost['time'].nunique() if 'time' in df_capcost.columns else 0
    except Exception as e:
        validation['details']['capcost_error'] = str(e)
    
    return validation


# ============================================================================
# TESTER (för debugging)
# ============================================================================

if __name__ == "__main__":
    """
    Tester för att verifiera att data-loading fungerar.
    OBS: Kräver att Flask session är satt (dvs. körs i Dash-kontext).
    """
    print("Testing kapitalbas_data_loader...")
    print("=" * 60)
    
    # Test 1: Ladda reconciliation
    print("\n1. Laddar reconciliation...")
    rec = load_reconciliation_foretag()
    print(f"   Laddade {len(rec)} rader")
    print(f"   Kolumner: {rec.columns.tolist()}")
    
    # Test 2: Företagsinformation
    print("\n2. Hämtar företagsinformation...")
    info = load_reconciliation_foretag_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Test 3: Validering
    print("\n3. Validerar företagsdata...")
    validation = validate_company_data()
    for key, value in validation.items():
        if key != 'details':
            print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Alla tester slutförda!")