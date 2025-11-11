"""
Effektiviseringskrav-tab med kedjestruktur
Effektivitetsvärde → DEA (optional) → Parametrar → Applicera
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from effektivitet.backend.dea_model import run_dea_model
from core.data_loader_dea import load_data
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
    
    if not st.session_state.current_scenario_name:
        st.warning("Skapa ett scenario i Översikt-fliken först")
        return
    
    user_dmu = get_user_dmu()
    
    reference_efficiency = st.session_state.scenario_data.get('reference_efficiency')
    
    if not reference_efficiency:
        st.error("Ingen referens-effektivitet hittades för ditt företag")
        st.info("Kontrollera att ditt företag finns i Ei:s DEA-dataset")
        return
    
    st.markdown("### 1. Effektivitetsvärde")
    active_efficiency, source = render_efficiency_value_section(reference_efficiency)
    
    if not active_efficiency:
        st.error("Kunde inte bestämma aktivt effektivitetsvärde")
        return
    
    st.markdown("---")
    
    st.markdown("### 2. Ny DEA-analys (valfritt)")
    st.caption("Kör egen DEA-analys för att byta effektivitetsvärde")
    
    render_dea_section(user_dmu)
    
    st.markdown("---")
    
    st.markdown("### 3. Beräkningsparametrar")
    render_calculation_parameters_section()
    
    st.markdown("---")
    
    st.markdown("### 4. Beräkna och applicera")
    render_apply_section_effkrav(active_efficiency, source)


def render_efficiency_value_section(reference_efficiency):
    """
    Visar aktivt effektivitetsvärde (ny DEA > referens)
    """
    
    staged = get_all_staged('paverkbara')
    
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
    
    if source == 'new_dea':
        if st.button("Reset till referens-DEA", key="reset_dea_to_reference"):
            remove_staged('paverkbara', 'new_dea_result')
            remove_staged('paverkbara', 'dea_params')
            st.rerun()
    
    return active_efficiency, source


def render_dea_section(user_dmu):
    """
    DEA-analys sektion med WACC-skalning och data-editor integrerad
    """
    
    try:
        data_file = "effektivitet/data/Data_modeller.xlsx"
        df_full = load_data(data_file)
    except Exception as e:
        st.error(f"Kunde inte ladda DEA-data: {e}")
        return
    
    if user_dmu not in df_full['DMU'].values:
        st.error(f"Ditt företag (DMU {user_dmu}) finns inte i DEA-datasetet")
        return
    
    df = df_full
    
    # === INPUT/OUTPUT VAL (FÖRENKLAD) ===
    st.markdown("**DEA-variabler**")
    
    base_inputs = ["CAPEX", "OPEXp", "TOTEX"]
    all_inputs = [c for c in base_inputs if c in df.columns]
    all_outputs = ["CU", "MW", "NS", "MWhl", "MWhh"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Variabler**")
        
        current_inputs = get_staged('paverkbara', 'dea_inputs', [c for c in ["CAPEX", "OPEXp"] if c in all_inputs])
        input_cols = st.multiselect(
            "Inputvariabler",
            all_inputs,
            default=current_inputs,
            help="Välj kostnadsvariabler som ska ingå i analysen"
        )
        if input_cols != current_inputs:
            set_staged('paverkbara', 'dea_inputs', input_cols)
        
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
        
        current_rts = get_staged('paverkbara', 'dea_rts', 'crs')
        dea_rts = st.selectbox(
            "Skalavkastning",
            ["crs", "vrs"],
            index=0 if current_rts == 'crs' else 1,
            help="CRS = Constant Returns to Scale, VRS = Variable Returns to Scale"
        )
        if dea_rts != current_rts:
            set_staged('paverkbara', 'dea_rts', dea_rts)
        
        current_filter = get_staged('paverkbara', 'outlier_filter', True)
        use_outlier_filter = st.checkbox(
            "Filtrera bort outliers före beräkning",
            value=current_filter,
            help="Exkluderar extremvärden från analysen"
        )
        if use_outlier_filter != current_filter:
            set_staged('paverkbara', 'outlier_filter', use_outlier_filter)
    
    if not validate_input_combinations(input_cols):
        return
    
    if not input_cols or not output_cols:
        st.warning("Välj minst en input och en output för att köra modellen")
        return
    
    # === REDIGERA FÖRETAGSDATA ===
    st.markdown("**Redigera företagsdata**")
    
    # WACC-skalning med number_input (decimalform)
    wacc_baseline = 0.0453
    current_wacc = get_staged('paverkbara', 'wacc_scenario', wacc_baseline)
    
    wacc_scenario = st.number_input(
        "Kalkylränta (WACC): Påverkar inputs CAPEX och TOTEX för alla nät",
        min_value=0.01,
        max_value=0.10,
        value=float(current_wacc),
        step=0.0001,
        format="%.4f",
        help="Testa DEA med annan kalkylränta än nuvarande 4.53 %"
    )
    
    if abs(wacc_scenario - current_wacc) > 0.00001:
        set_staged('paverkbara', 'wacc_scenario', wacc_scenario)
    
    if abs(wacc_scenario - wacc_baseline) > 0.00001:
        scaling = wacc_scenario / wacc_baseline
        df['CAPEX'] = df['CAPEX'] * scaling
        df['TOTEX'] = df['OPEXp'] + df['CAPEX']
    
    # Data-editor för OPEXp och volymer
    df_user = df[df['DMU'] == user_dmu].copy()
    
    if not df_user.empty:
        edit_cols = ['OPEXp', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
        df_editable = df_user[edit_cols].copy()
        
        df_edited = st.data_editor(
            df_editable,
            use_container_width=True,
            num_rows="fixed",
            hide_index=True,
            column_config={
                'OPEXp': st.column_config.NumberColumn(
                    'OPEXp (Påverkbara driftskostnader)',
                    min_value=0,
                    format="%.0f",
                ),
                'CU': st.column_config.NumberColumn(
                    'CU (Antal abonnemang)',
                    min_value=0,
                    format="%.0f",
                ),
                'MW': st.column_config.NumberColumn(
                    'MW (Det högsta värdet av abonnerad och uttagen effekt mot överliggande nät)',
                    min_value=0,
                    format="%.2f",
                ),
                'NS': st.column_config.NumberColumn(
                    'NS (nätstationer)',
                    min_value=0,
                    format="%.2f",
                ),
                'MWhl': st.column_config.NumberColumn(
                    'MWhl (Energi lågspänning)',
                    min_value=0,
                    format="%.2f",
                ),
                'MWhh': st.column_config.NumberColumn(
                    'MWhh (Energi högspänning)',
                    min_value=0,
                    format="%.2f",
                )
            },
            key="data_editor_opexp_volym"
        )
        
        if not df_edited.equals(df_editable):
            for col in edit_cols:
                df.loc[df['DMU'] == user_dmu, col] = df_edited[col].values[0]
            
            df.loc[df['DMU'] == user_dmu, 'TOTEX'] = \
                df.loc[df['DMU'] == user_dmu, 'OPEXp'] + \
                df.loc[df['DMU'] == user_dmu, 'CAPEX']
    
    # === OUTLIER-DEFINITION (ORIGINAL) ===
    st.markdown("**Outlier-definition**")
    st.caption("Konfigurera hur outliers identifieras baserat på supereffektivitet")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        current_q_lower = get_staged('paverkbara', 'q_lower', 0.25)
        q_lower = st.slider(
            "Nedre kvartil",
            min_value=0.0,
            max_value=0.5,
            value=float(current_q_lower),
            step=0.05,
            format="%.2f",
            help="Nedre kvartil för tröskel"
        )
        if abs(q_lower - current_q_lower) > 0.001:
            set_staged('paverkbara', 'q_lower', q_lower)
    
    with col4:
        current_q_upper = get_staged('paverkbara', 'q_upper', 0.75)
        q_upper = st.slider(
            "Övre kvartil",
            min_value=0.5,
            max_value=1.0,
            value=float(current_q_upper),
            step=0.05,
            format="%.2f",
            help="Övre kvartil för tröskel"
        )
        if abs(q_upper - current_q_upper) > 0.001:
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
    
    # === KÖR DEA (ORIGINAL API) ===
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
                    q_lower=int(q_lower * 100),
                    q_upper=int(q_upper * 100),
                    multiplier=multiplier
                )
                
                user_result = result[result['DMU'] == user_dmu]
                
                if not user_result.empty:
                    row = user_result.iloc[0]
                    
                    set_staged('paverkbara', 'new_dea_result', {
                        'DMU': int(row['DMU']),
                        'REId': str(row.get('REId', '')),
                        'Företag': str(row.get('Företag', '')),
                        'Effektivitet': float(row['Effektivitet']) if not row.get('is_outlier') else None,
                        'Supereffektivitet': float(row['Supereffektivitet']) if not row.get('is_outlier') else None,
                        'potential': float(row.get('potential', 0)),
                        'is_outlier': bool(row.get('is_outlier', False))
                    })
                    
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


def validate_input_combinations(input_cols):
    """Validerar input-kombinationer enligt DEA-regler (förenklad - ingen scenario-check)"""
    
    has_capex = "CAPEX" in input_cols
    has_opexp = "OPEXp" in input_cols
    has_totex = "TOTEX" in input_cols
    
    if has_totex and (has_capex or has_opexp):
        st.error("Välj antingen TOTEX ELLER CAPEX/OPEXp, inte båda")
        return False
    
    return True


def render_calculation_parameters_section():
    """
    Beräkningsparametrar för effektiviseringskrav
    """
    
    baseline_trunk_min = 0.162416
    baseline_trunk_max = 0.3
    baseline_outlier_krav = 0.01
    baseline_method = 'OPEX'
    
    st.caption("Justera parametrar för beräkning av effektiviseringskrav")
    
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
    
    staged = get_all_staged('paverkbara')
    param_changes = {k: v for k, v in staged.items() 
                    if k in ['trunk_min', 'trunk_max', 'outlier_krav', 'method']}
    
    if 'new_dea_result' not in staged and not param_changes:
        st.info("Inga ändringar att applicera. Kör DEA eller justera parametrar för att uppdatera effektiviseringskrav.")
        return
    
    change_list = []
    if 'new_dea_result' in staged:
        change_list.append("Ny DEA-körning")
    if param_changes:
        change_list.append(f"{len(param_changes)} parameter")
    
    st.caption(f"**Ändringar:** {', '.join(change_list)}")
    
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
            trunk_min = staged.get('trunk_min', 0.162416)
            trunk_max = staged.get('trunk_max', 0.3)
            outlier_krav = staged.get('outlier_krav', 0.01)
            method = staged.get('method', 'OPEX')
            
            efficiency_df = pd.DataFrame([{
                'DMU': active_efficiency['DMU'],
                'REId': active_efficiency.get('REId', ''),
                'Företag': active_efficiency.get('Företag', ''),
                'Effektivitet': active_efficiency.get('Effektivitet'),
                'Supereffektivitet': active_efficiency.get('Supereffektivitet'),
                'potential': active_efficiency.get('potential', 0),
                'is_outlier': active_efficiency.get('is_outlier', False)
            }])
            
            from core.effektiviseringskrav_calculations import calculate_effkrav_for_dataframe
            
            efficiency_with_krav = calculate_effkrav_for_dataframe(
                efficiency_df,
                potential_col='potential',
                outlier_col='is_outlier',
                trunkering_min=trunk_min,
                trunkering_max=trunk_max,
                outlier_krav=outlier_krav
            )
            
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