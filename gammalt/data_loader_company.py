"""
core/data_loader_company.py

Företagsspecifik data-laddning och filtrering.
Filtrerar all data till inloggat företags DMU och aggregerar till DMU-nivå.

Wrapper runt core.data_loader_base med DMU-filtrering och aggregering.
Används av alla företagsvyer.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, List

from core.data_loader_base import (
    load_reconciliation,
    load_dmu_volymer,
    load_capcost_full,
    get_company_id_networks
)


def get_user_dmu() -> Optional[int]:
    """
    Hämtar inloggat företags DMU från session state.

    Returns:
        DMU-nummer eller None om inte inloggad
    """
    return st.session_state.get('user_dmu', None)


@st.cache_data
def load_capcost_foretag() -> pd.DataFrame:
    """
    Laddar kapitalkostnad-data filtrerat för inloggat företags DMU.
    Aggregerar från id_network-nivå till DMU-nivå.

    Returns:
        DataFrame med aggregerade kapitalkostnader för företaget:
        - DMU, Företag, time (halvår)
        - capcost_sum, dep_ord, dep_tail, nuav_ord, nuav_tail, return_ord, return_tail
    """
    user_dmu = get_user_dmu()

    if user_dmu is None:
        st.error("Ingen DMU hittades för inloggad användare")
        return pd.DataFrame()

    # Hämta alla id_network för användarens DMU
    company_networks = get_company_id_networks(user_dmu)

    if not company_networks:
        st.error(f"Inga id_network hittades för DMU {user_dmu}")
        return pd.DataFrame()

    # Ladda full capcost_a data
    df_full = load_capcost_full()
    if df_full.empty:
        return pd.DataFrame()

    # Filtrera till användarens id_network
    df_company = df_full[df_full['id_network'].isin(company_networks)].copy()

    if df_company.empty:
        st.warning(f"Ingen data hittades för DMU {user_dmu} i capcost_a")
        return pd.DataFrame()

    # Lägg till DMU och företagsnamn från reconciliation
    rec = load_reconciliation()
    if not rec.empty:
        # Merge för att få DMU och företagsnamn
        df_company = df_company.merge(
            rec[['id_network', 'DMU', 'Företag']],
            on='id_network',
            how='left'
        )

    # Aggregera till DMU-nivå per halvår
    group_cols = ["DMU", "Företag", "time"]
    agg_cols = ["capcost_sum", "dep_ord", "dep_tail", "nuav_ord", "nuav_tail", "return_ord", "return_tail"]

    # Kontrollera att vi har alla nödvändiga kolumner
    available_agg_cols = [col for col in agg_cols if col in df_company.columns]
    available_group_cols = [col for col in group_cols if col in df_company.columns]

    if not available_agg_cols:
        st.error("Inga aggregerings-kolumner hittades i data")
        return df_company

    # Gruppera och aggregera
    df_aggregated = (df_company
        .groupby(available_group_cols, dropna=False)
        .agg({col: 'sum' for col in available_agg_cols})
        .reset_index()
    )

    # Debug-information
    st.session_state['company_debug'] = {
        'user_dmu': user_dmu,
        'company_networks': company_networks,
        'networks_found_in_data': len(df_company['id_network'].unique()),
        'total_networks_for_dmu': len(company_networks),
        'aggregated_periods': df_aggregated['time'].nunique() if 'time' in df_aggregated.columns else 0
    }

    return df_aggregated


@st.cache_data
def load_dmu_volymer_foretag() -> pd.DataFrame:
    """
    Laddar volymdata filtrerat för inloggat företag.

    Returns:
        DataFrame med volymer för företaget (CU, MW, NS, MWhl, MWhh)
    """
    user_dmu = get_user_dmu()

    if user_dmu is None:
        return pd.DataFrame()

    df_full = load_dmu_volymer()
    if df_full.empty:
        return pd.DataFrame()

    # Filtrera till användarens DMU
    df_company = df_full[df_full['DMU'] == user_dmu].copy()
    return df_company


def load_reconciliation_foretag_info() -> dict:
    """
    Returnerar information om användarens DMU och dess id_network-mappning.
    Användbar för debugging och information till användaren.

    Returns:
        Dict med:
        - user_dmu: int
        - company_name: str
        - total_networks: int (antal nätverk för DMU)
        - local_networks: int (antal lokalnät)
        - id_networks: List[int] (lista med id_network)
        - reid_list: List[str] (lista med REId)
    """
    user_dmu = get_user_dmu()

    if user_dmu is None:
        return {'error': 'Ingen DMU hittades för inloggad användare'}

    rec = load_reconciliation()
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


def validate_company_data() -> dict:
    """
    Validerar att företagsdata kan laddas korrekt.
    Returnerar valideringsresultat för debugging.

    Returns:
        Dict med valideringsstatus:
        - user_authenticated: bool
        - dmu_found: bool
        - reconciliation_loaded: bool
        - networks_found: bool
        - capcost_data_available: bool
        - details: dict med ytterligare detaljer
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
    rec = load_reconciliation()
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
        df_capcost = load_capcost_foretag()
        validation['capcost_data_available'] = not df_capcost.empty
        validation['details']['capcost_rows'] = len(df_capcost)
        validation['details']['capcost_periods'] = df_capcost['time'].nunique() if 'time' in df_capcost.columns else 0
    except Exception as e:
        validation['details']['capcost_error'] = str(e)

    return validation
