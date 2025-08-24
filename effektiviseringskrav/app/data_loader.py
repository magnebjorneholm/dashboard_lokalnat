# data_loader.py
# Läs DEA-bas, upptäck CAPEX-scenariofiler från kapitalbasen och merge:a in dem.
# Enheter: tkr (som i Data_modeller.xlsx). Exportår: 2024 (H1+H2).

from __future__ import annotations
from pathlib import Path   
import re
import pandas as pd
from typing import Tuple, Optional, Dict


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

def _find_latest_capex_export(folder: str = "dea_exports") -> Optional[Path]:
    """Hitta senaste capex-scenariofil (parquet) i mappen.
    Mönster: capex_wacc_0pXXXX_y2024_tkr.parquet
    """
    p = Path(folder)
    if not p.exists():
        return None
    files = list(p.glob("capex_wacc_0p*_y2024_tkr.parquet"))
    if not files:
        return None
    return max(files, key=lambda fp: fp.stat().st_mtime)

def merge_capex_scenario(
    df_base: pd.DataFrame,
    export_dir: str = "dea_exports",
    recon_path: str = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv",
) -> Tuple[pd.DataFrame, Optional[Dict]]:
    """
    Slår samman CAPEX-scenario (2024, tkr) till DEA-datat via **id_network → DMU**-mappning.
    - Letar upp senaste scenariofil i `export_dir` (capex_wacc_0p*_y2024_tkr.parquet)
    - Om scenariot saknar DMU, mappa via `recon_path` (id_network → DMU)
    - **Aggregera per DMU** (summa över nät) innan merge
    - Merge: one-to-one på DMU
    - Härled `TOTEX_wacc_<tag>` = `OPEXp` + aggregerad `CAPEX_2024_wacc_<tag>_tkr`
    """
    base = df_base.copy()

    # Grundkrav
    for col in ("DMU", "OPEXp"):
        if col not in base.columns:
            raise KeyError(f"merge_capex_scenario: Saknar obligatorisk kolumn '{col}' i bas-DF.")
    if not base["DMU"].is_unique:
        raise ValueError("merge_capex_scenario: Bas-DF har inte unika DMU – kontrollera indatan.")

    latest = _find_latest_capex_export(export_dir)
    if latest is None:
        return base, None

    # Tagg ur filnamn
    m = re.search(r"capex_wacc_(0p[0-9]+)_y2024_tkr\.parquet$", latest.name)
    tag = m.group(1) if m else None

    scen = pd.read_parquet(latest)

    # Hitta scenariokolumn (CAPEX_2024_wacc_<tag>_tkr)
    capex_cols = [c for c in scen.columns if c.startswith("CAPEX_2024_wacc_") and c.endswith("_tkr")]
    if not capex_cols:
        print(f"[merge_capex_scenario] Ingen scenariokolumn hittades i {latest}")
        return base, None
    # Försök välj den som matchar taggen
    if tag:
        capex_col = next((c for c in capex_cols if c == f"CAPEX_2024_wacc_{tag}_tkr"), None)
    else:
        capex_col = None
    if capex_col is None:
        capex_col = sorted(capex_cols)[-1]
        m2 = re.match(r"CAPEX_2024_wacc_(0p[0-9]+)_tkr$", capex_col)
        tag = m2.group(1) if m2 else (tag or "unknown")

    # Säkerställ DMU i scenariot – mappa via recon vid behov
    scen = scen.copy()
    if "DMU" not in scen.columns:
        rec = pd.read_csv(recon_path)
        # Normalisera kolumnnamn
        lower = {c.lower(): c for c in rec.columns}
        idcol = lower.get("id_network") or next((c for c in rec.columns if "id_net" in c.lower() or "network" in c.lower()), None)
        dmucol = lower.get("dmu") or next((c for c in rec.columns if c.lower().startswith("dmu")), None)
        if not idcol or not dmucol:
            raise KeyError("Reconciliation-CSV saknar 'id_network' eller 'DMU'.")
        rec = rec.rename(columns={idcol: "id_network", dmucol: "DMU"})
        rec = rec[["id_network", "DMU"]].dropna().drop_duplicates()
        # join per nät
        if "id_network" not in scen.columns:
            raise KeyError("Scenariofilen saknar 'id_network' – kan inte mappa till DMU.")
        scen = scen.merge(rec, on="id_network", how="left")

    # --- Aggregera till DMU ---
    agg_dict = {capex_col: "sum"}
    if "CAPEX_2024_tkr" in scen.columns:
        agg_dict["CAPEX_2024_tkr"] = "sum"

    scen_agg = (
        scen.dropna(subset=["DMU"])  # kasta rader utan DMU
            .groupby("DMU", as_index=False)
            .agg(agg_dict)
    )

    # --- Merge tillbaka one-to-one ---
    rows_before = len(base)
    try:
        merged = base.merge(scen_agg, on="DMU", how="left", validate="one_to_one")
    except Exception:
        merged = base.merge(scen_agg, on="DMU", how="left")

    if len(merged) != rows_before:
        print(f"[merge_capex_scenario] VARNING: Radantal ändrades {rows_before}→{len(merged)} – detta ska inte ske efter DMU-agg.")

    # --- Härled TOTEX-scenario ---
    totex_col = f"TOTEX_wacc_{tag}"
    merged[totex_col] = pd.to_numeric(merged.get("OPEXp"), errors="coerce") + pd.to_numeric(merged.get(capex_col), errors="coerce")

    # Täckningsinfo
    coverage = float(merged[capex_col].notna().mean()) if capex_col in merged.columns else 0.0

    scen_info = {
        "capex_col": capex_col,
        "totex_col": totex_col,
        "tag": tag or "unknown",
        "source_file": str(latest),
        "coverage": coverage,
    }

    return merged, scen_info
