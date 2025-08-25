"""
Modul: intensitet_backend.py

(1) Specifikation
- Merge capcost_a med volymdata (MWh, kunder) via reconciliation-fil
- Beräkna intensiteter: kr/MWh, kr/kund (tkr-basis, 2022 års prisnivå)
- Statistisk analys: fördelning, ranking, extremvärden
- Kvalitetskontroller: merge-täckning, outlier-detection
- Stöd för scenario-analys (påverkan av WACC-ändringar på intensiteter)

(2) Motivation
- Ger Ei möjlighet att jämföra kapitalkostnader relativt nätens storlek/aktivitetsnivå
- Kompletterar absoluta kapitalkostnadsmått med intensitetsperspektiv
- Underlättar identifiering av outlier-nät för närmare granskning
- Konsistent med DEA-effektivitetsanalysens output-variabler
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# --- Konstanter ---
YEAR_TO_CODES: Dict[int, List[int]] = {
    2024: [229, 230], 2025: [231, 232], 
    2026: [233, 234], 2027: [235, 236],
}

@dataclass
class IntensityStats:
    """Statistisk sammanfattning för intensitetsmått."""
    mean: float
    median: float
    std: float
    q25: float
    q75: float
    min_val: float
    max_val: float
    count: int

@dataclass
class MergeQuality:
    """Kvalitetsrapport för datasammanfogning."""
    total_networks: int
    networks_with_volumes: int
    merge_coverage_pct: float
    networks_missing_volumes: List[int]
    networks_with_zero_volumes: List[int]


def _require_columns(df: pd.DataFrame, cols: Sequence[str], df_name: str = "DataFrame") -> None:
    """Kontrollera att DataFrame innehåller nödvändiga kolumner."""
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{df_name} saknar kolumner: {missing}")


def load_and_validate_volume_data(
    dmu_volymer_df: pd.DataFrame,
    reconciliation_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ladda och validera volymdata och reconciliation-fil.
    
    Returns:
        Tuple[validerad_dmu_volymer, validerad_reconciliation]
    """
    # Validera dmu_volymer
    _require_columns(dmu_volymer_df, ["DMU", "CU", "MWh_total"], "dmu_volymer")
    dmu_clean = dmu_volymer_df.copy()
    
    # Konvertera till numeriska typer och hantera fel
    dmu_clean["DMU"] = pd.to_numeric(dmu_clean["DMU"], errors="coerce")
    dmu_clean["CU"] = pd.to_numeric(dmu_clean["CU"], errors="coerce")
    dmu_clean["MWh_total"] = pd.to_numeric(dmu_clean["MWh_total"], errors="coerce")
    
    # Filtrera bort rader med ogiltiga värden
    dmu_clean = dmu_clean.dropna(subset=["DMU", "CU", "MWh_total"])
    dmu_clean["DMU"] = dmu_clean["DMU"].astype("int64")
    
    # Validera reconciliation
    _require_columns(reconciliation_df, ["id_network", "DMU"], "reconciliation")
    recon_clean = reconciliation_df.copy()
    recon_clean["id_network"] = pd.to_numeric(recon_clean["id_network"], errors="coerce")
    recon_clean["DMU"] = pd.to_numeric(recon_clean["DMU"], errors="coerce")
    recon_clean = recon_clean.dropna(subset=["id_network", "DMU"])
    recon_clean["id_network"] = recon_clean["id_network"].astype("int64")
    recon_clean["DMU"] = recon_clean["DMU"].astype("int64")
    
    return dmu_clean, recon_clean


def merge_capcost_with_volumes(
    capcost_df: pd.DataFrame,
    dmu_volymer_df: pd.DataFrame,
    reconciliation_df: pd.DataFrame,
    year: int = 2024
) -> Tuple[pd.DataFrame, MergeQuality]:
    """
    Merge kapitalkostnadsdata med volymdata via reconciliation.
    
    Args:
        capcost_df: Kapitalkostnadsdata (capcost_a format)
        dmu_volymer_df: Volymdata (DMU, CU, MWh_total)
        reconciliation_df: Kopplingstabell (id_network -> DMU)
        year: År att filtrera på (default 2024)
        
    Returns:
        Tuple[merged_data_aggregated_to_DMU, merge_quality_report]
    """
    _require_columns(capcost_df, ["id_network", "time", "capcost_sum"], "capcost_df")
    
    # Validera och rensa volymdata
    dmu_clean, recon_clean = load_and_validate_volume_data(dmu_volymer_df, reconciliation_df)
    
    # Filtrera capcost_df på valt år och summera H1+H2
    if year not in YEAR_TO_CODES:
        raise ValueError(f"År {year} stöds inte. Giltiga år: {list(YEAR_TO_CODES.keys())}")
    
    year_codes = YEAR_TO_CODES[year]
    capcost_year = capcost_df[capcost_df["time"].isin(year_codes)].copy()
    
    # Summera per nät (H1+H2)
    capcost_agg = capcost_year.groupby("id_network").agg({
        "capcost_sum": "sum",
        "dep_ord": "sum",
        "dep_tail": "sum", 
        "return_ord": "sum",
        "return_tail": "sum"
    }).reset_index()
    
    # Merge capcost med reconciliation för att få DMU
    capcost_with_dmu = capcost_agg.merge(recon_clean, on="id_network", how="left")
    
    # KRITISK FIX: Aggregera till DMU-nivå före merge med volymer
    capcost_by_dmu = capcost_with_dmu.groupby("DMU").agg({
        "capcost_sum": "sum",
        "dep_ord": "sum",
        "dep_tail": "sum", 
        "return_ord": "sum",
        "return_tail": "sum"
    }).reset_index()
    
    # Merge DMU-aggregerad kapitalkostnad med volymer
    merged = capcost_by_dmu.merge(dmu_clean, on="DMU", how="left")
    
    # Beräkna kvalitetsstatistik (på nät-nivå för transparens)
    total_networks = len(capcost_agg)
    networks_with_dmu = capcost_with_dmu["DMU"].notna().sum()
    networks_with_volumes = capcost_with_dmu[capcost_with_dmu["DMU"].notna()].merge(
        dmu_clean, on="DMU", how="inner"
    )["DMU"].nunique()
    
    merge_coverage = (networks_with_dmu / total_networks * 100) if total_networks > 0 else 0
    
    missing_volumes = capcost_with_dmu[capcost_with_dmu["DMU"].isna()]["id_network"].tolist()
    zero_volumes = []  # På DMU-nivå behöver vi inte flagga noll-volymer på samma sätt
    
    quality = MergeQuality(
        total_networks=total_networks,
        networks_with_volumes=networks_with_volumes,
        merge_coverage_pct=merge_coverage,
        networks_missing_volumes=missing_volumes,
        networks_with_zero_volumes=zero_volumes
    )
    
    return merged, quality


def calculate_intensities(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräkna intensitetsmått (SEK/MWh, SEK/kund) baserat på merged DMU-data.
    
    Args:
        merged_df: Sammanslagen DMU-aggregerad data från merge_capcost_with_volumes
        
    Returns:
        DataFrame med intensitetsmått tillagda
    """
    result = merged_df.copy()
    
    # Beräkna intensiteter (tkr → SEK genom att multiplicera med 1000)
    # Undvik division med noll genom att sätta till NaN
    result["sek_per_mwh"] = np.where(
        (result["MWh_total"] > 0) & result["MWh_total"].notna(),
        (result["capcost_sum"] * 1000) / result["MWh_total"],
        np.nan
    )
    
    result["sek_per_kund"] = np.where(
        (result["CU"] > 0) & result["CU"].notna(),
        (result["capcost_sum"] * 1000) / result["CU"],
        np.nan
    )
    
    # Beräkna även komponentvis intensiteter
    for component in ["dep_ord", "dep_tail", "return_ord", "return_tail"]:
        result[f"{component}_per_mwh"] = np.where(
            (result["MWh_total"] > 0) & result["MWh_total"].notna(),
            (result[component] * 1000) / result["MWh_total"],
            np.nan
        )
        
        result[f"{component}_per_kund"] = np.where(
            (result["CU"] > 0) & result["CU"].notna(),
            (result[component] * 1000) / result["CU"],
            np.nan
        )
    
    return result


def compute_intensity_statistics(df: pd.DataFrame, intensity_col: str) -> IntensityStats:
    """
    Beräkna beskrivande statistik för ett intensitetsmått.
    
    Args:
        df: DataFrame med intensitetsdata
        intensity_col: Kolumnnamn för intensitetsmått
        
    Returns:
        IntensityStats objekt med statistisk sammanfattning
    """
    if intensity_col not in df.columns:
        raise KeyError(f"Kolumn {intensity_col} finns inte i DataFrame")
    
    values = df[intensity_col].dropna()
    
    if len(values) == 0:
        return IntensityStats(
            mean=np.nan, median=np.nan, std=np.nan,
            q25=np.nan, q75=np.nan, min_val=np.nan, max_val=np.nan, count=0
        )
    
    return IntensityStats(
        mean=float(values.mean()),
        median=float(values.median()),
        std=float(values.std()),
        q25=float(values.quantile(0.25)),
        q75=float(values.quantile(0.75)),
        min_val=float(values.min()),
        max_val=float(values.max()),
        count=len(values)
    )


def identify_outliers(
    df: pd.DataFrame, 
    intensity_col: str,
    method: str = "iqr",
    iqr_multiplier: float = 1.5
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Identifiera outliers baserat på intensitetsmått.
    
    Args:
        df: DataFrame med intensitetsdata
        intensity_col: Kolumnnamn för intensitetsmått
        method: Metod för outlier-detection ("iqr" eller "zscore")
        iqr_multiplier: Multiplikator för IQR-metoden (default 1.5)
        
    Returns:
        Tuple[outliers_high, outliers_low]
    """
    if intensity_col not in df.columns:
        raise KeyError(f"Kolumn {intensity_col} finns inte i DataFrame")
    
    values = df[intensity_col].dropna()
    
    if len(values) == 0:
        empty_df = df.iloc[0:0].copy()  # Tom DataFrame med samma struktur
        return empty_df, empty_df
    
    if method == "iqr":
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - iqr_multiplier * iqr
        upper_bound = q3 + iqr_multiplier * iqr
        
        outliers_high = df[df[intensity_col] > upper_bound].copy()
        outliers_low = df[df[intensity_col] < lower_bound].copy()
        
    elif method == "zscore":
        z_scores = np.abs((values - values.mean()) / values.std())
        outlier_mask = z_scores > 2.5  # 2.5 standard deviations
        outlier_indices = values[outlier_mask].index
        
        # Dela upp i höga och låga baserat på om de är över eller under medelvärde
        mean_val = values.mean()
        outliers_high = df[(df.index.isin(outlier_indices)) & (df[intensity_col] > mean_val)].copy()
        outliers_low = df[(df.index.isin(outlier_indices)) & (df[intensity_col] < mean_val)].copy()
        
    else:
        raise ValueError(f"Okänd outlier-metod: {method}")
    
    return outliers_high, outliers_low


def create_intensity_ranking(
    df: pd.DataFrame, 
    intensity_col: str, 
    top_n: int = 10,
    include_network_names: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Skapa ranking av nät baserat på intensitetsmått.
    
    Args:
        df: DataFrame med intensitetsdata
        intensity_col: Kolumnnamn för intensitetsmått
        top_n: Antal nät att inkludera i topp/botten-listor
        include_network_names: Inkludera nätnamn från reconciliation om tillgängligt
        
    Returns:
        Tuple[top_networks, bottom_networks]
    """
    if intensity_col not in df.columns:
        raise KeyError(f"Kolumn {intensity_col} finns inte i DataFrame")
    
    # Filtrera bort rader utan giltiga intensitetsvägen
    valid_df = df.dropna(subset=[intensity_col]).copy()
    
    if len(valid_df) == 0:
        empty_df = df.iloc[0:0].copy()
        return empty_df, empty_df
    
    # Sortera och ta top/bottom
    sorted_desc = valid_df.sort_values(intensity_col, ascending=False)
    sorted_asc = valid_df.sort_values(intensity_col, ascending=True)
    
    top_networks = sorted_desc.head(top_n).copy()
    bottom_networks = sorted_asc.head(top_n).copy()
    
    # Lägg till ranking-nummer
    top_networks["ranking"] = range(1, len(top_networks) + 1)
    bottom_networks["ranking"] = range(1, len(bottom_networks) + 1)
    
    return top_networks, bottom_networks


def apply_intensity_scenario(
    df: pd.DataFrame,
    r_old: float = 0.0453,
    r_new: float = 0.0453
) -> pd.DataFrame:
    """
    Tillämpa WACC-scenario på intensitetsdata genom att skala endast return-komponenter.
    
    Args:
        df: DataFrame med intensitetsdata (DMU-aggregerad)
        r_old: Gammal WACC (default 4.53%)
        r_new: Ny WACC för scenario
        
    Returns:
        DataFrame med scenario-kolumner tillagda
    """
    if not np.isfinite(r_old) or r_old == 0:
        raise ValueError("r_old måste vara ett ändligt tal ≠ 0")
    if not np.isfinite(r_new):
        raise ValueError("r_new måste vara ett ändligt tal")
    
    result = df.copy()
    scale_factor = float(r_new) / float(r_old)
    
    # Skala return-komponenter
    result["return_ord_new"] = result["return_ord"] * scale_factor
    result["return_tail_new"] = result["return_tail"] * scale_factor
    
    # Beräkna ny total kapitalkostnad
    result["capcost_sum_new"] = (
        result["dep_ord"] + result["dep_tail"] + 
        result["return_ord_new"] + result["return_tail_new"]
    )
    
    # Beräkna nya intensiteter i SEK
    result["sek_per_mwh_new"] = np.where(
        (result["MWh_total"] > 0) & result["MWh_total"].notna(),
        (result["capcost_sum_new"] * 1000) / result["MWh_total"],
        np.nan
    )
    
    result["sek_per_kund_new"] = np.where(
        (result["CU"] > 0) & result["CU"].notna(),
        (result["capcost_sum_new"] * 1000) / result["CU"],
        np.nan
    )
    
    # Beräkna deltan
    result["delta_sek_per_mwh"] = result["sek_per_mwh_new"] - result["sek_per_mwh"]
    result["delta_sek_per_kund"] = result["sek_per_kund_new"] - result["sek_per_kund"]
    
    return result


def prepare_distribution_data(
    df: pd.DataFrame, 
    intensity_col: str, 
    bins: int = 20
) -> pd.DataFrame:
    """
    Förbereda data för histogram/fördelningsanalys.
    
    Args:
        df: DataFrame med intensitetsdata
        intensity_col: Kolumnnamn för intensitetsmått
        bins: Antal bins för histogram
        
    Returns:
        DataFrame med bin-edges och counts för histogram
    """
    if intensity_col not in df.columns:
        raise KeyError(f"Kolumn {intensity_col} finns inte i DataFrame")
    
    values = df[intensity_col].dropna()
    
    if len(values) == 0:
        return pd.DataFrame({"bin_start": [], "bin_end": [], "count": []})
    
    counts, bin_edges = np.histogram(values, bins=bins)
    
    result = pd.DataFrame({
        "bin_start": bin_edges[:-1],
        "bin_end": bin_edges[1:],
        "count": counts
    })
    
    # Lägg till bin-mitt för visualisering
    result["bin_center"] = (result["bin_start"] + result["bin_end"]) / 2
    
    return result