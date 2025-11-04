"""
core/data_loader_dea.py

DEA-specifik datainläsning och scenariointegrering.

Laddar DEA-basdata från Excel och integrerar CAPEX-scenarier från kapitalbas.
Används av:
- foretag/view/effektivitet.py
- Moran/moran_run.py (geografisk analys)
- Eventuella regulator-vyer
"""

from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
from typing import Tuple, Dict
from core.session_utils import get_user_org


# Bas-katalog för CAPEX-scenarier (organisationsspecifik)
SCENARIO_DIR_BASE = "scenario/kapitalbas/exports_to_dea"


def load_data(filepath: str) -> pd.DataFrame:
    """
    Läser DEA-bas från Excel (blad 'Körning') och skapar TOTEX = OPEXp + CAPEX.

    Args:
        filepath: Sökväg till Excel-fil (vanligtvis Data_modeller.xlsx)

    Returns:
        DataFrame med kolumner:
        ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh', 'TOTEX']

    Enhet: tkr (tusen kronor)
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

    # Beräkna TOTEX
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]
    df.reset_index(drop=True, inplace=True)

    return df


def _latest_capex_scenario_path(org: str = None) -> Tuple[Path | None, str | None]:
    """
    Hittar senaste CAPEX-scenario i organisationsspecifik katalog.

    Letar efter filer som följer mönstret:
    capex_wacc_0p<tag>_y2024_dmu.parquet
    Exempel: capex_wacc_0p0453_y2024_dmu.parquet

    Args:
        org: Organisationsnamn (om None, hämtas från session_utils)

    Returns:
        (path, tag) eller (None, None) om inget hittas
        tag är t.ex. "0p0453" från filnamnet
    """
    if org is None:
        org = get_user_org()

    # Skapa organisationsspecifik sökväg
    dir_path = Path(SCENARIO_DIR_BASE) / org

    if not dir_path.exists():
        return None, None

    # Hitta alla CAPEX-filer och sortera efter modifierad tid
    cand = sorted(
        dir_path.glob("capex_wacc_0p*_y2024_dmu.parquet"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not cand:
        return None, None

    # Returnera senaste fil
    latest = cand[0]

    # Extrahera tag från filnamnet (t.ex. "0p0453")
    m = re.search(r"capex_wacc_(0p[0-9]+)_y2024_dmu\.parquet$", latest.name)
    tag = m.group(1) if m else None

    return latest, tag


def merge_capex_scenario(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Vänstermergar in senaste CAPEX-scenario (DMU-nivå) i DEA-basen från organisationsspecifik katalog.

    Processar:
    1. Hittar senaste CAPEX-scenario för organisationen
    2. Mergar CAPEX_2024_wacc_<tag>_tkr på DMU
    3. Beräknar TOTEX_wacc_<tag> = OPEXp + CAPEX_2024_wacc_<tag>_tkr

    Args:
        df: DEA-basdata med kolumner ['DMU', 'Företag', 'OPEXp', 'CAPEX']

    Returns:
        (df_merged, scen_info)
        - df_merged: DataFrame med nya kolumner CAPEX_2024_wacc_<tag>_tkr och TOTEX_wacc_<tag>
        - scen_info: Dict med metadata om scenariot:
          - found: bool - om scenario hittades
          - tag: str - WACC-tag (t.ex. "0p0453")
          - capex_col: str - namn på CAPEX-kolumn
          - totex_col: str - namn på TOTEX-kolumn
          - source_file: str - sökväg till scenario-fil
          - organization: str - användarens organisation
          - coverage: float - andel DMU som har scenario-data
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

    # Läs scenario-fil
    scen = pd.read_parquet(latest)

    # Hitta scenariokolumnen dynamiskt: CAPEX_2024_wacc_0p<tag>_tkr
    scen_cols = [c for c in scen.columns if c.startswith("CAPEX_2024_wacc_0p") and c.endswith("_tkr")]
    if not scen_cols:
        # Bakåtkompatibilitet eller fel export – låt bli att förstöra basen
        scen_info.update({"found": False, "source_file": str(latest), "reason": "no CAPEX_2024_wacc_* column"})
        return df, scen_info

    capex_col = scen_cols[0]
    if tag is None:
        # Härled tag från kolumnnamnet
        m = re.search(r"CAPEX_2024_wacc_(0p[0-9]+)_tkr", capex_col)
        tag = m.group(1) if m else "unknown"

    # Säkerställ nycklar
    required = {"DMU", "Företag", capex_col}
    if not required.issubset(set(scen.columns)):
        scen_info.update({
            "found": False,
            "source_file": str(latest),
            "reason": f"missing columns in scenario: {required - set(scen.columns)}"
        })
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
