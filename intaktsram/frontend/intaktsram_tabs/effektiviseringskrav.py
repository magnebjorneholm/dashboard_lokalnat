"""
Effektiviseringskrav-tab med kedjestruktur
Effektivitetsvärde → DEA (optional) → Parametrar → Applicera
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from effektivitet.backend.dea_model import run_dea_model
from core.data_loader_dea import merge_capex_scenario, load_data
from core.session_utils import get_user_dmu

from intaktsram.backend.pending_changes_manager import (
    get_staged,
    set_staged,
    get_all_staged,
    has_staged_changes,
    count_staged_changes,
    commit_staged_changes,
    reset_all,
    reset_parameter,
    get_active_value
)


def show_effektiviseringskrav_tab(entity_data, scenario_metadata):
    """Huvudfunktion för effektiviseringskrav-tab med kedjestruktur"""
    
    st.subheader("Effektiviseringskrav")
    
    # Scenario-check
    if not st.session_state.current_scenario_name:
        st.warning("Skapa ett scenario i Översikt-fliken först")
        return
    
    user_dmu = get_user_dmu()
    
    # Hämta referens-effektivitet från scenario
    reference_efficiency = st.session_state.scenario_data.get('reference_efficiency')
    
    if not reference_efficiency:
        st.error("Ingen referens-effektivitet hittades för ditt företag")
        st.info("Kontrollera att ditt företag finns i Ei:s DEA-dataset")
        return
    
    # === KEDJA STEG 1: EFFEKTIVITETSVÄRDE ===
    st.markdown("### 1. Effektivitetsvärde")
    active_efficiency, source = render_efficiency_value_section(reference_efficiency)
    
    if not active_efficiency:
        st.error("Kunde inte bestämma aktivt effektivitetsvärde")
        return
    
    st.markdown("---")
    
    # === KEDJA STEG 2: DEA (optional) ===
    st.markdown("### 2. Ny DEA-analys (valfritt)")
    st.caption("Kör egen DEA-analys för att byta effektivitetsvärde")
    
    render_dea_section(user_dmu)
    
    st.markdown("---")
    
    # === KEDJA STEG 3: BERÄKNINGSPARAMETRAR ===
    st.markdown("### 3. Beräkningsparametrar")
    render_calculation_parameters_section()
    
    st.markdown("---")
    
    # === KEDJA STEG 4: APPLICERA ===
    st.markdown("### 4. Beräkna och applicera")
    render_apply_section_effkrav(active_efficiency, source)


def render_efficiency_value_section(reference_efficiency):
    """
    Visar aktivt effektivitetsvärde (ny DEA > referens)
    """
    
    staged = get_all_staged('paverkbara')
    
    # Bestäm aktivt värde
    if 'new_dea_result' in staged:
        active_efficiency = staged['new_dea_result']
        source = 'new_dea'
        st.info("**Aktivt värde:** Från ny DEA-körning")
    elif reference_efficiency:
        active_efficiency = reference_efficiency
        source = 'reference'
        st.info("**Aktivt värde:** Från Ei:s referens-DEA")
    else:
        return None, None
    
    # Visa värden i metrics (3 kolumner)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if active_efficiency.get('is_outlier'):
            st.metric("Status", "Outlier")
        else:
            eff = active_efficiency.get('Effektivitet', 0)
            st.metric("Effektivitet", f"{eff:.3f}")
    
    with col2:
        if not active_efficiency.get('is_outlier'):
            supereff = active_efficiency.get('Supereffektivitet', 0)
            st.metric("Supereffektivitet", f"{supereff:.3f}")
        else:
            st.metric("Supereffektivitet", "N/A")
    
    with col3:
        pot = active_efficiency.get('potential', 0)
        st.metric("Potential", f"{pot:.3f}")
    
    # Reset-knapp om ny DEA
    if source == 'new_dea':
        if st.button("Reset till referens-DEA", key="reset_dea_to_reference"):
            remove_staged('paverkbara', 'new_dea_result')
            remove_staged('paverkbara', 'dea_params')
            st.rerun()
    
    return active_efficiency, source


def render_dea_section(user_dmu):
    """
    DEA-analys sektion med multiselect för variabler
    Återanvänder layout från effektivitet.py
    """
    
    # Ladda DEA-dataset
    try:
        data_file = "effektivitet/data/Data_modeller.xlsx"
        df_full = load_data(data_file)
    except Exception as e:
        st.error(f"Kunde inte ladda DEA-data: {e}")
        return
    
    if user_dmu not in df_full['DMU'].values:
        st.error(f"Ditt företag (DMU {user_dmu}) finns inte i DEA-datasetet")
        return
    
    # Försök merga CAPEX-scenario
    df, scen_info = merge_capex_scenario(df_full)
    
    if scen_info.get("found"):
        st.success(f"WACC-scenario aktivt: {scen_info['tag'].replace('p','.')} - täckning {scen_info['coverage']:.0%}")
    
    # Input/Output val
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]
    
    # Lägg till scenario-kolumner
    if scen_info.get("found"):
        capex_wacc_col = scen_info.get("capex_col")
        totex_wacc_col = scen_info.get("totex_col")
        all_inputs += [c for c in [capex_wacc_col, totex_wacc_col] if c and c in df.columns]
    
    # Två kolumner för parametrar
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Variabler**")
        
        # Inputs
        current_inputs = get_staged('paverkbara', 'dea_inputs', [c for c in ["CAPEX", "OPEXp"] if c in all_inputs])
        input_cols = st.multiselect(
            "Inputvariabler",
            all_inputs,
            default=current_inputs,
            help="Välj kostnadsvariabler som ska ingå i analysen"
        )
        if input_cols != current_inputs:
            set_staged('paverkbara', 'dea_inputs', input_cols)
        
        # Outputs
        current_outputs = get_staged('paverkbara', 'dea_outputs', all_outputs)
        output_cols = st.multiselect(
            "Outputvariabler",
            all_outputs,
            default=current_outputs,
            help="Välj outputvariabler som beskriver nätets storlek och aktivitet"
        )
        if output_cols != current_outputs:
            set_staged('paverkbara', 'dea_outputs', output_cols)
    
    with col2:
        st.markdown("**Modellinställningar**")
        
        # Skalavkastning
        current_rts = get_staged('paverkbara', 'dea_rts', 'crs')
        dea_rts = st.selectbox(
            "Skalavkastning",
            ["crs", "vrs"],
            index=0 if current_rts == 'crs' else 1,
            help="CRS = Constant Returns to Scale, VRS = Variable Returns to Scale"
        )
        if dea_rts != current_rts:
            set_staged('paverkbara', 'dea_rts', dea_rts)
        
        # Outlier-filter
        current_filter = get_staged('paverkbara', 'outlier_filter', True)
        use_outlier_filter = st.checkbox(
            "Filtrera bort outliers före beräkning",
            value=current_filter,
            help="Exkluderar extremvärden från analysen"
        )
        if use_outlier_filter != current_filter:
            set_staged('paverkbara', 'outlier_filter', use_outlier_filter)
    
    # Validera inputs
    if not validate_input_combinations(input_cols, scen_info, df):
        return
    
    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen")
        return
    
    # Outlier-definition (3 kolumner)
    st.markdown("**Outlier-definition**")
    st.caption("Konfigurera hur outliers identifieras baserat på supereffektivitet")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        current_q_lower = get_staged('paverkbara', 'q_lower', 25)
        q_lower = st.slider(
            "Nedre kvartil",
            0, 50, current_q_lower,
            step=5,
            help="Nedre kvartil för outlier-tröskel"
        )
        if q_lower != current_q_lower:
            set_staged('paverkbara', 'q_lower', q_lower)
    
    with col4:
        current_q_upper = get_staged('paverkbara', 'q_upper', 75)
        q_upper = st.slider(
            "Övre kvartil",
            50, 100, current_q_upper,
            step=5,
            help="Övre kvartil för outlier-tröskel"
        )
        if q_upper != current_q_upper:
            set_staged('paverkbara', 'q_upper', q_upper)
    
    with col5:
        current_multiplier = get_staged('paverkbara', 'multiplier', 2.0)
        multiplier = st.slider(
            "IQR-multiplikator",
            1.0, 3.0, current_multiplier,
            step=0.1,
            help="Multiplikator för interkvartilavstånd"
        )
        if multiplier != current_multiplier:
            set_staged('paverkbara', 'multiplier', multiplier)
    
    st.caption("Threshold: Q_upper + multiplikator × (Q_upper - Q_lower)")
    
    # Kör DEA-knapp
    st.markdown("")
    if st.button("Kör DEA-analys", type="primary", use_container_width=True, key="run_dea_effektiviseringskrav"):
        with st.spinner("Kör DEA-beräkningar..."):
            try:
                result = run_dea_model(
                    df,
                    rts=dea_rts,
                    input_cols=input_cols,
                    output_cols=output_cols,
                    outlier_filter=use_outlier_filter,
                    q_lower=q_lower,
                    q_upper=q_upper,
                    multiplier=multiplier
                )
                
                # Extrahera användarens resultat
                user_result = result[result['DMU'] == user_dmu]
                
                if not user_result.empty:
                    row = user_result.iloc[0]
                    
                    # Spara i staged som dictionary
                    set_staged('paverkbara', 'new_dea_result', {
                        'DMU': int(row['DMU']),
                        'REId': str(row.get('REId', '')),
                        'Företag': str(row.get('Företag', '')),
                        'Effektivitet': float(row['Effektivitet']) if not row.get('is_outlier') else None,
                        'Supereffektivitet': float(row['Supereffektivitet']) if not row.get('is_outlier') else None,
                        'potential': float(row.get('potential', 0)),
                        'is_outlier': bool(row.get('is_outlier', False))
                    })
                    
                    # Spara DEA-parametrar för referens
                    set_staged('paverkbara', 'dea_params', {
                        'input_cols': input_cols,
                        'output_cols': output_cols,
                        'rts': dea_rts,
                        'outlier_filter': use_outlier_filter,
                        'q_lower': q_lower,
                        'q_upper': q_upper,
                        'multiplier': multiplier
                    })
                    
                    st.success("DEA-analys slutförd - nytt effektivitetsvärde aktiverat")
                    st.rerun()
                else:
                    st.error(f"Ingen data för DMU {user_dmu} i resultat")
                    
            except Exception as e:
                st.error(f"DEA-analys misslyckades: {e}")
                import traceback
                st.error(traceback.format_exc())


def validate_input_combinations(input_cols, scen_info, df):
    """Validerar input-kombinationer enligt DEA-regler"""
    
    has_capex_std = "CAPEX" in input_cols
    has_capex_scen = any(col.startswith("CAPEX_2024_wacc_") for col in input_cols)
    has_opexp = "OPEXp" in input_cols
    has_totex_std = "TOTEX" in input_cols
    has_totex_scen = any(col.startswith("TOTEX_wacc_") for col in input_cols)
    
    capex_any = has_capex_std or has_capex_scen
    totex_any = has_totex_std or has_totex_scen
    
    if totex_any and (capex_any or has_opexp):
        st.error("Välj antingen TOTEX ELLER CAPEX/OPEXp, inte båda")
        return False
    
    if (has_capex_std and has_capex_scen) or (has_totex_std and has_totex_scen):
        st.error("Välj antingen baseline- ELLER scenario-variant inom samma familj")
        return False
    
    if scen_info.get("found"):
        capex_wacc_col = scen_info.get("capex_col")
        totex_wacc_col = scen_info.get("totex_col")
        chosen_scen_cols = [c for c in [capex_wacc_col, totex_wacc_col] if c and c in input_cols]
        
        if chosen_scen_cols:
            missing = [c for c in chosen_scen_cols if df[c].isna().any()]
            if missing:
                st.error(
                    "Scenario-kolumn saknar värden:\n"
                    f"- {', '.join(missing)}\n\n"
                    "Kontrollera exporten från Kapitalbas."
                )
                return False
    
    return True


def render_calculation_parameters_section():
    """
    Beräkningsparametrar för effektiviseringskrav
    """
    
    # Baseline-värden från Ei
    baseline_trunk_min = 0.162416
    baseline_trunk_max = 0.3
    baseline_outlier_krav = 0.01
    baseline_method = 'OPEX'
    
    st.caption("Justera parametrar för beräkning av effektiviseringskrav")
    
    # Trunkering (2 kolumner)
    col1, col2 = st.columns(2)
    
    with col1:
        current_trunk_min = get_active_value('paverkbara', 'trunk_min', baseline_trunk_min)
        new_trunk_min = st.number_input(
            "Trunkering min",
            value=float(current_trunk_min),
            min_value=0.0,
            max_value=0.3,
            step=0.001,
            format="%.3f",
            help="Nedre gräns för potential-trunkering"
        )
        st.caption(f"Baseline: {baseline_trunk_min:.3f}")
        
        if abs(new_trunk_min - current_trunk_min) > 0.0001:
            set_staged('paverkbara', 'trunk_min', new_trunk_min)
    
    with col2:
        current_trunk_max = get_active_value('paverkbara', 'trunk_max', baseline_trunk_max)
        new_trunk_max = st.number_input(
            "Trunkering max",
            value=float(current_trunk_max),
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            format="%.2f",
            help="Övre gräns för potential-trunkering"
        )
        st.caption(f"Baseline: {baseline_trunk_max:.2f}")
        
        if abs(new_trunk_max - current_trunk_max) > 0.001:
            set_staged('paverkbara', 'trunk_max', new_trunk_max)
    
    # Outlier-krav
    current_outlier = get_active_value('paverkbara', 'outlier_krav', baseline_outlier_krav)
    new_outlier = st.number_input(
        "Outlier-krav (%)",
        value=float(current_outlier * 100),
        min_value=1.0,
        max_value=1.82,
        step=0.01,
        format="%.2f",
        help="Fast årligt krav för outliers och 100% effektiva"
    ) / 100
    st.caption(f"Baseline: {baseline_outlier_krav*100:.2f}%")
    
    if abs(new_outlier - current_outlier) > 0.00001:
        set_staged('paverkbara', 'outlier_krav', new_outlier)
    
    # Metod
    current_method = get_active_value('paverkbara', 'method', baseline_method)
    new_method = st.selectbox(
        "Applicera på",
        options=['OPEX', 'TOTEX'],
        index=0 if current_method == 'OPEX' else 1,
        help="OPEX: Endast påverkbara kostnader | TOTEX: Påverkbara + kapitalkostnad"
    )
    st.caption(f"Baseline: {baseline_method}")
    
    if new_method != current_method:
        set_staged('paverkbara', 'method', new_method)


def render_apply_section_effkrav(active_efficiency, source):
    """
    Apply-sektion för effektiviseringskrav
    """
    
    # Kontrollera staged changes för parametrar (inte DEA-resultat)
    staged = get_all_staged('paverkbara')
    param_changes = {k: v for k, v in staged.items() 
                    if k in ['trunk_min', 'trunk_max', 'outlier_krav', 'method']}
    
    # Om ingen DEA-körning OCH inga parameterjusteringar
    if 'new_dea_result' not in staged and not param_changes:
        st.info("Inga ändringar att applicera. Kör DEA eller justera parametrar för att uppdatera effektiviseringskrav.")
        return
    
    # Visa antal ändringar
    change_list = []
    if 'new_dea_result' in staged:
        change_list.append("Ny DEA-körning")
    if param_changes:
        change_list.append(f"{len(param_changes)} parameter")
    
    st.caption(f"**Ändringar:** {', '.join(change_list)}")
    
    # Apply och Reset knappar
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Beräkna och applicera", type="primary", use_container_width=True, key="apply_effektiviseringskrav"):
            apply_effektiviseringskrav(active_efficiency, source, staged)
    
    with col2:
        if st.button("Återställ alla", use_container_width=True, key="reset_effektiviseringskrav"):
            reset_all('paverkbara')
            st.rerun()


def apply_effektiviseringskrav(active_efficiency, source, staged):
    """
    Beräknar och applicerar effektiviseringskrav
    """
    
    with st.spinner("Beräknar effektiviseringskrav..."):
        try:
            # Hämta parametrar
            trunk_min = staged.get('trunk_min', 0.162416)
            trunk_max = staged.get('trunk_max', 0.3)
            outlier_krav = staged.get('outlier_krav', 0.01)
            method = staged.get('method', 'OPEX')
            
            # Konvertera efficiency till DataFrame
            efficiency_df = pd.DataFrame([{
                'DMU': active_efficiency['DMU'],
                'REId': active_efficiency.get('REId', ''),
                'Företag': active_efficiency.get('Företag', ''),
                'Effektivitet': active_efficiency.get('Effektivitet'),
                'Supereffektivitet': active_efficiency.get('Supereffektivitet'),
                'potential': active_efficiency.get('potential', 0),
                'is_outlier': active_efficiency.get('is_outlier', False)
            }])
            
            # Beräkna Effkrav_proc
            from core.effektiviseringskrav_calculations import calculate_effkrav_for_dataframe
            
            efficiency_with_krav = calculate_effkrav_for_dataframe(
                efficiency_df,
                potential_col='potential',
                outlier_col='is_outlier',
                trunkering_min=trunk_min,
                trunkering_max=trunk_max,
                outlier_krav=outlier_krav
            )
            
            # Spara i applied_modifications
            st.session_state.scenario_data['applied_modifications']['paverkbara'] = {
                'source': 'effektiviseringskrav',
                'method': method,
                'dea_result': efficiency_with_krav,
                'metadata': {
                    'efficiency_source': source,
                    'trunk_min': trunk_min,
                    'trunk_max': trunk_max,
                    'outlier_krav': outlier_krav,
                    'dea_params': staged.get('dea_params') if source == 'new_dea' else None
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # Commit staged changes
            commit_staged_changes('paverkbara')
            
            st.success("Effektiviseringskrav beräknat och applicerat!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Applicering misslyckades: {e}")
            import traceback
            st.error(traceback.format_exc())


def remove_staged(module: str, param: str):
    """Helper för att ta bort staged parameter"""
    from intaktsram.backend.pending_changes_manager import remove_staged as _remove_staged
    _remove_staged(module, param)