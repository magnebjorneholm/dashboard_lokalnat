# foretag_kapital.py
# Företagsspecifik vy för kapitalkostnader
# Återanvänder översikt.py funktionalitet men filtrerat till inloggat företag

import streamlit as st
import pandas as pd
import numpy as np
import math
import json
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime
from pathlib import Path

# Import företagsspecifik data loader
from foretag.app.kapitalbas_data_loader import (
    load_capcost_a_foretag, 
    load_dmu_volymer_foretag,
    load_reconciliation_foretag_info,
    validate_company_data,
    get_user_dmu,
    get_user_org
)

# Import funktionalitet från befintlig översikt.py
from kapitalbas.visualiseringsfiler.översikt import (
    apply_interest_scenario,
    ei_wacc_real_pre_tax,
    EiWaccInputs,
    fmt_msek_from_tkr,
    fmt_msek_delta_from_tkr,
    fmt_msek_delta_from_tkr_tol,
    get_concession_adjustments,
    apply_concession_adjustments,
    _format_wacc_tag,
    _render_methodology_info,
    # NYTT: Importera funktioner för att hantera alla företags data för DEA-export
    _aggregate_to_dmu,
    _build_dea_export_table,
    _write_dea_export,
    get_period_df,
    YEAR_TO_CODES
)

# Använd autentisering från huvudappen
if "access_granted" not in st.session_state or not st.session_state.access_granted:
    st.stop()

if st.session_state.user_role != "company":
    st.error("Denna sida är endast tillgänglig för företagsanvändare")
    st.stop()

# Konstanter
R_OLD: float = 0.0453  # Ei 2024–2027, real, pre-tax
NBSP = "\u202f"
MINUS = "\u2212"

# Tidsperioder
TIME_LABEL_TO_CODE = {
    "2024h1": 229, "2024h2": 230,
    "2025h1": 231, "2025h2": 232,
    "2026h1": 233, "2026h2": 234,
    "2027h1": 235, "2027h2": 236,
}
CODE_TO_TIME_LABEL = {v: k for k, v in TIME_LABEL_TO_CODE.items()}

# KPI-definitioner (tkr → MSEK visuellt)
KPI_DISPLAY = ["capcost_sum", "dep_ord", "dep_tail", "nuav_ord", "nuav_tail", "return_ord", "return_tail"]
KPI_LABEL = {
    "capcost_sum": "Kapitalkostnad – år (capcost_sum) (MSEK)",
    "dep_ord": "Kapitalförslitning – ordinarie (dep_ord) (MSEK)",
    "dep_tail": "Kapitalförslitning – svans (dep_tail) (MSEK)",
    "nuav_ord": "Nuanskaffningsvärde – ordinarie (nuav_ord) (MSEK)",
    "nuav_tail": "Nuanskaffningsvärde – svans (nuav_tail) (MSEK)",
    "return_ord": "Kapitalbindning – ordinarie (return_ord) (MSEK)",
    "return_tail": "Kapitalbindning – svans (return_tail) (MSEK)",
}


def ensure_org_dir(base_path: str) -> str:
    """Skapar organisationsspecifik katalog och returnerar sökvägen"""
    org = get_user_org()
    org_path = os.path.join(base_path, org)
    os.makedirs(org_path, exist_ok=True)
    return org_path


def show_foretag_kapital():
    """Huvudfunktion för företagsspecifik kapitalvy"""
    
    st.set_page_config(page_title="Mitt företag - Kapitalkostnader", layout="wide")
    st.title("Mitt företag - Kapitalkostnader")
    
    # Validera användardata
    validation = validate_company_data()
    
    if not validation['capcost_data_available']:
        st.error("Kunde inte ladda kapitalkostnad-data för ditt företag")
        
        with st.expander("Debug-information"):
            st.json(validation)
        
        st.info("Kontakta support om problemet kvarstår")
        return
    
    # Ladda företagsdata
    df_company = load_capcost_a_foretag()
    company_info = load_reconciliation_foretag_info()
    
    if df_company.empty:
        st.error("Inga kapitalkostnad-data hittades för ditt företag")
        return
    
    # Visa företagsinformation
    user_dmu = get_user_dmu()
    company_name = company_info.get('company_name', 'Ditt företag')
    
    st.markdown(f"### {company_name} (DMU {user_dmu})")
    
    # Visa grundläggande information
    with st.expander("Företagsinformation"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("DMU", user_dmu)
        with col2:
            st.metric("Antal lokalnät", company_info.get('local_networks', 0))
        with col3:
            periods = df_company['time'].nunique() if 'time' in df_company.columns else 0
            st.metric("Tidsperioder", periods)
    
    # Filter för år
    with st.sidebar:
        st.subheader("Inställningar")
        year_choice = st.selectbox(
            "År", 
            options=[2024, 2025, 2026, 2027], 
            index=0,
            help="Årssiffror = H1+H2 (halvårsberäkning sker under huven)."
        )
    
    def _filter_df(base: pd.DataFrame) -> pd.DataFrame:
        return base[base["time"].isin(YEAR_TO_CODES[int(year_choice)])]
    
    # Huvudtabs
    TAB1, TAB2, TAB3 = st.tabs(["Översikt", "Beräkna kalkylränta", "Scenario + Export"])
    
    # Tab 1: Översikt
    with TAB1:
        show_company_overview(df_company, _filter_df, company_info)
    
    # Tab 2: WACC-beräkning
    with TAB2:
        show_wacc_calculation()
    
    # Tab 3: Scenario + Export
    with TAB3:
        show_scenario_and_export(df_company, _filter_df, year_choice, company_name)


def show_company_overview(df_company: pd.DataFrame, filter_func, company_info: dict):
    """Visar översikt för företaget"""
    
    st.subheader("Kapitalkostnader - Översikt")
    
    filt_df = filter_func(df_company)
    
    if filt_df.empty:
        st.warning("Ingen data för valt år")
        return
    
    # KPI-kort (MSEK)
    kpi = filt_df[KPI_DISPLAY].sum(numeric_only=True)
    
    st.markdown("#### Huvudindikatorer")
    for cols in [KPI_DISPLAY[i:i+2] for i in range(0, len(KPI_DISPLAY), 2)]:
        c = st.columns(2)
        for j, col in enumerate(cols):
            if j < len(c):
                c[j].metric(KPI_LABEL[col], fmt_msek_from_tkr(kpi[col]))
    
    st.caption("Värdena visas i MSEK (avrundade). Underliggande data är i tkr.")
    
    # Detaljerad data
    with st.expander("Visa underliggande data (tkr)"):
        display_df = filt_df.copy()
        if 'time' in display_df.columns:
            display_df["Tidsperiod"] = display_df["time"].map(CODE_TO_TIME_LABEL)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Nätverk-breakdown
    with st.expander("Nätverk-breakdown"):
        st.write("**Ditt företags lokalnät:**")
        
        id_networks = company_info.get('id_networks', [])
        reid_list = company_info.get('reid_list', [])
        
        if id_networks and reid_list:
            breakdown_data = []
            for i, (id_net, reid) in enumerate(zip(id_networks, reid_list)):
                breakdown_data.append({
                    'id_network': id_net,
                    'REId': reid,
                    'Typ': 'Lokalnät'
                })
            
            breakdown_df = pd.DataFrame(breakdown_data)
            st.dataframe(breakdown_df, use_container_width=True)
        else:
            st.info("Ingen detaljerad nätverksinformation tillgänglig")
    
    # Jämförelse med bransch (placeholder)
    with st.expander("Branchjämförelse"):
        st.info("Branchjämförelse kommer att implementeras i nästa version")


def show_wacc_calculation():
    """Visar WACC-beräkning (återanvänd från översikt.py)"""
    
    st.subheader("Beräkna kalkylränta från grunden")
    
    # Standardvärden enligt Ei
    defaults = {
        "rf_nom": 0.0287,
        "mrp": 0.0668,
        "infl": 0.0202,
        "credit": 0.0114,
        "debt_share": 0.36,
        "tax_rate": 0.206,
        "beta_mode": "β_A",
        "beta_a": 0.37,
        "beta_e": 0.54
    }
    
    # Initiera session state
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("r_new", R_OLD)
    
    # Input-kolumner
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.number_input(
            "Riskfri ränta (nominell) Rf", 
            key="rf_nom", 
            step=0.0001, 
            format="%.4f",
            help="KI:s 9-årsprognos för 10-årig svensk statsobligation (nominell)."
        )
        st.number_input(
            "Marknadsriskpremie (nominell) MRP", 
            key="mrp", 
            step=0.0001, 
            format="%.4f",
            help="Långsiktig aktiemarknadspremie (nominell), baserad på PwC:s riskpremiestudier."
        )
        st.number_input(
            "Inflation π (KPIF)", 
            key="infl", 
            step=0.0001, 
            format="%.4f",
            help="KPIF enligt KI:s 9-årsprognos. Fisher-omräkning till real nivå."
        )
    
    with c2:
        st.number_input(
            "Kreditriskpremie (nominell)", 
            key="credit", 
            step=0.0001, 
            format="%.4f",
            help="Spread för lånat kapital (typiskt europeiska utilities BBB vs 10-årig Bund)."
        )
        st.number_input(
            "Skuldsättningsgrad S = D/(D+E)", 
            key="debt_share",
            min_value=0.0, 
            max_value=0.95, 
            step=0.01, 
            format="%.2f",
            help="Vikt för skuld i WACC. Relation: D/E = S/(1−S)."
        )
        st.number_input(
            "Bolagsskatt T", 
            key="tax_rate",
            min_value=0.0, 
            max_value=0.99, 
            step=0.001, 
            format="%.3f",
            help="Omräkning från efter skatt till före skatt."
        )
    
    with c3:
        st.radio(
            "Beta-inmatning", 
            ["β_A", "β_E"], 
            index=0, 
            key="beta_mode",
            help="Välj att ange tillgångsbeta (β_A) eller aktiebeta (β_E) direkt."
        )
        
        if st.session_state["beta_mode"] == "β_A":
            st.number_input(
                "β_A", 
                key="beta_a", 
                step=0.01, 
                format="%.2f",
                help="Tillgångsbeta (obelanad). Omvandlas till aktiebeta med Hamada."
            )
        else:
            st.number_input(
                "β_E", 
                key="beta_e", 
                step=0.01, 
                format="%.2f",
                help="Aktiebeta (belanad). Används direkt i CAPM."
            )
    
    # Beräkna WACC
    beta_a = st.session_state["beta_a"] if st.session_state["beta_mode"] == "β_A" else None
    beta_e = st.session_state["beta_e"] if st.session_state["beta_mode"] == "β_E" else None
    
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
    
    # Resultat
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Re (nominell, efter skatt)", f"{Re*100:.2f} %")
    k2.metric("Rd (nominell, före skatt)", f"{Rd*100:.2f} %")
    k3.metric("WACC (nominell, före skatt)", f"{Wn*100:.2f} %")
    k4.metric("WACC (real, före skatt)", f"{Wr*100:.2f} %")
    
    # Kontrollknappar
    def _reset_ei_defaults():
        for k, v in defaults.items():
            st.session_state[k] = v
        st.session_state["r_new"] = R_OLD
    
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        if st.button("Använd denna kalkylränta i Scenario"):
            st.session_state["r_new"] = round(float(Wr), 4)
            st.success(f"Satt r_new = {st.session_state['r_new']:.4f}")
    
    with cc2:
        st.button("Återställ till Ei-standard", on_click=_reset_ei_defaults)
    
    # Metodikinfo
    _render_methodology_info()


def show_scenario_and_export(df_company: pd.DataFrame, filter_func, year_choice: int, company_name: str):
    """Visar scenario-hantering och export för företaget"""
    
    st.subheader("Scenarioanalys och Export")
    st.markdown(f"Räkna kapitalkostnader med annan WACC för **{company_name}**")
    
    # WACC-input
    r_new = round(float(st.number_input(
        "WACC (real, pre-tax) för scenario",
        value=float(st.session_state.get("r_new", R_OLD)),
        step=0.0001,
        format="%.4f"
    )), 4)
    
    # Filtrera data för valt år
    base_year = filter_func(df_company)
    
    if base_year.empty:
        st.warning("Ingen data för valt år")
        return
    
    # Beräkna scenario
    totals = base_year.agg({
        'return_ord': 'sum',
        'return_tail': 'sum',
        'dep_ord': 'sum',
        'dep_tail': 'sum'
    })
    
    # Scenario-beräkning
    scale = float(r_new) / R_OLD
    if abs(float(r_new) - R_OLD) < 1e-10:
        return_ord_new = totals["return_ord"]
        return_tail_new = totals["return_tail"]
    else:
        return_ord_new = round(totals["return_ord"] * scale)
        return_tail_new = round(totals["return_tail"] * scale)
    
    capcost_sum_new = totals["dep_ord"] + totals["dep_tail"] + return_ord_new + return_tail_new
    
    # Visa resultat
    new_vals = pd.Series({
        "return_ord_new": return_ord_new,
        "return_tail_new": return_tail_new,
        "capcost_sum_new": capcost_sum_new
    })
    
    base_vals = base_year[["return_ord", "return_tail", "capcost_sum"]].sum(numeric_only=True)
    
    st.caption("Värdena visas i MSEK (avrundade). Avskrivningar lämnas oförändrade.")
    
    # KPI-kort för scenario
    for keys in [["return_ord_new", "return_tail_new"], ["capcost_sum_new"]]:
        cols = st.columns(2)
        for i, k in enumerate(keys):
            if i > 1:
                break
            val_tkr = float(new_vals[k])
            base_k = k.replace("_new", "")
            delta_tkr = val_tkr - float(base_vals[base_k])
            
            label_map = {
                "return_ord_new": "Kapitalbindning – ordinarie (return_ord) (MSEK)",
                "return_tail_new": "Kapitalbindning – svans (return_tail) (MSEK)",
                "capcost_sum_new": "Kapitalkostnad - år (capcost_sum) (MSEK)"
            }
            
            cols[i].metric(
                label_map[k],
                fmt_msek_from_tkr(val_tkr),
                delta=fmt_msek_delta_from_tkr_tol(delta_tkr)
            )
    
    # Export-sektion
    st.markdown("---")
    st.subheader("Export till andra moduler")
    
    # Kontrollera att vi är på 2024
    if int(year_choice) != 2024:
        st.info("Export är låst till 2024. Välj 2024 för att aktivera export.")
        return
    
    # KRITISK FIX: Separata export-knappar
    st.markdown("#### Export-alternativ")
    st.caption("**Viktigt**: DEA kräver WACC-scenarier för alla företag för korrekt metodologisk jämförelse")
    
    # Förbered export-data
    try:
        # 1. IR-export (endast ditt företag) - befintlig logik
        df_ir_export, ir_tag = build_company_ir_export(df_company, r_new)
        
        # 2. DEA-export (alla företag) - NY LOGIK som återanvänder översikt.py
        df_dea_export, dea_tag = build_dea_export_all_companies(r_new)
        
        # Förhandsvisning
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**IR-export (endast ditt företag)**")
            st.markdown(f"*WACC_tag = {ir_tag}*")
            st.dataframe(
                df_ir_export[['DMU', 'Företag', 'Kapitalkostnad_Ny', 'Avskrivningar_Ny', 'Avkastning_Ny']],
                use_container_width=True, 
                hide_index=True
            )
        
        with col2:
            st.markdown(f"**DEA-export (alla företag)**")
            st.markdown(f"*WACC_tag = {dea_tag} • {len(df_dea_export)} DMU*")
            # Visa endast första 5 raderna för förhandsvisning
            preview_df = df_dea_export.head(5)[['DMU', 'Företag', 'CAPEX_2024_tkr', f'CAPEX_2024_wacc_{dea_tag}_tkr']]
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            if len(df_dea_export) > 5:
                st.caption(f"Visar 5 av {len(df_dea_export)} rader")
        
        # Export-knappar - SEPARERADE enligt design
        st.markdown("---")
        col_ir, col_dea, col_both = st.columns(3)
        
        with col_ir:
            if st.button("🏢 Exportera till IR-dekomposition", help="Exporterar detaljerad kapitalkostnad för DITT företag"):
                try:
                    path_data, path_meta = write_company_ir_export(df_ir_export, ir_tag)
                    st.success("IR-export klar!")
                    st.caption(f"Data: {path_data}")
                    st.caption(f"Metadata: {path_meta}")
                except Exception as e:
                    st.error(f"IR-export misslyckades: {e}")
        
        with col_dea:
            if st.button("📊 Exportera till DEA/Effektivitet", help="Exporterar WACC-scenario för ALLA företag (metodologiskt korrekt)"):
                try:
                    path_data, path_meta = write_dea_export_all_companies(df_dea_export, dea_tag)
                    st.success("DEA-export klar!")
                    st.caption(f"Data: {path_data}")
                    st.caption(f"Metadata: {path_meta}")
                    st.info("🔬 Nu kan DEA jämföra alla företag under samma WACC-förutsättningar")
                except Exception as e:
                    st.error(f"DEA-export misslyckades: {e}")
        
        with col_both:
            if st.button("🚀 Exportera båda", help="Exporterar både IR (ditt företag) och DEA (alla företag)"):
                try:
                    ir_path_data, ir_path_meta = write_company_ir_export(df_ir_export, ir_tag)
                    dea_path_data, dea_path_meta = write_dea_export_all_companies(df_dea_export, dea_tag)
                    
                    st.success("Båda exporterna klara!")
                    with st.expander("Export-detaljer"):
                        st.write("**IR (ditt företag):**")
                        st.caption(f"Data: {ir_path_data}")
                        st.caption(f"Metadata: {ir_path_meta}")
                        st.write("**DEA (alla företag):**")
                        st.caption(f"Data: {dea_path_data}")
                        st.caption(f"Metadata: {dea_path_meta}")
                except Exception as e:
                    st.error(f"Export misslyckades: {e}")
        
        # Export-information
        with st.expander("Export-information"):
            st.markdown(f"""
            **IR-export (endast ditt företag):**
            - Syfte: Mata IR-dekompositionen med uppdaterade kapitalkostnader
            - Innehåll: Detaljerad kapitalkostnad för DMU {get_user_dmu()}
            - Period: 2024–2027
            
            **DEA-export (alla företag - METODOLOGISKT KORREKT):**
            - Syfte: Mata DEA-analysen med WACC-scenario för ALLA företag
            - Innehåll: CAPEX baseline och scenario för {len(df_dea_export) if 'df_dea_export' in locals() else 'alla'} DMU
            - Period: 2024 (H1+H2)
            - **Viktigt**: Alla företag får samma WACC-justering för korrekt jämförelse
            
            **Gemensamt:**
            - Enhet: tkr, prisår nominell 2022
            - WACC: {R_OLD:.4f} → {r_new:.4f}
            """)
    
    except Exception as e:
        st.error(f"Fel vid förberedelse av export: {e}")
        import traceback
        st.code(traceback.format_exc())


def build_company_ir_export(df_company: pd.DataFrame, r_new: float) -> Tuple[pd.DataFrame, str]:
    """Bygger IR-export för företaget (2024-2027) - SAMMA LOGIK SOM ÖVERSIKT.PY"""
    
    df_period = get_period_df(df_company, years=(2024, 2025, 2026, 2027))
    
    if df_period.empty:
        raise ValueError("Ingen perioddata för företaget")
    
    # Applicera scenario
    scen = apply_interest_scenario(df_period, r_new)
    
    # Aggregera över hela perioden
    ir = scen.groupby(["DMU", "Företag"], as_index=False).agg({
        'dep_ord': 'sum',
        'dep_tail': 'sum',
        'return_ord': 'sum',
        'return_tail': 'sum',
        'return_ord_new': 'sum',
        'return_tail_new': 'sum',
        'capcost_sum': 'sum',
        'capcost_sum_new': 'sum'
    })
    
    # Sätt exportkolumner (period)
    ir["Kapitalkostnad_Baseline"] = ir["capcost_sum"]
    ir["Kapitalkostnad_Ny"] = ir["capcost_sum_new"]
    ir["Avskrivningar_Ny"] = ir["dep_ord"] + ir["dep_tail"]  # WACC påverkar ej
    ir["Avkastning_Baseline"] = ir["return_ord"] + ir["return_tail"]
    ir["Avkastning_Ny"] = ir["return_ord_new"] + ir["return_tail_new"]

    # KRITISK FIX: Lägg till detaljerade ord/tail-delar som apply_concession_adjustments() förväntar sig
    ir["dep_ord_Ny"] = ir["dep_ord"]
    ir["dep_tail_Ny"] = ir["dep_tail"]
    ir["return_ord_Ny"] = ir["return_ord_new"]
    ir["return_tail_Ny"] = ir["return_tail_new"]
    
    # Metadata
    tag = _format_wacc_tag(r_new)
    ir["r_old"] = R_OLD
    ir["r_new"] = round(float(r_new), 4)
    ir["price_year"] = 2022
    ir["scenario_tag"] = tag
    
    # Koncessionsjustering (applicera efter att alla kolumner skapats)
    ir = apply_concession_adjustments(ir)
    
    cols = ['DMU', 'Företag', 'Kapitalkostnad_Baseline', 'Kapitalkostnad_Ny',
            'Avskrivningar_Ny', 'Avkastning_Baseline', 'Avkastning_Ny',
            'dep_ord_Ny', 'dep_tail_Ny', 'return_ord_Ny', 'return_tail_Ny',
            'r_old', 'r_new', 'price_year', 'scenario_tag']
    
    return ir[cols], tag


def build_dea_export_all_companies(r_new: float) -> Tuple[pd.DataFrame, str]:
    """
    NYTT: Bygger DEA-export för ALLA företag (metodologiskt korrekt).
    Återanvänder logik från översikt.py för att hantera alla DMU.
    """
    
    try:
        # Ladda RAW facit-data (samma som översikt.py använder)
        from kapitalbas.datafiler.data_loader import load_capcost_a
        df_facit_all = load_capcost_a()
        
        if df_facit_all.empty:
            raise ValueError("Kunde inte ladda all kapitalkostnad-data")
        
        # Aggregera till DMU-nivå (samma som översikt.py)
        df_all_dmu = _aggregate_to_dmu(df_facit_all)
        
        if df_all_dmu.empty:
            raise ValueError("DMU-aggregering misslyckades")
        
        # Filtrera till 2024 data
        df_2024 = df_all_dmu[df_all_dmu["time"].isin(YEAR_TO_CODES[2024])].copy()
        
        if df_2024.empty:
            raise ValueError("Ingen 2024-data för alla företag")
        
        # Kontrollera komplett H1+H2 data (samma logik som översikt.py)
        def _check_year_completeness(df_year: pd.DataFrame) -> pd.DataFrame:
            """Returnerar DF med DMU som saknar H1 eller H2 för året."""
            cnt = df_year.groupby("DMU")["time"].nunique().reset_index(name="n_halvår")
            return cnt[cnt["n_halvår"]<2]
        
        incomplete = _check_year_completeness(df_2024)
        if not incomplete.empty:
            st.warning(f"{len(incomplete)} DMU saknar H1 eller H2 för 2024 och exporteras inte till DEA.")
            # Filtrera bort ofullständiga DMU
            complete_dmus = df_2024.groupby("DMU")["time"].nunique()
            complete_dmus = complete_dmus[complete_dmus == 2].index
            df_2024 = df_2024[df_2024["DMU"].isin(complete_dmus)]
        
        if df_2024.empty:
            raise ValueError("Ingen DMU har komplett H1+H2 data för 2024")
        
        # Bygg DEA-export med samma logik som översikt.py
        df_dea_export, df_dea_excl, dea_tag = _build_dea_export_table(df_2024, r_new)
        
        # Debug-info
        st.info(f"DEA-export byggd: {len(df_dea_export)} DMU inkluderade, {len(df_dea_excl)} exkluderade")
        
        return df_dea_export, dea_tag
        
    except Exception as e:
        st.error(f"Fel vid byggande av DEA-export för alla företag: {e}")
        import traceback
        st.code(traceback.format_exc())
        raise


def write_company_ir_export(df_export: pd.DataFrame, tag: str) -> Tuple[str, str]:
    """Skriver IR-export till organisationsspecifik katalog - BEFINTLIG LOGIK"""
    
    base_export_dir = "scenario/kapitalbas/exports_to_ir"
    export_dir = ensure_org_dir(base_export_dir)
    
    data_path = os.path.join(export_dir, f"ir_kapkost_wacc_{tag}_y2024_2027_company.parquet")
    meta_path = data_path.replace(".parquet", ".json")
    
    df_export.to_parquet(data_path, index=False)
    
    meta = {
        "description": "Detaljerad kapitalkostnad för IR-dekomposition – företagsspecifik",
        "organization": get_user_org(),
        "user_dmu": get_user_dmu(),
        "price_year": 2022,
        "unit": "tkr",
        "level": "DMU",
        "period": {"start": 2024, "end": 2027},
        "wacc_old": R_OLD,
        "wacc_new": float(tag.replace("p", ".")),
        "export_timestamp": datetime.now().isoformat(),
        "constructed_as": "Company-specific export with return components scaled per half-year"
    }
    
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return data_path, meta_path


def write_dea_export_all_companies(df_export: pd.DataFrame, tag: str) -> Tuple[str, str]:
    """
    NYTT: Skriver DEA-export för alla företag till organisationsspecifik katalog.
    Detta löser WACC-scenario problemet genom att exportera ALLA DMU med samma WACC-justering.
    """
    
    base_export_dir = "scenario/kapitalbas/exports_to_dea"
    export_dir = ensure_org_dir(base_export_dir)
    
    data_path = os.path.join(export_dir, f"capex_wacc_{tag}_y2024_dmu.parquet")
    meta_path = data_path.replace(".parquet", ".json")
    
    df_export.to_parquet(data_path, index=False)
    
    meta = {
        "description": "CAPEX export för DEA-pipen med ALLA företag - metodologiskt korrekt WACC-scenario",
        "organization": get_user_org(),
        "initiated_by_dmu": get_user_dmu(),
        "price_year": 2022,
        "unit": "tkr",
        "level": "DMU",
        "wacc_old": R_OLD,
        "wacc_new": float(tag.replace("p", ".")),
        "export_timestamp": datetime.now().isoformat(),
        "total_dmu_count": len(df_export),
        "constructed_as": "All-company export aggregated to annual level before scenario calculation - ensures methodological correctness in DEA analysis",
        "methodological_note": "ALL DMU receive the same WACC adjustment to ensure fair comparison in DEA efficiency analysis"
    }
    
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return data_path, meta_path


# Huvudfunktion som kallas från streamlit_app.py
if __name__ == "__main__":
    show_foretag_kapital()


# Logga ut
st.sidebar.markdown("---")
if st.button("Logga ut", key="logout_kapital"):
    st.session_state.access_granted = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.session_state.user_dmu = None
    st.rerun()