"""
core/data_loader_base.py

Grundläggande data-laddning som används av alla moduler.
Innehåller gemensamma funktioner för reconciliation, DMU-mappning och kapitalkostnad.

INGEN modul-specifik logik här - endast grunddata som delas av alla.
"""

import streamlit as st
import pandas as pd
from typing import List, Optional
from pathlib import Path


@st.cache_data
def load_reconciliation() -> pd.DataFrame:
    """
    MASTER-version av reconciliation-laddning.
    Laddar mappning mellan id_network, DMU, REId och Företag.

    Försöker både new_recon.csv och reconciliation_id_network_firm_dmu.csv.
    Returnerar DataFrame med standardiserade kolumnnamn.
    """
    # Försök new_recon.csv först (primär källa)
    recon_path = "intaktsram/data/new_recon.csv"
    fallback_path = "effektivitet/data/reconciliation_id_network_firm_dmu.csv"

    try:
        if Path(recon_path).exists():
            rec = pd.read_csv(recon_path)
        elif Path(fallback_path).exists():
            rec = pd.read_csv(fallback_path)
        else:
            raise FileNotFoundError(f"Kunde inte hitta reconciliation-fil: {recon_path} eller {fallback_path}")

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
        if "DMU" in rec.columns:
            rec["DMU"] = rec["DMU"].astype("Int64")
        if "REId" in rec.columns:
            rec["REId"] = rec["REId"].astype("string").str.strip()

        # Rensa bort rader utan DMU eller REId
        rec = rec.dropna(subset=['DMU', 'REId'])

        return rec

    except Exception as e:
        st.error(f"Kunde inte ladda reconciliation-fil: {e}")
        return pd.DataFrame(columns=["id_network", "DMU", "Företag", "REId"])


@st.cache_data
def load_dmu_mapping() -> pd.DataFrame:
    """
    Laddar mappning mellan REId, DMU och Företag.
    Alias för load_reconciliation() men returnerar endast REId, DMU, Företag.

    Används för scenario-integration med kapitalbas och intäktsram.
    """
    rec = load_reconciliation()
    if rec.empty:
        return pd.DataFrame(columns=['REId', 'DMU', 'Företag'])

    # Returnera endast REId, DMU, Företag
    return rec[['REId', 'DMU', 'Företag']].drop_duplicates()


@st.cache_data
def load_dmu_volymer() -> pd.DataFrame:
    """
    Laddar volymdata för alla DMU från dmu_volymer.csv.
    Innehåller CU, MW, NS, MWhl, MWhh per DMU.
    """
    try:
        return pd.read_csv("effektivitet/data/dmu_volymer.csv")
    except Exception as e:
        st.error(f"Kunde inte ladda DMU-volymer: {e}")
        return pd.DataFrame()


@st.cache_data
def load_capcost_full() -> pd.DataFrame:
    """
    Laddar full kapitalkostnad-data för alla id_network.
    Källa: kapitalkostnad/data/capcost_a_3_Sheet1.parquet

    Innehåller:
    - id_network, cat_encode, time (halvår)
    - nuav_ord, dep_ord, nuav_tail, dep_tail
    - age_component, age_reg
    - return_ord, return_tail
    - capcost_sum, capcost_network
    """
    try:
        return pd.read_parquet("kapitalkostnad/data/capcost_a_3_Sheet1.parquet")
    except Exception as e:
        st.error(f"Kunde inte ladda capcost_a data: {e}")
        return pd.DataFrame()


def get_company_id_networks(dmu: int) -> List[int]:
    """
    Hämtar alla id_network som tillhör ett specifikt DMU.
    Filtrerar till endast lokalnät (REId börjar med REL, inte RER).

    Args:
        dmu: DMU-nummer för företaget

    Returns:
        Lista med id_network som tillhör DMU:n
    """
    rec = load_reconciliation()
    if rec.empty:
        return []

    # Filtrera till specifikt DMU
    dmu_data = rec[rec['DMU'] == dmu]

    # Filtrera till endast lokalnät (REId börjar med REL, inte RER)
    if 'REId' in dmu_data.columns:
        dmu_data = dmu_data[
            dmu_data['REId'].astype(str).str.startswith('REL', na=False) &
            ~dmu_data['REId'].astype(str).str.startswith('RER', na=False)
        ]

    # Returnera lista med id_network
    if 'id_network' in dmu_data.columns:
        return dmu_data['id_network'].tolist()
    else:
        return []


def get_company_name(dmu: int) -> str:
    """
    Returnerar företagsnamn för ett DMU.

    Args:
        dmu: DMU-nummer

    Returns:
        Företagsnamn eller "Företag DMU {dmu}" om namnet inte hittas
    """
    rec = load_reconciliation()
    if rec.empty:
        return f"Företag DMU {dmu}"

    dmu_data = rec[rec['DMU'] == dmu]
    if dmu_data.empty:
        return f"Företag DMU {dmu}"

    if 'Företag' in dmu_data.columns:
        return dmu_data['Företag'].iloc[0]
    else:
        return f"Företag DMU {dmu}"


def get_company_display_name(dmu: int, company_name: str = None) -> str:
    """
    Returnerar företagsnamn med tillhörande id_network.

    Args:
        dmu: DMU-nummer
        company_name: Optionellt företagsnamn (fallback)

    Returns:
        Formaterad sträng med företagsnamn och id_network
    """
    rec = load_reconciliation()
    if rec.empty:
        return company_name or f"Företag DMU {dmu}"

    # Filtrera på DMU och lokalnät
    company_data = rec[
        (rec['DMU'] == dmu) &
        (rec['REId'].astype(str).str.startswith('REL', na=False))
    ]

    if company_data.empty:
        return company_name or f"Företag DMU {dmu}"

    # Använd företagsnamn från reconciliation-fil eller parameter
    name = company_data.iloc[0].get('Företag', company_name or f"Företag DMU {dmu}")

    # Lägg till id_network
    if 'id_network' in company_data.columns:
        networks = sorted(company_data['id_network'].dropna().unique())
        if len(networks) == 1:
            return f"{name} (nät: {int(networks[0])})"
        elif len(networks) > 1:
            network_str = ', '.join(map(str, [int(n) for n in networks]))
            return f"{name} (nät: {network_str})"

    return name
