"""
Modul: intensitet_view.py

(1) Specifikation
- UI-komponenter för intensitetsanalys (kr/MWh, kr/kund)
- Integreras som Tab 4 i översikt.py
- Visar KPI-kort, fördelningsanalys, ranking och scenario-påverkan
- Kvalitetsrapporter för datasammanfogning och outlier-identifiering

(2) Motivation
- Ger Ei interaktiv tillgång till intensitetsanalys via välbekant gränssnitt
- Kompletterar absoluta kapitalkostnadsmått med relativa perspektiv
- Underlättar identifiering av extremvärden och mönster mellan nät
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from kapitalbas.beräkningsfiler.intensitet_backend import (
    apply_intensity_scenario,
    calculate_intensities,
    compute_intensity_statistics,
    create_intensity_ranking,
    identify_outliers,
    merge_capcost_with_volumes,
    prepare_distribution_data,
)

# Konstanter för formatering
NBSP = "\u202f"
MINUS = "\u2212"

def _fmt_number(value: float, decimals: int = 1, unit: str = "") -> str:
    """Formatera numeriskt värde med tusental-separator."""
    if math.isnan(value):
        return "—"
    formatted = f"{value:,.{decimals}f}".replace(",", NBSP)
    return f"{formatted}{NBSP}{unit}" if unit else formatted

def _fmt_delta(value: float, decimals: int = 1, unit: str = "") -> str:
    """Formatera delta-värde med tecken."""
    if math.isnan(value):
        return "—"
    sign = "+" if value >= 0 else MINUS
    abs_val = abs(value)
    formatted = f"{abs_val:,.{decimals}f}".replace(",", NBSP)
    result = f"{sign}{formatted}"
    return f"{result}{NBSP}{unit}" if unit else result

def _year_selector() -> int:
    """Årväljare för analys."""
    return st.selectbox(
        "Analysår", 
        options=[2024, 2025, 2026, 2027], 
        index=0,
        help="År för intensitetsanalys (H1+H2 summeras automatiskt)"
    )

def _intensity_metric_selector() -> str:
    """Väljare för intensitetsmått."""
    options = {
        "sek_per_mwh": "SEK/MWh (Kapitalkostnad per energivolym)",
        "sek_per_kund": "SEK/kund (Kapitalkostnad per anslutningskund)"
    }
    
    return st.radio(
        "Intensitetsmått",
        options=list(options.keys()),
        format_func=lambda x: options[x],
        index=0,
        help="Välj vilket intensitetsmått som ska analyseras"
    )

def _scenario_controls() -> Tuple[bool, Optional[float]]:
    """Kontroller för scenario-analys."""
    show_scenario = st.toggle(
        "Visa scenario-påverkan (WACC-förändring)", 
        value=False,
        help="Analysera hur förändringar i kalkylränta påverkar intensiteter"
    )
    
    if not show_scenario:
        return False, None
    
    r_new = st.number_input(
        "Ny WACC (real, före skatt)",
        value=0.0453,
        min_value=0.0,
        max_value=0.15,
        step=0.0001,
        format="%.4f",
        help="Ny kalkylränta för scenarioanalys"
    )
    
    return True, float(r_new)

def _render_merge_quality(quality_report) -> None:
    """Visa kvalitetsrapport för datasammanfogning."""
    if quality_report.merge_coverage_pct < 90:
        st.warning(f"⚠️ Låg merge-täckning: {quality_report.merge_coverage_pct:.1f}%")
    else:
        st.success(f"✅ God merge-täckning: {quality_report.merge_coverage_pct:.1f}%")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Totalt antal nät", quality_report.total_networks)
    
    with col2:
        st.metric("Nät med volymdata", quality_report.networks_with_volumes)
    
    with col3:
        st.metric("Täckningsgrad", f"{quality_report.merge_coverage_pct:.1f}%")
    
    if quality_report.networks_missing_volumes:
        with st.expander(f"Nät utan volymdata ({len(quality_report.networks_missing_volumes)})"):
            missing_df = pd.DataFrame({
                "id_network": quality_report.networks_missing_volumes
            })
            st.dataframe(missing_df, use_container_width=True)
    
    if quality_report.networks_with_zero_volumes:
        with st.expander(f"Nät med noll-volym ({len(quality_report.networks_with_zero_volumes)})"):
            zero_df = pd.DataFrame({
                "id_network": quality_report.networks_with_zero_volumes
            })
            st.dataframe(zero_df, use_container_width=True)

def _render_statistics_overview(stats, intensity_col: str, unit: str) -> None:
    """Visa statistisk översikt för intensitetsmått."""
    if stats.count == 0:
        st.error("Ingen data tillgänglig för statistisk analys.")
        return
    
    st.subheader("Statistisk översikt")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Medelvärde", _fmt_number(stats.mean, unit=unit))
        st.metric("Median", _fmt_number(stats.median, unit=unit))
        st.metric("Standardavvikelse", _fmt_number(stats.std, unit=unit))
    
    with col2:
        st.metric("25:e percentil", _fmt_number(stats.q25, unit=unit))
        st.metric("75:e percentil", _fmt_number(stats.q75, unit=unit))
        st.metric("Antal DMU", f"{stats.count}")

def _render_distribution_chart(df: pd.DataFrame, intensity_col: str, unit: str) -> None:
    """Visa fördelningshistogram."""
    st.subheader("Fördelning")
    
    # Förbereda histogramdata
    hist_data = prepare_distribution_data(df, intensity_col, bins=20)
    
    if len(hist_data) == 0:
        st.warning("Ingen data för fördelningsanalys.")
        return
    
    # Skapa histogram med Altair - tjocka staplar
    chart = alt.Chart(hist_data).mark_bar(
        opacity=0.8, 
        color="#1f77b4",  # Mörkblå färg
        stroke="white",   # Vit kant mellan staplar
        strokeWidth=1
    ).encode(
        x=alt.X("bin_center:Q", 
                title=f"Intensitet ({unit})",
                scale=alt.Scale(nice=True)),
        y=alt.Y("count:Q", title="Antal DMU"),
        tooltip=[
            alt.Tooltip("bin_start:Q", title="Från", format=".1f"),
            alt.Tooltip("bin_end:Q", title="Till", format=".1f"),
            alt.Tooltip("count:Q", title="Antal DMU")
        ]
    ).properties(
        width=600,
        height=300,
        title=f"Fördelning av {intensity_col.replace('_', ' ')}"
    )
    
    st.altair_chart(chart, use_container_width=True)

def _render_ranking_tables(
    top_networks: pd.DataFrame, 
    bottom_networks: pd.DataFrame,
    intensity_col: str,
    unit: str
) -> None:
    """Visa ranking-tabeller."""
    st.subheader("Ranking av DMU")
    
    if len(top_networks) == 0 and len(bottom_networks) == 0:
        st.warning("Ingen data för ranking.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔴 Högsta intensitet")
        if len(top_networks) > 0:
            display_cols = ["ranking", "DMU", intensity_col]
            
            top_display = top_networks[display_cols].copy()
            top_display[intensity_col] = top_display[intensity_col].apply(
                lambda x: _fmt_number(x, decimals=1, unit=unit)
            )
            
            st.dataframe(
                top_display,
                column_config={
                    "ranking": st.column_config.NumberColumn("#", width="small"),
                    "DMU": st.column_config.NumberColumn("DMU", width="small"),
                    intensity_col: st.column_config.TextColumn(f"Intensitet ({unit})", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Ingen data tillgänglig.")
    
    with col2:
        st.markdown("#### 🟢 Lägsta intensitet")
        if len(bottom_networks) > 0:
            display_cols = ["ranking", "DMU", intensity_col]
            
            bottom_display = bottom_networks[display_cols].copy()
            bottom_display[intensity_col] = bottom_display[intensity_col].apply(
                lambda x: _fmt_number(x, decimals=1, unit=unit)
            )
            
            st.dataframe(
                bottom_display,
                column_config={
                    "ranking": st.column_config.NumberColumn("#", width="small"),
                    "DMU": st.column_config.NumberColumn("DMU", width="small"),
                    intensity_col: st.column_config.TextColumn(f"Intensitet ({unit})", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Ingen data tillgänglig.")

def _render_outlier_analysis(df: pd.DataFrame, intensity_col: str, unit: str) -> None:
    """Visa outlier-analys."""
    with st.expander("Outlier-analys (extremvärden)"):
        outlier_method = st.selectbox(
            "Outlier-metod",
            options=["iqr", "zscore"],
            format_func=lambda x: {
                "iqr": "IQR-metod (Interkvartil-avstånd)",
                "zscore": "Z-score metod (Standardavvikelser)"
            }[x],
            help="Metod för att identifiera extremvärden"
        )
        
        try:
            outliers_high, outliers_low = identify_outliers(df, intensity_col, method=outlier_method)
            
            total_outliers = len(outliers_high) + len(outliers_low)
            if total_outliers == 0:
                st.info("Inga extremvärden identifierade med vald metod.")
                return
            
            st.write(f"**Identifierade {total_outliers} extremvärden:**")
            
            if len(outliers_high) > 0:
                st.write(f"**Höga värden ({len(outliers_high)}):**")
                high_display = outliers_high[["DMU", intensity_col]].copy()
                high_display[intensity_col] = high_display[intensity_col].apply(
                    lambda x: _fmt_number(x, decimals=1, unit=unit)
                )
                st.dataframe(high_display, use_container_width=True, hide_index=True)
            
            if len(outliers_low) > 0:
                st.write(f"**Låga värden ({len(outliers_low)}):**")
                low_display = outliers_low[["DMU", intensity_col]].copy()
                low_display[intensity_col] = low_display[intensity_col].apply(
                    lambda x: _fmt_number(x, decimals=1, unit=unit)
                )
                st.dataframe(low_display, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Fel vid outlier-analys: {e}").selectbox(
            "Outlier-metod",
            options=["iqr", "zscore"],
            format_func=lambda x: {
                "iqr": "IQR-metod (Interkvartil-avstånd)",
                "zscore": "Z-score metod (Standardavvikelser)"
            }[x],
            help="Metod för att identifiera extremvärden"
        )
        
        try:
            outliers_high, outliers_low = identify_outliers(df, intensity_col, method=outlier_method)
            
            total_outliers = len(outliers_high) + len(outliers_low)
            if total_outliers == 0:
                st.info("Inga extremvärden identifierade med vald metod.")
                return
            
            st.write(f"**Identifierade {total_outliers} extremvärden:**")
            
            if len(outliers_high) > 0:
                st.write(f"**Höga värden ({len(outliers_high)}):**")
                high_display = outliers_high[["id_network", intensity_col]].copy()
                high_display[intensity_col] = high_display[intensity_col].apply(
                    lambda x: _fmt_number(x, unit=unit)
                )
                st.dataframe(high_display, use_container_width=True, hide_index=True)
            
            if len(outliers_low) > 0:
                st.write(f"**Låga värden ({len(outliers_low)}):**")
                low_display = outliers_low[["id_network", intensity_col]].copy()
                low_display[intensity_col] = low_display[intensity_col].apply(
                    lambda x: _fmt_number(x, unit=unit)
                )
                st.dataframe(low_display, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Fel vid outlier-analys: {e}")

def _render_scenario_comparison(
    df_scenario: pd.DataFrame,
    intensity_col: str,
    unit: str,
    r_old: float,
    r_new: float
) -> None:
    """Visa scenario-jämförelse."""
    st.subheader("Scenario-påverkan")
    
    # Beräkna aggregerad påverkan
    new_col = f"{intensity_col}_new"
    delta_col = f"delta_{intensity_col}"
    
    valid_data = df_scenario.dropna(subset=[intensity_col, new_col])
    if len(valid_data) == 0:
        st.warning("Ingen data för scenario-analys.")
        return
    
    # KPI-kort för scenario
    mean_base = valid_data[intensity_col].mean()
    mean_new = valid_data[new_col].mean()
    mean_delta = mean_new - mean_base
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Baseline (medel)", _fmt_number(mean_base, unit=unit))
    
    with col2:
        st.metric("Scenario (medel)", _fmt_number(mean_new, unit=unit))
    
    with col3:
        st.metric("Förändring (medel)", _fmt_delta(mean_delta, unit=unit))
    
    # Fördelning av scenario-påverkan
    st.write("**Fördelning av påverkan per nät:**")
    
    delta_data = prepare_distribution_data(valid_data, delta_col, bins=15)
    
    if len(delta_data) > 0:
        delta_chart = alt.Chart(delta_data).mark_bar(opacity=0.7, color="orange").encode(
            x=alt.X("bin_start:Q", 
                    title=f"Förändring i intensitet ({unit})",
                    scale=alt.Scale(nice=True)),
            x2=alt.X2("bin_end:Q"),
            y=alt.Y("count:Q", title="Antal nät"),
            tooltip=[
                alt.Tooltip("bin_start:Q", title="Från", format=".3f"),
                alt.Tooltip("bin_end:Q", title="Till", format=".3f"),
                alt.Tooltip("count:Q", title="Antal nät")
            ]
        ).properties(
            width=600,
            height=250,
            title=f"Fördelning av intensitetsförändring (WACC: {r_old:.2%} → {r_new:.2%})"
        )
        
        st.altair_chart(delta_chart, use_container_width=True)
    
    # Största vinnare och förlorare
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Störst förbättring (lägre intensitet):**")
        winners = valid_data.nsmallest(5, delta_col)[["DMU", delta_col]]
        winners_display = winners.copy()
        winners_display[delta_col] = winners_display[delta_col].apply(
            lambda x: _fmt_delta(x, unit=unit)
        )
        st.dataframe(winners_display, use_container_width=True, hide_index=True)
    
    with col2:
        st.write("**Störst försämring (högre intensitet):**")
        losers = valid_data.nlargest(5, delta_col)[["id_network", delta_col]]
        losers_display = losers.copy()
        losers_display[delta_col] = losers_display[delta_col].apply(
            lambda x: _fmt_delta(x, unit=unit)
        )
        st.dataframe(losers_display, use_container_width=True, hide_index=True)

def show_intensity_analysis(
    capcost_df: pd.DataFrame,
    dmu_volymer_df: pd.DataFrame,
    reconciliation_df: pd.DataFrame
) -> None:
    """
    Huvudfunktion för intensitetsanalys. Anropas från översikt.py Tab 4.
    
    Args:
        capcost_df: Kapitalkostnadsdata (capcost_a format)
        dmu_volymer_df: Volymdata (DMU, CU, MWh_total)
        reconciliation_df: Kopplingstabell (id_network -> DMU)
    """
    st.subheader("Intensitetsanalys - Kapitalkostnad per volym")
    st.caption("Analyserar kapitalkostnader relativt nätens storlek och aktivitetsnivå (tkr-basis, 2022 års prisnivå)")
    
    # Informationsruta om datastruktur
    with st.expander("ℹ️ Om datastruktur och nät-företag-mappning", expanded=False):
        st.markdown("""
        **Viktigt att förstå: Nät-nivå vs Företag-nivå**
        
        Denna analys kombinerar data från två olika system med olika granularitetsnivåer:
        
        **Kapitalbasdata (capcost_a):**
        - Granularitet: **Individuella elnät** (`id_network`)
        - Exempel: id_network 7, 160, 3035 = separata elnät
        - Källa: KENT-rapportering från elnätsföretag
        
        **Volymdata (effektivitetskrav):**
        - Granularitet: **Företag/koncerner** (`DMU` = Decision Making Unit)
        - Exempel: DMU 100, 101, 102 = olika företag/koncerner
        - Källa: DEA-effektivitetsanalys
        
        **Varför matchar inte ID-nummer?**
        - Ett företag (DMU) kan äga **flera nät** (id_network)
        - Vattenfall (en DMU) äger t.ex. 15+ olika nät
        - Mindre kommunala bolag har ofta 1:1-relation
        
        **Reconciliation-filen löser kopplingen:**
        - Mappar varje `id_network` → motsvarande `DMU`
        - Möjliggör analys av intensiteter på både nät- och företagsnivå
        - Säkerställer korrekt aggregering för stora elnätskoncerner
        """)
        
        st.info(
            "**Resultatintolkning:** En låg kr/MWh kan bero på hög volym (stora nät) "
            "eller låg kapitalkostnad (effektiva nät). Analysen hjälper till att särskilja dessa faktorer."
        )
    
    # Kontroller
    col1, col2 = st.columns([1, 2])
    
    with col1:
        year = _year_selector()
        intensity_metric = _intensity_metric_selector()
    
    with col2:
        show_scenario, r_new = _scenario_controls()
    
    # Merge och beräkna intensiteter
    try:
        merged_df, quality_report = merge_capcost_with_volumes(
            capcost_df, dmu_volymer_df, reconciliation_df, year=year
        )
        
        if len(merged_df) == 0:
            st.error("Ingen data efter sammanslagning. Kontrollera indata.")
            return
        
        df_with_intensities = calculate_intensities(merged_df)
        
    except Exception as e:
        st.error(f"Fel vid databearbetning: {e}")
        return
    
    # Kvalitetsrapport
    st.subheader("Datakvalitet")
    _render_merge_quality(quality_report)
    
    # Bestäm enhet baserat på vald metrik
    unit = "SEK/MWh" if intensity_metric == "sek_per_mwh" else "SEK/kund"
    
    # Statistisk översikt
    stats = compute_intensity_statistics(df_with_intensities, intensity_metric)
    _render_statistics_overview(stats, intensity_metric, unit)
    
    # Fördelningsanalys
    _render_distribution_chart(df_with_intensities, intensity_metric, unit)
    
    # Ranking
    top_networks, bottom_networks = create_intensity_ranking(
        df_with_intensities, intensity_metric, top_n=10
    )
    _render_ranking_tables(top_networks, bottom_networks, intensity_metric, unit)
    
    # Outlier-analys
    _render_outlier_analysis(df_with_intensities, intensity_metric, unit)
    
    # Scenario-analys (om aktiverad)
    if show_scenario and r_new is not None:
        try:
            df_scenario = apply_intensity_scenario(
                df_with_intensities, r_old=0.0453, r_new=r_new
            )
            _render_scenario_comparison(df_scenario, intensity_metric, unit, 0.0453, r_new)
            
        except Exception as e:
            st.error(f"Fel vid scenario-beräkning: {e}")
    
    # Detaljdata (expanderbar)
    with st.expander("🗃️ Detaljdata (alla DMU)"):
        display_cols = [
            "DMU", "MWh_total", "CU", 
            "capcost_sum", intensity_metric
        ]
        
        # Lägg till scenario-kolumner om aktiverat
        if show_scenario and r_new is not None:
            scenario_cols = [f"{intensity_metric}_new", f"delta_{intensity_metric}"]
            display_cols.extend(scenario_cols)
        
        detail_df = df_with_intensities[display_cols].dropna(subset=[intensity_metric])
        
        st.dataframe(
            detail_df,
            column_config={
                "DMU": "DMU",
                "MWh_total": st.column_config.NumberColumn("MWh", format="%.0f"),
                "CU": st.column_config.NumberColumn("Kunder", format="%.0f"),
                "capcost_sum": st.column_config.NumberColumn("Kapkostnad (tkr)", format="%.0f"),
                intensity_metric: st.column_config.NumberColumn(f"Intensitet ({unit})", format="%.1f")
            },
            use_container_width=True,
            hide_index=True
        )