"""
data_loaders/rab_data.py

Centraliserad laddning av kapitalbasdata (capbase_a).
Separerar dataladdning från beräkningslogik i kent_calculations.py.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List

# Återanvänd befintlig flagga från data_mapping
from calculations.data_mapping import TEST_MODE

# Sökvägar
CAPBASE_MINI_PATH = "data/capbase_a_mini.parquet"
CAPBASE_FULL_PATH = "data/capbase_a.parquet"


def load_capbase_a(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar capbase_a från parquet-fil.
    
    I TEST_MODE laddas mini-filen (3 företag) om full fil saknas.
    I produktion (TEST_MODE=False) krävs fullständig fil.
    
    Args:
        data_path: Explicit sökväg (override). Om None, sök automatiskt.
        
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
    
    # Sökordning: Full fil först, sedan mini (om TEST_MODE)
    search_paths = [
        CAPBASE_FULL_PATH,
        "capbase_a.parquet",
        "data/capbase_a.parquet",
    ]
    
    if TEST_MODE:
        search_paths.extend([
            CAPBASE_MINI_PATH,
            "capbase_a_mini.parquet",
            "data/capbase_a_mini.parquet",
        ])
    
    for path_str in search_paths:
        path = Path(path_str)
        if path.exists():
            df = pd.read_parquet(path)
            _log_load_info(df, path_str)
            return df
    
    raise FileNotFoundError(
        f"capbase_a hittades inte. TEST_MODE={TEST_MODE}. "
        f"Sökvägar: {search_paths}"
    )


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