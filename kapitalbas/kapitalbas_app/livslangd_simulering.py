# livslangd_simulering.py
# (1) Modellspecifikation
#   a) Detaljläge (komponentnivå, källa: final_capbase_sample):
#      - Beräknar NAV, årlig avskrivning och räntedel enligt EIFS 2023:5.
#      - Linjär avskrivning fram till ekonomisk livslängd; därefter konstant svansavskrivning (§5).
#      - Ålder tas direkt från age_component_236 (ingen halvårsskiftesjustering i denna version).
#   b) Översiktsläge (nät×kategori, källa: capbase_compress_tail):
#      - Snabb approximation: skalar årlig avskrivning och ränta proportionellt när livslängder ändras.
#   c) Trendläge (nät×år, källa: capcost_python):
#      - Justerar nät×år KPI (dep/return/kapkostnad) med samma proportionella ansats över tiden.
# (2) Motivation
#   - Enkel, stabil snapshotversion för 2023 som bas för vidareutveckling.
#   - Strukturen är förberedd för att senare bygga in halvårsskifteslogik och kategori‐specifika livslängder.

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional

# ================== Hjälpfunktioner ==================

def _compute_dep_and_nav(
    AV: np.ndarray,
    age: np.ndarray,
    eko: np.ndarray,
    max_age: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Beräkna (ackumulerad avskrivning, årets avskrivning, NAV_slut) vektoriserat."""
    AV = np.asarray(AV, dtype=float)
    a = np.clip(np.asarray(age, dtype=float), 0.0, max_age)

    # satser för ordinarie och svans
    rate_eko = np.where(eko > 0, AV / eko, 0.0)
    rate_tail = np.where((max_age - eko) > 0, AV / (max_age - eko), 0.0)

    # ackumulerad avskrivning
    ack_dep = np.where(
        a <= eko,
        AV * (a / eko),
        np.where(a <= max_age,
                 AV * (1.0 - (max_age - a) / (max_age - eko + 1e-12)),
                 AV)
    )

    # årets avskrivning (segmentbaserad)
    dep_year_raw = np.where(
        a <= 0.0, 0.0,
        np.where(a <= eko, rate_eko, np.where(a <= max_age, rate_tail, 0.0))
    )
    dep_year = np.minimum(dep_year_raw, np.maximum(0.0, AV - ack_dep + dep_year_raw))

    nav_end = np.clip(AV - ack_dep, 0.0, None)
    return ack_dep, dep_year, nav_end

def _nav_start_from_end(nav_end: np.ndarray, dep_year: np.ndarray) -> np.ndarray:
    """Ingående NAV ≈ utgående NAV + årets avskrivning."""
    return nav_end + dep_year

def _interest_from_nav(nav_start: np.ndarray, nav_end: np.ndarray, r: float) -> np.ndarray:
    """Beräkna ränta baserat på medel-NAV."""
    return r * (nav_start + nav_end) / 2.0

# ================== DETALJLÄGE ==================

def simulate_detail(
    df_components: pd.DataFrame,
    eko_years: Optional[Dict[str, float]] = None,
    max_years: Optional[Dict[str, float]] = None,
    default_eko: float = 30.0,
    default_max: float = 50.0,
    rate: float = 0.03,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Komponentvis simulering för snapshot 2023 (code=236).
    Kräver kolumner: ['id_component','id_network','cat_encode','anskaffningsvärde',
                      'age_component_236','nuav_236']
    """
    code = 236
    age_col = f"age_component_{code}"
    nuav_col = f"nuav_{code}"

    df = df_components.copy()
    needed = ["id_component", "id_network", "cat_encode", "anskaffningsvärde", age_col, nuav_col]
    for c in needed:
        if c not in df.columns:
            raise KeyError(f"Detaljläge saknar kolumn: {c}")

    # Ålder direkt från kolumn
    df["alder"] = df[age_col].astype(float).clip(lower=0.0)

    # Livslängder
    eko_map = np.vectorize(lambda cat: (eko_years or {}).get(str(cat), default_eko))
    max_map = np.vectorize(lambda cat: (max_years or {}).get(str(cat), default_max))
    eko = eko_map(df["cat_encode"].values).astype(float)
    maxl = max_map(df["cat_encode"].values).astype(float)
    maxl = np.where(maxl <= eko, eko + 1.0, maxl)

    AV = df["anskaffningsvärde"].astype(float).values

    # Beräkningar
    ack, dep_y, nav_end = _compute_dep_and_nav(AV, df["alder"].values, eko, maxl)
    nav_start = _nav_start_from_end(nav_end, dep_y)
    interest = _interest_from_nav(nav_start, nav_end, rate)

    df_out = df[["id_component", "id_network", "cat_encode"]].copy()
    df_out["year"] = 2023
    df_out["alder"] = df["alder"].values
    df_out["AV"] = AV
    df_out["nuav_faktisk"] = df[nuav_col].astype(float).values
    df_out["dep_ack_sim"] = ack
    df_out["dep_year_sim"] = dep_y
    df_out["nuav_sim"] = nav_end
    df_out["ranta_sim"] = interest
    df_out["kapkost_sim"] = df_out["dep_year_sim"] + df_out["ranta_sim"]

    agg = (
        df_out.groupby(["id_network"], as_index=False)
        .agg(
            nuav_faktisk=("nuav_faktisk", "sum"),
            nuav_sim=("nuav_sim", "sum"),
            dep_year_sim=("dep_year_sim", "sum"),
            ranta_sim=("ranta_sim", "sum"),
            kapkost_sim=("kapkost_sim", "sum"),
        )
    )
    agg["diff_nav"] = agg["nuav_sim"] - agg["nuav_faktisk"]

    return df_out, agg

# ================== ÖVERSIKTSLÄGE ==================

def simulate_overview(
    df_capbase_tail: pd.DataFrame,
    scale_dep: float,
    scale_return: float,
) -> pd.DataFrame:
    """
    Snapshot 2023: nät×kategori, skala dep och ränta proportionellt.
    Kräver kolumner: ['nuav_ord_236','nuav_tail_236','dep_ord_236','dep_tail_236']
    """
    code = 236
    cols = {
        "nuav_ord": f"nuav_ord_{code}",
        "nuav_tail": f"nuav_tail_{code}",
        "dep_ord": f"dep_ord_{code}",
        "dep_tail": f"dep_tail_{code}",
    }
    for c in cols.values():
        if c not in df_capbase_tail.columns:
            raise KeyError(f"Översiktsläge saknar kolumn: {c}")

    df = df_capbase_tail.copy()
    df["nuav"] = df[cols["nuav_ord"]].astype(float) + df[cols["nuav_tail"]].astype(float)
    dep_sum = df[cols["dep_ord"]].astype(float) + df[cols["dep_tail"]].astype(float)
    df["dep_sim"] = dep_sum * scale_dep
    df["return_sim"] = df["nuav"] * scale_return
    df["kapkost_sim"] = df["dep_sim"] + df["return_sim"]

    return df[["id_network", "cat_encode", "nuav", "dep_sim", "return_sim", "kapkost_sim"]]

# ================== TRENDLÄGE ==================

def simulate_trend(
    df_capcost: pd.DataFrame,
    dep_scale: float,
    return_scale: float,
) -> pd.DataFrame:
    """
    Skala dep och ränta över hela tidsserien (nät×år).
    Kräver kolumner: ['time','id_network','dep_ord','dep_tail','return_ord','return_tail','capcost_sum']
    """
    df = df_capcost.copy()
    needed = {"dep_ord","dep_tail","return_ord","return_tail","capcost_sum","time","id_network"}
    if not needed.issubset(df.columns):
        raise KeyError(f"Trendläge saknar kolumner: {needed - set(df.columns)}")

    df["dep_sum"] = df["dep_ord"].astype(float) + df["dep_tail"].astype(float)
    df["dep_sim"] = df["dep_sum"] * dep_scale
    df["return_sum"] = df["return_ord"].astype(float) + df["return_tail"].astype(float)
    df["return_sim"] = df["return_sum"] * return_scale
    df["kapkost_sim"] = df["dep_sim"] + df["return_sim"]

    return df[["time", "id_network", "dep_sum", "return_sum", "dep_sim", "return_sim", "kapkost_sim"]]
