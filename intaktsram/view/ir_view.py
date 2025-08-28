import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

from intaktsram.app.data_loader import (
    load_dmu_mapping, 
    detect_scenario_updates,
    load_scenario_data,
    calculate_intaktsram
)


def show_ir_dekomposition_view(df_baseline: pd.DataFrame):
    """Huvudvy för intäktsram-dekomposition med waterfall och scenario-hantering."""
    
    # === SCENARIO-HANTERING ===
    initialize_session_state()
    
    # Sidebar för scenario-kontroller
    st.sidebar.header("🔧 Scenario-hantering")
    
    scenario_name = st.sidebar.text_input(
        "Scenario-namn", 
        value=st.session_state.current_scenario_name,
        placeholder="t.ex. 'WACC 5.2% + Strängare DEA'"
    )
    
    # Vertikala knappar (3×1 layout)
    if st.sidebar.button("🆕 Nytt scenario", use_container_width=True):
        create_new_scenario(scenario_name, df_baseline)
    
    if st.sidebar.button("📁 Ladda scenario", use_container_width=True):
        st.session_state.show_scenario_loader = True
    
    if st.sidebar.button("🔄 Återställ allt", use_container_width=True):
        reset_all_components()
    
    # Visa scenario-loader om aktiverad
    if st.session_state.show_scenario_loader:
        show_scenario_loader()
    
    # Visa aktuellt scenario
    if st.session_state.current_scenario_name:
        st.sidebar.success(f"Aktivt scenario: **{st.session_state.current_scenario_name}**")
    else:
        st.sidebar.info("Inget scenario aktivt - arbetar med baseline")
    
    # === FÖRETAGS-/NÄTVAL ===
    st.sidebar.header("🏢 Val av företag/nät")
    
    # Hämta working dataframe (kommer redan med DMU-mappning från baseline)
    df_working = get_working_dataframe(df_baseline)
    
    # Skapa dropdown-alternativ med företagsnamn (DMU)
    entity_options = []
    entity_mapping = {}
    
    # Använd alltid REId som primär nyckel (internt)
    for reid in sorted(df_working['REId'].unique()):
        row = df_working[df_working['REId'] == reid].iloc[0]
        företag = row.get('Företag', 'Okänt företag')
        dmu = row.get('DMU')
        
        # Format: "Företagsnamn (DMU)"
        if pd.notna(dmu):
            display_name = f"{företag} ({int(dmu)})"
        else:
            display_name = f"{företag} (REId: {reid})"
        
        entity_options.append(display_name)
        entity_mapping[display_name] = reid
    
    selected_display = st.sidebar.selectbox(
        "Välj företag/nät",
        entity_options
    )
    
    # Hämta REId från mapping
    selected_entity = entity_mapping[selected_display]
    entity_col = 'REId'
    
    # Filtrera data för valt företag/nät
    entity_data = df_working[df_working[entity_col] == selected_entity].iloc[0]
    
    # === HUVUDVY ===
    show_main_waterfall_view(entity_data, selected_entity, entity_col)
    
    # === KOMPONENT-KONTROLLER ===
    show_component_controls(entity_data)
    
    # === EXPORT ===
    show_export_section(df_working)


def initialize_session_state():
    """Initialiserar session state för scenario-hantering."""
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = {}
    
    if 'current_scenario_name' not in st.session_state:
        st.session_state.current_scenario_name = ""
    
    if 'scenario_data' not in st.session_state:
        st.session_state.scenario_data = {}
    
    if 'show_scenario_loader' not in st.session_state:
        st.session_state.show_scenario_loader = False


def create_new_scenario(name: str, baseline_df: pd.DataFrame):
    """Skapar ett nytt scenario."""
    if not name.strip():
        st.sidebar.error("Scenario-namn får inte vara tomt")
        return
    
    st.session_state.current_scenario_name = name.strip()
    st.session_state.scenario_data = {
        'baseline': baseline_df.copy(),
        'modifications': {},
        'created': datetime.now(),
        'component_sources': {
            'paverkbara': 'baseline',
            'kapitalkostnad': 'baseline'
        }
    }
    st.sidebar.success(f"Nytt scenario '{name}' skapat!")
    st.rerun()


def reset_all_components():
    """Återställer alla komponenter till baseline."""
    if st.session_state.current_scenario_name:
        st.session_state.scenario_data['component_sources'] = {
            'paverkbara': 'baseline',
            'kapitalkostnad': 'baseline'
        }
        st.session_state.scenario_data['modifications'] = {}
        st.sidebar.success("Alla komponenter återställda till baseline")
        st.rerun()


def get_working_dataframe(baseline_df: pd.DataFrame) -> pd.DataFrame:
    """Hämtar aktuell arbetsdataframe (baseline eller scenario)."""
    if not st.session_state.current_scenario_name or 'scenario_data' not in st.session_state:
        return baseline_df.copy()
    
    # Börja med baseline
    working_df = st.session_state.scenario_data['baseline'].copy()
    
    # Applicera scenario-modifikationer
    modifications = st.session_state.scenario_data.get('modifications', {})
    
    for component, mod_data in modifications.items():
        if 'values' not in mod_data:
            continue
        
        if component == 'paverkbara':
            # REId-baserade modifikationer (som tidigare)
            for reid, new_value in mod_data['values'].items():
                mask = working_df['REId'] == reid
                working_df.loc[mask, 'Paverkbara_Kostnader'] = new_value
                working_df.loc[mask, 'Källa_Paverkbara'] = f"Scenario ({mod_data.get('source', 'manual')})"
                working_df.loc[mask, 'Uppdaterad_Paverkbara'] = True
        
        elif component == 'kapitalkostnad':
            # Kolla om det är DMU-baserat eller REId-baserat
            merge_on = mod_data.get('merge_on', 'REId')
            
            for entity_key, new_values in mod_data['values'].items():
                if merge_on == 'DMU':
                    # DMU-baserade modifikationer från kapitalbas
                    mask = working_df['DMU'] == float(entity_key)
                else:
                    # REId-baserade modifikationer (manuella)
                    mask = working_df['REId'] == entity_key
                
                if mask.any():
                    # Uppdatera värden
                    if isinstance(new_values, dict):
                        # Detaljerade komponenter
                        if 'avskrivningar' in new_values:
                            working_df.loc[mask, 'Avskrivningar'] = new_values['avskrivningar']
                        if 'avkastning' in new_values:
                            working_df.loc[mask, 'Avkastning'] = new_values['avkastning']
                        if 'total' in new_values:
                            working_df.loc[mask, 'Kapitalkostnad_Total'] = new_values['total']
                        # Om vi har både avskrivning och avkastning, beräkna total
                        elif 'avkastning' in new_values and 'avskrivningar' in new_values:
                            working_df.loc[mask, 'Kapitalkostnad_Total'] = (
                                new_values['avskrivningar'] + new_values['avkastning']
                            )
                    else:
                        # Enkel skalär för total kapitalkostnad
                        working_df.loc[mask, 'Kapitalkostnad_Total'] = new_values
                    
                    # Uppdatera metadata
                    working_df.loc[mask, 'Källa_Kapitalkostnad'] = f"Scenario ({mod_data.get('source', 'manual')})"
                    working_df.loc[mask, 'Uppdaterad_Kapitalkostnad'] = True
    
    # Omberäkna total intäktsram
    working_df = calculate_intaktsram(working_df)
    
    return working_df


def show_main_waterfall_view(entity_data: pd.Series, selected_entity: str, entity_col: str):
    """Visar huvudvyn med waterfall-chart för valt företag."""
    
    st.header(f"📊 Intäktsram dekomposition: {selected_entity}")
    
    # Kontrollera om vi har separerade kapitalkostnad-komponenter
    has_detailed_capital = all(col in entity_data.index for col in ['Avskrivningar', 'Avkastning'])
    
    if has_detailed_capital:
        # Detaljerad vy med separerade kapitalkostnader
        components = [
            ('Påverkbara kostnader', entity_data.get('Paverkbara_Kostnader', 0)),
            ('Opåverkbara kostnader', entity_data.get('Opaverkbara_Kostnader', 0)), 
            ('Flexibilitetstjänster', entity_data.get('Flexibilitetstjanster', 0)),
            ('Avbrottsersättning 12-24h', entity_data.get('Avbrottsersattning_12_24h', 0)),
            ('Avskrivningar', entity_data.get('Avskrivningar', 0)),
            ('Avkastning', entity_data.get('Avkastning', 0))
        ]
        st.caption("Kapitalkostnad uppdelad i: Avskrivningar (opåverkad av WACC) + Avkastning (påverkad av WACC)")
    else:
        # Enkel vy med total kapitalkostnad
        components = [
            ('Påverkbara kostnader', entity_data.get('Paverkbara_Kostnader', 0)),
            ('Opåverkbara kostnader', entity_data.get('Opaverkbara_Kostnader', 0)), 
            ('Flexibilitetstjänster', entity_data.get('Flexibilitetstjanster', 0)),
            ('Avbrottsersättning 12-24h', entity_data.get('Avbrottsersattning_12_24h', 0)),
            ('Kapitalkostnad', entity_data.get('Kapitalkostnad_Total', 0))
        ]
        st.caption("Kapitalkostnad som total (avskrivning + avkastning)")
    
    # Skapa waterfall-chart
    fig = create_waterfall_chart(components, entity_data, detailed_capital=has_detailed_capital)
    st.plotly_chart(fig, use_container_width=True)
    
    # Komponent-tabell under grafen
    show_component_table(entity_data, components, has_detailed_capital)


def create_waterfall_chart(components: List[tuple], entity_data: pd.Series, detailed_capital: bool = False) -> go.Figure:
    """Skapar waterfall-chart för intäktsram-komponenter."""
    
    labels = [comp[0] for comp in components] + ['Total Intäktsram']
    values = [comp[1] for comp in components]
    total_calculated = sum(values)
    
    # Färger anpassade för detaljerad vy
    if detailed_capital:
        # 6 komponenter: påverkbara, opåverkbara, flex, avbrott, avskrivning, avkastning
        colors = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral', 'lightsteelblue', 'lightpink']
    else:
        # 5 komponenter: standardfärger
        colors = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral', 'lightgray']
    
    fig = go.Figure()
    
    # Waterfall bars
    fig.add_trace(go.Waterfall(
        name="Intäktsram komponenter",
        orientation="v",
        measure=["relative"] * len(components) + ["total"],
        x=labels,
        textposition="outside",
        text=[f"{val:,.0f}" for val in values] + [f"{total_calculated:,.0f}"],
        y=values + [0],  # Sista värdet blir total automatiskt
        connector={"line":{"color":"rgb(63, 63, 63)"}},
        increasing={"marker":{"color":"lightblue"}},
        decreasing={"marker":{"color":"lightcoral"}},
        totals={"marker":{"color":"darkblue"}}
    ))
    
    title_suffix = "- Kapitalkostnad uppdelad" if detailed_capital else ""
    fig.update_layout(
        title=f"Intäktsram dekomposition (tkr, 2022 års prisnivå) {title_suffix}",
        showlegend=False,
        height=500,
        xaxis_title="Komponenter",
        yaxis_title="Belopp (tkr)",
        yaxis_tickformat=",",
    )
    
    return fig


def show_component_table(entity_data: pd.Series, components: List[tuple], has_detailed_capital: bool = False):
    """Visar detaljerad komponent-tabell."""
    
    st.subheader("📋 Komponent-detaljer")
    
    # Skapa tabell-data
    table_data = []
    baseline_total = entity_data.get('Intaktsram_Total', 0)
    
    for name, value in components:
        # Bestäm källa och uppdaterad-status
        if 'påverkbara' in name.lower():
            källa = entity_data.get('Källa_Paverkbara', 'Baseline')
            uppdaterad = entity_data.get('Uppdaterad_Paverkbara', False)
            # Hämta baseline-värde för delta-beräkning
            baseline_key = 'Paverkbara_Kostnader_Baseline'
            baseline_value = entity_data.get(baseline_key, value)  # Fallback till current om baseline saknas
        elif any(term in name.lower() for term in ['kapital', 'avskrivning', 'avkastning']):
            källa = entity_data.get('Källa_Kapitalkostnad', 'Baseline') 
            uppdaterad = entity_data.get('Uppdaterad_Kapitalkostnad', False)
            # Bestäm baseline-key baserat på komponent
            if 'avskrivning' in name.lower():
                baseline_key = 'Avskrivningar_Baseline'
            elif 'avkastning' in name.lower():
                baseline_key = 'Avkastning_Baseline'
            else:
                baseline_key = 'Kapitalkostnad_Total_Baseline'
            baseline_value = entity_data.get(baseline_key, value)
        else:
            källa = 'Baseline'
            uppdaterad = False
            baseline_value = value
        
        # Beräkna delta och formatera uppdaterad-kolumn
        if uppdaterad and baseline_value != value:
            delta = value - baseline_value
            delta_pct = (delta / baseline_value * 100) if baseline_value != 0 else 0
            uppdaterad_text = f"✅ Δ {delta:+,.0f} ({delta_pct:+.1f}%)"
        else:
            uppdaterad_text = '✅' if uppdaterad else '➖'
        
        table_data.append({
            'Komponent': name,
            'Belopp (tkr)': f"{value:,.0f}",
            'Källa': källa,
            'Uppdaterad': uppdaterad_text
        })
    
    # Total-rad
    total_calculated = sum([comp[1] for comp in components])
    delta = total_calculated - baseline_total if baseline_total > 0 else 0
    delta_pct = (delta / baseline_total * 100) if baseline_total > 0 else 0
    
    table_data.append({
        'Komponent': '**TOTAL INTÄKTSRAM**',
        'Belopp (tkr)': f"**{total_calculated:,.0f}**",
        'Källa': 'Beräknad',
        'Uppdaterad': f"Δ {delta:+,.0f} ({delta_pct:+.1f}%)" if abs(delta) > 0 else '➖'
    })
    
    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True)


def show_component_controls(entity_data: pd.Series):
    """Visar kontroller för att uppdatera komponenter."""
    
    st.sidebar.header("🔧 Uppdatera komponenter")
    
    if not st.session_state.current_scenario_name:
        st.sidebar.info("Skapa ett scenario för att kunna uppdatera komponenter")
        return
    
    # Detect scenario updates från andra sektioner  
    scenario_updates = detect_scenario_updates()
    
    # Visa tillgängliga scenarier kompakt
    st.sidebar.write("**Tillgängliga scenarier:**")
    for key, value in scenario_updates.items():
        status = "✅" if value else "❌"
        st.sidebar.caption(f"{status} {key}")
    
    # Påverkbara kostnader
    st.sidebar.subheader("💰 Påverkbara kostnader")
    if scenario_updates['effektiviseringskrav']:
        if st.sidebar.button("🔥 Hämta från Effektiviseringskrav"):
            update_component_from_scenario('paverkbara', 'effektiviseringskrav', scenario_updates['effektiviseringskrav'])
    
    # Manuell uppdatering
    current_paverkbara = entity_data.get('Paverkbara_Kostnader', 0)
    new_paverkbara = st.sidebar.number_input(
        "Ny nivå (tkr)",
        value=float(current_paverkbara),
        key="manual_paverkbara"
    )
    if st.sidebar.button("Uppdatera manuellt", key="update_paverkbara"):
        update_component_manual('paverkbara', entity_data['REId'], new_paverkbara)
    
    # Kapitalkostnad  
    st.sidebar.subheader("🗂️ Kapitalkostnad")
    if scenario_updates['kapitalbas']:
        if st.sidebar.button("🔥 Hämta från Kapitalbas"):
            update_component_from_scenario('kapitalkostnad', 'kapitalbas', scenario_updates['kapitalbas'])
    else:
        st.sidebar.info("Ingen kapitalbas-export hittades")
    
    # Manuell uppdatering - stöd för separerade komponenter
    has_detailed_capital = all(col in entity_data.index for col in ['Avskrivningar', 'Avkastning'])
    
    if has_detailed_capital:
        # Visa separata kontroller för avskrivning och avkastning
        current_avskrivning = entity_data.get('Avskrivningar', 0)
        current_avkastning = entity_data.get('Avkastning', 0)
        
        new_avskrivning = st.sidebar.number_input(
            "Avskrivningar (tkr)", 
            value=float(current_avskrivning),
            key="manual_avskrivning"
        )
        new_avkastning = st.sidebar.number_input(
            "Avkastning (tkr)", 
            value=float(current_avkastning),
            key="manual_avkastning"
        )
        
        if st.sidebar.button("Uppdatera komponenter", key="update_detailed_kapital"):
            update_component_manual_detailed('kapitalkostnad', entity_data['REId'], 
                                           new_avskrivning, new_avkastning)
    else:
        # Enkel total kapitalkostnad
        current_kapital = entity_data.get('Kapitalkostnad_Total', 0)
        new_kapital = st.sidebar.number_input(
            "Ny nivå (tkr)", 
            value=float(current_kapital),
            key="manual_kapital"
        )
        if st.sidebar.button("Uppdatera manuellt", key="update_kapital"):
            update_component_manual('kapitalkostnad', entity_data['REId'], new_kapital)
    
    # Återställ enskilda komponenter
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.sidebar.button("↩️ Återställ Påverkbara"):
            reset_component('paverkbara')
    with col2:
        if st.sidebar.button("↩️ Återställ Kapital"):
            reset_component('kapitalkostnad')


def update_component_from_scenario(component: str, source: str, scenario_file: str):
    """Uppdaterar komponent från scenario-fil."""
    
    try:
        # Ladda scenario-data från parquet-fil
        scenario_df = pd.read_parquet(scenario_file)
        
        # Försök ladda metadata från JSON-fil (samma namn som parquet men .json)
        json_metadata = {}
        json_file = scenario_file.replace('.parquet', '.json')
        if Path(json_file).exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_metadata = json.load(f)
            except Exception as e:
                print(f"Kunde inte läsa JSON-metadata från {json_file}: {e}")
        
        # Kontrollera att vi har aktivt scenario
        if not st.session_state.current_scenario_name:
            st.sidebar.error("Inget aktivt scenario - skapa ett scenario först")
            return
        
        # Förbered modifikationer baserat på komponent-typ
        if component == 'kapitalkostnad' and source == 'kapitalbas':
            # Hantera kapitalkostnad från översikt.py export
            required_cols = ['DMU', 'Kapitalkostnad_Ny']
            missing_cols = [col for col in required_cols if col not in scenario_df.columns]
            
            if missing_cols:
                st.sidebar.error(f"Scenario-fil saknar kolumner: {missing_cols}")
                return
            
            # Skapa modifikationer per DMU (inte REId)
            modifications = {}
            for _, row in scenario_df.iterrows():
                dmu = str(row['DMU'])  # Konvertera till string som key
                modification = {
                    'total': row['Kapitalkostnad_Ny']
                }
                
                # Lägg till separerade komponenter om de finns
                if 'Avskrivningar_Ny' in row and pd.notna(row['Avskrivningar_Ny']):
                    modification['avskrivningar'] = row['Avskrivningar_Ny']
                if 'Avkastning_Ny' in row and pd.notna(row['Avkastning_Ny']):
                    modification['avkastning'] = row['Avkastning_Ny']
                
                modifications[dmu] = modification
            
            # Applicera på session state - använd DMU som key
            if 'modifications' not in st.session_state.scenario_data:
                st.session_state.scenario_data['modifications'] = {}
            
            st.session_state.scenario_data['modifications'][component] = {
                'values': modifications,
                'source': 'kapitalbas',
                'merge_on': 'DMU',
                'metadata': json_metadata  # Lägg till JSON-metadata
            }
            
            # Uppdatera komponent-källor
            st.session_state.scenario_data['component_sources'][component] = 'kapitalbas'
            
            st.sidebar.success(f"Kapitalkostnad uppdaterad från kapitalbas ({len(modifications)} DMU)")
            
        elif component == 'paverkbara' and source == 'effektiviseringskrav':
            # Läs DEA-export: förväntar 'REId' och 'Paverkbara_Target' (eller fallback)
            required_id = 'REId'
            if required_id not in scenario_df.columns:
                st.sidebar.error("Scenario-fil saknar REId")
                return

            candidate_cols = [c for c in ['Paverkbara_Target', 'Paverkbara_Nya'] if c in scenario_df.columns]
            if not candidate_cols:
                st.sidebar.error("Scenario-fil saknar kolumnerna 'Paverkbara_Target'/'Paverkbara_Nya'")
                return
            value_col = candidate_cols[0]

            # Bygg modifikationer per REId (IR arbetar per REId i vyn)
            modifications = {}
            for _, row in scenario_df[[required_id, value_col]].dropna().iterrows():
                reid = row[required_id]
                new_val = float(row[value_col])
                modifications[str(reid)] = new_val

            if not modifications:
                st.sidebar.warning("Ingen rad att applicera (saknar värden i exporten)")
                return

            # Spara i session state
            if 'modifications' not in st.session_state.scenario_data:
                st.session_state.scenario_data['modifications'] = {}

            st.session_state.scenario_data['modifications'][component] = {
                'values': modifications,
                'source': 'effektiviseringskrav',
                'metadata': json_metadata  # Lägg till JSON-metadata
            }
            st.session_state.scenario_data['component_sources']['paverkbara'] = 'effektiviseringskrav'

            st.sidebar.success(f"Påverkbara uppdaterade från Effektiviseringskrav ({len(modifications)} REId)")
            st.rerun()

        
        else:
            st.sidebar.error(f"Okänd kombination: {component} + {source}")
            return
        
        # Tvinga uppdatering av UI
        st.rerun()
        
    except Exception as e:
        st.sidebar.error(f"Fel vid uppdatering från {source}: {str(e)}")
        import traceback
        print(f"ERROR: {traceback.format_exc()}")


def update_component_manual(component: str, reid: str, new_value: float):
    """Uppdaterar komponent manuellt."""
    if 'modifications' not in st.session_state.scenario_data:
        st.session_state.scenario_data['modifications'] = {}
    
    if component not in st.session_state.scenario_data['modifications']:
        st.session_state.scenario_data['modifications'][component] = {'values': {}, 'source': 'manual'}
    
    st.session_state.scenario_data['modifications'][component]['values'][reid] = new_value
    st.sidebar.success(f"{component.title()} uppdaterad manuellt")
    st.rerun()


def update_component_manual_detailed(component: str, reid: str, new_avskrivning: float, new_avkastning: float):
    """Uppdaterar detaljerade kapitalkomponenter manuellt."""
    if 'modifications' not in st.session_state.scenario_data:
        st.session_state.scenario_data['modifications'] = {}
    
    if component not in st.session_state.scenario_data['modifications']:
        st.session_state.scenario_data['modifications'][component] = {'values': {}, 'source': 'manual'}
    
    # Spara som dict för separerade värden
    st.session_state.scenario_data['modifications'][component]['values'][reid] = {
        'avskrivningar': new_avskrivning,
        'avkastning': new_avkastning
    }
    
    st.sidebar.success("Kapitalkomponenter uppdaterade manuellt")
    st.rerun()


def reset_component(component: str):
    """Återställer en komponent till baseline."""
    if 'modifications' in st.session_state.scenario_data:
        if component in st.session_state.scenario_data['modifications']:
            del st.session_state.scenario_data['modifications'][component]
    
    st.sidebar.success(f"{component.title()} återställd till baseline")
    st.rerun()


def show_scenario_loader():
    """Visar dialog för att ladda tidigare sparade scenarier."""
    scenario_dir = Path("scenario/saved")
    
    if not scenario_dir.exists():
        st.sidebar.error("Inga sparade scenarier finns ännu")
        if st.sidebar.button("Stäng", key="close_empty_loader"):
            st.session_state.show_scenario_loader = False
            st.rerun()
        return
    
    # Leta efter sparade scenario-filer
    scenario_files = list(scenario_dir.glob("ir_scenario_*.parquet"))
    
    if not scenario_files:
        st.sidebar.error("Inga sparade scenarier hittades")
        if st.sidebar.button("Stäng", key="close_no_files"):
            st.session_state.show_scenario_loader = False
            st.rerun()
        return
    
    # Sortera efter modifierad tid (nyast först)
    scenario_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Visa scenario-loader persistent i sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 Ladda tidigare scenario")
    
    # Skapa dropdown med scenario-filer
    file_names = [f.name.replace("ir_scenario_", "").replace(".parquet", "").replace("_", " ") 
                  for f in scenario_files]
    
    selected_index = st.sidebar.selectbox(
        "Välj scenario att ladda:",
        options=range(len(scenario_files)),
        format_func=lambda i: file_names[i],
        key="scenario_selection"
    )
    
    selected_file = scenario_files[selected_index]
    
    # Info om valt scenario
    file_info = selected_file.stat()
    st.sidebar.caption(f"Skapad: {datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M')}")
    
    # Knappar för att ladda eller avbryta
    col_load, col_cancel = st.sidebar.columns(2)
    
    with col_load:
        if st.button("✅ Ladda scenario", key="load_scenario_btn"):
            load_scenario_from_file(selected_file)
            st.session_state.show_scenario_loader = False
            st.rerun()
    
    with col_cancel:
        if st.button("❌ Avbryt", key="cancel_load_btn"):
            st.session_state.show_scenario_loader = False
            st.rerun()
    
    st.sidebar.markdown("---")


def load_scenario_from_file(filepath: Path):
    """Laddar scenario från fil."""
    try:
        # Läs scenario-data
        df_scenario = pd.read_parquet(filepath)
        
        # Försök hämta metadata från fil-attribut
        try:
            metadata = df_scenario.attrs.get('scenario_metadata', {})
        except:
            metadata = {}
        
        scenario_name = metadata.get('name', filepath.stem.replace('ir_scenario_', ''))
        
        # Skapa nytt scenario med laddad data
        st.session_state.current_scenario_name = scenario_name
        st.session_state.scenario_data = {
            'baseline': df_scenario.copy(),
            'modifications': metadata.get('modifications', {}),
            'created': datetime.now(),
            'loaded_from': str(filepath),
            'component_sources': metadata.get('component_sources', {
                'paverkbara': 'baseline',
                'kapitalkostnad': 'baseline'
            })
        }
        
        st.sidebar.success(f"Scenario '{scenario_name}' laddat från fil!")
        
    except Exception as e:
        st.sidebar.error(f"Kunde inte ladda scenario: {e}")


def show_export_section(df_working: pd.DataFrame):
    """Visar export-kontroller för scenario och data."""
    
    st.header("📤 Export och spara")
    
    if not st.session_state.current_scenario_name:
        st.info("Skapa ett scenario för att kunna exportera data")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💾 Spara scenario")
        
        if st.button("Spara scenario till fil"):
            try:
                save_scenario_to_file(st.session_state.current_scenario_name, df_working)
                st.success("Scenario sparat!")
            except Exception as e:
                st.error(f"Fel vid sparande: {e}")
    
    with col2:
        st.subheader("📊 Exportera data")
        
        export_format = st.selectbox("Format", ["Excel", "CSV", "PDF"])
        
        if st.button("Exportera"):
            try:
                if export_format == "Excel":
                    buffer = create_excel_export(df_working)
                    st.download_button(
                        label="Ladda ned Excel",
                        data=buffer.getvalue(),
                        file_name=f"intaktsram_scenario_{st.session_state.current_scenario_name}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                elif export_format == "CSV":
                    csv = df_working.to_csv(index=False)
                    st.download_button(
                        label="Ladda ned CSV",
                        data=csv,
                        file_name=f"intaktsram_scenario_{st.session_state.current_scenario_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:  # PDF
                    st.info("PDF-export kommer i nästa version")
                    
            except Exception as e:
                st.error(f"Fel vid export: {e}")
    
    # Scenario-information
    if st.session_state.current_scenario_name:
        with st.expander("📋 Scenario-information"):
            scenario_info = st.session_state.scenario_data
            
            st.write(f"**Namn:** {st.session_state.current_scenario_name}")
            st.write(f"**Skapat:** {scenario_info.get('created', 'Okänt')}")
            
            # Visa komponent-källor och deras metadata
            component_sources = scenario_info.get('component_sources', {})
            st.write("**Komponent-källor:**")
            
            modifications = scenario_info.get('modifications', {})
            if modifications:
                for comp, mod_data in modifications.items():
                    source = mod_data.get('source', 'okänd')
                    num_changes = len(mod_data.get('values', {}))
                    st.write(f"- **{comp}**: {num_changes} enheter ändrade (källa: {source})")
                    
                    # Visa detaljerad metadata från JSON-filer om tillgänglig
                    metadata = mod_data.get('metadata', {})
                    if metadata:
                        if source == 'effektiviseringskrav':
                            st.write(f"  - Metod: {metadata.get('analysis_method', 'N/A')}")
                            st.write(f"  - Period: {metadata.get('period', 'N/A')}")
                            st.write(f"  - Total reduktion: {metadata.get('total_reduction_tkr', 'N/A'):,} tkr")
                        elif source == 'kapitalbas':
                            wacc_old = metadata.get('wacc_old', 'N/A')
                            wacc_new = metadata.get('wacc_new', 'N/A')
                            st.write(f"  - WACC gammal: {wacc_old}")
                            st.write(f"  - WACC ny: {wacc_new}")
                            period = metadata.get('period', {})
                            if isinstance(period, dict):
                                st.write(f"  - Period: {period.get('start', '')}-{period.get('end', '')}")
            else:
                st.write("**Inga modifikationer gjorda**")


def save_scenario_to_file(scenario_name: str, df_data: pd.DataFrame):
    """Sparar scenario till fil för framtida användning."""
    scenario_dir = Path("scenario/saved")
    scenario_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ir_scenario_{scenario_name.replace(' ', '_')}_{timestamp}.parquet"
    filepath = scenario_dir / filename
    
    # Spara både data och metadata
    scenario_metadata = {
        'name': scenario_name,
        'created': datetime.now().isoformat(),
        'modifications': st.session_state.scenario_data.get('modifications', {}),
        'component_sources': st.session_state.scenario_data.get('component_sources', {})
    }
    
    # Lägg till metadata som attribut till parquet-filen
    df_data.attrs['scenario_metadata'] = scenario_metadata
    df_data.to_parquet(filepath)
    
    return str(filepath)


def create_excel_export(df_data: pd.DataFrame) -> io.BytesIO:
    """Skapar Excel-export med flera flikar."""
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Huvuddata
        df_export = df_data.copy()
        
        # Rensa bort interna kolumner
        cols_to_remove = [col for col in df_export.columns if col.startswith('Källa_') or col.startswith('Uppdaterad_')]
        df_export = df_export.drop(columns=cols_to_remove, errors='ignore')
        
        df_export.to_excel(writer, sheet_name='Intäktsram Data', index=False)
        
        # Scenario-sammanfattning
        if st.session_state.current_scenario_name:
            summary_data = create_scenario_summary(df_data)
            summary_data.to_excel(writer, sheet_name='Scenario Sammanfattning', index=False)
        
        # Komponent-breakdown per företag
        component_breakdown = create_component_breakdown(df_data)
        component_breakdown.to_excel(writer, sheet_name='Komponent Breakdown', index=False)
    
    return buffer


def create_scenario_summary(df_data: pd.DataFrame) -> pd.DataFrame:
    """Skapar sammanfattning av scenario-förändringar."""
    summary_data = []
    
    # Grundstatistik
    total_companies = len(df_data)
    updated_paverkbara = df_data['Uppdaterad_Paverkbara'].sum() if 'Uppdaterad_Paverkbara' in df_data.columns else 0
    updated_kapital = df_data['Uppdaterad_Kapitalkostnad'].sum() if 'Uppdaterad_Kapitalkostnad' in df_data.columns else 0
    
    summary_data.extend([
        {'Statistik': 'Totalt antal företag', 'Värde': total_companies},
        {'Statistik': 'Företag med uppdaterade påverkbara kostnader', 'Värde': updated_paverkbara},
        {'Statistik': 'Företag med uppdaterad kapitalkostnad', 'Värde': updated_kapital},
    ])
    
    # Scenario-metadata
    if st.session_state.current_scenario_name:
        summary_data.extend([
            {'Statistik': 'Scenario-namn', 'Värde': st.session_state.current_scenario_name},
            {'Statistik': 'Skapad', 'Värde': str(st.session_state.scenario_data.get('created', 'Okänt'))},
        ])
    
    return pd.DataFrame(summary_data)


def create_component_breakdown(df_data: pd.DataFrame) -> pd.DataFrame:
    """Skapar detaljerad breakdown av komponenter per företag."""
    breakdown_data = []
    
    # Kontrollera om vi har uppdelade kapitalkostnader
    has_detailed_capital = 'Avskrivningar' in df_data.columns and 'Avkastning' in df_data.columns
    
    if has_detailed_capital:
        components = [
            ('Påverkbara kostnader', 'Paverkbara_Kostnader'),
            ('Opåverkbara kostnader', 'Opaverkbara_Kostnader'),
            ('Flexibilitetstjänster', 'Flexibilitetstjanster'),
            ('Avbrottsersättning 12-24h', 'Avbrottsersattning_12_24h'),
            ('Avskrivningar', 'Avskrivningar'),
            ('Avkastning', 'Avkastning')
        ]
    else:
        components = [
            ('Påverkbara kostnader', 'Paverkbara_Kostnader'),
            ('Opåverkbara kostnader', 'Opaverkbara_Kostnader'),
            ('Flexibilitetstjänster', 'Flexibilitetstjanster'),
            ('Avbrottsersättning 12-24h', 'Avbrottsersattning_12_24h'),
            ('Kapitalkostnad', 'Kapitalkostnad_Total')
        ]
    
    for _, row in df_data.iterrows():
        for comp_name, col_name in components:
            breakdown_data.append({
                'REId': row['REId'],
                'Företag': row.get('Företag', 'N/A'),
                'Komponent': comp_name,
                'Belopp (tkr)': row.get(col_name, 0),
                'Källa': get_component_source(comp_name, row),
                'Uppdaterad': is_component_updated(comp_name, row)
            })
    
    return pd.DataFrame(breakdown_data)


def get_component_source(comp_name: str, row: pd.Series) -> str:
    """Hämtar källa för en komponent."""
    if 'påverkbara' in comp_name.lower():
        return row.get('Källa_Paverkbara', 'Baseline')
    elif any(term in comp_name.lower() for term in ['kapital', 'avskrivning', 'avkastning']):
        return row.get('Källa_Kapitalkostnad', 'Baseline')
    else:
        return 'Baseline'


def is_component_updated(comp_name: str, row: pd.Series) -> bool:
    """Kontrollerar om en komponent har uppdaterats."""
    if 'påverkbara' in comp_name.lower():
        return row.get('Uppdaterad_Paverkbara', False)
    elif any(term in comp_name.lower() for term in ['kapital', 'avskrivning', 'avkastning']):
        return row.get('Uppdaterad_Kapitalkostnad', False)
    else:
        return False