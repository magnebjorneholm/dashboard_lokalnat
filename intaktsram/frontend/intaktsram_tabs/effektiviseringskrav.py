"""
foretag/view/intaktsram_tabs/effektiviseringskrav.py
Effektiviseringskrav-tab med tydligt flöde och OPEX/TOTEX-toggle
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional
from pathlib import Path
import json

from core.session_utils import ensure_org_dir
from core.effektiviseringskrav_calculations import calculate_effkrav_for_dataframe


def show_effektiviseringskrav_tab(entity_data: pd.Series, df_company: pd.DataFrame):
    """
    Visar effektiviseringskrav-tab med tydligt flöde.
    """
    
    st.subheader("Effektiviseringskrav")
    
    is_modified = entity_data.get('Uppdaterad_Paverkbara', False)
    källa = entity_data.get('Källa_Paverkbara', 'Baseline')
    
    scenario_data = st.session_state.get('scenario_data', {})
    modifications = scenario_data.get('modifications', {})
    effkrav_mod = modifications.get('paverkbara', {})
    
    if is_modified and effkrav_mod.get('source') == 'effektiviseringskrav':
        method = effkrav_mod.get('method', 'OPEX')
        dea_result = effkrav_mod.get('dea_result')
        
        if dea_result is not None and not dea_result.empty:
            effkrav_pct = dea_result.iloc[0].get('Effkrav_proc', 0) * 100
            st.info(f"Effektiviseringskrav aktivt: **{effkrav_pct:.2f}%** applicerat på **{method}**")
        else:
            st.info(f"Effektiviseringskrav aktivt (metod: **{method}**)")
        
        if källa and källa != 'Baseline':
            st.caption(f"Källa: {källa}")
    else:
        st.caption("Visar referensperiod (inget effektiviseringskrav applicerat)")
    
    st.markdown("---")
    
    # METRICS
    paverkbara = entity_data.get('Paverkbara_Kostnader', 0)
    baseline_paverkbara = entity_data.get('Paverkbara_Kostnader_Baseline', paverkbara)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        delta_pav = None
        if is_modified and baseline_paverkbara > 0:
            delta_pav = paverkbara - baseline_paverkbara
            delta_pct = (delta_pav / baseline_paverkbara * 100)
        
        st.metric(
            "Påverkbara kostnader",
            f"{paverkbara:,.0f} tkr".replace(",", " "),
            delta=f"{delta_pct:.1f}%" if delta_pav else None
        )
    
    with col2:
        if baseline_paverkbara > 0:
            andel = (paverkbara / entity_data.get('Intaktsram_Total', 1) * 100)
            st.metric(
                "Andel av intäktsram",
                f"{andel:.1f}%"
            )
    
    with col3:
        if is_modified and delta_pav:
            st.metric(
                "Reduktion",
                f"{abs(delta_pav):,.0f} tkr".replace(",", " "),
                delta=f"{delta_pav:,.0f} tkr".replace(",", " ")
            )
    
    # APPLICERA EFFEKTIVISERINGSKRAV PÅ
    st.markdown("---")
    st.write("**Applicera effektiviseringskrav på:**")
    
    current_method = effkrav_mod.get('method', 'OPEX') if effkrav_mod else 'OPEX'
    
    col_toggle, col_info = st.columns([1, 2])
    
    with col_toggle:
        selected_method = st.radio(
            "Metod",
            options=['OPEX', 'TOTEX'],
            index=0 if current_method == 'OPEX' else 1,
            key="effkrav_method_toggle",
            help=(
                "OPEX: Krav appliceras endast på påverkbara kostnader\n"
                "TOTEX: Krav appliceras på påverkbara + kapitalkostnad"
            )
        )
    
    with col_info:
        if selected_method == 'TOTEX':
            st.info(
                "**TOTEX-metod:** Effektiviseringskravet appliceras på summan av "
                "påverkbara kostnader och kapitalkostnad. Om kapitalkostnad ändras "
                "omberäknas påverkbara automatiskt."
            )
        else:
            st.info(
                "**OPEX-metod:** Effektiviseringskravet appliceras endast på "
                "påverkbara kostnader. Kapitalkostnad påverkar inte beräkningen."
            )
    
    if is_modified and selected_method != current_method:
        if st.button("Tillämpa metodbyte", type="primary", use_container_width=True):
            if 'paverkbara' not in modifications:
                modifications['paverkbara'] = {}
            modifications['paverkbara']['method'] = selected_method
            st.success(f"Metod ändrad till {selected_method}")
            st.rerun()
    
    if not is_modified:
        st.caption(
            f"Metod **{selected_method}** kommer användas när du importerar effektiviseringskrav."
        )
    
    # BERÄKNINGSPARAMETRAR
    st.markdown("---")
    st.write("**Beräkningsparametrar för effektiviseringskrav**")
    
    # Hämta nuvarande parametrar från effkrav_mod eller defaults
    current_trunk_min = effkrav_mod.get('trunkering_min', 0.162416)
    current_trunk_max = effkrav_mod.get('trunkering_max', 0.3)
    current_outlier_krav = effkrav_mod.get('outlier_krav', 0.01)
    
    col_param1, col_param2, col_param3 = st.columns(3)
    
    with col_param1:
        trunk_min = st.slider(
            "Minsta trunkering",
            0.0, 0.3, current_trunk_min,
            step=0.005,
            key="effkrav_trunk_min",
            help="Lägsta gräns för hur mycket ineffektivitet som får påverka kravet"
        )
    
    with col_param2:
        trunk_max = st.slider(
            "Högsta trunkering",
            0.1, 0.5, current_trunk_max,
            step=0.005,
            key="effkrav_trunk_max",
            help="Högsta gräns för hur mycket ineffektivitet som får påverka kravet"
        )
    
    with col_param3:
        outlier_krav_pct = st.slider(
            "Krav för outliers (%)",
            1.0, 1.82, current_outlier_krav * 100,
            step=0.01,
            key="effkrav_outlier_krav",
            help="Fast årligt effektiviseringskrav för företag klassade som outliers i DEA"
        )
    
    st.caption("Outliers identifieras i DEA-modulen baserat på supereffektivitet")
    
    # Visa om parametrar har ändrats
    params_changed = (
        is_modified and (
            trunk_min != current_trunk_min or
            trunk_max != current_trunk_max or
            outlier_krav_pct / 100 != current_outlier_krav
        )
    )
    
    if params_changed:
        st.warning("⚠️ Parametrar har ändrats. Klicka 'Omberäkna med nya parametrar' för att tillämpa.")
        if st.button("Omberäkna med nya parametrar", type="primary", use_container_width=True):
            recalculate_effkrav_with_new_params(
                effkrav_mod=effkrav_mod,
                trunk_min=trunk_min,
                trunk_max=trunk_max,
                outlier_krav=outlier_krav_pct / 100,
                method=selected_method,
                df_company=df_company
            )
            st.success("Effektiviseringskrav omberäknat med nya parametrar!")
            st.rerun()
    
    # TILLGÄNGLIGA EXPORTS
    st.markdown("---")
    
    available_exports = list_available_effkrav_exports()
    
    if not available_exports.empty:
        available_exports['display'] = (
            "Eff: " +
            available_exports['mean_efficiency'].apply(lambda x: f"{x:.3f}") + 
            " | Outliers: " + 
            available_exports['outlier_count'].astype(str) +
            " | " + 
            available_exports['timestamp'].str[:10]
        )
        
        selected_display = st.selectbox(
            "Tillgängliga DEA-exports",
            options=available_exports['display'].tolist(),
            key="effkrav_export_selector",
            help="Välj en export baserat på medeleffektivitet, antal outliers och datum"
        )
        
        selected_export = available_exports[available_exports['display'] == selected_display].iloc[0]
    else:
        st.info(
            "Inga DEA-exports hittades. Gå till DEA-modulen för att köra analys "
            "och exportera effektivitetsvärden."
        )
        selected_export = None
    
    # KNAPPAR
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Importera från DEA", use_container_width=True, disabled=available_exports.empty):
            if not st.session_state.current_scenario_name:
                st.error("Skapa ett scenario först innan du importerar data")
            elif selected_export is not None:
                success = apply_effkrav_scenario(
                    scenario_file=selected_export['filepath'],
                    entity_dmu=entity_data.get('DMU'),
                    df_company=df_company,
                    method=selected_method,
                    trunk_min=trunk_min,
                    trunk_max=trunk_max,
                    outlier_krav=outlier_krav_pct / 100
                )
                if success:
                    st.success(f"Effektiviseringskrav importerat med {selected_method}-metod!")
                    st.rerun()
                else:
                    st.error("Kunde inte importera scenario")
    
    with col2:
        if st.button("Till DEA-analys", use_container_width=True, type="primary"):
            st.session_state['ir_context'] = {
                'from_page': 'intaktsram_ny',
                'reid': entity_data.get('REId'),
                'dmu': entity_data.get('DMU'),
                'scenario': st.session_state.get('current_scenario_name', ''),
                'fokus': 'effektiviseringskrav'
            }
            st.switch_page("pages/foretag/foretag_effektivitet.py")
    
    # ÅRSVISA PÅVERKBARA KOSTNADER - VISAS ALLTID
    st.markdown("---")
    show_yearly_paverkbara_table(entity_data, effkrav_mod)
    
    # INFO-EXPANDER
    if not is_modified:
        st.markdown("---")
        with st.expander("Om effektiviseringskrav"):
            st.write("""
            **Effektiviseringskrav** bestäms genom DEA-analys (Data Envelopment Analysis) 
            där ditt företag jämförs med andra lokalnätföretag.
            
            **Två metoder:**
            - **OPEX:** Kravet appliceras endast på påverkbara kostnader
            - **TOTEX:** Kravet appliceras på summan av påverkbara kostnader och kapitalkostnad
            
            **Processen:**
            1. Välj metod (OPEX/TOTEX) ovan
            2. Gå till DEA-modulen (knapp ovan)
            3. Kör DEA-analys och exportera effektiviseringskrav
            4. Kom tillbaka hit och importera från selectbox ovan
            
            För mer information, se DEA-modulen.
            """)


def show_yearly_paverkbara_table(entity_data: pd.Series, effkrav_mod: dict):
    """
    Visar tabell med årsvisa påverkbara kostnader.
    Visas alltid, oavsett om scenario är aktivt eller inte.
    """
    last_calc = effkrav_mod.get('last_calculation') if effkrav_mod else None
    
    # Om vi har beräkningsdata från scenario
    if last_calc is not None:
        export_data = last_calc.get('export_data')
        
        if export_data is not None and not export_data.empty:
            reid = entity_data['REId']
            entity_calc = export_data[export_data['REId'] == reid]
            
            if not entity_calc.empty:
                row = entity_calc.iloc[0]
                
                # Hämta årsvisa värden
                y2024_base = row.get('Y2024_baseline', 0)
                y2025_base = row.get('Y2025_baseline', 0)
                y2026_base = row.get('Y2026_baseline', 0)
                y2027_base = row.get('Y2027_baseline', 0)
                
                y2024_scn = row.get('Y2024_scenario', 0)
                y2025_scn = row.get('Y2025_scenario', 0)
                y2026_scn = row.get('Y2026_scenario', 0)
                y2027_scn = row.get('Y2027_scenario', 0)
                
                # Bygg komplett tabell med alla kolumner
                with st.expander("Årsvisa påverkbara kostnader efter avdrag"):
                    yearly_data = pd.DataFrame({
                        'År': [2024, 2025, 2026, 2027],
                        'Ei baseline (tkr)': [
                            f"{y2024_base:,.0f}".replace(",", " "),
                            f"{y2025_base:,.0f}".replace(",", " "),
                            f"{y2026_base:,.0f}".replace(",", " "),
                            f"{y2027_base:,.0f}".replace(",", " ")
                        ],
                        'Scenario (tkr)': [
                            f"{y2024_scn:,.0f}".replace(",", " "),
                            f"{y2025_scn:,.0f}".replace(",", " "),
                            f"{y2026_scn:,.0f}".replace(",", " "),
                            f"{y2027_scn:,.0f}".replace(",", " ")
                        ],
                        'Skillnad (tkr)': [
                            f"{(y2024_base - y2024_scn):+,.0f}".replace(",", " "),
                            f"{(y2025_base - y2025_scn):+,.0f}".replace(",", " "),
                            f"{(y2026_base - y2026_scn):+,.0f}".replace(",", " "),
                            f"{(y2027_base - y2027_scn):+,.0f}".replace(",", " ")
                        ],
                        'Inkrement (tkr)': [
                            f"{row.get('Inc_2024_scn', 0):,.0f}".replace(",", " "),
                            f"{row.get('Inc_2025_scn', 0):,.0f}".replace(",", " "),
                            f"{row.get('Inc_2026_scn', 0):,.0f}".replace(",", " "),
                            f"{row.get('Inc_2027_scn', 0):,.0f}".replace(",", " ")
                        ],
                        'Kumulativt avdrag (tkr)': [
                            f"{row.get('Avdrag_2024_scn', 0):,.0f}".replace(",", " "),
                            f"{row.get('Avdrag_2025_scn', 0):,.0f}".replace(",", " "),
                            f"{row.get('Avdrag_2026_scn', 0):,.0f}".replace(",", " "),
                            f"{row.get('Avdrag_2027_scn', 0):,.0f}".replace(",", " ")
                        ]
                    })
                    
                    st.dataframe(yearly_data, use_container_width=True, hide_index=True)
                    st.caption("Alla värden är för perioden 2024-2027 (4 år totalt)")
                return
    
    # Om inget scenario: visa bara info
    st.info("Importera effektiviseringskrav från DEA för att se årsvisa värden")
    

def list_available_effkrav_exports() -> pd.DataFrame:
    """
    Listar tillgängliga effektivitetsvärde-exports för aktuell organisation.
    """
    export_dir = Path(ensure_org_dir("scenario/effektiviseringskrav/exports_to_ir"))
    
    if not export_dir.exists():
        return pd.DataFrame(columns=['filename', 'mean_efficiency', 'outlier_count', 'timestamp', 'filepath'])
    
    exports = []
    
    for parquet_file in sorted(export_dir.glob("ir_effkrav_*.parquet"), reverse=True):
        json_file = parquet_file.with_suffix('.json')
        
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                mean_eff = metadata.get('mean_efficiency', 0)
                outliers = metadata.get('outlier_count', 0)
                timestamp = metadata.get('export_timestamp', 'Unknown')
                
                exports.append({
                    'filename': parquet_file.name,
                    'mean_efficiency': mean_eff,
                    'outlier_count': outliers,
                    'timestamp': timestamp,
                    'filepath': str(parquet_file)
                })
            except Exception:
                continue
    
    return pd.DataFrame(exports)


def recalculate_effkrav_with_new_params(
    effkrav_mod: dict,
    trunk_min: float,
    trunk_max: float,
    outlier_krav: float,
    method: str,
    df_company: pd.DataFrame
):
    """
    Omberäknar effektiviseringskrav med nya parametrar.
    Använder befintlig dea_result från effkrav_mod.
    """
    if not effkrav_mod or 'dea_result' not in effkrav_mod:
        st.error("Ingen DEA-data att omberäkna")
        return
    
    dea_result = effkrav_mod['dea_result']
    
    # Beräkna om Effkrav_proc med nya parametrar
    dea_recalc = calculate_effkrav_for_dataframe(
        dea_result,
        potential_col='potential',
        outlier_col='is_outlier',
        trunkering_min=trunk_min,
        trunkering_max=trunk_max,
        outlier_krav=outlier_krav
    )
    
    # Uppdatera effkrav_mod med nya värden
    effkrav_mod['dea_result'] = dea_recalc
    effkrav_mod['trunkering_min'] = trunk_min
    effkrav_mod['trunkering_max'] = trunk_max
    effkrav_mod['outlier_krav'] = outlier_krav
    effkrav_mod['method'] = method


def apply_effkrav_scenario(
    scenario_file: str, 
    entity_dmu: int, 
    df_company: pd.DataFrame,
    method: str = 'OPEX',
    trunk_min: float = 0.162416,
    trunk_max: float = 0.3,
    outlier_krav: float = 0.01
) -> bool:
    """
    Applicerar effektiviseringskrav-scenario på aktivt scenario.
    Beräknar Effkrav_proc från potential baserat på användarens parametrar.
    """
    try:
        dea_export = pd.read_parquet(scenario_file)
        
        required_cols = ['DMU', 'REId', 'potential', 'Effektivitet', 'Supereffektivitet', 'is_outlier']
        missing_cols = [col for col in required_cols if col not in dea_export.columns]
        
        if missing_cols:
            st.error(f"Export saknar kolumner: {missing_cols}")
            return False
        
        # Beräkna Effkrav_proc för alla företag med nya parametrar
        dea_with_krav = calculate_effkrav_for_dataframe(
            dea_export,
            potential_col='potential',
            outlier_col='is_outlier',
            trunkering_min=trunk_min,
            trunkering_max=trunk_max,
            outlier_krav=outlier_krav
        )
        
        dea_result = dea_with_krav[dea_with_krav['DMU'] == entity_dmu].copy()
        
        if dea_result.empty:
            st.warning(f"Ingen data hittades för DMU {entity_dmu} i exporten")
            return False
        
        json_file = Path(scenario_file).with_suffix('.json')
        metadata = {}
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        if 'scenario_data' not in st.session_state:
            return False
        
        st.session_state.scenario_data['modifications']['paverkbara'] = {
            'source': 'effektiviseringskrav',
            'method': method,
            'dea_result': dea_result,
            'metadata': metadata,
            'trunkering_min': trunk_min,
            'trunkering_max': trunk_max,
            'outlier_krav': outlier_krav,
            'import_timestamp': pd.Timestamp.now().isoformat()
        }
        
        st.session_state.scenario_data['component_sources']['paverkbara'] = 'effektiviseringskrav'
        
        return True
        
    except Exception as e:
        st.error(f"Fel vid import: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False