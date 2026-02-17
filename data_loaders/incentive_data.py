"""
data_loaders/incentive_data.py

Laddar och fÃ¶rbereder incitamentdata frÃ¥n all_adjust_vars.csv.
Mappar numerisk reid till REId-format (REL00001, etc.).
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
import streamlit as st


# Alla variabelkolumner som kan overridas
# Dessa Ã¤r fÃ¶retagsspecifika observerade och normvÃ¤rden
VARIABLE_COLUMNS: List[str] = [
    # NÃ¤tfÃ¶rlust
    "nf_norm", "nf_obs", "e_in",
    # Belastning  
    "ug_norm", "ug_obs", "k_upstream",
    # CEMI4
    "cemi4_norm", "cemi4_obs",
    # AIF observerade (12 st)
    "aif_a_1_obs", "aif_a_2_obs", "aif_a_3_obs", "aif_a_4_obs", "aif_a_5_obs", "aif_a_6_obs",
    "aif_o_1_obs", "aif_o_2_obs", "aif_o_3_obs", "aif_o_4_obs", "aif_o_5_obs", "aif_o_6_obs",
    # AIF norm (12 st)
    "aif_a_1_norm", "aif_a_2_norm", "aif_a_3_norm", "aif_a_4_norm", "aif_a_5_norm", "aif_a_6_norm",
    "aif_o_1_norm", "aif_o_2_norm", "aif_o_3_norm", "aif_o_4_norm", "aif_o_5_norm", "aif_o_6_norm",
    # AIT observerade (12 st)
    "ait_a_1_obs", "ait_a_2_obs", "ait_a_3_obs", "ait_a_4_obs", "ait_a_5_obs", "ait_a_6_obs",
    "ait_o_1_obs", "ait_o_2_obs", "ait_o_3_obs", "ait_o_4_obs", "ait_o_5_obs", "ait_o_6_obs",
    # AIT norm (12 st)
    "ait_a_1_norm", "ait_a_2_norm", "ait_a_3_norm", "ait_a_4_norm", "ait_a_5_norm", "ait_a_6_norm",
    "ait_o_1_norm", "ait_o_2_norm", "ait_o_3_norm", "ait_o_4_norm", "ait_o_5_norm", "ait_o_6_norm",
    # Ã…ME per kundtyp (6 st)
    "ame_1", "ame_2", "ame_3", "ame_4", "ame_5", "ame_6",
]


@st.cache_data(ttl=3600, show_spinner=False)
def load_incentive_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar incitamentdata och fÃ¶rbereder den fÃ¶r berÃ¤kning.
    
    Args:
        filepath: SÃ¶kvÃ¤g till all_adjust_vars.csv. Om None, anvÃ¤nd default.
    
    Returns:
        DataFrame med alla incitamentvariabler, REId i korrekt format.
        Kolumnen 'capcost' tas bort (placeholder som ersÃ¤tts med faktisk avkastning).
    """
    if filepath is None:
        # Default sÃ¶kvÃ¤g relativt till projektrot
        # Prova flera mÃ¶jliga platser
        possible_paths = [
            Path(__file__).parent / "data" / "all_adjust_vars.csv",
            Path(__file__).parent.parent / "data" / "all_adjust_vars.csv",
            Path("data") / "all_adjust_vars.csv",
        ]
        for path in possible_paths:
            if path.exists():
                filepath = path
                break
        else:
            raise FileNotFoundError(
                f"Kunde inte hitta all_adjust_vars.csv. PrÃ¶vade: {possible_paths}"
            )
    
    df = pd.read_csv(filepath)
    
    # Mappa numerisk reid till REId-format (REL00001, REL00886, etc.)
    df['REId'] = df['reid'].apply(lambda x: f"REL{int(x):05d}")
    
    # Ta bort placeholder capcost - ersÃ¤tts med faktisk avkastning i pipeline
    if 'capcost' in df.columns:
        df = df.drop(columns=['capcost'])
    
    return df


def prepare_incentive_input(
    incentive_data: pd.DataFrame,
    return_per_year: pd.DataFrame
) -> pd.DataFrame:
    """
    Prepare complete input for incentive calculation by merging
    incentive data with return per year.

    Args:
        incentive_data: DataFrame from load_incentive_data()
        return_per_year: DataFrame with REId, return_on_assets_2024..2027 (tkr)

    Returns:
        DataFrame with all variables ready for calculate_all_incentives().
        Contains column 'ret_period' (return in kr for each year).
    """
    df = incentive_data.copy()

    # Merge with return per year
    df = df.merge(return_per_year, on='REId', how='left')

    # Create ret_period based on year (convert tkr -> kr)
    df['ret_period'] = df.apply(
        lambda row: row.get(f"return_on_assets_{int(row['year'])}", 0) * 1000,
        axis=1
    )

    return df


def get_incentive_summary_by_reid(
    incentive_results: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregate incentive results to one row per REId (period sum).

    Args:
        incentive_results: Output from calculate_all_incentives()

    Returns:
        DataFrame with one row per REId:
        - REId
        - quality_incentive_total (tkr)
        - network_loss_incentive_total (tkr)
        - load_incentive_total (tkr)
        - incentive_adjustment_total (tkr)
        - Missing_Incentive_Data (bool)
    """
    from config.incentive_parameters import MISSING_DATA_IDS
    from config.column_names import (
        COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE,
        COL_LOAD_INCENTIVE, COL_INCENTIVE_TOTAL, COL_MISSING_INCENTIVE,
    )

    # Period sums are already on all rows (aggregate_period_totals)
    # Extract one row per REId
    df_summary = incentive_results.groupby('REId').first().reset_index()

    # Select relevant columns
    cols_to_keep = ['REId']
    rename_map = {}

    # Period sums (from aggregate_period_totals)
    if 'inter_incentive_sum' in df_summary.columns:
        cols_to_keep.append('inter_incentive_sum')
        rename_map['inter_incentive_sum'] = COL_QUALITY_INCENTIVE
    if 'loss_incentive_sum' in df_summary.columns:
        cols_to_keep.append('loss_incentive_sum')
        rename_map['loss_incentive_sum'] = COL_NETLOSS_INCENTIVE
    if 'util_incentive_sum' in df_summary.columns:
        cols_to_keep.append('util_incentive_sum')
        rename_map['util_incentive_sum'] = COL_LOAD_INCENTIVE
    if 'incentive_total' in df_summary.columns:
        cols_to_keep.append('incentive_total')
        rename_map['incentive_total'] = COL_INCENTIVE_TOTAL

    df_summary = df_summary[cols_to_keep].copy()

    # Convert from kr to tkr
    for col in cols_to_keep[1:]:  # Skip REId
        df_summary[col] = df_summary[col] / 1000

    # Rename to English
    df_summary = df_summary.rename(columns=rename_map)

    # Flag for missing data (based on numeric reid in MISSING_DATA_IDS)
    df_summary[COL_MISSING_INCENTIVE] = df_summary['REId'].apply(
        lambda x: int(x.replace('REL', '')) in MISSING_DATA_IDS
    )

    return df_summary


def get_incentive_detailed_by_reid(
    incentive_results: pd.DataFrame,
    user_reid: str
) -> Optional[pd.DataFrame]:
    """
    Extract detailed per-year incentive data for a specific company.
    
    Returns all intermediate values needed for User Manual Table 10 display:
    - 30.2.4/30.2.5: Network loss before/after cap
    - 30.3.4/30.3.5: Utilization before/after cap
    - 30.4.57/58/59: Quality before CEMI4, after CEMI4, after cap
    - 30.5.1/30.5.2: Total before/after aggregate cap
    - AIT/AIF per customer type (no Variable-ID)
    
    Args:
        incentive_results: Full output from calculate_all_incentives()
        user_reid: REId for the company (e.g., "REL00886")
    
    Returns:
        DataFrame with one row per year (2024-2027) plus period totals,
        or None if user not found.
    """
    if incentive_results is None or incentive_results.empty:
        return None
    
    # Filter to user's rows
    df_user = incentive_results[incentive_results['REId'] == user_reid].copy()
    
    if df_user.empty:
        return None
    
    # Columns to extract (User Manual Table 10 outputs)
    output_columns = [
        'year',
        # 30.2 Network loss
        'loss_incentive_a',      # 30.2.4 before cap
        'loss_incentive',        # 30.2.5 after cap
        # 30.3 Utilization
        'util_incentive_a',      # 30.3.4 before cap
        'util_incentive',        # 30.3.5 after cap
        # 30.4 Quality/Interruption
        'inc_inter',             # 30.4.57 before CEMI4
        'inter_incentive_a',     # 30.4.58 after CEMI4
        'inter_incentive',       # 30.4.59 after CEMI4 + cap
        # 30.5 Total
        'incentive_total_year',  # 30.5.2 after aggregate cap
        # Cap reference
        'max_adj',               # Max adjustment (1/3 of return)
        'ret_period',            # Return used for cap calculation
    ]
    
    # AIT/AIF per customer type columns (no Variable-ID in User Manual)
    ait_aif_columns = []
    for ind_type in ['ait', 'aif']:
        for ann in ['a', 'o']:
            for sni in range(1, 7):
                col = f'inc_{ind_type}_{ann}_{sni}'
                if col in df_user.columns:
                    ait_aif_columns.append(col)
    
    # Build column list with available columns only
    available_cols = [c for c in output_columns if c in df_user.columns]
    available_cols.extend(ait_aif_columns)
    
    # Select and sort by year
    df_detail = df_user[available_cols].copy()
    df_detail = df_detail.sort_values('year').reset_index(drop=True)
    
    # Calculate 30.5.1: Total after individual caps but before aggregate cap
    # This is the sum of individually capped values (not _a values)
    if all(c in df_detail.columns for c in ['inter_incentive', 'loss_incentive', 'util_incentive']):
        df_detail['total_before_agg_cap'] = (
            df_detail['inter_incentive'] + 
            df_detail['loss_incentive'] + 
            df_detail['util_incentive']
        )
    
    # Add period totals row
    period_totals = {'year': 'Total'}
    for col in df_detail.columns:
        if col == 'year':
            continue
        if col in ['ret_period', 'max_adj']:
            # Sum these for period total
            period_totals[col] = df_detail[col].sum()
        elif df_detail[col].dtype in ['float64', 'int64']:
            period_totals[col] = df_detail[col].sum()
    
    df_detail = pd.concat([df_detail, pd.DataFrame([period_totals])], ignore_index=True)
    
    return df_detail


def apply_variable_overrides(
    df: pd.DataFrame,
    user_reid: str,
    variable_overrides: Optional[Dict[str, float]]
) -> pd.DataFrame:
    """
    Applicerar variabel-overrides fÃ¶r ett specifikt fÃ¶retag.
    
    Overrides appliceras pÃ¥ ALLA Ã¥r (2024-2027) fÃ¶r det angivna fÃ¶retaget.
    Ã–vriga fÃ¶retag pÃ¥verkas inte.
    
    Args:
        df: DataFrame med incitamentdata (output frÃ¥n prepare_incentive_input)
        user_reid: REId fÃ¶r fÃ¶retaget vars variabler ska Ã¤ndras (ex: "REL00886")
        variable_overrides: Dict med kolumnnamn -> nytt vÃ¤rde
                           Ex: {"nf_obs": 0.045, "ug_obs": 0.65}
                           Om None eller tom dict -> ingen Ã¤ndring
    
    Returns:
        DataFrame med applicerade overrides
    """
    if not variable_overrides:
        return df
    
    df = df.copy()
    
    # Skapa mask fÃ¶r anvÃ¤ndarens rader
    mask = df['REId'] == user_reid
    
    if not mask.any():
        print(f"    [VARNING] FÃ¶retag {user_reid} hittades inte i incitamentdata")
        return df
    
    # Applicera varje override (filtrera bort ogiltiga vÃ¤rden)
    applied = []
    for col, value in variable_overrides.items():
        # Skippa None, "NULL", "null" och andra ogiltiga vÃ¤rden
        if value is None or value == "NULL" or value == "null":
            continue
        
        if col in df.columns:
            try:
                df.loc[mask, col] = float(value)
                applied.append(col)
            except (ValueError, TypeError) as e:
                print(f"    [VARNING] Kunde inte konvertera '{col}'={value}: {e}")
        else:
            print(f"    [VARNING] OkÃ¤nd variabel '{col}' ignorerades")
    
    if applied:
        print(f"    Variabel-overrides fÃ¶r {user_reid}: {len(applied)} st ({', '.join(applied[:5])}{'...' if len(applied) > 5 else ''})")
    
    return df


def get_user_baseline_variables(
    user_reid: str,
    year: int = 2024,
    filepath: Optional[str] = None
) -> Dict[str, float]:
    """
    HÃ¤mtar baseline-vÃ¤rden fÃ¶r ett fÃ¶retags incitamentvariabler.
    
    Returnerar vÃ¤rden fÃ¶r ett specifikt Ã¥r (default 2024).
    AnvÃ¤nds i UI fÃ¶r att visa baseline i input-fÃ¤lt.
    
    Args:
        user_reid: REId fÃ¶r fÃ¶retaget (ex: "REL00886")
        year: Ã…r att hÃ¤mta vÃ¤rden fÃ¶r (default 2024)
        filepath: SÃ¶kvÃ¤g till data (None = default)
    
    Returns:
        Dict med variabelnamn -> baseline-vÃ¤rde
        Ex: {"nf_obs": 0.039, "ug_obs": 0.404, ...}
        
        Returnerar tom dict om fÃ¶retaget inte hittas.
    """
    try:
        df = load_incentive_data(filepath)
    except FileNotFoundError:
        return {}
    
    # Filtrera pÃ¥ fÃ¶retag och Ã¥r
    mask = (df['REId'] == user_reid) & (df['year'] == year)
    df_user = df[mask]
    
    if df_user.empty:
        return {}
    
    # Extrahera fÃ¶rsta (och enda) raden
    row = df_user.iloc[0]
    
    # Bygg dict med alla tillgÃ¤ngliga variabler
    result = {}
    for col in VARIABLE_COLUMNS:
        if col in row.index:
            val = row[col]
            # Hantera NaN
            if pd.notna(val):
                result[col] = float(val)
            else:
                result[col] = None
    
    return result


def get_variable_metadata() -> Dict[str, Dict]:
    """
    Returnerar metadata fÃ¶r alla incitamentvariabler.
    
    AnvÃ¤nds fÃ¶r att bygga UI med korrekta labels, enheter och kategorier.
    
    Returns:
        Dict med variabelnamn -> metadata dict:
        {
            "nf_obs": {
                "label": "NÃ¤tfÃ¶rlust observerad",
                "category": "netloss",
                "unit": "andel",
                "format": ".4f",
            },
            ...
        }
    """
    return {
        # NÃ¤tfÃ¶rlust
        "nf_norm": {"label": "NÃ¤tfÃ¶rlust norm", "category": "netloss", "unit": "andel", "format": ".4f"},
        "nf_obs": {"label": "NÃ¤tfÃ¶rlust observerad", "category": "netloss", "unit": "andel", "format": ".4f"},
        "e_in": {"label": "Energi in", "category": "netloss", "unit": "MWh", "format": ",.0f"},
        
        # Belastning
        "ug_norm": {"label": "Utnyttjandegrad norm", "category": "load", "unit": "andel", "format": ".4f"},
        "ug_obs": {"label": "Utnyttjandegrad observerad", "category": "load", "unit": "andel", "format": ".4f"},
        "k_upstream": {"label": "Kostnad Ã¶verliggande nÃ¤t", "category": "load", "unit": "kr", "format": ",.0f"},
        
        # CEMI4
        "cemi4_norm": {"label": "CEMI4 norm", "category": "quality", "unit": "andel", "format": ".4f"},
        "cemi4_obs": {"label": "CEMI4 observerad", "category": "quality", "unit": "andel", "format": ".4f"},
        
        # AIF observerade
        "aif_a_1_obs": {"label": "AIF aviserad jordbruk", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_2_obs": {"label": "AIF aviserad industri", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_3_obs": {"label": "AIF aviserad handel/tjÃ¤nster", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_4_obs": {"label": "AIF aviserad offentlig", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_5_obs": {"label": "AIF aviserad hushÃ¥ll", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_6_obs": {"label": "AIF aviserad grÃ¤nspunkt", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_1_obs": {"label": "AIF oaviserad jordbruk", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_2_obs": {"label": "AIF oaviserad industri", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_3_obs": {"label": "AIF oaviserad handel/tjÃ¤nster", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_4_obs": {"label": "AIF oaviserad offentlig", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_5_obs": {"label": "AIF oaviserad hushÃ¥ll", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_6_obs": {"label": "AIF oaviserad grÃ¤nspunkt", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        
        # AIF norm
        "aif_a_1_norm": {"label": "AIF aviserad jordbruk norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_2_norm": {"label": "AIF aviserad industri norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_3_norm": {"label": "AIF aviserad handel/tjÃ¤nster norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_4_norm": {"label": "AIF aviserad offentlig norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_5_norm": {"label": "AIF aviserad hushÃ¥ll norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_6_norm": {"label": "AIF aviserad grÃ¤nspunkt norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_1_norm": {"label": "AIF oaviserad jordbruk norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_2_norm": {"label": "AIF oaviserad industri norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_3_norm": {"label": "AIF oaviserad handel/tjÃ¤nster norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_4_norm": {"label": "AIF oaviserad offentlig norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_5_norm": {"label": "AIF oaviserad hushÃ¥ll norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_6_norm": {"label": "AIF oaviserad grÃ¤nspunkt norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        
        # AIT observerade
        "ait_a_1_obs": {"label": "AIT aviserad jordbruk", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_2_obs": {"label": "AIT aviserad industri", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_3_obs": {"label": "AIT aviserad handel/tjÃ¤nster", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_4_obs": {"label": "AIT aviserad offentlig", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_5_obs": {"label": "AIT aviserad hushÃ¥ll", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_6_obs": {"label": "AIT aviserad grÃ¤nspunkt", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_1_obs": {"label": "AIT oaviserad jordbruk", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_2_obs": {"label": "AIT oaviserad industri", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_3_obs": {"label": "AIT oaviserad handel/tjÃ¤nster", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_4_obs": {"label": "AIT oaviserad offentlig", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_5_obs": {"label": "AIT oaviserad hushÃ¥ll", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_6_obs": {"label": "AIT oaviserad grÃ¤nspunkt", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        
        # AIT norm
        "ait_a_1_norm": {"label": "AIT aviserad jordbruk norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_2_norm": {"label": "AIT aviserad industri norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_3_norm": {"label": "AIT aviserad handel/tjÃ¤nster norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_4_norm": {"label": "AIT aviserad offentlig norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_5_norm": {"label": "AIT aviserad hushÃ¥ll norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_6_norm": {"label": "AIT aviserad grÃ¤nspunkt norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_1_norm": {"label": "AIT oaviserad jordbruk norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_2_norm": {"label": "AIT oaviserad industri norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_3_norm": {"label": "AIT oaviserad handel/tjÃ¤nster norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_4_norm": {"label": "AIT oaviserad offentlig norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_5_norm": {"label": "AIT oaviserad hushÃ¥ll norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_6_norm": {"label": "AIT oaviserad grÃ¤nspunkt norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        
        # Ã…ME
        "ame_1": {"label": "Ã…ME jordbruk", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_2": {"label": "Ã…ME industri", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_3": {"label": "Ã…ME handel/tjÃ¤nster", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_4": {"label": "Ã…ME offentlig", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_5": {"label": "Ã…ME hushÃ¥ll", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_6": {"label": "Ã…ME grÃ¤nspunkt", "category": "ame", "unit": "kW", "format": ",.1f"},
    }