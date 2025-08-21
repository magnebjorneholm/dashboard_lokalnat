"""
Modellspecifikation (översikt)
- Syfte: Beräkna kalkylränta (WACC) enligt Ei 2024–2027 och applicera denna på facitdata för kapitalbas.
- Slutmått: WACC_real_pre (real, före skatt). CAPM körs nominellt efter skatt och räknas om till före skatt och därefter till realt (Fisher).
- Metodkedja (Ei):
  1) CAPM (nominellt, efter skatt): Re_nom = Rf_nom + β_E * MRP_nom
  2) Skuldränta (nominell, före skatt): Rd_nom = Rf_nom + kreditspread
  3) WACC_nom_after = (1−S)*Re_nom + S*Rd_nom*(1−T)
     WACC_nom_pre   = WACC_nom_after / (1−T)
  4) Real omräkning (Fisher): WACC_real_pre = (1+WACC_nom_pre)/(1+π) − 1
- Definitioner: S = D/(D+E) (skuldandel); E-vikt = 1−S, D-vikt = S. Hamada-hävstång: β_E = β_A * (1 + (1−T)*D/E) med D/E = S/(1−S).
- Policyantaganden: Ingen särskild riskpremie; T antas konstant över perioden; beräkningar i full precision — visning avrundad.
- Integration: Exporterar show_capcost(df_facit: pd.DataFrame) -> None. Inga filinläsningar eller page config här.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Literal, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# ============================
# KONSTANTER & FORMATTERING
# ============================
R_OLD: float = 0.0453  # Ei 2024–2027, real, pre-tax (facit)

NBSP = "\u202f"   # smalt icke-brytande mellanslag
MINUS = "\u2212"  # typografiskt minus

def _to_sek_int_from_tkr(x) -> int:
    val = pd.to_numeric(x, errors="coerce")
    if pd.isna(val):
        return 0
    return int(round(float(val) * 1000.0))

def _fmt_nbsp_thousands(n: int) -> str:
    return f"{abs(n):,}".replace(",", NBSP)

def fmt_sek(x) -> str:
    n = _to_sek_int_from_tkr(x)
    return f"{MINUS}{_fmt_nbsp_thousands(-n)}" if n < 0 else _fmt_nbsp_thousands(n)

def fmt_sek_delta(x) -> str:
    n = _to_sek_int_from_tkr(x)
    sign = "+" if n >= 0 else MINUS
    return f"{sign}{_fmt_nbsp_thousands(abs(n))}"

# Halvårsmappning (som i tidigare översikt)
TIME_LABEL_TO_CODE = {
    "2024h1": 229,
    "2024h2": 230,
    "2025h1": 231,
    "2025h2": 232,
    "2026h1": 233,
    "2026h2": 234,
    "2027h1": 235,
    "2027h2": 236,
}
CODE_TO_TIME_LABEL = {v: k for k, v in TIME_LABEL_TO_CODE.items()}

# KPI-kolumner för Tab 1 (aggregering utan cat_encode)
KPI_COLUMNS = [
    "capcost_network", "capcost_sum",
    "dep_ord", "dep_tail",
    "nuav_ord", "nuav_tail",
    "return_ord", "return_tail",
]

# Mer begripliga visningsnamn (behåller originalnamn i parentes)
KPI_LABEL = {
    "capcost_network": "Kapitalkostnad – totalt nät (capcost_network) (SEK)",
    "capcost_sum":     "Kapitalkostnad – summa (capcost_sum) (SEK)",
    "dep_ord":         "Ordinarie avskrivning (dep_ord) (SEK)",
    "dep_tail":        "Svansavskrivning (dep_tail) (SEK)",
    "nuav_ord":        "Nuanskaffningsvärde – ordinarie (nuav_ord) (SEK)",
    "nuav_tail":       "Nuanskaffningsvärde – svans (nuav_tail) (SEK)",
    "return_ord":      "Avkastning – ordinarie (return_ord) (SEK)",
    "return_tail":     "Avkastning – svans (return_tail) (SEK)",
}

# ============================
# SCENARIOLOGIK (skala räntekomponent)
# ============================

def apply_interest_scenario(df: pd.DataFrame, r_new: float) -> pd.DataFrame:
    """Skala avrundade returdelar i tkr med r_new/r_old och räkna diffar/nya summor.
    Antaganden: 
      - Endast return_ord/return_tail påverkas; avskrivningar lämnas oförändrade.
      - Ny avrundning i tkr efter skalning (Ei-logik). Små differenser ±1 tkr kan uppstå.
    """
    if not (isinstance(r_new, (float, int)) and math.isfinite(r_new)):
        raise ValueError("r_new måste vara ett ändligt tal.")

    scale = float(r_new) / R_OLD
    out = df.copy()
    out["return_ord_new"] = (out["return_ord"] * scale).round().astype("Int64")
    out["return_tail_new"] = (out["return_tail"] * scale).round().astype("Int64")

    out["capcost_sum_new"] = (
        out["dep_ord"].astype("float64")
        + out["dep_tail"].astype("float64")
        + out["return_ord_new"].astype("float64")
        + out["return_tail_new"].astype("float64")
    )
    out["capcost_network_new"] = out.groupby("id_network")["capcost_sum_new"].transform("sum")

    out["d_return_ord"] = out["return_ord_new"] - out["return_ord"]
    out["d_return_tail"] = out["return_tail_new"] - out["return_tail"]
    out["d_capcost_sum"] = out["capcost_sum_new"] - out["capcost_sum"]
    out["d_capcost_network"] = out["capcost_network_new"] - out["capcost_network"]
    return out

# ============================
# WACC – SCENARIO (icke-Ei)
# ============================
# Behålls för forskningsscenarier. Ej använd i standardflödet.
@dataclass
class WaccInputs:
    rf_real: float
    mrp: float
    beta: float
    debt_premium: float
    gearing: float
    tax_rate: float

def equity_cost_real_pre_tax(inp: WaccInputs) -> float:
    return float(inp.rf_real) + float(inp.beta) * float(inp.mrp)

def debt_cost_real_pre_tax(inp: WaccInputs) -> float:
    return float(inp.rf_real) + float(inp.debt_premium)

def wacc_real_pre_tax(inp: WaccInputs, method: Literal["vanilla", "after_tax_to_pre_tax"]) -> Tuple[float, float, float]:
    """Scenario-variant. **Ej gällande metod**. Används endast i forskningsläge.
    Varning: CAPM ska köras nominellt och efter skatt i Ei-flödet.
    """
    g = float(np.clip(inp.gearing, 0.0, 1.0))
    T = float(np.clip(inp.tax_rate, 0.0, 0.99))
    Re = equity_cost_real_pre_tax(inp)
    Rd = debt_cost_real_pre_tax(inp)
    if method == "vanilla":
        wacc = (1 - g) * Re + g * Rd
    else:
        wacc_after = (1 - g) * Re + g * Rd * (1 - T)
        wacc = wacc_after / (1 - T)
    return Re, Rd, wacc

# ============================
# WACC – Ei (nominell -> real, före skatt)
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
    """Returnerar (Re_nom, Rd_nom, WACC_nom_pre, WACC_real_pre). Standard i appen.
    Definitioner och kedja:
      - CAPM (nom, after): Re_nom = Rf_nom + β_E * MRP_nom
      - Skuldränta (nom, pre): Rd_nom = Rf_nom + kreditspread
      - Omräkning till pre-tax: WACC_nom_after → WACC_nom_pre genom division med (1−T)
      - Fisher: nom → real med π (KPIF)
    """
    beta_e = inp.beta_equity if inp.beta_equity is not None else hamada_equity_beta(inp.beta_asset, inp.debt_share, inp.tax_rate)
    Re_nom = inp.rf_nominal + beta_e * inp.mrp_nominal
    Rd_nom = inp.rf_nominal + inp.credit_spread
    wacc_nom_after = (1.0 - inp.debt_share) * Re_nom + inp.debt_share * Rd_nom * (1.0 - inp.tax_rate)
    wacc_nom_pre   = wacc_nom_after / (1.0 - inp.tax_rate)
    wacc_real_pre  = (1.0 + wacc_nom_pre) / (1.0 + inp.inflation) - 1.0
    return Re_nom, Rd_nom, wacc_nom_pre, wacc_real_pre

# ============================
# UI-HJÄLP: Inforutor och varningar
# ============================

def _render_methodology_info():
    with st.expander("Metodik, information och definitioner (Ei)", expanded=False):
        # 1) Vad är kalkylräntan?
        st.markdown(
            """
            **Vad är kalkylräntan (WACC)?** Kalkylräntan är den vägt genomsnittliga kapitalkostnaden.
            I regleringen är slutmåttet **real, före skatt**. Beräkningen startar dock **nominellt och efter skatt**
            och räknas om i två steg: till **före skatt** och därefter till **real** nivå.
            """
        )

        # 2) Varför startar vi nominellt & efter skatt?
        st.markdown(
            """
            **Varför nominellt & efter skatt i CAPM?** Ei definierar kapitalkostnaden för eget kapital via CAPM i
            **nominella** termer och **efter skatt**. Därefter görs den formella omräkningen till **före skatt** och
            slutligen till **real** nivå via Fisher.
            """
        )

        # 3) Beräkningskedjan (rendera formler med st.latex för att undvika visuella fel)
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

        # 4) Hävstång & definitioner
        st.markdown("**Hamada-hävstång (från tillgångsbeta till aktiebeta):**")
        st.latex(r"\beta_E = \beta_A \left(1 + (1-T)\frac{D}{E}\right)")
        st.latex(r"\frac{D}{E} = \frac{S}{1-S}, \quad S = \frac{D}{D+E}")

        # 5) Begrepp – nybörjarvänligt
        st.markdown(
            """
            **Begrepp (kortfattat)**  
            • **Riskfri ränta,** $R_f$: prognos/medel för statsobligation.  
            • **Marknadsriskpremie,** $MRP$: genomsnittligt riskpåslag för aktiemarknaden.  
            • **Beta,** $\\beta$: känslighet mot marknaden.  
            • **Skuldsättningsgrad,** $S$: skuldandel $S=\\tfrac{D}{D+E}$; vikter i WACC: E-vikt $=1-S$, D-vikt $=S$.  
            • **Kreditriskpremie,** $CR$: extra ränta på skulder utöver $R_f$.  
            • **Bolagsskatt,** $T$: används för omräkning från efter skatt till före skatt.  
            • **Inflation,** $\\pi$: används i Fisher-omräkningen för att få real nivå.
            """
        )

        # 6) Kvalitet & vanliga misstag
        st.markdown(
            """
            **Rundning & precision**  
            Beräkningar görs i full precision; visning avrundas (t.ex. två decimaler på räntor, tkr i tabeller).
            Små differenser kan uppstå i kontrollsummor.

            **Vanliga misstag att undvika**  
            – Mata **reala** värden i CAPM-steget (ska vara **nominellt, efter skatt**).  
            – Blanda ihop **$S$** med **$D/E$** (använd $D/E = S/(1-S)$).  
            – Lägga kreditriskpremien $CR$ på något annat än skuldräntan $R_D$.
            """
        )

# ============================
# HUVUDVY
# ============================

def show_capcost(df_facit: pd.DataFrame) -> None:
    """Visar tre tabbar. Tar in facit-DF (långformat) från omgivande app.
    Kravkolumner: id_network, time, capcost_network, capcost_sum, dep_ord, dep_tail, nuav_ord, nuav_tail, return_ord, return_tail.
    """
    required = {
        "id_network", "time",
        "capcost_network", "capcost_sum",
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

    # --- Sidopanel: halvår + nät ---
    with st.sidebar:
        st.subheader("Filter")
        time_label = st.selectbox(
            "Halvår",
            options=list(TIME_LABEL_TO_CODE.keys()),
            index=0,
            help="Välj halvårsperiod. Koderna följer facitens tidsskala."
        )
        time_code = TIME_LABEL_TO_CODE[time_label]
        networks = sorted(df["id_network"].unique().tolist())
        network_choice = st.selectbox(
            "Välj nät (id_network)",
            options=["Alla"] + networks,
            index=0,
            help="Visa aggregat för alla nät eller ett specifikt id_network."
        )

    # Hjälp: funktion för att filtrera enligt valet ovan
    def _filter_df(base: pd.DataFrame) -> pd.DataFrame:
        out = base[base["time"] == time_code]
        if network_choice != "Alla":
            out = out[out["id_network"] == network_choice]
        return out

    # Tre tabbar
    TAB1, TAB2, TAB3 = st.tabs([
        "Tab 1 – Facit",
        "Tab 2 – Beräkna kalkylränta",
        "Tab 3 – Scenario med ny kalkylränta",
    ])

    # ----------------------------
    # Tab 1 – Facit (aggregering över cat_encode)
    # ----------------------------
    with TAB1:
        st.subheader("KPI:er (facit)")
        filt_df = _filter_df(df)
        if filt_df.empty:
            st.warning("Ingen rad matchar valt nät/halvår.")
        else:
            kpi_values = filt_df[KPI_COLUMNS].sum(numeric_only=True)
            st.markdown(f"**KPI för {time_label} · Nät: {network_choice}**")

            # 4 rader × 2 kolumner för att undvika '...'-avkortning i rubriker
            rows = [KPI_COLUMNS[i:i+2] for i in range(0, len(KPI_COLUMNS), 2)]
            for row_cols in rows:
                c = st.columns(2)
                for j, col in enumerate(row_cols):
                    c[j].metric(KPI_LABEL[col], fmt_sek(kpi_values[col]))

            st.caption("Korten visas i SEK (inga ören). Tabellen nedan visar tkr.")
            with st.expander("Visa underlag för beräkning"):
                tmp = filt_df.copy()
                tmp['time_label'] = tmp['time'].map(CODE_TO_TIME_LABEL)
                st.dataframe(tmp, use_container_width=True, hide_index=True)


    # ----------------------------
    # Tab 2 – Kalkylränta (från komponenter)
    # ----------------------------
    with TAB2:
        st.subheader("Beräkna kalkylränta enligt Ei (nominell → real, före skatt)")

        c1, c2, c3 = st.columns(3)
        with c1:
            rf_nom = st.number_input(
                "Riskfri ränta (nominell) Rf",
                value=0.0287, step=0.0001, format="%.4f",
                help="10-årig statsobligation (prognos/medel). Ange som andel, t.ex. 0.0287 för 2,87 %."
            )
            mrp    = st.number_input(
                "Marknadsriskpremie (nominell) MRP",
                value=0.0668, step=0.0001, format="%.4f",
                help="Aritmetiskt medel för riskpremien. Används i CAPM för Re (nominell)."
            )
            infl   = st.number_input(
                "Inflation π (KPIF)",
                value=0.0202, step=0.0001, format="%.4f",
                help="KPIF (flerårsantagande) för realomräkning via Fisher."
            )
        with c2:
            credit = st.number_input(
                "Kreditriskpremie (nominell)",
                value=0.0114, step=0.0001, format="%.4f",
                help="Tillkommer endast skuldräntan: Rd_nom = Rf_nom + kreditspread."
            )
            debt_share = st.number_input(
                "Skuldsättningsgrad S = D/(D+E)",
                value=0.36, min_value=0.0, max_value=0.95, step=0.01, format="%.2f",
                help="Vikter i WACC: E-vikt = 1−S, D-vikt = S. För beta används D/E = S/(1−S)."
            )
            tax_rate = st.number_input(
                "Bolagsskatt T",
                value=0.206, min_value=0.0, max_value=0.99, step=0.001, format="%.3f",
                help="Används för omräkning från nominell efter skatt till nominell före skatt."
            )
        with c3:
            beta_mode = st.radio("Beta-inmatning", ["Tillgångsbeta (β_A)", "Aktiebeta (β_E)"], index=0,
                                 help="Ange antingen β_A (och räkna fram β_E via Hamada) eller mata β_E direkt.")
            if beta_mode == "Tillgångsbeta (β_A)":
                beta_a = st.number_input("β_A", value=0.37, step=0.01, format="%.2f",
                                         help="Tillgångsbeta före hävstång. Omvandlas till β_E med Hamada.")
                beta_e = None
            else:
                beta_e = st.number_input("β_E", value=0.54, step=0.01, format="%.2f",
                                         help="Aktiebeta (redan hävstångsjusterad). Hoppar över Hamada.")
                beta_a = None

        ei_inputs = EiWaccInputs(
            rf_nominal=rf_nom,
            mrp_nominal=mrp,
            credit_spread=credit,
            debt_share=debt_share,
            tax_rate=tax_rate,
            inflation=infl,
            beta_asset=beta_a,
            beta_equity=beta_e,
        )
        Re_nom, Rd_nom, WACC_nom_pre, WACC_real_pre = ei_wacc_real_pre_tax(ei_inputs)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Re (nominell, efter skatt)", f"{Re_nom*100:.2f} %")
        k2.metric("Rd (nominell, före skatt)", f"{Rd_nom*100:.2f} %")
        k3.metric("WACC (nominell, före skatt)", f"{WACC_nom_pre*100:.2f} %")
        k4.metric("WACC (real, före skatt) — används i Tab 3", f"{WACC_real_pre*100:.2f} %")

        # Varningar & metodvakt
        if beta_mode == "Aktiebeta (β_E)" and beta_e is not None and beta_a is not None:
            st.warning("Både β_A och β_E är satta. Endast β_E används. Rensa β_A om du vill använda Hamada.")
        if debt_share >= 0.9:
            st.warning("Mycket hög S. Notera att Hamada-hävstång växer kraftigt när S→1.")

        _render_methodology_info()

        cc1, cc2, cc3 = st.columns([1,1,2])
        with cc1:
            if st.button("Använd denna kalkylränta i Tab 3"):
                st.session_state["r_new"] = round(float(WACC_real_pre), 4)
                st.success(f"Satt r_new = {st.session_state['r_new']:.4f}")

        with cc2:
            if st.button("Återställ till Ei-standard"):
                st.session_state["r_new"] = float(R_OLD)
                st.info(f"Återställt r_new = {R_OLD:.6f}")
        with cc3:
            st.info(f"Kontroll: r_old (facit) = {R_OLD:.4f}. Med standardvärden bör nolltestet ge ≈ 0.0453.")

        with st.expander("Audit: mellanled och indata"):
            st.markdown(
                f"- **Indata**: Rf={rf_nom:.4f}, MRP={mrp:.4f}, π={infl:.4f}, CR={credit:.4f}, S={debt_share:.2f}, T={tax_rate:.3f}, β_mode={beta_mode}"
            )
            st.markdown(
                f"- **Mellanled**: Re_nom={Re_nom:.6f}, Rd_nom={Rd_nom:.6f}, WACC_nom_pre={WACC_nom_pre:.6f}, WACC_real_pre={WACC_real_pre:.6f}"
            )
            st.caption("Alla beräkningar sker i full precision. Visning avrundas för läsbarhet.")

    # ----------------------------
    # Tab 3 – Scenario (aggregering utan cat_encode)
    # ----------------------------
    with TAB3:
        st.subheader("Scenario: ny kalkylränta på facitdata (Ei-logik i tkr)")

        default_r = float(st.session_state.get("r_new", R_OLD))
        r_new = st.number_input(
            "Ny kalkylränta r_new (real, före skatt)", value=default_r, step=0.0005, format="%.6f",
            help="Använd värdet från Tab 2 eller ange manuellt."
        )

        if abs(r_new - R_OLD) > 1e-9:
            st.warning("Scenario-läge aktivt: avviker från Ei:s r_old. Resultat flaggas som scenario (ej gällande metodnivå).")
        else:
            st.info("Standardläge: använder Ei:s fastställda nivå (facit).")

        df_scn = apply_interest_scenario(df, r_new)
        filt_scn = _filter_df(df_scn)
        filt_base = _filter_df(df)

        if filt_scn.empty:
            st.warning("Ingen rad matchar valt nät/halvår.")
        else:
            # Summera nya KPI:er (2×2-kort med tydliga etiketter + delta även för capcost_network)
            SCENARIO_LABEL = {
                "return_ord_new":      "Avkastning – ordinarie (return_ord) (SEK)",
                "return_tail_new":     "Avkastning – svans (return_tail) (SEK)",
                "capcost_sum_new":     "Kapitalkostnad – summa (capcost_sum) (SEK)",
                "capcost_network_new": "Kapitalkostnad – totalt nät (capcost_network) (SEK)",
            }
            BASE_MAP = {  # mapping till facit-kolumn för delta-beräkning
                "return_ord_new":  "return_ord",
                "return_tail_new": "return_tail",
                "capcost_sum_new": "capcost_sum",
            }

            # Nya värden (summor)
            new_cols = ["return_ord_new", "return_tail_new", "capcost_sum_new", "capcost_network_new"]
            new_vals = filt_scn[new_cols].sum(numeric_only=True)

            # Bas/facit (summor för jämförelse)
            base_cols = ["return_ord", "return_tail", "capcost_sum"]
            base_vals = filt_base[base_cols].sum(numeric_only=True)

            # Använd drop_duplicates per nät så vi inte dubbelräknar när vi summerar.
            base_net = (
                filt_base[["id_network", "capcost_network"]]
                .drop_duplicates(subset=["id_network"])
                ["capcost_network"]
                .sum()
            )
            new_net = (
                filt_scn[["id_network", "capcost_network_new"]]
                .drop_duplicates(subset=["id_network"])
                ["capcost_network_new"]
                .sum()
            )

            st.caption(
                "Korten visas i SEK (inga ören). Vi skalar returdelarna med r_new/r_old och avrundar igen (Ei-logik). "
                "Avskrivningarna lämnas oförändrade. Tabellen i expander visar tkr."
            )

            st.markdown(f"**Scenario-KPI för {time_label} · Nät: {network_choice}**")

            # --- 2×2 layout ---
            rows = [
                ["return_ord_new", "return_tail_new"],
                ["capcost_sum_new", "capcost_network_new"],
            ]

            for left_key, right_key in rows:
                c1, c2 = st.columns(2)

                # Vänster kort
                if left_key == "capcost_network_new":
                    left_value = new_net
                    left_delta = new_net - base_net
                else:
                    left_value = new_vals[left_key]
                    left_delta = left_value - base_vals[BASE_MAP[left_key]]
                c1.metric(SCENARIO_LABEL[left_key], fmt_sek(left_value), delta=fmt_sek_delta(left_delta))

                # Höger kort
                if right_key == "capcost_network_new":
                    right_value = new_net
                    right_delta = new_net - base_net
                else:
                    right_value = new_vals[right_key]
                    right_delta = right_value - base_vals[BASE_MAP[right_key]]
                c2.metric(SCENARIO_LABEL[right_key], fmt_sek(right_value), delta=fmt_sek_delta(right_delta))
