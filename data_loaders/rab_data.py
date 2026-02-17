"""
data_loaders/rab_data.py

Centraliserad laddning av kapitalbasdata (capbase_a).
Separerar dataladdning frÃ¥n berÃ¤kningslogik i kent_calculations.py.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List
import streamlit as st

# Ã…teranvÃ¤nd befintlig flagga frÃ¥n data_mapping
from calculations.capex.data_mapping import TEST_MODE

# Paths
CAPBASE_MINI_PATH = "data/capbase_a_mini.parquet"
CAPBASE_FULL_PATH = "data/capbase_a.parquet"
CAPCOST_PATH = "data/capcost_a.parquet"

@st.cache_data(ttl=3600, show_spinner=False)
def load_capbase_a(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar capbase_a frÃ¥n parquet-fil.
    
    I TEST_MODE laddas mini-filen (3 fÃ¶retag) om full fil saknas.
    I produktion (TEST_MODE=False) krÃ¤vs fullstÃ¤ndig fil.
    
    Args:
        data_path: Explicit sÃ¶kvÃ¤g (override). Om None, sÃ¶k automatiskt.
        
    Returns:
        DataFrame med kapitalbaskomponenter.
        
    Raises:
        FileNotFoundError: Om ingen fil hittas.
    """
    if data_path:
        path = Path(data_path)
        if path.exists():
            return pd.read_parquet(path)
        raise FileNotFoundError(f"Angiven fil finns inte: {data_path}")
    
    if TEST_MODE:
        search_paths = [
            CAPBASE_MINI_PATH,           #
            "capbase_a_mini.parquet",
            "data/capbase_a_mini.parquet",
            ]
    else:
        search_paths = [
                CAPBASE_FULL_PATH,
                "capbase_a.parquet", 
                "data/capbase_a.parquet",
            ]
    
    for path_str in search_paths:
        path = Path(path_str)
        if path.exists():
            df = pd.read_parquet(path)
            _log_load_info(df, path_str)
            return df
    
    raise FileNotFoundError(
        f"capbase_a hittades inte. TEST_MODE={TEST_MODE}. "
        f"SÃ¶kvÃ¤gar: {search_paths}"
    )


def load_user_capbase(user_id_network: int, data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar kapitalbasdata fÃ¶r ett specifikt fÃ¶retag.
    
    Args:
        user_id_network: FÃ¶retagets id_network
        data_path: Explicit sÃ¶kvÃ¤g (optional)
        
    Returns:
        DataFrame med anvÃ¤ndarens komponenter.
    """
    df = load_capbase_a(data_path)
    user_df = df[df['id_network'] == user_id_network].copy()
    
    if len(user_df) == 0 and TEST_MODE:
        available = sorted(df['id_network'].unique().tolist())
        print(f"  Varning: id_network={user_id_network} finns inte i data. "
              f"TillgÃ¤ngliga: {available[:10]}{'...' if len(available) > 10 else ''}")
    
    return user_df


def get_available_networks(data_path: Optional[str] = None) -> List[int]:
    """Returnerar lista med tillgÃ¤ngliga id_network i capbase_a."""
    df = load_capbase_a(data_path)
    return sorted(df['id_network'].unique().tolist())


def _log_load_info(df: pd.DataFrame, path: str) -> None:
    """Loggar info om laddad data."""
    n_components = len(df)
    n_networks = df['id_network'].nunique()
    total_nuav = df['nuav_2022'].sum() / 1e9 if 'nuav_2022' in df.columns else 0
    
    mode = "TEST" if TEST_MODE else "PROD"
    print(f"[{mode}] Laddade capbase_a frÃ¥n {path}")
    print(f"  - {n_components:,} komponenter, {n_networks} nÃ¤tverk, {total_nuav:.1f} Mdr kr NUAV")


# =============================================================================
# CAPCOST_A: Aggregated capital costs per category (baseline)
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_capcost_a(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load aggregated capital cost data per category (baseline).
    
    Structure: (id_network, cat_encode, time) with columns:
    - nuav_ord, nuav_tail: NUAV for M1 Asset Base
    - dep_ord, dep_tail: Depreciation for M2
    - return_ord, return_tail: Returns for M3
    - capcost_sum: Total capital cost per category/time
    
    Args:
        data_path: Explicit path (override). If None, search automatically.
        
    Returns:
        DataFrame with baseline capital costs per category.
        
    Raises:
        FileNotFoundError: If file not found.
    """
    if data_path:
        path = Path(data_path)
        if path.exists():
            return pd.read_parquet(path)
        raise FileNotFoundError(f"File not found: {data_path}")
    
    search_paths = [
        CAPCOST_PATH,
        "capcost_a.parquet",
        "data/capcost_a.parquet",
    ]
    
    for path_str in search_paths:
        path = Path(path_str)
        if path.exists():
            df = pd.read_parquet(path)
            _log_capcost_load_info(df, path_str)
            return df
    
    raise FileNotFoundError(
        f"capcost_a not found. Searched: {search_paths}"
    )


def load_user_capcost(user_id_network: int, data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load category-level capital cost data for a specific company.
    
    Args:
        user_id_network: Company's id_network
        data_path: Explicit path (optional)
        
    Returns:
        DataFrame with user's category data (id_network, cat_encode, time, ...).
    """
    df = load_capcost_a(data_path)
    user_df = df[df['id_network'] == user_id_network].copy()
    return user_df


def _log_capcost_load_info(df: pd.DataFrame, path: str) -> None:
    """Log info about loaded capcost data."""
    n_rows = len(df)
    n_networks = df['id_network'].nunique()
    n_categories = df['cat_encode'].nunique() if 'cat_encode' in df.columns else 0
    
    mode = "TEST" if TEST_MODE else "PROD"
    print(f"[{mode}] Loaded capcost_a from {path}")
    print(f"  - {n_rows:,} rows, {n_networks} networks, {n_categories} categories")