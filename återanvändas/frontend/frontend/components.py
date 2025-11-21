"""
Frontend Streamlit-komponenter för DEA-analys.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
    """
    st.sidebar.subheader("DEA-parametrar")
    
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]
    
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
    
    error_msg = _validate_input_exclusivity(input_cols)
    if error_msg:
        st.error(error_msg)
        return None
    
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
    
    st.sidebar.caption(
        "**Outlier-definition**\n"
        "Konfigurera hur outliers identifieras baserat på supereffektivitet."
    )
    
    q_lower = st.sidebar.slider(
        "Nedre kvartil",
        0, 50, 25,
        step=5,
        help="Nedre kvartil för outlier-tröskel"
    )
    
    q_upper = st.sidebar.slider(
        "Övre kvartil",
        50, 100, 75,
        step=5,
        help="Övre kvartil för outlier-tröskel"
    )
    
    multiplier = st.sidebar.slider(
        "IQR-multiplikator",
        1.0, 3.0, 2.0,
        step=0.1,
        help="Multiplikator för interkvartilavstånd (IQR)"
    )
    
    st.sidebar.caption(
        "Threshold: Q_upper + multiplikator × (Q_upper - Q_lower)"
    )
    
    st.sidebar.caption(
        "**Skalavkastning (RTS)**\n"
        "• crs: Konstant skalavkastning\n"
        "• vrs: Variabel skalavkastning"
    )
    dea_rts = st.sidebar.selectbox("Skalavkastning (RTS)", ["crs", "vrs"], index=0)
    
    run_model = st.sidebar.button("Kör DEA", type="primary")
    
    if not run_model:
        return None
    
    return {
        'input_cols': input_cols,
        'output_cols': output_cols,
        'rts': dea_rts,
        'outlier_filter': use_outlier_filter,
        'q_lower': q_lower,
        'q_upper': q_upper,
        'multiplier': multiplier
    }


def _validate_input_exclusivity(input_cols: List[str]) -> Optional[str]:
    """
    Validerar exklusivitetsregler för input-kolumner.
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

def display_dea_results_summary(result: pd.DataFrame, outlier_krav_pct: float = None):
    """
    Visar sammanfattande metrics för DEA-resultat.
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
        avg_pot = result["potential"].mean()
        st.metric("Medelpotential", f"{avg_pot:.3f}")
    
    if n_outliers > 0:
        st.warning(f"{n_outliers} företag klassificerade som outliers")
        _display_outliers_table(result)


def _display_outliers_table(result: pd.DataFrame):
    """Visar expanderbar tabell med outliers."""
    df_outliers = result[result["is_outlier"] == True][
        ["Företag", "Effektivitet", "Supereffektivitet", "potential"]
    ].copy()
    df_outliers["potential"] = df_outliers["potential"].round(4)
    
    with st.expander("Visa outliers"):
        st.dataframe(df_outliers, width='stretch')


def display_dea_results_table(result: pd.DataFrame):
    """
    Visar huvudresultat-tabell för DEA.
    """
    display_result = result[
        ["DMU", "Företag", "Effektivitet", "Supereffektivitet", "potential", "is_outlier"]
    ].copy()
    
    display_result["potential"] = (display_result["potential"] * 100).round(2)
    display_result = display_result.rename(columns={
        "potential": "Potential (%)",
        "is_outlier": "Outlier"
    })
    
    st.dataframe(display_result, width='stretch')


def display_efficiency_histogram(data: pd.Series, title: str = "Effektivitet"):
    """
    Visar histogram för effektivitetsfördelning med Plotly.
    """
    data_clean = pd.to_numeric(data, errors="coerce").dropna()
    
    if data_clean.empty:
        st.warning("Ingen data att visa")
        return
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=data_clean,
        nbinsx=15,
        marker=dict(
            color='#1976D2',
            line=dict(color='#0D3B66', width=1)
        ),
        hovertemplate='Värde: %{x}<br>Antal: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14, color='#1E3A5F')
        ),
        xaxis=dict(
            title="Värde",
            gridcolor='#E5E5E5',
            showgrid=True,
            showline=False,
            zeroline=False
        ),
        yaxis=dict(
            title="Antal företag",
            gridcolor='#E5E5E5',
            showgrid=True,
            showline=False,
            zeroline=False
        ),
        plot_bgcolor='#F5F7FA',
        paper_bgcolor='#F5F7FA',
        height=400,
        margin=dict(l=50, r=20, t=50, b=50),
        font=dict(family="sans-serif", size=12, color='#2C3E50'),
        bargap=0.1
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_efficiency_distributions(result: pd.DataFrame):
    """
    Visar två histogram: effektivitet och potential.
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
            df_plot["potential"] * 100, 
            title="Potential (%) (exkl. outliers)"
        )


# ============================================================================
# GEOGRAFISK ANALYS
# ============================================================================

def display_company_geographic_analysis(
    result: pd.DataFrame, 
    user_dmu: int, 
    company_name: str,
    value_column: str
):
    """
    Visar företagsspecifik geografisk karta med företaget markerat.
    
    Args:
        result: DEA-resultat (alla företag)
        user_dmu: Företagets DMU
        company_name: Företagsnamn
        value_column: Kolumn att visualisera (t.ex. "Effektivitet" eller "Supereffektivitet")
    """
    from effektivitet.backend.spatial_analysis import get_company_geographic_context
    from effektivitet.backend.map_vizualization import plot_efficiency_map_plotly
    
    with st.spinner("Laddar geografisk karta..."):
        context = get_company_geographic_context(result, user_dmu, value_column)
    
    if context is None:
        st.warning("Geografisk data saknas för ditt företag")
        return
    
    try:
        fig = plot_efficiency_map_plotly(
            context['all_data'],
            company_geoms=context['company_data'],
            value_column=value_column,
            title=f"{value_column} per verksamhetsområde - {company_name} markerat",
            height=700,
            dark_theme=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Kunde inte visa karta: {e}")
        import traceback
        st.error(traceback.format_exc())


# ============================================================================
# DIAGNOSTIK-KOMPONENTER
# ============================================================================

def display_matching_diagnostics(match_stats: Dict, metadata: Dict):
    """
    Visar transparent matchningsdiagnostik för geografisk data.
    """
    st.write("### 📊 Shapefile-information")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ursprungliga polygoner", metadata["n_polygons_original"])
    with col2:
        st.metric("Efter REId-explosion", metadata["n_rows_after_explode"])
    with col3:
        st.metric("Giltiga REId (reconciliation)", metadata["n_valid_remaining"])
    
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
    
    st.write("**Behållna nättyper:**")
    for net_type, count in metadata["kept_by_type"].items():
        st.write(f"  - {net_type}: {count} REId")
    
    st.write("### 🔗 REId-matchning (Geodata ↔ DEA-resultat)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("REId med geografi", match_stats["total_shapes"])
    with col2:
        st.metric("REId med DEA-data", match_stats["total_dea"])
    with col3:
        match_pct = match_stats["match_rate"] * 100
        st.metric("Matchning", f"{match_pct:.1f}%")
    
    expected_missing = match_stats["expected_but_missing"]
    ok_missing = match_stats["ok_to_miss"]
    no_geo = match_stats["only_in_dea"]
    
    if expected_missing:
        n = len(expected_missing)
        st.error(
            f"⚠️ **{n} REId förväntas ha DEA-data men saknar det**\n\n"
            f"Dessa har `in_data_modeller=True` i reconciliation-filen.\n\n"
            f"Exempel: {', '.join(expected_missing[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} problematiska REId"):
                st.write(expected_missing)
    
    if ok_missing:
        n = len(ok_missing)
        rer_missing = [r for r in ok_missing if r.startswith("RER")]
        ret_missing = [r for r in ok_missing if r.startswith("RET")]
        
        status_icon = "✓" if n == len(rer_missing) + len(ret_missing) else "ℹ️"
        
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
    
    if no_geo:
        n = len(no_geo)
        st.warning(
            f"⚠️ **{n} REId har DEA-data men saknar geografi**\n\n"
            f"Dessa kan inte visualiseras på kartan.\n\n"
            f"Exempel: {', '.join(no_geo[:5])}"
        )
        
        if n > 5:
            with st.expander(f"Visa alla {n} icke-visualiserbara REId"):
                st.write(no_geo)
    
    if not expected_missing and match_stats["match_rate"] >= 0.85:
        st.success("✓ Utmärkt matchning - alla förväntade REId har DEA-data")
    elif not expected_missing:
        st.info("✓ Matchning OK - alla förväntade REId har DEA-data")
    else:
        st.warning("⚠️ Problem - vissa förväntade REId saknar DEA-data")


# ============================================================================
# EXPORT-KOMPONENTER
# ============================================================================

def display_ir_export_controls(
    export_data: pd.DataFrame,
    metadata: dict
) -> Optional[Tuple[str, bool]]:
    """
    Visar export-kontroller för IR-påverkbara kostnader.
    """
    st.subheader("Export till Intäktsram-dekomposition")
    st.caption("Beräknar påverkbara kostnader för 2024-2027 perioden baserat på Ei:s verkliga beräkningsmetod")
    
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
    
    with st.expander("Förhandsvisning av export-data"):
        preview_data = export_data[
            ['DMU', 'REId', 'Företag', 'Paverkbara_Baseline_4yr', 
             'Effektiviseringskrav', 'Paverkbara_Target', 'Total_Reduction_tkr']
        ].copy()
        preview_data['Effektiviseringskrav'] = (preview_data['Effektiviseringskrav'] * 100).round(2)
        preview_data = preview_data.rename(columns={'Effektiviseringskrav': 'Årligt krav (%)'})
        st.dataframe(preview_data, width='stretch')
    
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
    """
    st.success("Export klar!")
    st.caption(f"Data: {data_path}")
    st.caption(f"Metadata: {meta_path}")
    st.info("Scenariot är nu tillgängligt i IR-dekompositionen under 'Hämta från Effektiviseringskrav'")


def display_standard_excel_export(result: pd.DataFrame) -> bytes:
    """
    Skapar Excel-export för DEA-resultat och returnerar bytes.
    """
    import io
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        result.to_excel(writer, sheet_name="Resultat", index=False)
    
    return buffer.getvalue()