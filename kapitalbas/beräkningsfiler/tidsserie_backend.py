"""
Modul: tidsserie_backend.py

(1) Specifikation
- Bygger tidsserie-beräkningar ovanpå capcost_a (facit), laddad via data_loader -> st.session_state["capcost_a"].
- Arbetar i halvår (time-koder 229–236) och summerar alltid till helår (2024–2027) efter avrundning i tkr.
- Scenario (WACC): replikerar Tab 3-logiken – skalar ENDAST räntedelarna (return_ord, return_tail) med r_new/r_old per halvår, rundar i tkr, summerar till helår.
- Enheter: input i tkr (2022 års prisnivå), utdata för visning i MSEK (2022).
- Aggregat: när flera nät väljs summeras värden (systemperspektiv).
- Kvalitetskontroll: kontrollerar att dep_ord + dep_tail + return_ord + return_tail == capcost_sum per halvår, med tolerans 0,5 MSEK (500 tkr).

(2) Motivation
- Ei behöver transparent tidsserielogik som exakt matchar översikten (Tab 1/3) men med helårsvyer och scenarioöverlagring i samma flik.
- Helårssummering över H1+H2 minimerar brus och följer KPI-definitionerna i översikten.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# --- Tidkoder (hårdkodat enligt instruktion) ---
TIME_LABEL_TO_CODE: Dict[str, int] = {
    "2024h1": 229, "2024h2": 230,
    "2025h1": 231, "2025h2": 232,
    "2026h1": 233, "2026h2": 234,
    "2027h1": 235, "2027h2": 236,
}

YEAR_TO_CODES: Dict[int, List[int]] = {
    2024: [229, 230],
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236],
}

CODE_TO_YEAR: Dict[int, int] = {code: year for year, codes in YEAR_TO_CODES.items() for code in codes}

# --- Kolumndefinitioner ---
COMP_COLS = ["dep_ord", "dep_tail", "return_ord", "return_tail"]
ALL_COLS = COMP_COLS + ["capcost_sum"]

@dataclass
class QualityReport:
    mismatched_rows: int
    max_abs_diff_tkr: float
    total_abs_diff_tkr: float
    details: pd.DataFrame


def _require_columns(df: pd.DataFrame, cols: Sequence[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Saknade kolumner: {missing}")


def normalize_halfyear(df: pd.DataFrame) -> pd.DataFrame:
    """Summera till (id_network, time) över ev. extra dimensioner (t.ex. kategori).

    Kräver kolumnerna ALL_COLS; antar en rad per komponent/kategori idag och summerar till halvårsnivå.
    """
    _require_columns(df, ["id_network", "time"] + ALL_COLS)
    grp = df.groupby(["id_network", "time"], dropna=False)[ALL_COLS].sum(min_count=1)
    out = grp.reset_index()
    return out


def add_year_column(df_half: pd.DataFrame) -> pd.DataFrame:
    """Lägg till kolumn 'year' via CODE_TO_YEAR; rader vars time inte finns i mapping filtreras bort."""
    _require_columns(df_half, ["time"])  # övriga kontroller görs i normalize
    out = df_half.copy()
    out["year"] = out["time"].map(CODE_TO_YEAR)
    out = out[out["year"].notna()].copy()
    out["year"] = out["year"].astype(int)
    return out


def aggregate_year(df_half: pd.DataFrame) -> pd.DataFrame:
    """Summera H1+H2 till helår per nät (id_network, year)."""
    _require_columns(df_half, ["id_network", "time"] + ALL_COLS)
    df_y = add_year_column(df_half)
    grp = df_y.groupby(["id_network", "year"], dropna=False)[ALL_COLS].sum(min_count=1)
    return grp.reset_index()


def filter_by_networks_and_years(
    df_half: pd.DataFrame,
    networks: Optional[Sequence[int]] = None,
    years: Optional[Sequence[int]] = None,
) -> pd.DataFrame:
    """Filtrera på valda nät och år (år appliceras via time->year)."""
    out = df_half
    if networks:
        out = out[out["id_network"].isin(list(networks))]
    if years:
        years_set = set(int(y) for y in years)
        out = add_year_column(out)
        out = out[out["year"].isin(years_set)]
    return out


def to_msek(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c] / 1000.0  # tkr -> MSEK
    return out


def compute_kpi_year(
    df_year_sum: pd.DataFrame,
    years: Sequence[int],
) -> dict:
    """Beräkna KPI för vald årsmängd på redan summerat (id_network, year).

    Returnerar dict med: latest_year, capcost_msek, delta_msek, delta_pct, tail_share_pct.
    """
    _require_columns(df_year_sum, ["id_network", "year"] + ALL_COLS)
    if not len(df_year_sum):
        return {
            "latest_year": None,
            "capcost_msek": np.nan,
            "delta_msek": np.nan,
            "delta_pct": np.nan,
            "tail_share_pct": np.nan,
        }

    years_sorted = sorted(set(int(y) for y in years)) if years else sorted(df_year_sum["year"].unique().tolist())
    latest = years_sorted[-1]

    # Summa över valda nät för senaste året
    cur = df_year_sum.loc[df_year_sum["year"] == latest, ALL_COLS].sum(min_count=1)
    capcost_msek = float(cur["capcost_sum"]) / 1000.0

    # Δ mot föregående år
    prev_year = years_sorted[-2] if len(years_sorted) >= 2 else None
    if prev_year is not None and (df_year_sum["year"] == prev_year).any():
        prev = df_year_sum.loc[df_year_sum["year"] == prev_year, ALL_COLS].sum(min_count=1)
        delta_msek = float(cur["capcost_sum"] - prev["capcost_sum"]) / 1000.0
        delta_pct = (delta_msek * 1000.0) / float(prev["capcost_sum"]) * 100.0 if float(prev["capcost_sum"]) != 0 else np.nan
    else:
        delta_msek = np.nan
        delta_pct = np.nan

    # Tail-andel på dep+return
    tail_num = float(cur["dep_tail"] + cur["return_tail"]) if not cur.isna().any() else np.nan
    tail_den = float(cur["dep_ord"] + cur["dep_tail"] + cur["return_ord"] + cur["return_tail"]) if not cur.isna().any() else np.nan
    tail_share_pct = (tail_num / tail_den * 100.0) if (tail_den and not np.isnan(tail_den) and tail_den != 0) else np.nan

    return {
        "latest_year": latest,
        "capcost_msek": capcost_msek,
        "delta_msek": delta_msek,
        "delta_pct": delta_pct,
        "tail_share_pct": tail_share_pct,
    }


def delta_decomposition_year(df_year_sum: pd.DataFrame) -> pd.DataFrame:
    """Årsvis Δ-dekomponering: Δdep, Δreturn, Δtotal på totalsummor över valda nät.

    Returnerar tabell med kolumner: year, d_dep, d_return, d_total (alla i MSEK).
    """
    _require_columns(df_year_sum, ["year"] + ALL_COLS)
    if not len(df_year_sum):
        return pd.DataFrame(columns=["year", "d_dep", "d_return", "d_total"])  # tom

    # Summera över nät per år
    annual = df_year_sum.groupby("year", dropna=False)[ALL_COLS].sum(min_count=1).reset_index()
    annual = to_msek(annual, ALL_COLS)
    annual.sort_values("year", inplace=True)
    annual[["d_dep", "d_return", "d_total"]] = np.nan

    for i in range(1, len(annual)):
        cur = annual.iloc[i]
        prev = annual.iloc[i - 1]
        d_dep = (cur["dep_ord"] + cur["dep_tail"]) - (prev["dep_ord"] + prev["dep_tail"])
        d_ret = (cur["return_ord"] + cur["return_tail"]) - (prev["return_ord"] + prev["return_tail"])
        d_tot = cur["capcost_sum"] - prev["capcost_sum"]
        annual.loc[annual.index[i], ["d_dep", "d_return", "d_total"]] = [d_dep, d_ret, d_tot]

    return annual[["year", "d_dep", "d_return", "d_total"]]


def tail_share_series(df_year_sum: pd.DataFrame) -> pd.DataFrame:
    """Beräkna tail-andel per år: (dep_tail + return_tail) / (dep_total + return_total)."""
    _require_columns(df_year_sum, ["year"] + ALL_COLS)
    annual = df_year_sum.groupby("year", dropna=False)[ALL_COLS].sum(min_count=1).reset_index()
    num = annual["dep_tail"] + annual["return_tail"]
    den = annual[["dep_ord", "dep_tail", "return_ord", "return_tail"]].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        share = np.where(den != 0, num / den * 100.0, np.nan)
    out = pd.DataFrame({"year": annual["year"].astype(int), "tail_share_pct": share})
    return out


def quality_report(df_half: pd.DataFrame, tol_msek: float = 0.5) -> QualityReport:
    """Kvalitetsrapport per halvår: kontrollerar att komponenterna summerar till capcost_sum.

    tol_msek = tolerans i MSEK; avvikelser > tol flaggas.
    """
    _require_columns(df_half, ["id_network", "time"] + ALL_COLS)
    tmp = df_half.copy()
    tmp["sum_components"] = tmp[["dep_ord", "dep_tail", "return_ord", "return_tail"]].sum(axis=1)
    tmp["diff_tkr"] = (tmp["sum_components"] - tmp["capcost_sum"]).astype(float)
    tol_tkr = tol_msek * 1000.0
    tmp["flag"] = tmp["diff_tkr"].abs() > tol_tkr

    rep = QualityReport(
        mismatched_rows=int(tmp["flag"].sum()),
        max_abs_diff_tkr=float(tmp["diff_tkr"].abs().max()) if len(tmp) else 0.0,
        total_abs_diff_tkr=float(tmp["diff_tkr"].abs().sum()) if len(tmp) else 0.0,
        details=tmp.loc[tmp["flag"] == True, ["id_network", "time", "diff_tkr"]].sort_values("diff_tkr", key=lambda s: s.abs(), ascending=False),
    )
    return rep


def scenario_scale_returns_halfyear(
    df_half: pd.DataFrame,
    r_old: float,
    r_new: float,
) -> pd.DataFrame:
    """Skala räntedelarna per halvår med (r_new/r_old) och runda i tkr – matchar Tab 3.

    Returnerar en ny tabell med kolumnerna return_ord_new, return_tail_new, capcost_sum_new per (id_network, time).
    """
    _require_columns(df_half, ["id_network", "time"] + ALL_COLS)
    if not np.isfinite(r_old) or r_old == 0:
        raise ValueError("r_old måste vara ett ändligt tal ≠ 0")
    if not np.isfinite(r_new):
        raise ValueError("r_new måste vara ett ändligt tal")

    scale = float(r_new) / float(r_old)
    out = df_half.copy()

    # Runda till heltal tkr för att spegla facit/Tab 3-semantik
    out["return_ord_new"] = (out["return_ord"].astype("float64") * scale).round().astype("Int64")
    out["return_tail_new"] = (out["return_tail"].astype("float64") * scale).round().astype("Int64")

    out["capcost_sum_new"] = (
        out["dep_ord"].astype("float64")
        + out["dep_tail"].astype("float64")
        + out["return_ord_new"].astype("float64")
        + out["return_tail_new"].astype("float64")
    )
    return out


def scenario_year_from_half(
    df_half_scaled: pd.DataFrame,
) -> pd.DataFrame:
    """Summera scenario (capcost_sum_new) till helår per nät."""
    _require_columns(df_half_scaled, ["id_network", "time", "capcost_sum_new", "return_ord_new", "return_tail_new"])
    df_y = add_year_column(df_half_scaled)
    grp = df_y.groupby(["id_network", "year"], dropna=False)[["capcost_sum_new", "return_ord_new", "return_tail_new"]].sum(min_count=1)
    return grp.reset_index()


def label_networks(df_ids: pd.DataFrame, recon: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Slå på etiketter från reconciliation (om tillgängligt). Förväntar kolumner id_network, Företag, DMU."""
    out = df_ids.copy()
    if recon is None:
        out["label"] = out["id_network"].astype(str)
        return out[["id_network", "label"]]

    # Normalisera kolumnnamn lite försiktigt
    cols = {c.lower(): c for c in recon.columns}
    id_col = cols.get("id_network")
    firm_col = next((recon.columns[i] for i in range(len(recon.columns)) if str(recon.columns[i]).lower() in {"företag", "foretag", "company", "namn"}), None)
    dmu_col = next((recon.columns[i] for i in range(len(recon.columns)) if str(recon.columns[i]).lower() == "dmu"), None)

    if id_col is None:
        out["label"] = out["id_network"].astype(str)
        return out[["id_network", "label"]]

    tmp = recon.copy()
    tmp = tmp.rename(columns={id_col: "id_network"})
    parts = [
        tmp["id_network"].astype(str),
    ]
    if firm_col is not None:
        parts.insert(0, tmp[firm_col].astype(str))
    if dmu_col is not None:
        parts.append(tmp[dmu_col].astype(str))

    tmp["label"] = " - ".join(["{0}"] * len(parts))  # placeholder, ersätts str.format per rad
    # Bygg label radvis
    labels = []
    for vals in zip(*parts):
        if len(vals) == 3:
            labels.append(f"{vals[0]} - {vals[1]} - {vals[2]}")
        elif len(vals) == 2:
            labels.append(f"{vals[0]} - {vals[1]}")
        else:
            labels.append(str(vals[0]))
    tmp["label"] = labels

    out = out.merge(tmp[["id_network", "label"]], on="id_network", how="left")
    out["label"] = out["label"].fillna(out["id_network"].astype(str))
    return out[["id_network", "label"]]
