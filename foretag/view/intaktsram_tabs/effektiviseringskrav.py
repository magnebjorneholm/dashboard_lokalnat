"""
foretag/view/intaktsram_tabs/effektiviseringskrav.py
Effektiviseringskrav-tab med tydligt flöde och OPEX/TOTEX-toggle
"""

import streamlit as st
import pandas as pd
from typing import Optional
from pathlib import Path
import json

from core.session_utils import ensure_org_dir


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
        st.caption("Visar baseline-värden (inget effektiviseringskrav applicerat)")
    
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
    
    # TILLGÄNGLIGA EXPORTS
    st.markdown("---")
    
    available_exports = list_available_effkrav_exports()
    
    if not available_exports.empty:
        available_exports['display'] = (
            available_exports['mean_effkrav'].apply(lambda x: f"{x:.2f}%") + 
            " - " + 
            available_exports['timestamp'].str[:10]
        )
        
        selected_display = st.selectbox(
            "Tillgängliga DEA-exports",
            options=available_exports['display'].tolist(),
            key="effkrav_export_selector"
        )
        
        selected_export = available_exports[available_exports['display'] == selected_display].iloc[0]
    else:
        st.info(
            "Inga DEA-exports hittades. Gå till DEA-modulen för att köra analys "
            "och exportera effektiviseringskrav."
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
                    method=selected_method
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
    
    # BREAKDOWN
    if is_modified and effkrav_mod.get('source') == 'effektiviseringskrav':
        st.markdown("---")
        show_effkrav_breakdown(entity_data, effkrav_mod)
    
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


def show_effkrav_breakdown(entity_data: pd.Series, effkrav_mod: dict):
    """
    Visar detaljerad breakdown av effektiviseringskrav-beräkning.
    Använder sparad beräkningsdata från calculate_ir_paverkbara_export().
    """
    st.write("**Värden:**")
    
    method = effkrav_mod.get('method', 'OPEX')
    
    last_calc = effkrav_mod.get('last_calculation')
    
    if last_calc is None:
        st.warning(
            "Beräkningsdata inte tillgänglig. "
            "Detta kan inträffa om scenariot inte har laddats korrekt."
        )
        return
    
    export_data = last_calc.get('export_data')
    metadata = last_calc.get('metadata')
    
    if export_data is None or export_data.empty:
        st.warning("Ingen beräkningsdata tillgänglig")
        return
    
    reid = entity_data['REId']
    entity_calc = export_data[export_data['REId'] == reid]
    
    if entity_calc.empty:
        st.warning(f"Ingen beräkningsdata hittades för REId {reid}")
        return
    
    row = entity_calc.iloc[0]
    
    baseline_4yr = row.get('Paverkbara_Baseline_4yr', 0)
    target_4yr = row.get('Paverkbara_Target', 0)
    reduction_total = row.get('Total_Reduction_tkr', 0)
    effkrav_pct = row.get('Effektiviseringskrav', 0)
    
    y2024_base = row.get('Y2024_baseline', 0)
    y2025_base = row.get('Y2025_baseline', 0)
    y2026_base = row.get('Y2026_baseline', 0)
    y2027_base = row.get('Y2027_baseline', 0)
    
    y2024_scn = row.get('Y2024_scenario', 0)
    y2025_scn = row.get('Y2025_scenario', 0)
    y2026_scn = row.get('Y2026_scenario', 0)
    y2027_scn = row.get('Y2027_scenario', 0)
    
    if method == 'OPEX':    
        # Årsvisa värden i tabell
        with st.expander("Påverkbara löpande kostnader efter avdrag för effektiviseringskrav"):
            yearly_data = pd.DataFrame({
                'År': [2024, 2025, 2026, 2027],
                'Nuvarande reglering (tkr)': [
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
                ]
            })

            st.dataframe(yearly_data, use_container_width=True, hide_index=True)

    else:
        st.write("**TOTEX-metod:** Effektiviseringskrav applicerat på OPEX + CAPEX")
        
        if 'CAPEX_periodsumma' in row:
            capex_total = row.get('CAPEX_periodsumma', 0)
            capex_per_year = row.get('CAPEX_arsbas', 0)
            
            baseline_opex_4yr = baseline_4yr - capex_total
            baseline_totex = baseline_4yr
            
            target_totex = target_4yr
            target_opex = target_totex - capex_total
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Innan avdrag (4 år):**")
                st.write(f"OPEX: {baseline_opex_4yr:,.0f} tkr".replace(",", " "))
                st.write(f"CAPEX: {capex_total:,.0f} tkr".replace(",", " "))
                st.write(f"**TOTEX:** {baseline_totex:,.0f} tkr".replace(",", " "))
                st.write(f"Effektiviseringskrav: {effkrav_pct*100:.2f}%")
            
            with col2:
                st.write("**Efter avdrag (4 år):**")
                st.write(f"TOTEX efter avdrag: {target_totex:,.0f} tkr".replace(",", " "))
                st.write(f"CAPEX (oförändrat): {capex_total:,.0f} tkr".replace(",", " "))
                st.write(f"**Nya OPEX:** {target_opex:,.0f} tkr".replace(",", " "))
                st.write(f"Total reduktion: {reduction_total:,.0f} tkr".replace(",", " "))
            
            capex_updated = entity_data.get('Uppdaterad_Kapitalkostnad', False)
            if capex_updated:
                st.info(
                    "Kapitalkostnad har uppdaterats från scenario. "
                    "OPEX har automatiskt omberäknats för att bibehålla TOTEX-krav."
                )
        else:
            st.warning("CAPEX-komponenter saknas i beräkningen")
    
    with st.expander("Avdrag för effektiviseringskrav (Beräknat som avdrag från medelvärdet)"):
        df_avdrag = pd.DataFrame({
            'År': [2024, 2025, 2026, 2027],
            'Inkrement (tkr)': [row[f'Inc_{y}_scn'] for y in [2024, 2025, 2026, 2027]],
            'Kumulativt avdrag (tkr)': [row[f'Avdrag_{y}_scn'] for y in [2024, 2025, 2026, 2027]]
        })
        st.dataframe(df_avdrag, use_container_width=True)
    
    with st.expander("Tekniska detaljer"):
        
        tech_params = {
            'Medelvärde 2018-2021 påverkbara kostnader': row.get('DT_exact', 0),
            'Justering där nätföretagets inte separerat yrkandet på vart och ett av åren 2018-2021 (2022 års prisnivå) (Δ)': row.get('Delta_exact', 0),
            'Årsbas (B)': row.get('B_exact', 0),
            'Nuvarande krav (e₀)': row.get('e_base_exact', 0),
            'Scenariokrav (e)': row.get('e_scn_exact', 0)
        }
        
        for param, value in tech_params.items():
            if value != 0 or param in ['e_baseline', 'e_scenario']:
                st.write(f"- {param}: {value:,.4f}".replace(",", " "))
        


def list_available_effkrav_exports() -> pd.DataFrame:
    """
    Listar tillgängliga effektiviseringskrav-exports för aktuell organisation.
    """
    export_dir = Path(ensure_org_dir("scenario/effektiviseringskrav/exports_to_ir"))
    
    if not export_dir.exists():
        return pd.DataFrame(columns=['filename', 'mean_effkrav', 'timestamp', 'filepath'])
    
    exports = []
    
    for parquet_file in sorted(export_dir.glob("ir_effkrav_*.parquet"), reverse=True):
        json_file = parquet_file.with_suffix('.json')
        
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                mean_effkrav = metadata.get('mean_effkrav_pct', 0)
                timestamp = metadata.get('export_timestamp', 'Unknown')
                
                exports.append({
                    'filename': parquet_file.name,
                    'mean_effkrav': mean_effkrav,
                    'timestamp': timestamp,
                    'filepath': str(parquet_file)
                })
            except Exception:
                continue
    
    return pd.DataFrame(exports)


def apply_effkrav_scenario(
    scenario_file: str, 
    entity_dmu: int, 
    df_company: pd.DataFrame,
    method: str = 'OPEX'
) -> bool:
    """
    Applicerar effektiviseringskrav-scenario på aktivt scenario.
    """
    try:
        dea_export = pd.read_parquet(scenario_file)
        
        required_cols = ['DMU', 'REId', 'Effkrav_proc']
        missing_cols = [col for col in required_cols if col not in dea_export.columns]
        
        if missing_cols:
            st.error(f"Export saknar kolumner: {missing_cols}")
            return False
        
        dea_result = dea_export[dea_export['DMU'] == entity_dmu].copy()
        
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
            'import_timestamp': pd.Timestamp.now().isoformat()
        }
        
        st.session_state.scenario_data['component_sources']['paverkbara'] = 'effektiviseringskrav'
        
        return True
        
    except Exception as e:
        st.error(f"Fel vid import: {e}")
        import traceback
        st.error(traceback.format_exc())
        return False