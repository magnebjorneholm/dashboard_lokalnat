"""
Frontend Streamlit-komponenter för DEA-analys.
================================================

Återanvändbara UI-komponenter som tar data och parametrar,
renderar dem i Streamlit.

DESIGN:
- Varje funktion ansvarar för EN UI-komponent
- Tar input (DataFrames, configs), returnerar user input eller None
- Inga backend-beräkningar här
- Streamlit-specifik kod (kommer bytas ut vid Dash-migration)
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple


# ============================================================================
# PARAMETER-KOMPONENTER (SIDEBAR)
# ============================================================================

def display_dea_parameters(
    df: pd.DataFrame,
    scenario_info: dict
) -> Optional[Dict]:
    """
    Visar DEA-parametrar i sidebar och returnerar användarens val.
    
    Args:
        df: DataFrame med DEA-data (för att identifiera tillgängliga kolumner)
        scenario_info: Dict från data_loader med info om CAPEX-scenario
        
    Returns:
        Dict med valda parametrar eller None om användaren inte klickat "Kör DEA"
        {
            'input_cols': List[str],
            'output_cols': List[str],
            'rts': str,
            'trunkering_min': float,
            'trunkering_max': float,
            'outlier_filter': bool,
            'outlier_krav': float (decimal)
        }
    """
    st.sidebar.subheader("DEA-parametrar")
    
    # Kolumnval
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]
    
    # Scenario-kolumner
    capex_wacc_col = None
    totex_wacc_col = None
    if scenario_info.get("found"):
        capex_wacc_col = scenario_info.get("capex_col")
        totex_wacc_col = scenario_info.get("totex_col")
        all_inputs += [c for c in [capex_wacc_col, totex_wacc_col] if c and c in df.columns]
        st.sidebar.success(
            f"WACC-scenario aktiv: {scenario_info['tag'].replace('p','.')} • "
            f"täckning {scenario_info['coverage']:.0%}"
        )
    else:
        st.sidebar.info("Inget CAPEX-scenario laddat från Kapitalbas")
    
    st.sidebar.caption(
        "**Input-alternativ**\n"
        "• CAPEX + OPEXp: separata poster för analys av kostnadstyper\n"
        "• TOTEX: totalkostnad utan uppdelning\n"
        "• _wacc_: scenario från Kapitalbas med justerad kalkylränta"
    )
    
    input_cols = st.sidebar.multiselect(
        "Välj inputvariabler", 
        all_inputs, 
        default=[c for c in ["CAPEX", "OPEXp"] if c in all_inputs]
    )
    
    # Validera exklusivitetsregler
    error_msg = _validate_input_exclusivity(input_cols)
    if error_msg:
        st.error(error_msg)
        return None
    
    # Scenario-specifik validering
    if scenario_info.get("found"):
        chosen_scen_cols = [c for c in [capex_wacc_col, totex_wacc_col] if c and c in input_cols]
        if chosen_scen_cols:
            missing = [c for c in chosen_scen_cols if df[c].isna().any()]
            if missing:
                st.error(
                    "Scenario-kolumn saknar värden för alla DMU och kan inte användas:\n"
                    f"- {', '.join(missing)}\n\n"
                    "Kontrollera exporten från Kapitalbas (nät utan DMU-match exkluderas)."
                )
                return None
    
    output_cols = st.sidebar.multiselect(
        "Välj outputvariabler", 
        all_outputs, 
        default=all_outputs
    )
    
    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen.")
        return None
    
    use_outlier_filter = st.sidebar.checkbox(
        "Filtrera bort outliers före beräkning", 
        value=True
    )
    
    # RTS och trunkering
    st.sidebar.caption(
        "**Skalavkastning (RTS)**\n"
        "• crs: Konstant skalavkastning\n"
        "• vrs: Variabel skalavkastning"
    )
    dea_rts = st.sidebar.selectbox("Skalavkastning (RTS)", ["crs", "vrs"], index=0)
    
    st.sidebar.caption(
        "**Trunkering av intäktsreduktion**\n"
        "Begränsar hur mycket ineffektivitet får påverka kraven."
    )
    dea_trunk_min = st.sidebar.slider(
        "Minsta trunkering", 
        0.0, 0.3, 0.162416, 
        step=0.005
    )
    dea_trunk_max = st.sidebar.slider(
        "Högsta trunkering", 
        0.1, 0.5, 0.3, 
        step=0.005
    )
    
    dea_outlier_krav = st.sidebar.slider(
        "Årligt krav för outliers (%)",
        1.0, 1.82, 1.0, 0.01,
        help="Vilket fast krav (i procent) ska ges till företag som klassas som outliers?"
    )
    
    # Körknapp
    run_model = st.sidebar.button("Kör DEA", type="primary")
    
    if not run_model:
        return None
    
    return {
        'input_cols': input_cols,
        'output_cols': output_cols,
        'rts': dea_rts,
        'trunkering_min': dea_trunk_min,
        'trunkering_max': dea_trunk_max,
        'outlier_filter': use_outlier_filter,
        'outlier_krav': dea_outlier_krav / 100  # Konvertera till decimal
    }


def _validate_input_exclusivity(input_cols: List[str]) -> Optional[str]:
    """
    Validerar exklusivitetsregler för input-kolumner.
    
    Returns:
        Felmeddelande (str) eller None om OK
    """
    has_capex_std = "CAPEX" in input_cols
    has_capex_scen = any(col.startswith("CAPEX_2024_wacc_") for col in input_cols)
    has_opexp = "OPEXp" in input_cols
    has_totex_std = "TOTEX" in input_cols
    has_totex_scen = any(col.startswith("TOTEX_wacc_") for col in input_cols)
    
    capex_any = has_capex_std or has_capex_scen
    totex_any = has_totex_std or has_totex_scen
    
    if totex_any and (capex_any or has_opexp):
        return "Välj antingen bara TOTEX (baseline/scenario) ELLER CAPEX (baseline/scenario) och/eller OPEXp."
    
    if (has_capex_std and has_capex_scen) or (has_totex_std and has_totex_scen):
        return "Välj antingen baseline- ELLER scenario-variant inom samma familj (CAPEX/TOTEX)."
    
    return None


# ============================================================================
# RESULTAT-KOMPONENTER
# ============================================================================

def display_dea_results_summary(result: pd.DataFrame, outlier_krav_pct: float):
    """
    Visar sammanfattande metrics för DEA-resultat.
    
    Args:
        result: DataFrame med DEA-resultat
        outlier_krav_pct: Fast krav för outliers (i procent, t.ex. 1.0)
    """
    st.subheader("DEA-resultat")
    
    n_outliers = (result["is_outlier"] == True).sum()
    n_total = len(result)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Totalt antal DMU", n_total)
    
    with col2:
        st.metric("Outliers", n_outliers)
    
    with col3:
        avg_eff = result[~result["is_outlier"]]["Effektivitet"].mean()
        st.metric("Medeleffektivitet", f"{avg_eff:.3f}")
    
    with col4:
        avg_krav = result["Effkrav_proc"].mean() * 100
        st.metric("Medelkrav (%)", f"{avg_krav:.2f}%")
    
    if n_outliers > 0:
        st.warning(f"{n_outliers} företag klassificerade som outliers (fast krav {outlier_krav_pct:.1f}%)")
        _display_outliers_table(result)


def _display_outliers_table(result: pd.DataFrame):
    """Visar expanderbar tabell med outliers."""
    df_outliers = result[result["is_outlier"] == True][
        ["Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc"]
    ].copy()
    df_outliers["Effkrav_proc"] = df_outliers["Effkrav_proc"].round(4)
    
    with st.expander("Visa outliers"):
        st.dataframe(df_outliers, use_container_width=True)


def display_dea_results_table(result: pd.DataFrame):
    """
    Visar huvudresultat-tabell för DEA.
    
    Args:
        result: DataFrame med DEA-resultat
    """
    display_result = result[
        ["DMU", "Företag", "Effektivitet", "Supereffektivitet", "Effkrav_proc", "is_outlier"]
    ].copy()
    
    display_result["Effkrav_proc"] = (display_result["Effkrav_proc"] * 100).round(2)
    display_result = display_result.rename(columns={
        "Effkrav_proc": "Årligt krav (%)",
        "is_outlier": "Outlier"
    })
    
    st.dataframe(display_result, use_container_width=True)


def display_efficiency_histogram(data: pd.Series, title: str = "Effektivitet"):
    """
    Visar histogram för effektivitetsfördelning.
    
    Args:
        data: Serie med effektivitetsvärden
        title: Titel för histogram
    """
    # Filtrera till numeriska värden
    data_clean = pd.to_numeric(data, errors="coerce").dropna()
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(data_clean, bins=15, edgecolor='black')
    ax.set_title(title)
    ax.set_xlabel("Värde")
    ax.set_ylabel("Antal företag")
    ax.grid(True)
    
    st.pyplot(fig)
    plt.close()


def display_efficiency_distributions(result: pd.DataFrame):
    """
    Visar två histogram: effektivitet och årligt krav.
    
    Args:
        result: DataFrame med DEA-resultat
    """
    st.subheader("Fördelningar")
    
    col1, col2 = st.columns(2)
    
    df_plot = result[result["is_outlier"] == False]
    
    with col1:
        display_efficiency_histogram(
            df_plot["Effektivitet"], 
            title="Effektivitet (exkl. outliers)"
        )
    
    with col2:
        display_efficiency_histogram(
            df_plot["Effkrav_proc"] * 100, 
            title="Årligt effektiviseringskrav (%) (exkl. outliers)"
        )


# ============================================================================
# DIAGNOSTIK-KOMPONENTER (GEOGRAFISK ANALYS)
# ============================================================================

def display_matching_diagnostics(match_stats: Dict, metadata: Dict):
    """
    Visar transparent matchningsdiagnostik för geografisk data.
    
    Porterad från heatmap_utils.display_matching_diagnostics med minimal förändring.
    
    Args:
        match_stats: Dict från merge_dea_with_geodata()
        metadata: Dict från load_shapes_for_dea()
    """
    st.write("###  Shapefile-information")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ursprungliga polygoner", metadata["n_polygons_original"])
    with col2:
        st.metric("Efter REId-explosion", metadata["n_rows_after_explode"])
    with col3:
        st.metric("Giltiga REId (reconciliation)", metadata["n_valid_remaining"])
    
    # Visa vad som exkluderades
    if metadata["n_filtered_out"] > 0:
        st.write(f"**Exkluderade från shapefile (ej i reconciliation):** {metadata['n_filtered_out']} rader")
        
        if metadata["excluded_by_type"]:
            excluded_str = ", ".join([f"{k}: {v}" for k, v in metadata["excluded_by_type"].items()])
            st.write(f"  Fördelning: {excluded_str}")
        
        if len(metadata["excluded_reid"]) <= 10:
            st.write(f"  REId: {', '.join(metadata['excluded_reid'])}")
        else:
            with st.expander(f"Visa alla {len(metadata['excluded_reid'])} exkluderade REId"):
                st.write(metadata["excluded_reid"])
    
    # Visa vad som behölls
    st.write("**Behållna nättyper:**")
    for net_type, count in metadata["kept_by_type"].items():
        st.write(f"  - {net_type}: {count} REId")
    
    st.write("###  REId-matchning (Geodata ↔ DEA-resultat)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("REId med geografi", match_stats["total_shapes"])
    with col2:
        st.metric("REId med DEA-data", match_stats["total_dea"])
    with col3:
        match_pct = match_stats["match_rate"] * 100
        st.metric("Matchning", f"{match_pct:.1f}%")
    
    # Intelligent kategorisering av saknade
    expected_missing = match_stats["expected_but_missing"]
    ok_missing = match_stats["ok_to_miss"]
    no_geo = match_stats["only_in_dea"]
    
    # Problematiska saknade
    if expected_missing:
        n = len(expected_missing)
        st.error(
            f" **{n} REId förväntas ha DEA-data men saknar det**\n\n"
            f"Dessa har `in_data_modeller=True` i reconciliation-filen.\n\n"
            f"Exempel: {', '.join(expected_missing[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} problematiska REId"):
                st.write(expected_missing)
    
    # OK saknade
    if ok_missing:
        n = len(ok_missing)
        rer_missing = [r for r in ok_missing if r.startswith("RER")]
        ret_missing = [r for r in ok_missing if r.startswith("RET")]
        
        status_icon = "" if n == len(rer_missing) + len(ret_missing) else ""
        
        st.info(
            f"{status_icon} **{n} REId saknar DEA-data (förväntat)**\n\n"
            f"Dessa har `in_data_modeller=False` i reconciliation-filen.\n\n"
            f"Fördelning:\n"
            f"  - RER (regionnät): {len(rer_missing)}\n"
            f"  - RET (transmission): {len(ret_missing)}\n"
            f"  - Övriga: {n - len(rer_missing) - len(ret_missing)}\n\n"
            f"Exempel: {', '.join(ok_missing[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} REId utan DEA-data (OK)"):
                st.write(ok_missing)
    
    # REId med data men utan geografi
    if no_geo:
        n = len(no_geo)
        st.warning(
            f" **{n} REId har DEA-data men saknar geografi**\n\n"
            f"Dessa kan inte visualiseras på kartan.\n\n"
            f"Exempel: {', '.join(no_geo[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} icke-visualiserbara REId"):
                st.write(no_geo)
    
    # Sammanfattning
    if not expected_missing and match_stats["match_rate"] >= 0.85:
        st.success(" Utmärkt matchning - alla förväntade REId har DEA-data")
    elif not expected_missing:
        st.info(" Matchning OK - alla förväntade REId har DEA-data")
    else:
        st.warning(" Problem - vissa förväntade REId saknar DEA-data")


# ============================================================================
# EXPORT-KOMPONENTER
# ============================================================================

def display_ir_export_controls(
    export_data: pd.DataFrame,
    metadata: dict
) -> Optional[Tuple[str, bool]]:
    """
    Visar export-kontroller för IR-påverkbara kostnader.
    
    Args:
        export_data: DataFrame med beräknade påverkbara kostnader
        metadata: Metadata från calculate_ir_paverkbara_export
        
    Returns:
        Tuple med (scenario_name, export_clicked) eller None
    """
    st.subheader("Export till Intäktsram-dekomposition")
    st.caption("Beräknar påverkbara kostnader för 2024-2027 perioden baserat på Ei:s verkliga beräkningsmetod")
    
    # Visa metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_baseline = metadata['total_baseline_tkr'] / 1000
        st.metric("Baseline innan pålägg av eff.krav.", f"{total_baseline:.1f} MSEK")
    
    with col2:
        total_target = metadata['total_target_tkr'] / 1000
        st.metric("Efter effektiviseringskrav", f"{total_target:.1f} MSEK")
    
    with col3:
        total_reduction = metadata['total_reduction_tkr'] / 1000
        reduction_pct = (total_reduction / total_baseline) * 100 if total_baseline > 0 else 0
        st.metric("Total reduktion", f"{total_reduction:.1f} MSEK ({reduction_pct:.1f}%)")
    
    # Förhandsvisning
    with st.expander("Förhandsvisning av export-data"):
        preview_data = export_data[
            ['DMU', 'REId', 'Företag', 'Paverkbara_Baseline_4yr', 
             'Effektiviseringskrav', 'Paverkbara_Target', 'Total_Reduction_tkr']
        ].copy()
        preview_data['Effektiviseringskrav'] = (preview_data['Effektiviseringskrav'] * 100).round(2)
        preview_data = preview_data.rename(columns={'Effektiviseringskrav': 'Årligt krav (%)'})
        st.dataframe(preview_data, use_container_width=True)
    
    # Export-kontroller
    export_name = st.text_input(
        "Export-namn (valfritt)", 
        placeholder="t.ex. 'DEA_CRS_2024'"
    )
    
    export_clicked = st.button("Exportera till IR-dekomposition", type="primary")
    
    if export_clicked:
        return (export_name or "DEA", True)
    
    return None


def display_export_success(data_path: str, meta_path: str):
    """
    Visar framgångsmeddelande efter export.
    
    Args:
        data_path: Sökväg till exporterad data-fil
        meta_path: Sökväg till metadata-fil
    """
    st.success("Export klar!")
    st.caption(f"Data: {data_path}")
    st.caption(f"Metadata: {meta_path}")
    st.info("Scenariot är nu tillgängligt i IR-dekompositionen under 'Hämta från Effektiviseringskrav'")


def display_standard_excel_export(result: pd.DataFrame) -> bytes:
    """
    Skapar Excel-export för DEA-resultat och returnerar bytes.
    
    Args:
        result: DataFrame med DEA-resultat
        
    Returns:
        Excel-fil som bytes (för st.download_button)
    """
    import io
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        result.to_excel(writer, sheet_name="Resultat", index=False)
    
    return buffer.getvalue()

def display_company_geographic_analysis(result: pd.DataFrame, user_dmu: int, company_name: str):
    """
    Visar företagsspecifik geografisk karta med företaget markerat.
    
    Args:
        result: DEA-resultat (alla företag)
        user_dmu: Företagets DMU
        company_name: Företagsnamn
    """
    from effektiviseringskrav.backend.spatial_analysis import get_company_geographic_context
    from effektiviseringskrav.backend.heatmap_utils import plot_efficiency_map
    
    with st.spinner("Laddar geografisk karta..."):
        context = get_company_geographic_context(result, user_dmu)
    
    if context is None:
        st.warning("Geografisk data saknas för ditt företag")
        return
    
    try:
        fig = plot_efficiency_map(
            context['all_data'],
            value_column="Effektivitet",
            title="Effektivitet per verksamhetsområde"
        )
        
        # Markera företagets områden
        ax = fig.axes[0]
        context['company_data'].boundary.plot(
            ax=ax,
            edgecolor='red',
            linewidth=3,
            label=company_name
        )
        ax.legend(loc='upper right')
        
        st.pyplot(fig)
        
    except Exception as e:
        st.error(f"Kunde inte visa karta: {e}")