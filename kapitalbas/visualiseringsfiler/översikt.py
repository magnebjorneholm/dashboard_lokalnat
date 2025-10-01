"""
översikt.py – Årsvy (H1+H2), MSEK-visning, WACC-scenario och Export (2024, tkr)

UPPDATERAD: Använder core-moduler för beräkningslogik
- Beräkningar från core/calculations.py
- DMU-aggregering från core/dmu_aggregation.py
- Export-logik från core/export_builders.py och core/export_writers.py
- UI-lager behåller session state och Streamlit-specifika funktioner
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

# ========= Import från core-moduler =========
from core.calculations import (
    R_OLD, YEAR_TO_CODES, TIME_LABEL_TO_CODE, CODE_TO_TIME_LABEL,
    EiWaccInputs, ei_wacc_real_pre_tax, apply_interest_scenario, 
    get_period_df, format_wacc_tag,
    fmt_msek_from_tkr, fmt_msek_delta_from_tkr, fmt_msek_delta_from_tkr_tol
)
from core.dmu_aggregation import (
    aggregate_to_dmu, check_year_completeness
)
from core.export_builders import (
    build_dea_export_table, build_ir_export_table_period,
    apply_concession_adjustments
)
from core.export_writers import (
    write_dea_export, write_ir_export
)
from core.session_utils import get_user_org, ensure_org_dir

# ========= Konstanter & format (UI-specifika) =========
NBSP = "\u202f"
MINUS = "\u2212"

# Sökvägar - uppdaterade för ny mappstruktur
SCENARIO_DIR = "scenario"
DEA_EXPORT_DIR = os.path.join(SCENARIO_DIR, "kapitalbas", "exports_to_dea")
IR_EXPORT_DIR = os.path.join(SCENARIO_DIR, "kapitalbas", "exports_to_ir")
DEA_BASE_XLSX = "effektiviseringskrav/data/Data_modeller.xlsx"
RECON_CSV = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv"

# KPI (tkr → MSEK visuellt)
KPI_DISPLAY = ["capcost_sum", "dep_ord", "dep_tail", "nuav_ord", "nuav_tail", "return_ord", "return_tail"]
KPI_LABEL = {
    "capcost_sum": "Kapitalkostnad – år (capcost_sum) (MSEK)",
    "dep_ord":     "Kapitalförslitning – ordinarie (dep_ord) (MSEK)",
    "dep_tail":    "Kapitalförslitning – svans (dep_tail) (MSEK)",
    "nuav_ord":    "Nuanskaffningsvärde – ordinarie (nuav_ord) (MSEK)",
    "nuav_tail":   "Nuanskaffningsvärde – svans (nuav_tail) (MSEK)",
    "return_ord":  "Kapitalbindning – ordinarie (return_ord) (MSEK)",
    "return_tail": "Kapitalbindning – svans (return_tail) (MSEK)",
}


# ========= Metodikruta (UI-specifik) =========
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
        st.error(f"Saknade kolumner i df_facit: {sorted(miss)}")
        return

    # Aggregera till DMU-nivå från start (använder core-funktion)
    df = aggregate_to_dmu(
        df_facit,
        recon_path=RECON_CSV,
        filter_regional=True
    )
    
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
        
        TAB1, TAB2, TAB3 = st.tabs(["Tab 1 – Facit", "Tab 2 – Beräkna kalkylränta från grunden", "Tab 3 – Export (inaktiverad)"])
        
        with TAB3:
            st.error("Export är inaktiverad eftersom DMU-mappning misslyckades. Kontrollera reconciliation-filen.")
        
        return

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

    TAB1, TAB2, TAB3 = st.tabs(["Översikt", "Beräkna kalkylränta från grunden", "Scenario + Export"])

    # ---- Tab 1: Facit (år, MSEK) ----
    with TAB1:
        st.subheader("Översikt")
        filt_df = _filter_df(df)
        if filt_df.empty:
            st.warning("Ingen rad matchar valt DMU/år.")
        else:
            kpi = filt_df[KPI_DISPLAY].sum(numeric_only=True)
            for cols in [KPI_DISPLAY[i:i+2] for i in range(0,len(KPI_DISPLAY),2)]:
                c = st.columns(2)
                for j, col in enumerate(cols):
                    c[j].metric(KPI_LABEL[col], fmt_msek_from_tkr(kpi[col]))
            st.caption("Korten visar MSEK (avrundat). Underliggande tabell visar tkr.")
            with st.expander("Visa underlag (tkr)"):
                tmp = filt_df.copy()
                tmp["time_label"] = tmp["time"].map(CODE_TO_TIME_LABEL)
                st.dataframe(tmp, use_container_width=True, hide_index=True)
        
        with st.expander("DMU-mappning: vilka nätverk tillhör varje DMU"):
            from core.dmu_aggregation import read_reconciliation
            rec = read_reconciliation(RECON_CSV)
            if rec is not None:
                # Gruppera id_networks per DMU
                dmu_networks = rec.groupby('DMU').agg({
                    'id_network': lambda x: list(x),
                    'Företag': 'first'  # Ta första företagsnamnet per DMU
                }).reset_index()
                
                # Lägg till antal nätverk per DMU
                dmu_networks['antal_nätverk'] = dmu_networks['id_network'].apply(len)
                dmu_networks['nätverk_lista'] = dmu_networks['id_network'].apply(
                    lambda x: ', '.join(map(str, sorted(x)))
                )
                
                # Sortera efter antal nätverk (flest först)
                dmu_networks = dmu_networks.sort_values('antal_nätverk', ascending=False)
                
                # Visa tabell
                display_df = dmu_networks[['DMU', 'Företag', 'antal_nätverk', 'nätverk_lista']].copy()
                display_df.columns = ['DMU', 'Företag', 'Antal nätverk', 'id_network lista']
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.error("Kunde inte ladda reconciliation-data för mappningstabell")

    # ---- Tab 2: WACC ----
    with TAB2:
        st.subheader("Beräkna kalkylränta från grunden")
        defaults = {
            "rf_nom":0.0287, "mrp":0.0668, "infl":0.0202, "credit":0.0114,
            "debt_share":0.36, "tax_rate":0.206, "beta_mode":"β_A",
            "beta_a":0.37, "beta_e":0.54
        }
        for k,v in defaults.items():
            st.session_state.setdefault(k,v)
        st.session_state.setdefault("r_new", R_OLD)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.number_input(
                "Riskfri ränta (nominell) Rf", 
                key="rf_nom", step=0.0001, format="%.4f",
                help="KI:s 9-årsprognos för 10-årig svensk statsobligation (nominell)."
            )
            st.number_input(
                "Marknadsriskpremie (nominell) MRP", 
                key="mrp", step=0.0001, format="%.4f",
                help="Långsiktig aktiemarknadspremie (nominell), baserad på PwC:s riskpremiestudier."
            )
            st.number_input(
                "Inflation π (KPIF)", 
                key="infl", step=0.0001, format="%.4f",
                help="KPIF enligt KI:s 9-årsprognos. Fisher-omräkning till real nivå."
            )

        with c2:
            st.number_input(
                "Kreditriskpremie (nominell)", 
                key="credit", step=0.0001, format="%.4f",
                help="Spread för lånat kapital (typiskt europeiska utilities BBB vs 10-årig Bund)."
            )
            st.number_input(
                "Skuldsättningsgrad S = D/(D+E)", 
                key="debt_share", min_value=0.0, max_value=0.95, 
                step=0.01, format="%.2f",
                help="Vikt för skuld i WACC. Relation: D/E = S/(1−S)."
            )
            st.number_input(
                "Bolagsskatt T", 
                key="tax_rate", min_value=0.0, max_value=0.99, 
                step=0.001, format="%.3f",
                help="Omräkning från efter skatt till före skatt."
            )

        with c3:
            st.radio(
                "Beta-inmatning", ["β_A", "β_E"], index=0, key="beta_mode",
                help="Välj att ange tillgångsbeta (β_A) eller aktiebeta (β_E) direkt."
            )
            if st.session_state["beta_mode"] == "β_A":
                st.number_input(
                    "β_A", key="beta_a", step=0.01, format="%.2f",
                    help="Tillgångsbeta (obelanad). Omvandlas till aktiebeta med Hamada."
                )
            else:
                st.number_input(
                    "β_E", key="beta_e", step=0.01, format="%.2f",
                    help="Aktiebeta (belanad). Används direkt i CAPM."
                )

        beta_a = st.session_state["beta_a"] if st.session_state["beta_mode"]=="β_A" else None
        beta_e = st.session_state["beta_e"] if st.session_state["beta_mode"]=="β_E" else None
        
        # Använd core-funktion för WACC-beräkning
        Re, Rd, Wn, Wr = ei_wacc_real_pre_tax(EiWaccInputs(
            rf_nominal=st.session_state["rf_nom"],
            mrp_nominal=st.session_state["mrp"],
            credit_spread=st.session_state["credit"],
            debt_share=st.session_state["debt_share"],
            tax_rate=st.session_state["tax_rate"],
            inflation=st.session_state["infl"],
            beta_asset=beta_a,
            beta_equity=beta_e
        ))

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Re (nominell, efter skatt)", f"{Re*100:.2f} %")
        k2.metric("Rd (nominell, före skatt)",  f"{Rd*100:.2f} %")
        k3.metric("WACC (nominell, före skatt)", f"{Wn*100:.2f} %")
        k4.metric("WACC (real, före skatt)",     f"{Wr*100:.2f} %")

        def _reset_ei_defaults():
            for k,v in defaults.items():
                st.session_state[k]=v
            st.session_state["r_new"]=R_OLD

        cc1, cc2 = st.columns([1,1])
        with cc1:
            if st.button("Använd denna kalkylränta i Tab 3"):
                st.session_state["r_new"] = round(float(Wr), 4)
                st.success(f"Satt r_new = {st.session_state['r_new']:.4f}")
        with cc2:
            st.button("Återställ till Ei-standard", on_click=_reset_ei_defaults)

        _render_methodology_info()

    # ---- Tab 3: Scenario + Export ----
    with TAB3:
        st.subheader("Räkna kapitalkostnader med annan WACC och exportera")

        r_new = round(float(st.number_input(
            "WACC (real, pre-tax) för scenario",
            value=float(st.session_state.get("r_new", R_OLD)),
            step=0.0001, format="%.4f"
        )), 4)

        base_year = _filter_df(df)
        if base_year.empty:
            st.warning("Ingen rad matchar valt DMU/år.")
            return

        # Aggregera först (samma logik som baseline KPI:er)
        totals = base_year.agg({
            'return_ord': 'sum',
            'return_tail': 'sum', 
            'dep_ord': 'sum',
            'dep_tail': 'sum'
        })

        # Scenario-beräkning på aggregerad data
        scale = float(r_new) / R_OLD
        if abs(float(r_new) - R_OLD) < 1e-10:
            return_ord_new = totals["return_ord"]
            return_tail_new = totals["return_tail"]
        else:
            return_ord_new = round(totals["return_ord"] * scale)
            return_tail_new = round(totals["return_tail"] * scale)

        capcost_sum_new = totals["dep_ord"] + totals["dep_tail"] + return_ord_new + return_tail_new

        # Skapa new_vals Series för kompatibilitet
        new_vals = pd.Series({
            "return_ord_new": return_ord_new,
            "return_tail_new": return_tail_new,
            "capcost_sum_new": capcost_sum_new
        })
        base_vals = base_year[["return_ord","return_tail","capcost_sum"]].sum(numeric_only=True)

        st.caption("Korten visar MSEK (avrundat). Avskrivningar lämnas oförändrade.")
        for keys in [["return_ord_new","return_tail_new"],["capcost_sum_new"]]:
            cols = st.columns(2)
            for i,k in enumerate(keys):
                if i>1: break
                val_tkr = float(new_vals[k])
                base_k = k.replace("_new","")
                delta_tkr = val_tkr - float(base_vals[base_k])
                cols[i].metric(
                    {
                        "return_ord_new":"Kapitalbindning – ordinarie (return_ord) (MSEK)",
                        "return_tail_new":"Kapitalbindning – svans (return_tail) (MSEK)",
                        "capcost_sum_new":"Kapitalkostnad - år (capcost_sum) (MSEK)"
                    }[k],
                    fmt_msek_from_tkr(val_tkr),
                    delta=fmt_msek_delta_from_tkr_tol(delta_tkr)
                )

        # ==== Export-sektion (endast 2024) ====
        st.markdown("---")
        st.subheader("Export – DEA (endast 2024) & IR (summa 2024–2027)")
        st.caption("Exporterar CAPEX och detaljerad kapitalkostnad i **tkr** per DMU. Prisår = nominell 2022.")

        # Kontrollera att vi är på 2024
        if int(year_choice) != 2024:
            st.info("Export är låst till 2024. Välj 2024 i filtret för att aktivera export.")
            return

        df_2024 = df[df["time"].isin(YEAR_TO_CODES[2024])].copy()
        
        # Komplett H1+H2? (använder core-funktion)
        df_complete, incomplete = check_year_completeness(df_2024, 2024)
        if not incomplete.empty:
            st.warning(f"{len(incomplete)} DMU saknar H1 eller H2 för 2024 och exporteras inte.")
            # Filtrera bort ofullständiga DMU
            df_2024 = df_complete 

        if df_2024.empty:
            st.error("Ingen DMU har komplett H1+H2 data för 2024")
            return

        # Bygg båda export-tabellerna (använder core-funktioner)
        try:
            df_dea_export, df_dea_excl, dea_tag = build_dea_export_table(
                df_2024, r_new, 
                dea_base_path=DEA_BASE_XLSX,
                exclude_missing_dmus=True
            )
            df_ir_export, ir_tag = build_ir_export_table_period(
                df, r_new, 
                years=(2024,2025,2026,2027),
                apply_concessions=True
            )

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
            st.markdown(f"**IR-export (SUMMA 2024–2027) · WACC_tag = {ir_tag}**")
            st.dataframe(
                df_ir_export[['DMU', 'Företag', 'Kapitalkostnad_Ny', 'Avskrivningar_Ny', 'Avkastning_Ny']], 
                use_container_width=True, hide_index=True
            )

        # Export-knappar (använder core-funktioner med org-parameter)
        st.markdown("---")
        col_dea, col_ir, col_both = st.columns(3)
        
        with col_dea:
            if st.button("Exportera till DEA", help="Exporterar CAPEX-data för DEA-pipen"):
                try:
                    org = get_user_org()  # UI-lager hämtar org
                    path_data, path_meta = write_dea_export(df_dea_export, dea_tag, org)
                    st.success(f"DEA-export klar!")
                    st.caption(f"Data: {path_data}")
                    st.caption(f"Metadata: {path_meta}")
                except Exception as e:
                    st.error(f"DEA-export misslyckades: {e}")

        with col_ir:
            if st.button("Exportera till IR", help="Exporterar detaljerad kapitalkostnad för IR-dekomposition"):
                try:
                    org = get_user_org()  # UI-lager hämtar org
                    path_data, path_meta = write_ir_export(df_ir_export, ir_tag, org)
                    st.success(f"IR-export klar!")
                    st.caption(f"Data: {path_data}")
                    st.caption(f"Metadata: {path_meta}")
                except Exception as e:
                    st.error(f"IR-export misslyckades: {e}")

        with col_both:
            if st.button("Exportera båda", help="Exporterar till både DEA och IR"):
                try:
                    org = get_user_org()  # UI-lager hämtar org
                    # DEA export
                    dea_path_data, dea_path_meta = write_dea_export(df_dea_export, dea_tag, org)
                    # IR export
                    ir_path_data, ir_path_meta = write_ir_export(df_ir_export, ir_tag, org)
                    
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
        with st.expander("Export-information"):
            st.markdown(
                f"""
                **DEA-export:**
                - Fil: `scenario/kapitalbas/exports_to_dea/{get_user_org()}/capex_wacc_{dea_tag}_y2024_dmu.parquet`
                - Innehåll: CAPEX baseline och scenario per DMU
                - Syfte: Mata DEA-pipen med WACC-scenariot
                
                **IR-export:**
                - Fil: `scenario/kapitalbas/exports_to_ir/{get_user_org()}/ir_kapkost_wacc_{ir_tag}_y2024_2027_dmu.parquet`
                - Innehåll: Detaljerad kapitalkostnad (total + avskrivning/avkastning) per DMU
                - Syfte: Mata IR-dekompositionen med uppdaterade kapitalkostnader
                
                **Gemensamt:**
                - Enhet: tkr, prisår nominell 2022
                - Nivå: DMU (aggregerat från id_network)
                - År: 2024 (H1+H2 efter halvårsavrundning)
                - WACC: {R_OLD:.4f} → {r_new:.4f} (endast avkastningsdelarna påverkas)
                """
            )