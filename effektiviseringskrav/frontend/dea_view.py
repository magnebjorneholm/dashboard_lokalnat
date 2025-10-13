"""
DEA View - Huvudorkestrering för DEA-analys i Streamlit.
=========================================================

Kombinerar backend-logik med frontend-komponenter.
Detta är den enda filen som behöver skrivas om vid Dash-migration.

DESIGN:
- Använder backend för all beräkningslogik
- Använder components för all UI-rendering
- Hanterar flöde och session state
- Minimal egen logik - mest "glue code"
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# Backend imports
from effektiviseringskrav.backend.dea_model import run_dea_model
from effektiviseringskrav.backend.data_loader import merge_capex_scenario
from effektiviseringskrav.backend.ir_calculations import calculate_ir_paverkbara_from_file
from effektiviseringskrav.backend.ir_export import export_ir_paverkbara_scenario
from effektiviseringskrav.backend.spatial_analysis import lägg_till_grannsnitt, get_spatial_summary_stats
from effektiviseringskrav.backend.heatmap_utils import (
    load_shapes_for_dea,
    merge_dea_with_geodata,
    aggregate_to_unique_geometries,
    plot_efficiency_map
)

# Frontend imports
from effektiviseringskrav.frontend.components import (
    display_dea_parameters,
    display_dea_results_summary,
    display_dea_results_table,
    display_efficiency_distributions,
    display_matching_diagnostics,
    display_ir_export_controls,
    display_export_success,
    display_standard_excel_export
)


# Konstanter
IR_BASELINE_FILE = "intaktsram/data/Löpande kostnader från SDF 2024-27.xlsx"


def show_dea_view(df: pd.DataFrame):
    """
    Huvudvy för DEA-analys.
    
    Args:
        df: DataFrame med DEA base-data från load_data()
    """
    st.header("DEA-modell")
    
    # Varning om små skillnader vs Ei
    st.warning(
        "NOTERA: Om man kör Ei:s standard-DEA så får man exakt samma påverkbara kostnader "
        "för alla företag förutom LKAB nät (delta -23 tkr) och Jukkasjärvi (delta -238 tkr). "
        "Anledningen är att vi får små skillnader i uppskattade krav (1,75% hos Ei vs. 1,82% "
        "här för LKAB och 1,50% hos Ei vs. 1,62% här Jukkasjärvi), oklart varför."
    )
    
    # ========================================================================
    # CAPEX SCENARIO MERGE
    # ========================================================================
    df, scen_info = merge_capex_scenario(df)
    
    if scen_info.get("found"):
        capex_col = scen_info.get("capex_col")
        missing_scenario = df[df[capex_col].isna()]
        
        if not missing_scenario.empty:
            st.warning(f"CAPEX-scenario saknas för {len(missing_scenario)} DMU:")
            st.dataframe(missing_scenario[['DMU', 'Företag']])
    
    # ========================================================================
    # PARAMETRAR OCH MODELLKÖRNING
    # ========================================================================
    params = display_dea_parameters(df, scen_info)
    
    if params is not None:
        # Användaren klickade "Kör DEA"
        with st.spinner("Kör DEA-beräkningar..."):
            result = run_dea_model(
                df,
                rts=params['rts'],
                trunkering_min=params['trunkering_min'],
                trunkering_max=params['trunkering_max'],
                input_cols=params['input_cols'],
                output_cols=params['output_cols'],
                outlier_filter=params['outlier_filter'],
                outlier_krav=params['outlier_krav']
            )
        
        # Spara i session state
        st.session_state['dea_result'] = result
        st.session_state['dea_params'] = params
    
    # ========================================================================
    # RESULTATVISNING (om körning finns)
    # ========================================================================
    if 'dea_result' not in st.session_state:
        st.info("Välj modellspecifikationer och klicka på 'Kör DEA' för att se resultat och export-alternativ.")
        return
    
    result = st.session_state['dea_result']
    params = st.session_state['dea_params']
    
    # Sammanfattning och tabell
    display_dea_results_summary(result, params['outlier_krav'] * 100)
    display_dea_results_table(result)
    
    # Histogram
    display_efficiency_distributions(result)
    
    # ========================================================================
    # GEOGRAFISK ANALYS
    # ========================================================================
    st.markdown("---")
    st.header("Geografisk analys")
    
    st.info(
        "**Filtrering baserad på auktoritativa källor:**\n\n"
        "Visualiseringen använder `reconciliation_id_network_firm_dmu.csv` och `Data_modeller.xlsx` "
        "för att avgöra vilka REId som är giltiga. Endast de 159 REId från dessa filer inkluderas."
    )
    
    _display_geographic_analysis(result)
    
    # ========================================================================
    # IR-EXPORT
    # ========================================================================
    st.markdown("---")
    _display_ir_export_section(result)
    
    # ========================================================================
    # STANDARD EXCEL-EXPORT
    # ========================================================================
    st.markdown("---")
    st.subheader("Export av DEA-resultat")
    
    excel_bytes = display_standard_excel_export(result)
    
    st.download_button(
        label="Ladda ned DEA-resultat som Excel",
        data=excel_bytes,
        file_name=f"dea_resultat_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def _display_geographic_analysis(result: pd.DataFrame):
    """
    Visar geografisk analys (karta + grannskapsanalys).
    
    Args:
        result: DataFrame med DEA-resultat
    """
    try:
        # Ladda shapefile
        with st.spinner("Laddar geografisk data (filtrerar enligt reconciliation)..."):
            gdf_shapes, shape_metadata = load_shapes_for_dea()
        
        # Välj indikator
        available_indicators = ["Effektivitet"]
        if "Supereffektivitet" in result.columns:
            available_indicators.append("Supereffektivitet")
        
        selected_indicator = st.selectbox(
            "Välj indikator för visualisering",
            available_indicators,
            index=0
        )
        
        # Merge DEA-resultat med geodata
        gdf_merged, match_stats = merge_dea_with_geodata(
            gdf_shapes, 
            result, 
            value_column=selected_indicator
        )
        
        # Visa matchningsdiagnostik
        with st.expander("Visa detaljerad matchningsdiagnostik", expanded=False):
            display_matching_diagnostics(match_stats, shape_metadata)
        
        # Aggregera till unika geometrier
        gdf_agg = aggregate_to_unique_geometries(gdf_merged, value_column=selected_indicator)
        
        # HEATMAP
        st.subheader(f"Karta: {selected_indicator}")
        
        st.caption(
            f"Visualiserar {selected_indicator} för {len(gdf_agg)} unika verksamhetsområden. "
            f"Grå områden saknar DEA-data (regionnät eller transmissionsnät)."
        )
        
        fig = plot_efficiency_map(
            gdf_agg,
            value_column=selected_indicator,
            title=f"{selected_indicator} per verksamhetsområde"
        )
        st.pyplot(fig)
        
        # GRANNSKAPSANALYS
        _display_neighborhood_analysis(gdf_agg, selected_indicator)
        
    except FileNotFoundError as e:
        st.error(f"Kunde inte ladda geografisk data: {e}")
        st.info(
            "Geografisk analys kräver:\n"
            "1. Shapefile: Samtliga nätföretags del- och verksamhetsområden.shp\n"
            "2. Reconciliation: reconciliation_id_network_firm_dmu.csv"
        )
    except Exception as e:
        st.error(f"Fel vid geografisk analys: {e}")
        import traceback
        with st.expander("Visa teknisk felinfo"):
            st.code(traceback.format_exc())


def _display_neighborhood_analysis(gdf_agg, selected_indicator: str):
    """
    Visar grannskapsanalys-sektion.
    
    Args:
        gdf_agg: Aggregerad GeoDataFrame
        selected_indicator: Vald indikator (t.ex. "Effektivitet")
    """
    st.markdown("---")
    st.subheader("Jämför med geografiska grannar")
    
    st.caption(
        "Analyserar hur varje nätområde presterar relativt till sina geografiska grannar. "
        "Positivt gap = högre effektivitet än grannar."
    )
    
    # Parametrar
    col1, col2 = st.columns(2)
    
    with col1:
        spatial_method = st.selectbox(
            "Grannskapsmetod", 
            ["knn", "distanceband"],
            format_func=lambda x: "K närmaste grannar (KNN)" if x == "knn" else "Avståndsbaserad"
        )
    
    with col2:
        use_distance_weight = st.checkbox(
            "Avståndsviktning",
            value=False,
            help="Om aktiverad viktas grannar med 1/avstånd (närmare grannar får större vikt)"
        )
    
    # Metodspecifika parametrar
    if spatial_method == "knn":
        gdf_with_data = gdf_agg[gdf_agg[selected_indicator].notna()]
        max_k = min(20, len(gdf_with_data) - 1)
        
        if max_k < 1:
            st.error("För få nätområden med data för grannskapsanalys.")
            return
        
        k_neighbors = st.slider(
            "Antal närmaste grannar (k)",
            min_value=1,
            max_value=max_k,
            value=min(4, max_k),
            help="Hur många närmaste grannar ska inkluderas i jämförelsen?"
        )
    else:
        distance_km = st.slider(
            "Maximalt avstånd (km)",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            help="Alla nätområden inom detta avstånd räknas som grannar"
        )
        distance_threshold = distance_km * 1000
    
    # Kör grannskapsanalys
    if st.button("Kör grannskapsanalys", type="primary"):
        with st.spinner("Beräknar grannskapseffektivitet..."):
            try:
                # Filtrera bort rader utan data FÖRE spatial analys
                gdf_for_spatial = gdf_agg[gdf_agg[selected_indicator].notna()].copy()
                
                if len(gdf_for_spatial) < 2:
                    st.error("För få nätområden med data för grannskapsanalys.")
                    return
                
                if spatial_method == "knn":
                    gdf_spatial = lägg_till_grannsnitt(
                        gdf_for_spatial,
                        indikator=selected_indicator,
                        method="knn",
                        k=k_neighbors,
                        avståndsviktning=use_distance_weight
                    )
                    method_desc = f"{k_neighbors} närmaste grannar"
                else:
                    gdf_spatial = lägg_till_grannsnitt(
                        gdf_for_spatial,
                        indikator=selected_indicator,
                        method="distanceband",
                        distance_threshold=distance_threshold,
                        avståndsviktning=use_distance_weight
                    )
                    method_desc = f"alla grannar inom {distance_km} km"
                
                st.success(f"Grannskapsanalys klar med {method_desc}")
                
                weight_desc = "med avståndsviktning" if use_distance_weight else "utan viktning"
                st.caption(f"Metod: {method_desc}, {weight_desc}")
                
                # Förbered resultat-tabell
                result_cols = ["REId", selected_indicator, "grannsnitt", "eff_gap"]
                if "Företag" in gdf_spatial.columns:
                    result_cols.insert(1, "Företag")
                
                df_spatial = gdf_spatial[result_cols].dropna().copy()
                df_spatial = df_spatial.sort_values("eff_gap", ascending=False).reset_index(drop=True)
                
                # Sammanfattning
                stats = get_spatial_summary_stats(gdf_spatial, selected_indicator)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Medel effektivitetsgap", f"{stats['mean_gap']:.3f}")
                with col2:
                    best_performer = df_spatial.iloc[0]
                    st.metric(
                        "Bäst relativt grannar",
                        best_performer.get("Företag", best_performer["REId"]),
                        delta=f"+{best_performer['eff_gap']:.3f}"
                    )
                with col3:
                    worst_performer = df_spatial.iloc[-1]
                    st.metric(
                        "Sämst relativt grannar",
                        worst_performer.get("Företag", worst_performer["REId"]),
                        delta=f"{worst_performer['eff_gap']:.3f}"
                    )
                
                # Resultat-tabell med färgkodning
                st.dataframe(
                    df_spatial.style.background_gradient(
                        cmap="RdYlGn",
                        subset=["eff_gap"]
                    ),
                    width='stretch'
                )
                
                # Export
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df_spatial.to_excel(writer, sheet_name="Grannskapsanalys", index=False)
                
                st.download_button(
                    label="Ladda ned grannskapsanalys som Excel",
                    data=buffer.getvalue(),
                    file_name=f"grannskapsanalys_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            except ValueError as e:
                st.error(f"Fel vid grannskapsanalys: {e}")
                st.info("Tips: Prova att minska k eller öka avståndet.")
            except Exception as e:
                st.error(f"Oväntat fel: {e}")
                import traceback
                with st.expander("Visa teknisk felinfo"):
                    st.code(traceback.format_exc())


def _display_ir_export_section(result: pd.DataFrame):
    """
    Visar IR-export-sektion med beräkningar och export-kontroller.
    
    Args:
        result: DataFrame med DEA-resultat
    """
    if 'Effkrav_proc' not in result.columns:
        st.error("Export kräver Effkrav_proc. Kontrollera DEA-modellens output.")
        return
    
    if not Path(IR_BASELINE_FILE).exists():
        st.warning(f"IR baseline-fil hittades inte: {IR_BASELINE_FILE}")
        return
    
    try:
        # Beräkna påverkbara kostnader (backend)
        export_data, metadata = calculate_ir_paverkbara_from_file(result, IR_BASELINE_FILE)
        
        if export_data is None or export_data.empty:
            st.error("Kunde inte beräkna påverkbara kostnader.")
            return
        
        # Visa export-kontroller (frontend)
        export_request = display_ir_export_controls(export_data, metadata)
        
        if export_request is not None:
            scenario_name, _ = export_request
            
            try:
                # Exportera (backend)
                data_path, meta_path, summary = export_ir_paverkbara_scenario(
                    export_data, 
                    scenario_name,
                    st.session_state  # Streamlit session state
                )
                
                # Visa framgång (frontend)
                display_export_success(data_path, meta_path)
                
            except Exception as e:
                st.error(f"Export misslyckades: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    except Exception as e:
        st.error(f"Fel vid läsning av IR baseline: {e}")
        import traceback
        st.code(traceback.format_exc())