"""
data_loaders/incentive_data.py

Laddar och förbereder incitamentdata från all_adjust_vars.csv.
Mappar numerisk reid till REId-format (REL00001, etc.).
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List


# Alla variabelkolumner som kan overridas
# Dessa är företagsspecifika observerade och normvärden
VARIABLE_COLUMNS: List[str] = [
    # Nätförlust
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
    # ÅME per kundtyp (6 st)
    "ame_1", "ame_2", "ame_3", "ame_4", "ame_5", "ame_6",
]


def load_incentive_data(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Laddar incitamentdata och förbereder den för beräkning.
    
    Args:
        filepath: Sökväg till all_adjust_vars.csv. Om None, använd default.
    
    Returns:
        DataFrame med alla incitamentvariabler, REId i korrekt format.
        Kolumnen 'capcost' tas bort (placeholder som ersätts med faktisk avkastning).
    """
    if filepath is None:
        # Default sökväg relativt till projektrot
        # Prova flera möjliga platser
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
                f"Kunde inte hitta all_adjust_vars.csv. Prövade: {possible_paths}"
            )
    
    df = pd.read_csv(filepath)
    
    # Mappa numerisk reid till REId-format (REL00001, REL00886, etc.)
    df['REId'] = df['reid'].apply(lambda x: f"REL{int(x):05d}")
    
    # Ta bort placeholder capcost - ersätts med faktisk avkastning i pipeline
    if 'capcost' in df.columns:
        df = df.drop(columns=['capcost'])
    
    return df


def prepare_incentive_input(
    incentive_data: pd.DataFrame,
    return_per_year: pd.DataFrame
) -> pd.DataFrame:
    """
    Förbereder komplett input för incitamentberäkning genom att
    slå ihop incitamentdata med avkastning per år.
    
    Args:
        incentive_data: DataFrame från load_incentive_data()
        return_per_year: DataFrame med REId, Avkastning_2024..2027 (tkr)
    
    Returns:
        DataFrame med alla variabler redo för calculate_all_incentives().
        Innehåller kolumnen 'ret_period' (avkastning i kr för respektive år).
    """
    df = incentive_data.copy()
    
    # Slå ihop med avkastning per år
    df = df.merge(return_per_year, on='REId', how='left')
    
    # Skapa ret_period baserat på år (konvertera tkr -> kr)
    df['ret_period'] = df.apply(
        lambda row: row.get(f"Avkastning_{int(row['year'])}", 0) * 1000,
        axis=1
    )
    
    return df


def get_incentive_summary_by_reid(
    incentive_results: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregerar incitamentresultat till en rad per REId (periodsumma).
    
    Args:
        incentive_results: Output från calculate_all_incentives()
    
    Returns:
        DataFrame med en rad per REId:
        - REId
        - Kvalitetsjustering_Total (tkr)
        - Natforlustjustering_Total (tkr)
        - Belastningsjustering_Total (tkr)
        - Incitamentjustering_Total (tkr)
        - Missing_Incentive_Data (bool)
    """
    from calculations.incentive_parameters import MISSING_DATA_IDS
    
    # Periodsummorna finns redan på alla rader (aggregate_period_totals)
    # Extrahera en rad per REId
    df_summary = incentive_results.groupby('REId').first().reset_index()
    
    # Välj relevanta kolumner
    cols_to_keep = ['REId']
    rename_map = {}
    
    # Periodsummor (från aggregate_period_totals)
    if 'inter_incentive_sum' in df_summary.columns:
        cols_to_keep.append('inter_incentive_sum')
        rename_map['inter_incentive_sum'] = 'Kvalitetsjustering_Total'
    if 'loss_incentive_sum' in df_summary.columns:
        cols_to_keep.append('loss_incentive_sum')
        rename_map['loss_incentive_sum'] = 'Natforlustjustering_Total'
    if 'util_incentive_sum' in df_summary.columns:
        cols_to_keep.append('util_incentive_sum')
        rename_map['util_incentive_sum'] = 'Belastningsjustering_Total'
    if 'incentive_total' in df_summary.columns:
        cols_to_keep.append('incentive_total')
        rename_map['incentive_total'] = 'Incitamentjustering_Total'
    
    df_summary = df_summary[cols_to_keep].copy()
    
    # Konvertera från kr till tkr
    for col in cols_to_keep[1:]:  # Skippa REId
        df_summary[col] = df_summary[col] / 1000
    
    # Byt namn
    df_summary = df_summary.rename(columns=rename_map)
    
    # Flagga för saknad data (baserat på numerisk reid i MISSING_DATA_IDS)
    df_summary['Missing_Incentive_Data'] = df_summary['REId'].apply(
        lambda x: int(x.replace('REL', '')) in MISSING_DATA_IDS
    )
    
    return df_summary


def apply_variable_overrides(
    df: pd.DataFrame,
    user_reid: str,
    variable_overrides: Optional[Dict[str, float]]
) -> pd.DataFrame:
    """
    Applicerar variabel-overrides för ett specifikt företag.
    
    Overrides appliceras på ALLA år (2024-2027) för det angivna företaget.
    Övriga företag påverkas inte.
    
    Args:
        df: DataFrame med incitamentdata (output från prepare_incentive_input)
        user_reid: REId för företaget vars variabler ska ändras (ex: "REL00886")
        variable_overrides: Dict med kolumnnamn -> nytt värde
                           Ex: {"nf_obs": 0.045, "ug_obs": 0.65}
                           Om None eller tom dict -> ingen ändring
    
    Returns:
        DataFrame med applicerade overrides
    """
    if not variable_overrides:
        return df
    
    df = df.copy()
    
    # Skapa mask för användarens rader
    mask = df['REId'] == user_reid
    
    if not mask.any():
        print(f"    [VARNING] Företag {user_reid} hittades inte i incitamentdata")
        return df
    
    # Applicera varje override (filtrera bort ogiltiga värden)
    applied = []
    for col, value in variable_overrides.items():
        # Skippa None, "NULL", "null" och andra ogiltiga värden
        if value is None or value == "NULL" or value == "null":
            continue
        
        if col in df.columns:
            try:
                df.loc[mask, col] = float(value)
                applied.append(col)
            except (ValueError, TypeError) as e:
                print(f"    [VARNING] Kunde inte konvertera '{col}'={value}: {e}")
        else:
            print(f"    [VARNING] Okänd variabel '{col}' ignorerades")
    
    if applied:
        print(f"    Variabel-overrides för {user_reid}: {len(applied)} st ({', '.join(applied[:5])}{'...' if len(applied) > 5 else ''})")
    
    return df


def get_user_baseline_variables(
    user_reid: str,
    year: int = 2024,
    filepath: Optional[str] = None
) -> Dict[str, float]:
    """
    Hämtar baseline-värden för ett företags incitamentvariabler.
    
    Returnerar värden för ett specifikt år (default 2024).
    Används i UI för att visa baseline i input-fält.
    
    Args:
        user_reid: REId för företaget (ex: "REL00886")
        year: År att hämta värden för (default 2024)
        filepath: Sökväg till data (None = default)
    
    Returns:
        Dict med variabelnamn -> baseline-värde
        Ex: {"nf_obs": 0.039, "ug_obs": 0.404, ...}
        
        Returnerar tom dict om företaget inte hittas.
    """
    try:
        df = load_incentive_data(filepath)
    except FileNotFoundError:
        return {}
    
    # Filtrera på företag och år
    mask = (df['REId'] == user_reid) & (df['year'] == year)
    df_user = df[mask]
    
    if df_user.empty:
        return {}
    
    # Extrahera första (och enda) raden
    row = df_user.iloc[0]
    
    # Bygg dict med alla tillgängliga variabler
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
    Returnerar metadata för alla incitamentvariabler.
    
    Används för att bygga UI med korrekta labels, enheter och kategorier.
    
    Returns:
        Dict med variabelnamn -> metadata dict:
        {
            "nf_obs": {
                "label": "Nätförlust observerad",
                "category": "netloss",
                "unit": "andel",
                "format": ".4f",
            },
            ...
        }
    """
    return {
        # Nätförlust
        "nf_norm": {"label": "Nätförlust norm", "category": "netloss", "unit": "andel", "format": ".4f"},
        "nf_obs": {"label": "Nätförlust observerad", "category": "netloss", "unit": "andel", "format": ".4f"},
        "e_in": {"label": "Energi in", "category": "netloss", "unit": "MWh", "format": ",.0f"},
        
        # Belastning
        "ug_norm": {"label": "Utnyttjandegrad norm", "category": "load", "unit": "andel", "format": ".4f"},
        "ug_obs": {"label": "Utnyttjandegrad observerad", "category": "load", "unit": "andel", "format": ".4f"},
        "k_upstream": {"label": "Kostnad överliggande nät", "category": "load", "unit": "kr", "format": ",.0f"},
        
        # CEMI4
        "cemi4_norm": {"label": "CEMI4 norm", "category": "quality", "unit": "andel", "format": ".4f"},
        "cemi4_obs": {"label": "CEMI4 observerad", "category": "quality", "unit": "andel", "format": ".4f"},
        
        # AIF observerade
        "aif_a_1_obs": {"label": "AIF aviserad jordbruk", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_2_obs": {"label": "AIF aviserad industri", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_3_obs": {"label": "AIF aviserad handel/tjänster", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_4_obs": {"label": "AIF aviserad offentlig", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_5_obs": {"label": "AIF aviserad hushåll", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_a_6_obs": {"label": "AIF aviserad gränspunkt", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_1_obs": {"label": "AIF oaviserad jordbruk", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_2_obs": {"label": "AIF oaviserad industri", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_3_obs": {"label": "AIF oaviserad handel/tjänster", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_4_obs": {"label": "AIF oaviserad offentlig", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_5_obs": {"label": "AIF oaviserad hushåll", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        "aif_o_6_obs": {"label": "AIF oaviserad gränspunkt", "category": "aif_obs", "unit": "antal/kW", "format": ".4f"},
        
        # AIF norm
        "aif_a_1_norm": {"label": "AIF aviserad jordbruk norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_2_norm": {"label": "AIF aviserad industri norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_3_norm": {"label": "AIF aviserad handel/tjänster norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_4_norm": {"label": "AIF aviserad offentlig norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_5_norm": {"label": "AIF aviserad hushåll norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_a_6_norm": {"label": "AIF aviserad gränspunkt norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_1_norm": {"label": "AIF oaviserad jordbruk norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_2_norm": {"label": "AIF oaviserad industri norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_3_norm": {"label": "AIF oaviserad handel/tjänster norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_4_norm": {"label": "AIF oaviserad offentlig norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_5_norm": {"label": "AIF oaviserad hushåll norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        "aif_o_6_norm": {"label": "AIF oaviserad gränspunkt norm", "category": "aif_norm", "unit": "antal/kW", "format": ".4f"},
        
        # AIT observerade
        "ait_a_1_obs": {"label": "AIT aviserad jordbruk", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_2_obs": {"label": "AIT aviserad industri", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_3_obs": {"label": "AIT aviserad handel/tjänster", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_4_obs": {"label": "AIT aviserad offentlig", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_5_obs": {"label": "AIT aviserad hushåll", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_6_obs": {"label": "AIT aviserad gränspunkt", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_1_obs": {"label": "AIT oaviserad jordbruk", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_2_obs": {"label": "AIT oaviserad industri", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_3_obs": {"label": "AIT oaviserad handel/tjänster", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_4_obs": {"label": "AIT oaviserad offentlig", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_5_obs": {"label": "AIT oaviserad hushåll", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_6_obs": {"label": "AIT oaviserad gränspunkt", "category": "ait_obs", "unit": "tim/kWh", "format": ".4f"},
        
        # AIT norm
        "ait_a_1_norm": {"label": "AIT aviserad jordbruk norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_2_norm": {"label": "AIT aviserad industri norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_3_norm": {"label": "AIT aviserad handel/tjänster norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_4_norm": {"label": "AIT aviserad offentlig norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_5_norm": {"label": "AIT aviserad hushåll norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_a_6_norm": {"label": "AIT aviserad gränspunkt norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_1_norm": {"label": "AIT oaviserad jordbruk norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_2_norm": {"label": "AIT oaviserad industri norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_3_norm": {"label": "AIT oaviserad handel/tjänster norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_4_norm": {"label": "AIT oaviserad offentlig norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_5_norm": {"label": "AIT oaviserad hushåll norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        "ait_o_6_norm": {"label": "AIT oaviserad gränspunkt norm", "category": "ait_norm", "unit": "tim/kWh", "format": ".4f"},
        
        # ÅME
        "ame_1": {"label": "ÅME jordbruk", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_2": {"label": "ÅME industri", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_3": {"label": "ÅME handel/tjänster", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_4": {"label": "ÅME offentlig", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_5": {"label": "ÅME hushåll", "category": "ame", "unit": "kW", "format": ",.1f"},
        "ame_6": {"label": "ÅME gränspunkt", "category": "ame", "unit": "kW", "format": ",.1f"},
    }