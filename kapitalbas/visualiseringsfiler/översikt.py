# Write oversikt.py with the requested changes to /mnt/data and display a download link

"""
oversikt.py — Årsvy (H1+H2), MSEK-visning och WACC-scenario
- Visar KPI på ÅR (H1+H2) men behåller halvårslogik under huven för skalning/avrundning.
- Alla KPI-kort i MSEK.
- Tar bort capcost_network (periodsumma) ur huvudvyer; årskort bygger på sum(capcost_sum).
- Scenario (ny WACC) skalar endast returdelar; avskrivningarna lämnas oförändrade.
- Rättad Streamlit-hantering av session_state (reset via callback, ej efter widget-instansiering).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple, Literal, Dict, Any

import numpy as np
import pandas as pd
import streamlit as st

# ============================
# KONSTANTER & FORMATTERING
# ============================
R_OLD: float = 0.0453  # Ei 2024–2027, real, pre-tax (facit)

EI_DEFAULTS = {
    "rf_nom": 0.0287,
    "mrp": 0.0668,
    "infl": 0.0202,
    "credit": 0.0114,
    "debt_share": 0.36,
    "tax_rate": 0.206,
    # Beta-läge och nivåer
    "beta_a": 0.37,  # används om du har valt "Tillgångsbeta (β_A)"
    "beta_e": 0.54,  # används om du har valt "Aktiebeta (β_E)"
}

NBSP = "\u202f"   # smalt icke-brytande mellanslag
MINUS = "\u2212"  # typografiskt minus

def fmt_msek_from_tkr(x, decimals: int = 3) -> str:
    """Visuell formattering till MSEK. Indata är tkr (som i facit)."""
    val = pd.to_numeric(x, errors="coerce")
    if pd.isna(val):
        val = 0.0
    msek = float(val) / 1000.0  # tkr → MSEK
    s = f"{msek:,.{decimals}f}".replace(",", NBSP)
    return s

def fmt_msek_delta_from_tkr(x, decimals: int = 3) -> str:
    """Delta i MSEK med +/−. Indata tkr."""
    val = pd.to_numeric(x, errors="coerce")
    if pd.isna(val):
        val = 0.0
    msek = float(val) / 1000.0
    sign = "+" if msek >= 0 else MINUS
    s = f"{abs(msek):,.{decimals}f}".replace(",", NBSP)
    return f"{sign}{s}"

def fmt_msek_delta_from_tkr_tol(x, decimals: int = 3, tol_tkr: int = 1) -> str:
    """Visa ≈0.000 om |delta| ≤ tol_tkr (default 1 tkr), annars vanlig MSEK-delta."""
    try:
        val = float(x)
    except Exception:
        val = 0.0
    if abs(val) <= tol_tkr:
        return "≈0.000"
    return fmt_msek_delta_from_tkr(val, decimals)

# Halvårskoder (som i facit)
TIME_LABEL_TO_CODE = {
    "2024h1": 229, "2024h2": 230,
    "2025h1": 231, "2025h2": 232,
    "2026h1": 233, "2026h2": 234,
    "2027h1": 235, "2027h2": 236,
}
CODE_TO_TIME_LABEL = {v: k for k, v in TIME_LABEL_TO_CODE.items()}

# År → [H1, H2]
YEAR_TO_CODES = {
    2024: [229, 230],
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236],
}

# KPI-kolumner vi summerar (tkr)
KPI_DISPLAY = [
    "capcost_sum",
    "dep_ord", "dep_tail",
    "nuav_ord", "nuav_tail",
    "return_ord", "return_tail",
]
KPI_LABEL = {
    "capcost_sum": "Kapitalkostnad – summa (capcost_sum) (MSEK)",
    "dep_ord":     "Ordinarie avskrivning (dep_ord) (MSEK)",
    "dep_tail":    "Svansavskrivning (dep_tail) (MSEK)",
    "nuav_ord":    "Nuanskaffningsvärde – ordinarie (nuav_ord) (MSEK)",
    "nuav_tail":   "Nuanskaffningsvärde – svans (nuav_tail) (MSEK)",
    "return_ord":  "Avkastning – ordinarie (return_ord) (MSEK)",
    "return_tail": "Avkastning – svans (return_tail) (MSEK)",
}

# ============================
# SCENARIO – skala returdelar
# ============================
def apply_interest_scenario(df: pd.DataFrame, r_new: float) -> pd.DataFrame:
    """
    Skalar endast returdelarna med r_new/r_old på halvårsrader (avrundar i tkr),
    och bygger årssummor genom filtreringen utanför denna funktion.
    Lämnar dep_* oförändrade.
    """
    if not (isinstance(r_new, (float, int)) and math.isfinite(r_new)):
        raise ValueError("r_new måste vara ett ändligt tal.")
    scale = float(r_new) / R_OLD

    out = df.copy()
    # Skala returdelar och avrunda i tkr (som i Ei-logik)
    out["return_ord_new"] = (out["return_ord"] * scale).round().astype("Int64")
    out["return_tail_new"] = (out["return_tail"] * scale).round().astype("Int64")

    # Ny capcost_sum som dep + scaled return
    out["capcost_sum_new"] = (
        out["dep_ord"].astype("float64")
        + out["dep_tail"].astype("float64")
        + out["return_ord_new"].astype("float64")
        + out["return_tail_new"].astype("float64")
    )
    # Deltakolumner (för QA)
    out["d_return_ord"] = out["return_ord_new"] - out["return_ord"]
    out["d_return_tail"] = out["return_tail_new"] - out["return_tail"]
    out["d_capcost_sum"] = out["capcost_sum_new"] - out["capcost_sum"]
    return out

# ============================
# WACC – Ei (nominellt → real, före skatt)
# ============================
@dataclass
class EiWaccInputs:
    rf_nominal: float = 0.0287        # 2,87 %
    mrp_nominal: float = 0.0668       # 6,68 %
    credit_spread: float = 0.0114     # 1,14 %
    debt_share: float = 0.36          # S = D/V
    tax_rate: float = 0.206           # 20,60 %
    inflation: float = 0.0202         # π (KPIF) 2,02 %
    beta_asset: float | None = 0.37   # β_A (tillgångsbeta)
    beta_equity: float | None = None  # β_E (om satt används denna direkt)

def hamada_equity_beta(beta_asset: float, debt_share: float, tax_rate: float) -> float:
    # β_E = β_A * (1 + (1−T) * D/E), med D/E = S/(1−S)
    d_over_e = debt_share / max(1e-12, (1.0 - debt_share))
    return beta_asset * (1.0 + (1.0 - tax_rate) * d_over_e)

def ei_wacc_real_pre_tax(inp: EiWaccInputs) -> tuple[float, float, float, float]:
    """Returnerar (Re_nom, Rd_nom, WACC_nom_pre, WACC_real_pre)."""
    beta_e = inp.beta_equity if inp.beta_equity is not None else hamada_equity_beta(inp.beta_asset, inp.debt_share, inp.tax_rate)
    Re_nom = inp.rf_nominal + beta_e * inp.mrp_nominal
    Rd_nom = inp.rf_nominal + inp.credit_spread
    wacc_nom_after = (1.0 - inp.debt_share) * Re_nom + inp.debt_share * Rd_nom * (1.0 - inp.tax_rate)
    wacc_nom_pre   = wacc_nom_after / (1.0 - inp.tax_rate)
    wacc_real_pre  = (1.0 + wacc_nom_pre) / (1.0 + inp.inflation) - 1.0
    return Re_nom, Rd_nom, wacc_nom_pre, wacc_real_pre

# ============================
# UI – Metodikruta
# ============================
def _render_methodology_info():
    with st.expander("Metodik, information och definitioner (Ei)", expanded=False):
        st.markdown(
            """
            **Vad är kalkylräntan (WACC)?** Vägt genomsnitt av kapitalkostnaden för skuld och eget kapital.
            Slutmått i regleringen är **real, före skatt**. Beräkningen börjar **nominellt och efter skatt**, räknas om till
            **före skatt** och därefter till **real** via Fisher.
            """
        )
        st.markdown("**Beräkningskedja i fyra steg**")
        st.markdown("1. **CAPM (nominell, efter skatt)** – kostnad för eget kapital")
        st.latex(r"R_E = R_f + \beta_E \cdot MRP")
        st.markdown("2. **Skuldränta (nominell, före skatt)** – kostnad för skuld")
        st.latex(r"R_D = R_f + CR")
        st.markdown("3. **WACC (nominell)** – blanda E och D samt omräkning till före skatt")
        st.latex(r"\text{WACC}_{nom,after} = (1-S)R_E + S \cdot R_D \cdot (1-T)")
        st.latex(r"\text{WACC}_{nom,pre} = \frac{\text{WACC}_{nom,after}}{1-T}")
        st.markdown("4. **Fisher-omräkning (nominell → real)**")
        st.latex(r"1 + r_{\text{real}} = \frac{1 + r_{\text{nom}}}{1 + \pi}")
        st.markdown("Här används $\\pi$ = KPIF (flerårsantagande).")
        st.markdown("**Hamada-hävstång:**")
        st.latex(r"\beta_E = \beta_A \left(1 + (1-T)\frac{D}{E}\right)")
        st.latex(r"\frac{D}{E} = \frac{S}{1-S}, \quad S = \frac{D}{D+E}")
        st.markdown(
            """
            **Rundning & precision**  
            Skalning görs per halvår och avrundas i tkr innan H1+H2 summeras till år. Visning sker i MSEK.
            Små differenser (±1 tkr) kan uppstå jämfört med att först summera och sedan avrunda.
            """
        )

# ============================
# HUVUDFUNKTION
# ============================
def show_capcost(df_facit: pd.DataFrame) -> None:
    """
    Visar tre tabbar (facit, beräkna WACC, scenario). Tar in facit-DF (långformat).
    Kräver minst kolumnerna:
      id_network, time, capcost_sum, dep_ord, dep_tail, nuav_ord, nuav_tail, return_ord, return_tail
    Enheter: tkr. Visning: MSEK.
    """
    required = {
        "id_network", "time",
        "capcost_sum",
        "dep_ord", "dep_tail",
        "nuav_ord", "nuav_tail",
        "return_ord", "return_tail",
    }
    missing = required - set(df_facit.columns)
    if missing:
        st.error(f"Saknade kolumner i df_facit: {sorted(missing)}")
        return

    df = df_facit.copy()
    df["id_network"] = df["id_network"].astype("int64")
    df["time"] = df["time"].astype("int64")

    st.header("Översikt – Kapitalbas")
    st.caption("Standard: Ei-metodik 2024–2027. Slutmått: WACC (real, före skatt). CAPM körs nominellt (efter skatt) och räknas om.")

    # ----------------------------
    # SIDOPANEL – ÅR (H1+H2) + NÄT
    # ----------------------------
    with st.sidebar:
        st.subheader("Filter")
        year_choice = st.selectbox(
            "År",
            options=[2024, 2025, 2026, 2027],
            index=0,
            help="Årssiffror = H1+H2 (halvårsberäkning sker under huven)."
        )
        networks = sorted(df["id_network"].unique().tolist())
        network_choice = st.selectbox(
            "Välj nät (id_network)",
            options=["Alla"] + networks,
            index=0,
            help="Visa aggregat för alla nät eller ett specifikt id_network."
        )

    def _filter_df(base: pd.DataFrame) -> pd.DataFrame:
        codes = YEAR_TO_CODES[int(year_choice)]
        out = base[base["time"].isin(codes)]
        if network_choice != "Alla":
            out = out[out["id_network"] == network_choice]
        return out

    TAB1, TAB2, TAB3 = st.tabs(["Tab 1 – Facit", "Tab 2 – Beräkna kalkylränta", "Tab 3 – Scenario med ny kalkylränta"])

    # ----------------------------
    # TAB 1 – FACIT (ÅR, MSEK)
    # ----------------------------
    with TAB1:
        st.subheader("KPI:er (facit)")
        filt_df = _filter_df(df)
        if filt_df.empty:
            st.warning("Ingen rad matchar valt nät/år.")
        else:
            kpi_values = filt_df[KPI_DISPLAY].sum(numeric_only=True)
            st.markdown(f"**KPI för {year_choice} · Nät: {network_choice}**")

            rows = [KPI_DISPLAY[i:i+2] for i in range(0, len(KPI_DISPLAY), 2)]
            for row_cols in rows:
                c = st.columns(2)
                for j, col in enumerate(row_cols):
                    c[j].metric(KPI_LABEL[col], fmt_msek_from_tkr(kpi_values[col]))

            st.caption("Korten visar MSEK (avrundat). Underliggande tabell visar tkr.")
            with st.expander("Visa underlag för beräkning (tkr)"):
                tmp = filt_df.copy()
                tmp["time_label"] = tmp["time"].map(CODE_TO_TIME_LABEL)
                st.dataframe(tmp, use_container_width=True, hide_index=True)

    # ----------------------------
    # TAB 2 – BERÄKNA WACC
    # ----------------------------
    with TAB2:
        st.subheader("Beräkna kalkylränta enligt Ei (nominell → real, före skatt)")

        # Defaults i session_state (en gång)
        EI_DEFAULTS = {
            "rf_nom": 0.0287,
            "mrp": 0.0668,
            "infl": 0.0202,
            "credit": 0.0114,
            "debt_share": 0.36,
            "tax_rate": 0.206,
            "beta_mode": "β_A",
            "beta_a": 0.37,
            "beta_e": 0.54,
        }
        for k, v in EI_DEFAULTS.items():
            st.session_state.setdefault(k, v)
        st.session_state.setdefault("r_new", R_OLD)

        # Widgets (styrda av key, ingen direkt skrivning efter instansiering)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input("Riskfri ränta (nominell) Rf", key="rf_nom", step=0.0001, format="%.4f")
            st.number_input("Marknadsriskpremie (nominell) MRP", key="mrp", step=0.0001, format="%.4f")
            st.number_input("Inflation π (KPIF)", key="infl", step=0.0001, format="%.4f")
        with c2:
            st.number_input("Kreditriskpremie (nominell)", key="credit", step=0.0001, format="%.4f")
            st.number_input("Skuldsättningsgrad S = D/(D+E)", key="debt_share", min_value=0.0, max_value=0.95, step=0.01, format="%.2f")
            st.number_input("Bolagsskatt T", key="tax_rate", min_value=0.0, max_value=0.99, step=0.001, format="%.3f")
        with c3:
            st.radio("Beta-inmatning", ["β_A", "β_E"], index=0, key="beta_mode",
                     help="Ange antingen β_A (och räkna fram β_E via Hamada) eller mata β_E direkt.")
            if st.session_state["beta_mode"] == "β_A":
                st.number_input("β_A", key="beta_a", step=0.01, format="%.2f")
            else:
                st.number_input("β_E", key="beta_e", step=0.01, format="%.2f")

        # Beräkna
        beta_a = st.session_state["beta_a"] if st.session_state["beta_mode"] == "β_A" else None
        beta_e = st.session_state["beta_e"] if st.session_state["beta_mode"] == "β_E" else None
        inp = EiWaccInputs(
            rf_nominal=st.session_state["rf_nom"],
            mrp_nominal=st.session_state["mrp"],
            credit_spread=st.session_state["credit"],
            debt_share=st.session_state["debt_share"],
            tax_rate=st.session_state["tax_rate"],
            inflation=st.session_state["infl"],
            beta_asset=beta_a,
            beta_equity=beta_e,
        )
        Re_nom, Rd_nom, WACC_nom_pre, WACC_real_pre = ei_wacc_real_pre_tax(inp)

        # --- Baslinje mot Ei-standard (använder samma beta-läge som i radion) ---
        mode = st.session_state["beta_mode"]  # "β_A" eller "β_E"
        if mode == "β_A":
            base_beta_a = EI_DEFAULTS["beta_a"]
            base_beta_e = None
        else:  # mode == "β_E"
            base_beta_a = None
            base_beta_e = EI_DEFAULTS["beta_e"]

        _base_inputs = EiWaccInputs(
            rf_nominal=EI_DEFAULTS["rf_nom"],
            mrp_nominal=EI_DEFAULTS["mrp"],
            credit_spread=EI_DEFAULTS["credit"],
            debt_share=EI_DEFAULTS["debt_share"],
            tax_rate=EI_DEFAULTS["tax_rate"],
            inflation=EI_DEFAULTS["infl"],
            beta_asset=base_beta_a,
            beta_equity=base_beta_e,
        )
        Re0, Rd0, WACC_nom0, WACC_real0 = ei_wacc_real_pre_tax(_base_inputs)

        # --- Korten med Δ i procentenheter (pp) ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Re (nominell, efter skatt)", f"{Re_nom*100:.2f} %", delta=f"{(Re_nom - Re0)*100:.2f} pp")
        k2.metric("Rd (nominell, före skatt)",  f"{Rd_nom*100:.2f} %", delta=f"{(Rd_nom - Rd0)*100:.2f} pp")
        k3.metric("WACC (nominell, före skatt)", f"{WACC_nom_pre*100:.2f} %", delta=f"{(WACC_nom_pre - WACC_nom0)*100:.2f} pp")
        k4.metric("WACC (real, före skatt)",     f"{WACC_real_pre*100:.2f} %", delta=f"{(WACC_real_pre - WACC_real0)*100:.2f} pp")




        # Reset via callback (inte direkt skrivning efter widget-instansiering)
        def _reset_ei_defaults():
            for k, v in EI_DEFAULTS.items():
                st.session_state[k] = v
            st.session_state["r_new"] = R_OLD

        cc1, cc2, cc3 = st.columns([1,1,2])
        with cc1:
            if st.button("Använd denna kalkylränta i Tab 3"):
                st.session_state["r_new"] = round(float(WACC_real_pre), 4)
                st.success(f"Satt r_new = {st.session_state['r_new']:.4f} (avrundat)")
        with cc2:
            st.button("Återställ till Ei-standard", on_click=_reset_ei_defaults)
        with cc3:
            st.info(f"Kontroll: r_old (facit) = {R_OLD:.4f}. Med standardvärden bör nolltestet ge ≈ {R_OLD:.4f}.")

        _render_methodology_info()

        with st.expander("Audit: mellanled och indata"):
            st.markdown(
                f"- **Indata**: Rf={st.session_state['rf_nom']:.4f}, MRP={st.session_state['mrp']:.4f}, "
                f"π={st.session_state['infl']:.4f}, CR={st.session_state['credit']:.4f}, "
                f"S={st.session_state['debt_share']:.2f}, T={st.session_state['tax_rate']:.3f}, mode={st.session_state['beta_mode']}"
            )
            st.markdown(
                f"- **Mellanled**: Re_nom={Re_nom:.6f}, Rd_nom={Rd_nom:.6f}, "
                f"WACC_nom_pre={WACC_nom_pre:.6f}, WACC_real_pre={WACC_real_pre:.6f}"
            )

    # ----------------------------
    # TAB 3 – SCENARIO (ÅR, MSEK)
    # ----------------------------
    with TAB3:
        st.subheader("Scenario: ny kalkylränta på facitdata (Ei-logik i tkr)")

        default_r = float(st.session_state.get("r_new", R_OLD))
        r_new_input = st.number_input("WACC (real, pre-tax) för scenario", value=default_r, step=0.0001, format="%.4f")
        r_new = round(float(r_new_input), 4)

        filt_base = _filter_df(df)
        if filt_base.empty:
            st.warning("Ingen rad matchar valt nät/år.")
            return

        # Räkna scenario på halvårsrader och visa årssummor
        scen = apply_interest_scenario(filt_base, r_new)
        filt_scn = scen  # alias

        # Summera årsvärden (tkr)
        new_vals  = filt_scn[["return_ord_new", "return_tail_new", "capcost_sum_new"]].sum(numeric_only=True)
        base_vals = filt_base[["return_ord", "return_tail", "capcost_sum"]].sum(numeric_only=True)

        st.caption("Korten visar MSEK (avrundat). Skalning görs per halvår och summeras till år; avskrivningar lämnas oförändrade.")

        st.markdown(f"**Scenario-KPI för {year_choice} · Nät: {network_choice}**")

        SCEN_LABEL = {
            "return_ord_new":  "Avkastning – ordinarie (return_ord) (MSEK)",
            "return_tail_new": "Avkastning – svans (return_tail) (MSEK)",
            "capcost_sum_new": "Kapitalkostnad – summa (capcost_sum) (MSEK)",
        }
        # 2×2 layout (3 kort → sista rutan lämnas tom)
        keys = ["return_ord_new", "return_tail_new", "capcost_sum_new"]
        rows = [keys[i:i+2] for i in range(0, len(keys), 2)]
        for row in rows:
            c = st.columns(2)
            for j, key in enumerate(row):
                val_tkr = float(new_vals[key])
                base_key = key.replace("_new", "")
                delta_tkr = val_tkr - float(base_vals[base_key])
                c[j].metric(SCEN_LABEL[key], fmt_msek_from_tkr(val_tkr), delta=fmt_msek_delta_from_tkr_tol(delta_tkr))

        with st.expander("Visa underlag (scenario, tkr)"):
            tmp = filt_scn.copy()
            tmp["time_label"] = tmp["time"].map(CODE_TO_TIME_LABEL)
            st.dataframe(tmp, use_container_width=True, hide_index=True)

        with st.expander("Visa underlag (facit, tkr)"):
            tmp = filt_base.copy()
            tmp["time_label"] = tmp["time"].map(CODE_TO_TIME_LABEL)
            st.dataframe(tmp, use_container_width=True, hide_index=True)

