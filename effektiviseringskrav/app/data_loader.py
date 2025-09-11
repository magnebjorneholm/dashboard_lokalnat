# data_loader.py
# Läs DEA-bas, upptäck CAPEX-scenariofiler från kapitalbasen och merge:a in dem.
# Enheter: tkr (som i Data_modeller.xlsx). Exportår: 2024 (H1+H2).
# UPPDATERAD: Organisationsbaserade sökvägar för scenario-filer

from __future__ import annotations
from pathlib import Path   
import re
import pandas as pd
from typing import Tuple, Dict
import streamlit as st

# UPPDATERAD: Bas-katalog utan organisationsspecifikation (läggs till senare)
SCENARIO_DIR_BASE = "scenario/kapitalbas/exports_to_dea"


def get_user_org() -> str:
    """Hämtar aktuell organisations-ID från session state"""
    return st.session_state.get('current_user', 'default')


# ======= Basinläsning av DEA-data (Excel) ====================================
def load_data(filepath: str) -> pd.DataFrame:
    """
    Läs DEA-bas från Excel (blad 'Körning') och skapa TOTEX = OPEXp + CAPEX.
    Förväntade kolumner: ['DMU','REId','Företag','OPEXp','CAPEX','CU','MW','NS','MWhl','MWhh'].
    Enhet: tkr.
    """
    try:
        df = pd.read_excel(filepath, sheet_name="Körning", engine="openpyxl")
    except Exception as e:
        raise RuntimeError(f"Fel vid inläsning av fil: {e}")

    expected = ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Saknade kolumner i Excel-filen: {missing}")

    # Säkerställ numerik för kostnader
    for c in ['OPEXp', 'CAPEX']:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]
    df.reset_index(drop=True, inplace=True)
    return df

# ------------------------------------------------------------
# Scenariomerge: aggregera per DMU innan merge för att undvika 1→N-dubbletter
# ------------------------------------------------------------

def _latest_capex_scenario_path(org: str = None) -> Tuple[Path | None, str | None]:
    """
    UPPDATERAD: Hitta senaste Parquet som följer vårt namnmönster i organisationsspecifik katalog:
    capex_wacc_0p<tag>_y2024_dmu.parquet  (ex: capex_wacc_0p0453_y2024_dmu.parquet)
    Returnerar (path, tag) eller (None, None) om inget hittas.
    """
    if org is None:
        org = get_user_org()
    
    # Skapa organisationsspecifik sökväg
    dir_path = Path(SCENARIO_DIR_BASE) / org
    
    if not dir_path.exists():
        return None, None

    cand = sorted(
        dir_path.glob("capex_wacc_0p*_y2024_dmu.parquet"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not cand:
        return None, None

    latest = cand[0]
    m = re.search(r"capex_wacc_(0p[0-9]+)_y2024_dmu\.parquet$", latest.name)
    tag = m.group(1) if m else None
    return latest, tag

def merge_capex_scenario(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    UPPDATERAD: Vänstermega in senaste CAPEX-scenariot (DMU-nivå) i DEA-basen från organisationsspecifik katalog.
    - Beräknar även TOTEX_wacc_<tag> = OPEXp + CAPEX_2024_wacc_… (om OPEXp finns).
    - Returnerar (df_merged, scen_info).
    - Om inget scenario hittas returneras input-df och scen_info['found']=False.
    Förväntar att df har kolumner: ['DMU','Företag','OPEXp','CAPEX'] (TOTEX byggs i show_dea).
    """
    scen_info: Dict = {"found": False}
    
    # Hämta aktuell organisation
    org = get_user_org()

    latest, tag = _latest_capex_scenario_path(org)
    if latest is None:
        # DEBUG: Visa vilken katalog som letas i
        search_dir = Path(SCENARIO_DIR_BASE) / org
        scen_info.update({
            "found": False, 
            "search_directory": str(search_dir),
            "organization": org,
            "reason": f"No scenario files found in {search_dir}"
        })
        return df, scen_info  # inget scenario ännu

    scen = pd.read_parquet(latest)
    # Hitta scenariokolumnen dynamiskt: CAPEX_2024_wacc_0p<tag>_tkr
    scen_cols = [c for c in scen.columns if c.startswith("CAPEX_2024_wacc_0p") and c.endswith("_tkr")]
    if not scen_cols:
        # Bakåtkomp eller fel export – låt bli att förstöra basen
        scen_info.update({"found": False, "source_file": str(latest), "reason": "no CAPEX_2024_wacc_* column"})
        return df, scen_info

    capex_col = scen_cols[0]
    if tag is None:
        # härled tag från kolumnnamnet
        m = re.search(r"CAPEX_2024_wacc_(0p[0-9]+)_tkr", capex_col)
        tag = m.group(1) if m else "unknown"

    # Säkerställ nycklar
    required = {"DMU", "Företag", capex_col}
    if not required.issubset(set(scen.columns)):
        scen_info.update({"found": False, "source_file": str(latest), "reason": f"missing columns in scenario: {required - set(scen.columns)}"})
        return df, scen_info

    # Vänsterjoin på DMU
    merged = df.merge(scen[["DMU", capex_col]], on="DMU", how="left", suffixes=("", "_scen"))

    # Bygg TOTEX_wacc_<tag> om OPEXp finns
    totex_col = f"TOTEX_wacc_{tag}"
    if "OPEXp" in merged.columns:
        merged[totex_col] = pd.to_numeric(merged["OPEXp"], errors="coerce") + pd.to_numeric(merged[capex_col], errors="coerce")

    # Täckningsgrad över DMU
    coverage = float(merged[capex_col].notna().mean())

    scen_info.update({
        "found": True,
        "tag": tag,
        "capex_col": capex_col,
        "totex_col": totex_col if totex_col in merged.columns else None,
        "source_file": str(latest),
        "organization": org,
        "search_directory": str(Path(SCENARIO_DIR_BASE) / org),
        "coverage": coverage,
    })
    return merged, scen_info