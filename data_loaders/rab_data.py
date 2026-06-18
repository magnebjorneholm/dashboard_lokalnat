"""
data_loaders/rab_data.py

Centraliserad laddning av kapitalbasdata (capbase_a).
Separerar dataladdning från beräkningslogik i kent_calculations.py.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List

from config.data_paths import require_dataset
from config.runtime import TEST_MODE
from data_loaders._cache import cached
from data_loaders.schemas import require_columns

@cached(ttl=3600)
def load_capbase_a(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar capbase_a från parquet-fil.

    I TEST_MODE laddas mini-filen (3 företag), annars den fullständiga.

    Args:
        data_path: Explicit fil-sökväg (override). Om None, resolva via registry.

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

    name = "capbase_a_mini" if TEST_MODE else "capbase_a"
    path = require_dataset(name)
    df = pd.read_parquet(path)
    require_columns(df, "capbase_a")
    _log_load_info(df, str(path))
    return df


def load_user_capbase(user_id_network: int, data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar kapitalbasdata för ett specifikt företag.
    
    Args:
        user_id_network: Företagets id_network
        data_path: Explicit sökväg (optional)
        
    Returns:
        DataFrame med användarens komponenter.
    """
    df = load_capbase_a(data_path)
    user_df = df[df['id_network'] == user_id_network].copy()
    
    if len(user_df) == 0 and TEST_MODE:
        available = sorted(df['id_network'].unique().tolist())
        print(f"  Varning: id_network={user_id_network} finns inte i data. "
              f"Tillgängliga: {available[:10]}{'...' if len(available) > 10 else ''}")
    
    return user_df


def get_available_networks(data_path: Optional[str] = None) -> List[int]:
    """Returnerar lista med tillgängliga id_network i capbase_a."""
    df = load_capbase_a(data_path)
    return sorted(df['id_network'].unique().tolist())


def _log_load_info(df: pd.DataFrame, path: str) -> None:
    """Loggar info om laddad data."""
    n_components = len(df)
    n_networks = df['id_network'].nunique()
    total_nuav = df['nuav_2022'].sum() / 1e9 if 'nuav_2022' in df.columns else 0
    
    mode = "TEST" if TEST_MODE else "PROD"
    print(f"[{mode}] Laddade capbase_a från {path}")
    print(f"  - {n_components:,} komponenter, {n_networks} nätverk, {total_nuav:.1f} Mdr kr NUAV")


# =============================================================================
# CAPCOST_A: Aggregated capital costs per category (baseline)
# =============================================================================

@cached(ttl=3600)
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

    path = require_dataset("capcost_a")
    df = pd.read_parquet(path)
    require_columns(df, "capcost_a")
    df = _enforce_capcost_amount_dtypes(df)
    _log_capcost_load_info(df, str(path))
    return df


# Monetary columns in capcost_a. Some (return_ord/return_tail) are stored as
# float32 in the parquet while the rest are float64 — an inconsistent contract
# that silently loses precision above ~16M tkr and, on pandas >= 3, raises when a
# float64 KENT value is written back into a float32 column. Normalise the whole
# amount contract to float64 at the load boundary.
CAPCOST_AMOUNT_COLS = (
    "nuav_ord", "nuav_tail", "dep_ord", "dep_tail",
    "return_ord", "return_tail", "capcost_sum", "capcost_network",
)


def _enforce_capcost_amount_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce capcost_a amount columns to float64 (see CAPCOST_AMOUNT_COLS)."""
    for col in CAPCOST_AMOUNT_COLS:
        if col in df.columns and df[col].dtype != "float64":
            df[col] = df[col].astype("float64")
    return df


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