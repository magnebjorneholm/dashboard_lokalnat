"""
oversikt.py — Årsvy (H1+H2), MSEK-visning, WACC-scenario och Export till DEA (2024, tkr)

- KPI visas på ÅR (H1+H2), halvårslogik används under huven.
- Visning i MSEK; DATA & EXPORT i tkr (DEA-konsekvent).
- capcost_network används inte i KPI; årsvärde = sum(capcost_sum).
- Scenario skalar endast returdelar; avskrivningar lämnas oförändrade.
- Exportsektion i Tab 3 (endast 2024): per-nät-tabell, exkludera nät som saknas i DEA via reconciliation-CSV.
- Skrivs till 'dea_exports/capex_wacc_0pXXXX_y2024_tkr.parquet' + '.json' metadata.
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

# Sökvägar (ändra om din repo har andra paths)
DEA_EXPORT_DIR = "dea_exports"
DEA_BASE_XLSX = "effektiviseringskrav/data/Data_modeller.xlsx"                 # för DMU-lista
RECON_CSV     = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"  # id_network→DMU/Företag

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

# ========= Export-hjälpare =========
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
        # Normalisera kolumnnamn
        cols = {c.lower(): c for c in rec.columns}
        idcol = cols.get("id_network") or next((c for c in rec.columns if "network" in c.lower()), "id_network")
        dmucol = cols.get("dmu","DMU")
        foretag = cols.get("företag", cols.get("foretag","Företag"))
        rec = rec.rename(columns={idcol:"id_network", dmucol:"DMU", foretag:"Företag"})
        return rec[["id_network","DMU","Företag"]].drop_duplicates()
    except Exception:
        return None

def _check_year_completeness(df_year: pd.DataFrame) -> pd.DataFrame:
    """Returnerar DF med id_network som saknar H1 eller H2 för året."""
    cnt = df_year.groupby("id_network")["time"].nunique().reset_index(name="n_halvår")
    return cnt[cnt["n_halvår"]<2]

def _build_export_table(df_year: pd.DataFrame, r_new: float) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Bygger exporttabell (tkr) per nät för 2024 och exklusionslista."""
    # Scenario-beräkning per halvår
    scen = apply_interest_scenario(df_year, r_new)

    # Årssumma per nät
    base = df_year.groupby("id_network", as_index=False).agg(CAPEX_2024_tkr=("capcost_sum","sum"))
    new  = scen.groupby("id_network", as_index=False).agg(CAPEX_2024_wacc_tkr=("capcost_sum_new","sum"))
    out  = base.merge(new, on="id_network", how="outer")
    out["delta_tkr"] = out["CAPEX_2024_wacc_tkr"] - out["CAPEX_2024_tkr"]
    out["r_old"]  = R_OLD
    out["r_new"]  = round(float(r_new), 4)
    out["price_year"] = 2022

    # Lägg DMU/Företag och exkludera de som saknas i DEA
    rec = _read_reconciliation(RECON_CSV)
    if rec is not None:
        out = out.merge(rec, on="id_network", how="left")

    dmu = _read_dmu_from_dea_base(DEA_BASE_XLSX)
    excluded = pd.DataFrame()
    if dmu is not None and "DMU" in out.columns and "Företag" in out.columns:
        out = out.merge(dmu.assign(in_dea=1), on=["DMU","Företag"], how="left")
        excluded = out[out["in_dea"].isna()][["id_network","DMU","Företag"]].copy()
        out = out[out["in_dea"].eq(1)].drop(columns=["in_dea"])

    # Döp scenariokolumnen med wacc-tagg
    tag = _format_wacc_tag(out["r_new"].iloc[0] if len(out) else r_new)
    out = out.rename(columns={"CAPEX_2024_wacc_tkr": f"CAPEX_2024_wacc_{tag}_tkr"})
    return out, excluded, tag

def _write_dea_export(df_export: pd.DataFrame, tag: str) -> tuple[str,str]:
    """Skriv Parquet + metadata JSON. Return: (data_path, meta_path)."""
    _ensure_dir(DEA_EXPORT_DIR)
    data_path = os.path.join(DEA_EXPORT_DIR, f"capex_wacc_{tag}_y2024_tkr.parquet")
    meta_path = data_path.replace(".parquet",".json")
    df_export.to_parquet(data_path, index=False)
    meta = {
        "price_year": 2022, "unit": "tkr",
        "wacc_old": R_OLD, "wacc_new": float(tag.replace("p",".")),
        "constructed_as": "H1+H2 after half-year rounding"
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return data_path, meta_path

# ========= Metodikruta =========
def _render_methodology_info():
    with st.expander("Metodik, information och definitioner (Ei)", expanded=False):
        st.markdown(
            "Slutmått: **real, före skatt**. Beräkningen börjar **nominellt och efter skatt**, "
            "räknas om till **före skatt** och därefter till **real** via Fisher."
        )
        st.latex(r"1 + r_{\text{real}} = \frac{1 + r_{\text{nom}}}{1 + \pi}")
        st.latex(r"\beta_E = \beta_A \left(1 + (1-T)\frac{D}{E}\right),\quad \frac{D}{E}=\frac{S}{1-S}")
        st.caption("Skalning görs per halvår och avrundas i tkr innan H1+H2 summeras till år. Visning sker i MSEK.")

# ========= Huvudvy =========
def show_capcost(df_facit: pd.DataFrame) -> None:
    req = {"id_network","time","capcost_sum","dep_ord","dep_tail","nuav_ord","nuav_tail","return_ord","return_tail"}
    miss = req - set(df_facit.columns)
    if miss:
        st.error(f"Saknade kolumner i df_facit: {sorted(miss)}"); return

    df = df_facit.copy()
    df["id_network"] = df["id_network"].astype("int64")
    df["time"]       = df["time"].astype("int64")

    st.header("Översikt – Kapitalbas")
    st.caption("Enhet: tkr (data) / MSEK (visas). Prisår: nominell 2022. Årssiffror: H1+H2.")

    # ---- Filter (år & nät) ----
    with st.sidebar:
        st.subheader("Filter")
        year_choice = st.selectbox("År", options=[2024,2025,2026,2027], index=0,
                                   help="Årssiffror = H1+H2 (halvårsberäkning sker under huven).")
        nets = sorted(df["id_network"].unique().tolist())
        network_choice = st.selectbox("Välj nät (id_network)", options=["Alla"]+nets, index=0)

    def _filter_df(base: pd.DataFrame) -> pd.DataFrame:
        out = base[base["time"].isin(YEAR_TO_CODES[int(year_choice)])]
        return out if network_choice=="Alla" else out[out["id_network"]==network_choice]

    TAB1, TAB2, TAB3 = st.tabs(["Tab 1 – Facit", "Tab 2 – Beräkna kalkylränta", "Tab 3 – Scenario + Export till DEA"])

    # ---- Tab 1: Facit (år, MSEK) ----
    with TAB1:
        st.subheader("KPI:er (facit)")
        filt_df = _filter_df(df)
        if filt_df.empty:
            st.warning("Ingen rad matchar valt nät/år.")
        else:
            kpi = filt_df[KPI_DISPLAY].sum(numeric_only=True)
            st.markdown(f"**KPI för {year_choice} · Nät: {network_choice}**")
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
        # Defaults i session_state
        defaults = {"rf_nom":0.0287,"mrp":0.0668,"infl":0.0202,"credit":0.0114,"debt_share":0.36,"tax_rate":0.206,"beta_mode":"β_A","beta_a":0.37,"beta_e":0.54}
        for k,v in defaults.items(): st.session_state.setdefault(k,v)
        st.session_state.setdefault("r_new", R_OLD)

        c1,c2,c3 = st.columns(3)
        with c1:
            st.number_input("Riskfri ränta (nominell) Rf", key="rf_nom", step=0.0001, format="%.4f")
            st.number_input("Marknadsriskpremie (nominell) MRP", key="mrp", step=0.0001, format="%.4f")
            st.number_input("Inflation π (KPIF)", key="infl", step=0.0001, format="%.4f")
        with c2:
            st.number_input("Kreditriskpremie (nominell)", key="credit", step=0.0001, format="%.4f")
            st.number_input("Skuldsättningsgrad S = D/(D+E)", key="debt_share", min_value=0.0, max_value=0.95, step=0.01, format="%.2f")
            st.number_input("Bolagsskatt T", key="tax_rate", min_value=0.0, max_value=0.99, step=0.001, format="%.3f")
        with c3:
            st.radio("Beta-inmatning", ["β_A","β_E"], index=0, key="beta_mode")
            if st.session_state["beta_mode"]=="β_A":
                st.number_input("β_A", key="beta_a", step=0.01, format="%.2f")
            else:
                st.number_input("β_E", key="beta_e", step=0.01, format="%.2f")

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
            st.warning("Ingen rad matchar valt nät/år."); return

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

        # ==== Export (endast 2024) ====
        st.markdown("---")
        st.subheader("Export till DEA (endast 2024)")
        st.caption("Exporterar **CAPEX 2024** i **tkr** per nät. Prisår = nominell 2022. Exkluderar nät som saknas i DEA.")

        df_2024 = df[df["time"].isin(YEAR_TO_CODES[2024])].copy()
        # Komplett H1+H2?
        incomplete = _check_year_completeness(df_2024)
        if not incomplete.empty:
            st.warning(f"{len(incomplete)} nät saknar H1 eller H2 för 2024 och exporteras inte.")

        # Bygg förhandsvisning & exklusionslista (efter DMU-match)
        df_export, df_excl, tag = _build_export_table(df_2024, r_new)

        st.markdown(f"**Förhandsgranskning (exportår 2024, WACC_tag = {tag})**")
        st.dataframe(df_export, use_container_width=True, hide_index=True)

        if not df_excl.empty:
            with st.expander(f"Exkluderas (saknas i DEA-bas): {len(df_excl)} nät"):
                st.dataframe(df_excl, use_container_width=True, hide_index=True)

        disabled = (int(year_choice) != 2024)
        if disabled:
            st.info("Exportår låst till 2024. Välj 2024 i filtret för att aktivera knappen.")

        if st.button("Exportera CAPEX 2024 till DEA (tkr)", disabled=disabled):
            try:
                path_data, path_meta = _write_dea_export(df_export, tag)
                st.success(f"Export klar: {path_data}")
                st.caption(f"Metadata: {path_meta}")
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
