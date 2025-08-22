# data_loader.py
# Läs DEA-bas, upptäck CAPEX-scenariofiler från kapitalbasen och merge:a in dem.
# Enheter: tkr (som i Data_modeller.xlsx). Exportår: 2024 (H1+H2).

from __future__ import annotations

import os
import glob
import json
import pandas as pd
from typing import Tuple, Optional, Dict, Any


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


# ======= Scenario-upptäckt i dea_exports/ ====================================
def _find_latest_capex_scenario(export_dir: str = "dea_exports") -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[Dict[str, Any]]]:
    """
    Hitta senast modifierade scenariofil i export_dir med mönster:
      capex_wacc_0p*_y2024_tkr.(parquet|xlsx|csv)
    Returnerar (scen_df, tag, metadata_dict).
    """
    patterns = [
        os.path.join(export_dir, "capex_wacc_0p*_y2024_tkr.parquet"),
        os.path.join(export_dir, "capex_wacc_0p*_y2024_tkr.xlsx"),
        os.path.join(export_dir, "capex_wacc_0p*_y2024_tkr.csv"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    if not files:
        return None, None, None

    path = max(files, key=os.path.getmtime)
    # capex_wacc_0p0475_y2024_tkr.parquet -> tag = '0p0475'
    try:
        tag = os.path.basename(path).split("capex_wacc_")[1].split("_y2024")[0]
    except Exception:
        tag = None

    # Läs metadata om den finns
    meta_path = os.path.splitext(path)[0] + ".json"
    meta = None
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = None

    # Läs scenariotabell
    if path.endswith(".parquet"):
        scen = pd.read_parquet(path)
    elif path.endswith(".xlsx"):
        scen = pd.read_excel(path)
    else:
        scen = pd.read_csv(path)

    return scen, tag, meta


# ======= Merge av CAPEX-scenario till DEA-bas ================================
def merge_capex_scenario(
    df_base: pd.DataFrame,
    export_dir: str = "dea_exports",
    recon_path: str = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv",
) -> Tuple[pd.DataFrame, Optional[Dict[str, str]]]:
    """
    Slår samman CAPEX-scenario (om fil finns) till DEA-datat via DMU.
    - Letar upp senaste scenariofil i `export_dir`.
    - Förväntar en kolumn i scenariot som heter t.ex. 'CAPEX_2024_wacc_0p0475_tkr'.
    - Om 'DMU' saknas i scenariofilen, försöker läsa 'recon_path' och mappa id_network->DMU.

    Returnerar (df_merged, info_dict|None),
      där info_dict innehåller: {"tag": ..., "capex_col": ..., "totex_col": ...}
    """
    scen, tag, meta = _find_latest_capex_scenario(export_dir)
    if scen is None:
        return df_base, None

    scen = scen.copy()

    # Finn CAPEX-scenariokolumnen
    cand_cols = [c for c in scen.columns if c.startswith("CAPEX_2024_wacc_0p") and c.endswith("_tkr")]
    if not cand_cols:
        # Inget att merga om kolumn saknas
        return df_base, None
    capex_col = cand_cols[0]

    # Säkerställ DMU i scenariot
    if "DMU" not in scen.columns:
        # Försök mappa via reconciliation CSV (id_network -> DMU)
        try:
            rec = pd.read_csv(recon_path)
            # Normalisera kolumnnamn
            cols = {c.lower(): c for c in rec.columns}
            idcol = cols.get("id_network") or next((c for c in rec.columns if "network" in c.lower()), None)
            dmuc = cols.get("dmu", "DMU")
            if idcol:
                rec = rec.rename(columns={idcol: "id_network", dmuc: "DMU"})
                scen = scen.merge(rec[["id_network", "DMU"]].drop_duplicates(), on="id_network", how="left")
        except Exception:
            pass

    if "DMU" not in scen.columns:
        # Kan inte merga utan DMU
        return df_base, None

    # Rensa till nödvändiga kolumner och merge:a
    scen_small = scen[["DMU", capex_col]].drop_duplicates()
    merged = df_base.merge(scen_small, on="DMU", how="left")

    # Skapa TOTEX-scenariokolumn (samma enhet: tkr)
    totex_col = f"TOTEX_wacc_{tag}" if tag else "TOTEX_wacc_scenario"
    merged[totex_col] = merged["OPEXp"] + merged[capex_col]

    info = {"tag": tag or "", "capex_col": capex_col, "totex_col": totex_col}
    return merged, info
