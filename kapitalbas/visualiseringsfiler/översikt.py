"""
oversikt.py – Årsvy (H1+H2), MSEK-visning, WACC-scenario och Export (2024, tkr)

VIKTIGA ÄNDRINGAR:
- Aggregerar från id_network till DMU-nivå redan vid inläsning
- Visar och arbetar på DMU-nivå i hela applikationen
- Fixar dubblettproblemet i exporten genom korrekt DMU-aggregering
- Två separata export-funktioner: DEA och IR-dekomposition

- KPI visas på ÅR (H1+H2), halvårslogik används under huven.
- Visning i MSEK; DATA & EXPORT i tkr (DEA-konsekvent).
- capcost_network används inte i KPI; årsvärde = sum(capcost_sum).
- Scenario skalar endast returdelar; avskrivningar lämnas oförändrade.
- Exportsektion i Tab 3 (endast 2024): per-DMU-tabell, exkludera DMU som saknas i DEA.
- Skrivs till 'scenario/kapitalbas/exports_to_dea/' och 'scenario/ir/kapitalkostnader/'.
"""

from __future__ import annotations

import os, math, json
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import streamlit as st

# ========= Konstanter & format =========
R_OLD: float = 0.0453  # Ei 2024–2027, real, pre-tax
NBSP = "\u202f"
MINUS = "\u2212"

# Sökvägar - uppdaterade för ny mappstruktur
SCENARIO_DIR = "scenario"
DEA_EXPORT_DIR = os.path.join(SCENARIO_DIR, "kapitalbas", "exports_to_dea")
IR_EXPORT_DIR = os.path.join(SCENARIO_DIR, "ir", "kapitalkostnader")
DEA_BASE_XLSX = "effektiviseringskrav/data/Data_modeller.xlsx"
RECON_CSV = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"

# Halvårskoder (facit)
TIME_LABEL_TO_CODE = {
    "2024h1": 229, "2024h2": 230,
    "2025h1": 231, "2025h2": 232,
    "2026h1": 233, "2026h2": 234,
    "2027h1": 235, "2027h2": 236,
}
CODE_TO_TIME_LABEL = {v: k for k, v in TIME_LABEL_TO_CODE.items()}
YEAR_TO_CODES = {2024: [229,230], 2025: [231,232], 2026: [233,234], 2027: [235,236]}

# KPI (tkr → MSEK visuellt)
KPI_DISPLAY = ["capcost_sum", "dep_ord", "dep_tail", "nuav_ord", "nuav_tail", "return_ord", "return_tail"]
KPI_LABEL = {
    "capcost_sum": "Kapitalkostnad – summa (capcost_sum) (MSEK)",
    "dep_ord":     "Ordinarie avskrivning (dep_ord) (MSEK)",
    "dep_tail":    "Svansavskrivning (dep_tail) (MSEK)",
    "nuav_ord":    "Nuanskaffningsvärde – ordinarie (nuav_ord) (MSEK)",
    "nuav_tail":   "Nuanskaffningsvärde – svans (nuav_tail) (MSEK)",
    "return_ord":  "Avkastning – ordinarie (return_ord) (MSEK)",
    "return_tail": "Avkastning – svans (return_tail) (MSEK)",
}

def fmt_msek_from_tkr(x, decimals: int = 3) -> str:
    v = pd.to_numeric(x, errors="coerce")
    v = 0.0 if pd.isna(v) else float(v)
    s = f"{v/1000.0:,.{decimals}f}".replace(",", NBSP)
    return s

def fmt_msek_delta_from_tkr(x, decimals: int = 3) -> str:
    v = pd.to_numeric(x, errors="coerce")
    v = 0.0 if pd.isna(v) else float(v)
    sign = "+" if v >= 0 else MINUS
    s = f"{abs(v)/1000.0:,.{decimals}f}".replace(",", NBSP)
    return f"{sign}{s}"

def fmt_msek_delta_from_tkr_tol(x, decimals: int = 3, tol_tkr: int = 1) -> str:
    try:
        v = float(x)
    except Exception:
        v = 0.0
    return "≈0.000" if abs(v) <= tol_tkr else fmt_msek_delta_from_tkr(v, decimals)

# ========= Scenario: skala returdelar =========
def apply_interest_scenario(df: pd.DataFrame, r_new: float) -> pd.DataFrame:
    """Skalar enbart return_* med r_new/r_old per halvår (avrundning i tkr); dep_* oförändrat; skapar capcost_sum_new."""
    if not (isinstance(r_new, (float,int)) and math.isfinite(r_new)):
        raise ValueError("r_new måste vara ändligt.")
    scale = float(r_new) / R_OLD
    out = df.copy()
    out["return_ord_new"]  = (out["return_ord"]  * scale).round().astype("Int64")
    out["return_tail_new"] = (out["return_tail"] * scale).round().astype("Int64")
    out["capcost_sum_new"] = (
        out["dep_ord"].astype("float64")
        + out["dep_tail"].astype("float64")
        + out["return_ord_new"].astype("float64")
        + out["return_tail_new"].astype("float64")
    )
    return out

# ========= WACC-beräkning (Ei) =========
@dataclass
class EiWaccInputs:
    rf_nominal: float = 0.0287
    mrp_nominal: float = 0.0668
    credit_spread: float = 0.0114
    debt_share: float = 0.36
    tax_rate: float = 0.206
    inflation: float = 0.0202
    beta_asset: Optional[float] = 0.37
    beta_equity: Optional[float] = None

def _hamada(beta_a: float, S: float, T: float) -> float:
    d_over_e = S/max(1e-12,(1-S))
    return beta_a * (1+(1-T)*d_over_e)

def ei_wacc_real_pre_tax(inp: EiWaccInputs) -> tuple[float,float,float,float]:
    beta_e = inp.beta_equity if inp.beta_equity is not None else _hamada(inp.beta_asset, inp.debt_share, inp.tax_rate)
    Re_nom = inp.rf_nominal + beta_e * inp.mrp_nominal
    Rd_nom = inp.rf_nominal + inp.credit_spread
    wacc_nom_after = (1-inp.debt_share)*Re_nom + inp.debt_share*Rd_nom*(1-inp.tax_rate)
    wacc_nom_pre   = wacc_nom_after/(1-inp.tax_rate)
    wacc_real_pre  = (1+wacc_nom_pre)/(1+inp.inflation) - 1
    return Re_nom, Rd_nom, wacc_nom_pre, wacc_real_pre

# ========= DMU-aggregering och hjälpfunktioner =========
def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _format_wacc_tag(r_new: float) -> str:
    return f"{float(r_new):.4f}".replace(".", "p")  # 0.0475 → "0p0475"

def _read_dmu_from_dea_base(path_xlsx: str) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_excel(path_xlsx, sheet_name="Körning")
        return df[["DMU","Företag"]].drop_duplicates()
    except Exception:
        return None

def _read_reconciliation(path_csv: str) -> Optional[pd.DataFrame]:
    try:
        rec = pd.read_csv(path_csv)
        # Normalisera kolumnnamn - justera för faktisk filstruktur
        cols = {c.lower(): c for c in rec.columns}
        
        # Hitta rätt kolumner baserat på faktisk filstruktur
        idcol = cols.get("id_network", "id_network")
        dmucol = cols.get("dmu", "DMU")
        
        # Använd id_firm som företagsnamn (detta är vad som finns i filen)
        foretag = cols.get("id_firm", "id_firm")
        
        # Skapa standardiserade kolumnnamn
        rec = rec.rename(columns={
            idcol: "id_network", 
            dmucol: "DMU", 
            foretag: "Företag"  # Byt namn från id_firm till Företag
        })
        
        # Kontrollera att vi har nödvändiga kolumner
        required_cols = ["id_network", "DMU", "Företag"]
        missing_cols = [col for col in required_cols if col not in rec.columns]
        if missing_cols:
            st.error(f"Saknade kolumner i reconciliation-fil efter rename: {missing_cols}")
            return None
        
        return rec[required_cols].drop_duplicates()
        
    except Exception as e:
        st.error(f"Kunde inte läsa reconciliation-fil: {e}")
        return None

def _aggregate_to_dmu(df_facit: pd.DataFrame) -> pd.DataFrame:
    """KRITISK FIX: Aggregerar från id_network till DMU-nivå redan vid start."""
    rec = _read_reconciliation(RECON_CSV)
    if rec is None:
        st.error("Kan inte ladda reconciliation-fil - stannar på id_network-nivå")
        return df_facit
    
    # Spara debug-info före merge
    original_networks = set(df_facit['id_network'].unique())
    reconciliation_networks = set(rec['id_network'].unique())
    
    # Merge med reconciliation för att få DMU-mappning
    df_with_dmu = df_facit.merge(rec, on="id_network", how="left")
    
    # Analysera mappningsresultatet
    missing_dmu = df_with_dmu['DMU'].isna()
    mapped_networks = df_with_dmu[~missing_dmu]['id_network'].unique()
    unmapped_networks = df_with_dmu[missing_dmu]['id_network'].unique()
    
    # Spara debug-info i session state för debug-tab
    st.session_state['dmu_debug'] = {
        'original_count': len(original_networks),
        'reconciliation_count': len(reconciliation_networks),
        'mapped_count': len(mapped_networks),
        'unmapped_count': len(unmapped_networks),
        'unmapped_networks': unmapped_networks,
        'networks_in_both': original_networks & reconciliation_networks,
        'networks_only_in_facit': original_networks - reconciliation_networks,
        'networks_only_in_recon': reconciliation_networks - original_networks,
        'mapping_stats': df_with_dmu.groupby('DMU')['id_network'].nunique().describe() if not missing_dmu.all() else None
    }
    
    if missing_dmu.sum() > 0:
        missing_count = len(unmapped_networks)  # Antal unika nätverk, inte rader
        st.warning(f"{missing_count} id_network saknar DMU-mappning och exkluderas")
        df_with_dmu = df_with_dmu.dropna(subset=['DMU'])
    
    if df_with_dmu.empty:
        st.error("Ingen data kvar efter DMU-mappning")
        return pd.DataFrame()
    
    # Aggregera till DMU-nivå
    group_cols = ["DMU", "Företag", "time"]
    agg_cols = ["capcost_sum", "dep_ord", "dep_tail", "nuav_ord", "nuav_tail", "return_ord", "return_tail"]
    
    df_aggregated = df_with_dmu.groupby(group_cols, dropna=False).agg(
        {col: 'sum' for col in agg_cols}
    ).reset_index()
    
    # Logga resultat
    final_dmus = df_aggregated['DMU'].nunique()
    st.info(f"Aggregerat från {len(mapped_networks)} nätverk till {final_dmus} DMU:er")
    
    return df_aggregated

def _check_year_completeness(df_year: pd.DataFrame) -> pd.DataFrame:
    """Returnerar DF med DMU som saknar H1 eller H2 för året."""
    cnt = df_year.groupby("DMU")["time"].nunique().reset_index(name="n_halvår")
    return cnt[cnt["n_halvår"]<2]

def _build_dea_export_table(df_year: pd.DataFrame, r_new: float) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Bygger DEA-exporttabell (tkr) per DMU för 2024 och exklusionslista."""
    # Scenario-beräkning per halvår
    scen = apply_interest_scenario(df_year, r_new)

    # Årssumma per DMU (KRITISK FIX: inte per id_network)
    base = df_year.groupby(["DMU", "Företag"], as_index=False).agg(CAPEX_2024_tkr=("capcost_sum","sum"))
    new = scen.groupby(["DMU", "Företag"], as_index=False).agg(CAPEX_2024_wacc_tkr=("capcost_sum_new","sum"))
    out = base.merge(new, on=["DMU", "Företag"], how="outer")
    
    out["delta_tkr"] = out["CAPEX_2024_wacc_tkr"] - out["CAPEX_2024_tkr"]
    out["r_old"] = R_OLD
    out["r_new"] = round(float(r_new), 4)
    out["price_year"] = 2022

    # Exkludera DMU som saknas i DEA-bas
    dmu = _read_dmu_from_dea_base(DEA_BASE_XLSX)
    excluded = pd.DataFrame()
    if dmu is not None:
        out = out.merge(dmu.assign(in_dea=1), on=["DMU","Företag"], how="left")
        excluded = out[out["in_dea"].isna()][["DMU","Företag"]].copy()
        out = out[out["in_dea"].eq(1)].drop(columns=["in_dea"])

    # Döp scenariokolumnen med wacc-tagg
    tag = _format_wacc_tag(out["r_new"].iloc[0] if len(out) else r_new)
    out = out.rename(columns={"CAPEX_2024_wacc_tkr": f"CAPEX_2024_wacc_{tag}_tkr"})
    return out, excluded, tag

def _build_ir_export_table(df_year: pd.DataFrame, r_new: float) -> tuple[pd.DataFrame, str]:
    """Bygger IR-exporttabell med detaljerad kapitalkostnad per DMU."""
    scen = apply_interest_scenario(df_year, r_new)
    
    # Aggregera komponenter per DMU
    ir_data = scen.groupby(["DMU", "Företag"], as_index=False).agg({
        'dep_ord': 'sum', 
        'dep_tail': 'sum',
        'return_ord': 'sum',
        'return_tail': 'sum', 
        'return_ord_new': 'sum', 
        'return_tail_new': 'sum',
        'capcost_sum': 'sum',
        'capcost_sum_new': 'sum'
    })
    
    # Beräkna IR-format (separerade komponenter)
    ir_data['Kapitalkostnad_Baseline'] = ir_data['capcost_sum']
    ir_data['Kapitalkostnad_Ny'] = ir_data['capcost_sum_new']
    ir_data['Avskrivningar_Ny'] = ir_data['dep_ord'] + ir_data['dep_tail']  # Oförändrad
    ir_data['Avkastning_Baseline'] = ir_data['return_ord'] + ir_data['return_tail']
    ir_data['Avkastning_Ny'] = ir_data['return_ord_new'] + ir_data['return_tail_new']
    
    # Framtidssäkra: ordinarie vs tail
    ir_data['dep_ord_Ny'] = ir_data['dep_ord']  # Oförändrad
    ir_data['dep_tail_Ny'] = ir_data['dep_tail']  # Oförändrad
    ir_data['return_ord_Ny'] = ir_data['return_ord_new']
    ir_data['return_tail_Ny'] = ir_data['return_tail_new']
    
    # Metadata
    ir_data['r_old'] = R_OLD
    ir_data['r_new'] = round(float(r_new), 4)
    ir_data['price_year'] = 2022
    tag = _format_wacc_tag(r_new)
    ir_data['scenario_tag'] = tag
    
    # Välj kolumner för export
    export_cols = ['DMU', 'Företag', 'Kapitalkostnad_Baseline', 'Kapitalkostnad_Ny', 
                   'Avskrivningar_Ny', 'Avkastning_Baseline', 'Avkastning_Ny',
                   'dep_ord_Ny', 'dep_tail_Ny', 'return_ord_Ny', 'return_tail_Ny',
                   'r_old', 'r_new', 'price_year', 'scenario_tag']
    
    return ir_data[export_cols], tag

def _write_dea_export(df_export: pd.DataFrame, tag: str) -> tuple[str,str]:
    """Skriv DEA-export (Parquet + metadata JSON). Return: (data_path, meta_path)."""
    _ensure_dir(DEA_EXPORT_DIR)
    data_path = os.path.join(DEA_EXPORT_DIR, f"capex_wacc_{tag}_y2024_dmu.parquet")
    meta_path = data_path.replace(".parquet",".json")
    df_export.to_parquet(data_path, index=False)
    meta = {
        "description": "CAPEX export för DEA-pipen, DMU-nivå",
        "price_year": 2022, 
        "unit": "tkr",
        "level": "DMU",
        "wacc_old": R_OLD, 
        "wacc_new": float(tag.replace("p",".")),
        "constructed_as": "H1+H2 after half-year rounding, aggregated to DMU"
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return data_path, meta_path

def _write_ir_export(df_export: pd.DataFrame, tag: str) -> tuple[str,str]:
    """Skriv IR-export (Parquet + metadata JSON). Return: (data_path, meta_path)."""
    _ensure_dir(IR_EXPORT_DIR)
    data_path = os.path.join(IR_EXPORT_DIR, f"ir_kapkost_wacc_{tag}_y2024_dmu.parquet")
    meta_path = data_path.replace(".parquet",".json")
    df_export.to_parquet(data_path, index=False)
    meta = {
        "description": "Detaljerad kapitalkostnad för IR-dekomposition, DMU-nivå",
        "price_year": 2022,
        "unit": "tkr", 
        "level": "DMU",
        "wacc_old": R_OLD,
        "wacc_new": float(tag.replace("p",".")),
        "constructed_as": "H1+H2 after half-year rounding, aggregated to DMU",
        "components": {
            "Avskrivningar_Ny": "dep_ord + dep_tail (unchanged by WACC)",
            "Avkastning_Ny": "return_ord_new + return_tail_new (scaled by WACC)"
        }
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return data_path, meta_path

# ========= Metodikruta =========
def _render_methodology_info():
    with st.expander("Metodik, information och definitioner (Ei)", expanded=False):
        st.markdown(
            """
            **Vad är kalkylräntan (WACC)?** Vägt genomsnitt av kapitalkostnaden för eget kapital och skuld.
            I regleringen används **real, före skatt** som slutmått.
            Beräkningen startar **nominellt och efter skatt**, räknas om till **före skatt** och därefter till **real** via Fisher.
            """
        )

        st.markdown("**Beräkningskedja (överblick)**")
        st.markdown("1. **CAPM (nominell, efter skatt)** – kostnad för eget kapital")
        st.latex(r"R_E = R_f + \beta_E \cdot MRP")

        st.markdown("2. **Skuldränta (nominell, före skatt)** – kostnad för skuld")
        st.latex(r"R_D = R_f + CR")

        st.markdown("3. **WACC (nominell)** – blanda E och D, sedan omräkning till före skatt")
        st.latex(r"\text{WACC}_{\text{nom,after}} = (1-S)\,R_E + S\,R_D\,(1-T)")
        st.latex(r"\text{WACC}_{\text{nom,pre}} = \frac{\text{WACC}_{\text{nom,after}}}{1-T}")

        st.markdown("4. **Fisher-omräkning (nominell → real)**")
        st.latex(r"r_{\text{real}} = \frac{1 + r_{\text{nom}}}{1 + \pi} - 1")
        st.markdown("Här används \\( \\pi \\) = KPIF (flerårsantagande).")

        st.markdown("**Hamada-hävstång (från tillgångsbeta till aktiebeta):**")
        st.latex(r"\beta_E = \beta_A \left(1 + (1-T)\frac{D}{E}\right)")
        st.latex(r"\frac{D}{E} = \frac{S}{1-S}, \quad S = \frac{D}{D+E}")

        st.markdown(
            """
            **Hur siffrorna i denna vy beräknas och visas**  
            • **Årssiffror = H1 + H2.** Beräkning och avrundning sker per halvår; därefter summeras H1+H2 till år.  
            • **Visning i MSEK.** Underliggande data och export sker i **tkr** (prisår **nominell 2022**).  
            • **DMU-nivå.** Data aggregeras från id_network till DMU redan vid inläsning.
            • **Scenario (Tab 3):** endast **returdelarna** skalas med \\( r_{\\text{new}}/r_{\\text{old}} \\); **avskrivningar (dep_*)** lämnas oförändrade.  
            • **Rundning:** räntor visas med fyra decimaler; små differenser (±1 tkr) kan uppstå i kontrollsummor.
            """
        )

        st.markdown(
            """
            **Vanliga misstag att undvika**  
            – Ange **nominella, efter skatt**-värden i CAPM (inte reala).  
            – Blanda inte ihop **S** med **D/E** (använd \\( D/E = S/(1-S) \\)).  
            – Lägg **kreditriskpremien (CR)** endast på skuldräntan \\( R_D \\).
            """
        )

# ========= Huvudvy =========
def show_capcost(df_facit: pd.DataFrame) -> None:
    req = {"id_network","time","capcost_sum","dep_ord","dep_tail","nuav_ord","nuav_tail","return_ord","return_tail"}
    miss = req - set(df_facit.columns)
    if miss:
        st.error(f"Saknade kolumner i df_facit: {sorted(miss)}"); return

    # KRITISK FIX: Aggregera till DMU-nivå från start
    df = _aggregate_to_dmu(df_facit)
    
    # Fallback om DMU-aggregeringen misslyckades
    if df.empty or 'DMU' not in df.columns:
        st.warning("DMU-aggregering misslyckades - arbetar på id_network-nivå istället")
        df = df_facit.copy()
        df["id_network"] = df["id_network"].astype("int64")
        df["time"] = df["time"].astype("int64")
        
        # Använd original-UI för id_network
        st.header("Översikt – Kapitalbas (id_network-nivå)")
        st.caption("VARNING: Data visas på id_network-nivå då DMU-mappning misslyckades. Export kommer inte fungera korrekt.")
        
        with st.sidebar:
            st.subheader("Filter")
            year_choice = st.selectbox("År", options=[2024,2025,2026,2027], index=0)
            nets = sorted(df["id_network"].unique().tolist())
            network_choice = st.selectbox("Välj nät (id_network)", options=["Alla"]+nets, index=0)

        def _filter_df(base: pd.DataFrame) -> pd.DataFrame:
            out = base[base["time"].isin(YEAR_TO_CODES[int(year_choice)])]
            return out if network_choice=="Alla" else out[out["id_network"]==network_choice]
        
        # Resten av Tab 1 och 2 fungerar som vanligt, men export kommer inte fungera
        # Lägg till varning i Tab 3
        TAB1, TAB2, TAB3 = st.tabs(["Tab 1 – Facit", "Tab 2 – Beräkna kalkylränta", "Tab 3 – Export (inaktiverad)"])
        
        with TAB3:
            st.error("Export är inaktiverad eftersom DMU-mappning misslyckades. Kontrollera reconciliation-filen.")
        
        return

    st.header("Översikt – Kapitalbas (DMU-nivå)")
    st.caption("Enhet: tkr (data) / MSEK (visas). Prisår: nominell 2022. Årssiffror: H1+H2. Aggregerat till DMU-nivå.")

    # ---- Filter (år & DMU) ----
    with st.sidebar:
        st.subheader("Filter")
        year_choice = st.selectbox("År", options=[2024,2025,2026,2027], index=0,
                                   help="Årssiffror = H1+H2 (halvårsberäkning sker under huven).")
        
        # Säkerhetscheck för DMU-kolumn
        if 'DMU' in df.columns:
            dmus = sorted([int(d) for d in df["DMU"].dropna().unique()])
            dmu_options = ["Alla"] + [str(d) for d in dmus]
            dmu_choice = st.selectbox("Välj DMU", options=dmu_options, index=0,
                                     help="Data aggregerad från id_network till DMU-nivå.")
        else:
            st.error("DMU-kolumn saknas - något gick fel med aggregeringen")
            return

    def _filter_df(base: pd.DataFrame) -> pd.DataFrame:
        out = base[base["time"].isin(YEAR_TO_CODES[int(year_choice)])]
        if dmu_choice == "Alla":
            return out
        return out[out["DMU"] == float(dmu_choice)]

    TAB1, TAB2, TAB3, TAB_DEBUG = st.tabs(["Tab 1 – Facit", "Tab 2 – Beräkna kalkylränta", "Tab 3 – Scenario + Export", "Debug – DMU-mappning"])

    # ---- Tab 1: Facit (år, MSEK) ----
    with TAB1:
        st.subheader("KPI:er (facit)")
        filt_df = _filter_df(df)
        if filt_df.empty:
            st.warning("Ingen rad matchar valt DMU/år.")
        else:
            kpi = filt_df[KPI_DISPLAY].sum(numeric_only=True)
            st.markdown(f"**KPI för {year_choice} · DMU: {dmu_choice}**")
            for cols in [KPI_DISPLAY[i:i+2] for i in range(0,len(KPI_DISPLAY),2)]:
                c = st.columns(2)
                for j, col in enumerate(cols):
                    c[j].metric(KPI_LABEL[col], fmt_msek_from_tkr(kpi[col]))
            st.caption("Korten visar MSEK (avrundat). Underliggande tabell visar tkr.")
            with st.expander("Visa underlag (tkr)"):
                tmp = filt_df.copy(); tmp["time_label"] = tmp["time"].map(CODE_TO_TIME_LABEL)
                st.dataframe(tmp, use_container_width=True, hide_index=True)

    # ---- Tab 2: WACC ----
    with TAB2:
        st.subheader("Beräkna kalkylränta (Ei)")
        defaults = {"rf_nom":0.0287,"mrp":0.0668,"infl":0.0202,"credit":0.0114,"debt_share":0.36,"tax_rate":0.206,"beta_mode":"β_A","beta_a":0.37,"beta_e":0.54}
        for k,v in defaults.items(): st.session_state.setdefault(k,v)
        st.session_state.setdefault("r_new", R_OLD)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input("Riskfri ränta (nominell) Rf", key="rf_nom", step=0.0001, format="%.4f",
                help="KI:s 9-årsprognos för 10-årig svensk statsobligation (nominell). Ingår i både R_E och R_D.")
            st.number_input("Marknadsriskpremie (nominell) MRP", key="mrp", step=0.0001, format="%.4f",
                help="Långsiktig aktiemarknadspremie (nominell), baserad på PwC:s riskpremiestudier.")
            st.number_input("Inflation π (KPIF)", key="infl", step=0.0001, format="%.4f",
                help="KPIF enligt KI:s 9-årsprognos. Fisher-omräkning till real nivå.")

        with c2:
            st.number_input("Kreditriskpremie (nominell)", key="credit", step=0.0001, format="%.4f",
                help="Spread för lånat kapital (typiskt europeiska utilities BBB vs 10-årig Bund).")
            st.number_input("Skuldsättningsgrad S = D/(D+E)", key="debt_share", 
                min_value=0.0, max_value=0.95, step=0.01, format="%.2f",
                help="Vikt för skuld i WACC. Relation: D/E = S/(1−S).")
            st.number_input("Bolagsskatt T", key="tax_rate", 
                min_value=0.0, max_value=0.99, step=0.001, format="%.3f",
                help="Omräkning från efter skatt till före skatt.")

        with c3:
            st.radio("Beta-inmatning", ["β_A", "β_E"], index=0, key="beta_mode",
                help="Välj att ange tillgångsbeta (β_A) eller aktiebeta (β_E) direkt.")
            if st.session_state["beta_mode"] == "β_A":
                st.number_input("β_A", key="beta_a", step=0.01, format="%.2f",
                    help="Tillgångsbeta (obelanad). Omvandlas till aktiebeta med Hamada.")
            else:
                st.number_input("β_E", key="beta_e", step=0.01, format="%.2f",
                    help="Aktiebeta (belanad). Används direkt i CAPM.")

        beta_a = st.session_state["beta_a"] if st.session_state["beta_mode"]=="β_A" else None
        beta_e = st.session_state["beta_e"] if st.session_state["beta_mode"]=="β_E" else None
        Re,Rd,Wn,Wr = ei_wacc_real_pre_tax(EiWaccInputs(
            rf_nominal=st.session_state["rf_nom"], mrp_nominal=st.session_state["mrp"],
            credit_spread=st.session_state["credit"], debt_share=st.session_state["debt_share"],
            tax_rate=st.session_state["tax_rate"], inflation=st.session_state["infl"],
            beta_asset=beta_a, beta_equity=beta_e
        ))

        k1,k2,k3,k4 = st.columns(4)
        k1.metric("Re (nominell, efter skatt)", f"{Re*100:.2f} %")
        k2.metric("Rd (nominell, före skatt)",  f"{Rd*100:.2f} %")
        k3.metric("WACC (nominell, före skatt)", f"{Wn*100:.2f} %")
        k4.metric("WACC (real, före skatt)",     f"{Wr*100:.2f} %")

        def _reset_ei_defaults():
            for k,v in defaults.items(): st.session_state[k]=v
            st.session_state["r_new"]=R_OLD

        cc1,cc2 = st.columns([1,1])
        with cc1:
            if st.button("Använd denna kalkylränta i Tab 3"):
                st.session_state["r_new"] = round(float(Wr), 4)
                st.success(f"Satt r_new = {st.session_state['r_new']:.4f}")
        with cc2:
            st.button("Återställ till Ei-standard", on_click=_reset_ei_defaults)

        _render_methodology_info()

    # ---- Tab 3: Scenario + Export ----
    with TAB3:
        st.subheader("Scenario: ny kalkylränta (Ei-logik i tkr)")

        r_new = round(float(st.number_input("WACC (real, pre-tax) för scenario",
                                            value=float(st.session_state.get("r_new", R_OLD)),
                                            step=0.0001, format="%.4f")), 4)

        base_year = _filter_df(df)
        if base_year.empty:
            st.warning("Ingen rad matchar valt DMU/år."); return

        scen_year = apply_interest_scenario(base_year, r_new)

        new_vals  = scen_year[["return_ord_new","return_tail_new","capcost_sum_new"]].sum(numeric_only=True)
        base_vals = base_year[["return_ord","return_tail","capcost_sum"]].sum(numeric_only=True)

        st.caption("Korten visar MSEK (avrundat). Skalning görs per halvår och summeras till år; avskrivningar lämnas oförändrade.")
        for keys in [["return_ord_new","return_tail_new"],["capcost_sum_new"]]:
            cols = st.columns(2)
            for i,k in enumerate(keys):
                if i>1: break
                val_tkr = float(new_vals[k]); base_k = k.replace("_new","")
                delta_tkr = val_tkr - float(base_vals[base_k])
                cols[i].metric(
                    {"return_ord_new":"Avkastning – ordinarie (return_ord) (MSEK)",
                     "return_tail_new":"Avkastning – svans (return_tail) (MSEK)",
                     "capcost_sum_new":"Kapitalkostnad – summa (capcost_sum) (MSEK)"}[k],
                    fmt_msek_from_tkr(val_tkr),
                    delta=fmt_msek_delta_from_tkr_tol(delta_tkr)
                )

        with st.expander("Underlag (scenario, tkr)"):
            t = scen_year.copy(); t["time_label"]=t["time"].map(CODE_TO_TIME_LABEL)
            st.dataframe(t, use_container_width=True, hide_index=True)
        with st.expander("Underlag (facit, tkr)"):
            t = base_year.copy(); t["time_label"]=t["time"].map(CODE_TO_TIME_LABEL)
            st.dataframe(t, use_container_width=True, hide_index=True)

        # ==== Export-sektion (endast 2024) ====
        st.markdown("---")
        st.subheader("Export (endast 2024)")
        st.caption("Exporterar CAPEX och detaljerad kapitalkostnad i **tkr** per DMU. Prisår = nominell 2022.")

        # Kontrollera att vi är på 2024
        if int(year_choice) != 2024:
            st.info("Export är låst till 2024. Välj 2024 i filtret för att aktivera export.")
            return

        df_2024 = df[df["time"].isin(YEAR_TO_CODES[2024])].copy()
        
        # Komplett H1+H2?
        incomplete = _check_year_completeness(df_2024)
        if not incomplete.empty:
            st.warning(f"{len(incomplete)} DMU saknar H1 eller H2 för 2024 och exporteras inte.")
            # Filtrera bort ofullständiga DMU
            complete_dmus = df_2024.groupby("DMU")["time"].nunique()
            complete_dmus = complete_dmus[complete_dmus == 2].index
            df_2024 = df_2024[df_2024["DMU"].isin(complete_dmus)]

        if df_2024.empty:
            st.error("Ingen DMU har komplett H1+H2 data för 2024")
            return

        # Bygg båda export-tabellerna
        try:
            df_dea_export, df_dea_excl, dea_tag = _build_dea_export_table(df_2024, r_new)
            df_ir_export, ir_tag = _build_ir_export_table(df_2024, r_new)
        except Exception as e:
            st.error(f"Fel vid byggning av export-tabeller: {e}")
            return

        # Visa förhandsvisning
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**DEA-export förhandsvisning (WACC_tag = {dea_tag})**")
            st.dataframe(df_dea_export, use_container_width=True, hide_index=True)
            
            if not df_dea_excl.empty:
                with st.expander(f"Exkluderas från DEA (saknas i DEA-bas): {len(df_dea_excl)} DMU"):
                    st.dataframe(df_dea_excl, use_container_width=True, hide_index=True)

        with col2:
            st.markdown(f"**IR-export förhandsvisning (WACC_tag = {ir_tag})**")
            st.dataframe(df_ir_export[['DMU', 'Företag', 'Kapitalkostnad_Ny', 'Avskrivningar_Ny', 'Avkastning_Ny']], 
                        use_container_width=True, hide_index=True)

        # Export-knappar
        st.markdown("---")
        col_dea, col_ir, col_both = st.columns(3)
        
        with col_dea:
            if st.button("📊 Exportera till DEA", help="Exporterar CAPEX-data för DEA-pipen"):
                try:
                    path_data, path_meta = _write_dea_export(df_dea_export, dea_tag)
                    st.success(f"DEA-export klar!")
                    st.caption(f"Data: {path_data}")
                    st.caption(f"Metadata: {path_meta}")
                except Exception as e:
                    st.error(f"DEA-export misslyckades: {e}")

        with col_ir:
            if st.button("🔍 Exportera till IR", help="Exporterar detaljerad kapitalkostnad för IR-dekomposition"):
                try:
                    path_data, path_meta = _write_ir_export(df_ir_export, ir_tag)
                    st.success(f"IR-export klar!")
                    st.caption(f"Data: {path_data}")
                    st.caption(f"Metadata: {path_meta}")
                except Exception as e:
                    st.error(f"IR-export misslyckades: {e}")

        with col_both:
            if st.button("🚀 Exportera båda", help="Exporterar till både DEA och IR"):
                try:
                    # DEA export
                    dea_path_data, dea_path_meta = _write_dea_export(df_dea_export, dea_tag)
                    # IR export
                    ir_path_data, ir_path_meta = _write_ir_export(df_ir_export, ir_tag)
                    
                    st.success("Båda exporterna klara!")
                    with st.expander("Export-detaljer"):
                        st.write("**DEA:**")
                        st.caption(f"Data: {dea_path_data}")
                        st.caption(f"Metadata: {dea_path_meta}")
                        st.write("**IR:**")
                        st.caption(f"Data: {ir_path_data}")
                        st.caption(f"Metadata: {ir_path_meta}")
                except Exception as e:
                    st.error(f"Export misslyckades: {e}")

        # Export-information
        with st.expander("ℹ️ Export-information"):
            st.markdown(
                f"""
                **DEA-export:**
                - Fil: `scenario/kapitalbas/exports_to_dea/capex_wacc_{dea_tag}_y2024_dmu.parquet`
                - Innehåll: CAPEX baseline och scenario per DMU
                - Syfte: Mata DEA-pipen med WACC-scenariot
                
                **IR-export:**
                - Fil: `scenario/ir/kapitalkostnader/ir_kapkost_wacc_{ir_tag}_y2024_dmu.parquet`
                - Innehåll: Detaljerad kapitalkostnad (total + avskrivning/avkastning) per DMU
                - Syfte: Mata IR-dekompositionen med uppdaterade kapitalkostnader
                
                **Gemensamt:**
                - Enhet: tkr, prisår nominell 2022
                - Nivå: DMU (aggregerat från id_network)
                - År: 2024 (H1+H2 efter halvårsavrundning)
                - WACC: {R_OLD:.4f} → {r_new:.4f} (endast avkastningsdelarna påverkas)
                """
            )
    
    # ---- Debug-tab: DMU-mappning ----
    with TAB_DEBUG:
        st.subheader("Debug: DMU-mappning och aggregering")
        
        if 'dmu_debug' not in st.session_state:
            st.warning("Ingen debug-information tillgänglig. Kör om aggregeringen.")
            return
        
        debug = st.session_state['dmu_debug']
        
        # Översikt
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Kapitalbas-nätverk (original)", debug['original_count'])
        with col2:
            st.metric("Reconciliation-nätverk", debug['reconciliation_count'])  
        with col3:
            st.metric("Slutliga DMU:er", df['DMU'].nunique() if 'DMU' in df.columns else 0)
        
        # Mappningsresultat
        st.subheader("Mappningsresultat")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Mappade nätverk", debug['mapped_count'], delta=None)
        with col2:
            st.metric("Exkluderade nätverk", debug['unmapped_count'], delta=f"-{debug['unmapped_count']}")
        
        # Detaljerad analys
        with st.expander("DMU-mappning: vilka nätverk tillhör varje DMU"):
            rec = _read_reconciliation(RECON_CSV)
            if rec is not None:
                # Gruppera id_networks per DMU
                dmu_networks = rec.groupby('DMU').agg({
                    'id_network': lambda x: list(x),
                    'Företag': 'first'  # Ta första företagsnamnet per DMU
                }).reset_index()
                
                # Lägg till antal nätverk per DMU
                dmu_networks['antal_nätverk'] = dmu_networks['id_network'].apply(len)
                dmu_networks['nätverk_lista'] = dmu_networks['id_network'].apply(lambda x: ', '.join(map(str, sorted(x))))
                
                # Sortera efter antal nätverk (flest först) för att se aggregeringarna tydligt
                dmu_networks = dmu_networks.sort_values('antal_nätverk', ascending=False)
                
                # Visa tabell
                display_df = dmu_networks[['DMU', 'Företag', 'antal_nätverk', 'nätverk_lista']].copy()
                display_df.columns = ['DMU', 'Företag', 'Antal nätverk', 'id_network lista']
                
                st.dataframe(display_df, use_container_width=True)
                
                # Sammanfattning av aggregering
                multi_network_dmus = dmu_networks[dmu_networks['antal_nätverk'] > 1]
                if not multi_network_dmus.empty:
                    st.write(f"**{len(multi_network_dmus)} DMU har flera nätverk:**")
                    for _, row in multi_network_dmus.head(10).iterrows():  # Visa top 10
                        st.write(f"- DMU {int(row['DMU'])} ({row['Företag']}): {row['antal_nätverk']} nätverk")
                    
                    if len(multi_network_dmus) > 10:
                        st.write(f"... och {len(multi_network_dmus) - 10} till")
            else:
                st.error("Kunde inte ladda reconciliation-data för mappningstabell")
        
        # Lista över exkluderade nätverk
        if debug['unmapped_count'] > 0:
            with st.expander(f"Exkluderade id_network ({debug['unmapped_count']} st)"):
                if len(debug['unmapped_networks']) > 100:
                    st.warning(f"Visar första 100 av {len(debug['unmapped_networks'])} exkluderade nätverk")
                    unmapped_sample = debug['unmapped_networks'][:100]
                else:
                    unmapped_sample = debug['unmapped_networks']
                
                # Skapa DataFrame för bättre visning
                unmapped_df = pd.DataFrame({
                    'id_network': unmapped_sample,
                    'status': ['Saknas i reconciliation'] * len(unmapped_sample)
                })
                st.dataframe(unmapped_df, use_container_width=True)
        
        # Rådata-inspektion
        with st.expander("Rådata för felsökning"):
            st.write("**Kapitalbas id_networks (sample):**")
            if debug['original_count'] > 0:
                sample_original = list(df_facit['id_network'].unique())[:20]
                st.code(f"{sample_original}")
            
            st.write("**Reconciliation id_networks (sample):**") 
            if debug['reconciliation_count'] > 0:
                rec = _read_reconciliation(RECON_CSV)
                if rec is not None:
                    sample_recon = list(rec['id_network'].unique())[:20]
                    st.code(f"{sample_recon}")

    # Avslut med fallback-hantering som tidigare...