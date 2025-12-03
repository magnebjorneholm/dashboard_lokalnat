"""
Data Upload & Validation Module for Beräkningskedjan
Allows users to upload their own capbase_a dataset with validation
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import io


# ============================================================================
# VALIDATION SCHEMA
# ============================================================================

REQUIRED_COLUMNS = {
    'id_component': ['int', 'object', 'string'],
    'time_from': ['int', 'float'],
    'time_invest': ['int', 'float'],
    'capbase_existing': ['int', 'float'],
    'ekdep': ['int', 'float'],
    'maxdep': ['int', 'float'],
    'nuav_2022': ['int', 'float'],
    'cat_encode': ['int', 'object', 'string', 'category'],
    'id_network': ['int', 'float'],
    'invest': ['int', 'float', 'object']
}


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_uploaded_data(df: pd.DataFrame) -> Dict:
    """
    Validates if uploaded data can be used for beräkningskedjan.
    Returns validation result with pass/fail and specific issues.
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'info': []
    }
    
    # 1. Check required columns exist
    missing_cols = [col for col in REQUIRED_COLUMNS.keys() if col not in df.columns]
    if missing_cols:
        validation_result['is_valid'] = False
        validation_result['errors'].append(
            f"Saknade obligatoriska kolumner: {', '.join(missing_cols)}"
        )
        return validation_result
    
    # 2. Check data types
    for col, allowed_types in REQUIRED_COLUMNS.items():
        actual_type = str(df[col].dtype)
        
        type_valid = False
        for allowed in allowed_types:
            if allowed == 'int' and 'int' in actual_type.lower():
                type_valid = True
                break
            elif allowed == 'float' and 'float' in actual_type.lower():
                type_valid = True
                break
            elif allowed == 'object' and 'object' in actual_type.lower():
                type_valid = True
                break
            elif allowed == 'string' and 'string' in actual_type.lower():
                type_valid = True
                break
            elif allowed == 'category' and 'category' in actual_type.lower():
                type_valid = True
                break
        
        if not type_valid:
            validation_result['errors'].append(
                f"Kolumn '{col}' har fel datatyp. "
                f"Förväntad kategori: {', '.join(allowed_types)}, Faktisk: {actual_type}"
            )
            validation_result['is_valid'] = False
    
    # 3. Check for empty dataframe
    if len(df) == 0:
        validation_result['is_valid'] = False
        validation_result['errors'].append("Datasetet är tomt (0 rader)")
        return validation_result
    
    # 4. Check for valid grouping
    if 'cat_encode' in df.columns and 'id_network' in df.columns:
        n_groups = df.groupby(['cat_encode', 'id_network']).ngroups
        if n_groups == 0:
            validation_result['errors'].append(
                "Ingen giltig gruppering på cat_encode + id_network kunde skapas"
            )
            validation_result['is_valid'] = False
    
    return validation_result


def load_uploaded_file(uploaded_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Loads uploaded file (parquet or excel) and returns dataframe.
    Returns (dataframe, error_message)
    """
    try:
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        if file_extension == '.parquet':
            df = pd.read_parquet(uploaded_file)
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(uploaded_file)
        else:
            return None, f"Filformat stöds ej: {file_extension}. Använd .parquet eller .xlsx/.xls"
        
        return df, None
        
    except Exception as e:
        return None, f"Kunde inte läsa fil: {str(e)}"


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_data_source_selector():
    """
    Renders data source selection UI.
    Returns selected data source and loaded dataframe.
    """
    st.markdown("### Välj datakälla")
    
    uploaded_file = st.file_uploader(
        "Ladda upp egen data eller lämna tom för att använda befintlig data", 
        type=['parquet', 'xlsx', 'xls'],
    )
    
    uploaded_df = None
    data_source = "Baseline (befintlig data)"
    
    if uploaded_file is not None:
        data_source = "Ladda upp egen data"
        
        with st.spinner("Läser in fil..."):
            uploaded_df, error = load_uploaded_file(uploaded_file)
            
            if error:
                st.error(f"⚠ {error}")
            else:
                st.success(f"Fil inläst: {len(uploaded_df)} rader, {len(uploaded_df.columns)} kolumner")
    
    return data_source, uploaded_df


def render_validation_results(validation: Dict):
    """
    Renders validation results in a minimal format.
    Only shows pass/fail status and critical errors.
    """
    
    if validation['is_valid']:
        st.success("Data kan användas för beräkning")
    else:
        st.error("Data kan INTE användas för beräkning")
        
        # Show only critical errors
        if validation['errors']:
            for error in validation['errors']:
                st.error(f"• {error}")


def render_data_preview(df: pd.DataFrame):
    """
    Renders data preview in expander.
    """
    with st.expander("Visa input-data som används i beräkningen", expanded=False):
        st.markdown("#### Alla kolumner i capbase_a:")
        st.dataframe(df, use_container_width=True, height=400)
        
        st.markdown("#### Datatyper:")
        dtype_info = pd.DataFrame({
            'Kolumn': df.columns,
            'Datatyp': [str(dtype) for dtype in df.dtypes],
            'Antal icke-null': [df[col].notna().sum() for col in df.columns],
            'Antal null': [df[col].isna().sum() for col in df.columns]
        })
        st.dataframe(dtype_info, use_container_width=True, hide_index=True)


# ============================================================================
# MAIN INTEGRATION FUNCTION
# ============================================================================

def get_validated_data_for_berakningskedja(default_loader_func):
    """
    Main function to integrate into existing beräkningskedja.
    
    Args:
        default_loader_func: Function to load baseline data (e.g., load_dmu_capbase_a)
    
    Returns:
        (pd.DataFrame, bool): Validated dataframe and whether it's custom data
    """
    # Data source selection
    data_source, uploaded_df = render_data_source_selector()
    
    is_custom_data = (data_source == "Ladda upp egen data")
    
    # Load appropriate data
    if is_custom_data and uploaded_df is not None:
        # Validate uploaded data
        validation = validate_uploaded_data(uploaded_df)
        render_validation_results(validation)
        
        if validation['is_valid']:
            render_data_preview(uploaded_df)
            return uploaded_df, True
        else:
            st.warning("⚠ Korrigera felen innan du kan fortsätta med beräkningen")
            return None, True
            
    elif is_custom_data and uploaded_df is None:
        st.info("📁 Ladda upp en fil för att fortsätta")
        return None, True
        
    else:
        # Use baseline data
        baseline_df = default_loader_func()
        
        # Validate baseline too
        validation = validate_uploaded_data(baseline_df)
        if not validation['is_valid']:
            st.error("⚠ Data är ogiltig! Kontakta systemadministratör.")
            render_validation_results(validation)
            return None, False
        
        render_data_preview(baseline_df)
        return baseline_df, False


def apply_lifetime_scenario(capbase_data: pd.DataFrame) -> pd.DataFrame:
    """
    Låter användare justera ekonomisk och maximal livslängd per kategori eller subkategori
    för scenarioanalys med en interaktiv tabell.
    
    Returns modified dataframe with scenario adjustments
    """
    
    with st.expander("Justera ekonomisk/maximal livslängd", expanded=False):
        st.info("För scenarioanalys: Testa hur ändringar i regulatoriska livslängder påverkar kapitalkostnaden")
        
        # Check required columns
        required_cols = ['cat_encode', 'ekdep', 'maxdep']
        missing_cols = [col for col in required_cols if col not in capbase_data.columns]
        if missing_cols:
            st.error(f"Data saknar obligatoriska kolumner: {', '.join(missing_cols)}")
            return capbase_data
        
        # Check if we have text columns
        has_cat_text = 'cat' in capbase_data.columns
        has_subcat = 'subcat_encode' in capbase_data.columns and 'subcat' in capbase_data.columns
        
        # Select aggregation level
        st.markdown("**Välj justeringsnivå:**")
        
        if has_subcat:
            agg_level = st.radio(
                "Justera på:",
                ["Kategorinivå (cat)", "Subkategorinivå (subcat)"],
                horizontal=True,
                key="lifetime_agg_level"
            )
            use_subcat = (agg_level == "Subkategorinivå (subcat)")
        else:
            st.caption("Data innehåller endast kategorinivå")
            use_subcat = False
        
        # Determine grouping columns
        if use_subcat:
            group_encode = 'subcat_encode'
            group_text = 'subcat'
        else:
            group_encode = 'cat_encode'
            group_text = 'cat' if has_cat_text else None
        
        # Build aggregation for current values
        agg_dict = {
            'ekdep': 'first',
            'maxdep': 'first'
        }
        
        # Group by selected level
        if group_text:
            current_values = capbase_data.groupby([group_encode, group_text]).agg(agg_dict).reset_index()
            current_values = current_values.rename(columns={
                group_encode: 'Kod',
                group_text: 'Beskrivning',
                'ekdep': 'Ekonomisk livslängd',
                'maxdep': 'Maximal livslängd'
            })
        else:
            current_values = capbase_data.groupby(group_encode).agg(agg_dict).reset_index()
            current_values = current_values.rename(columns={
                group_encode: 'Kod',
                'ekdep': 'Ekonomisk livslängd',
                'maxdep': 'Maximal livslängd'
            })
        
        # Sort by code
        current_values = current_values.sort_values('Kod').reset_index(drop=True)
        
        # Create editable copy for adjustments
        st.markdown("**Redigera värden:**")
        st.caption("Ändra värdena direkt i tabellen nedan och klicka 'Applicera ändringar'")
        
        # Prepare editable dataframe
        editable_df = current_values.copy()
        
        # Use data_editor for interactive editing
        edited_df = st.data_editor(
            editable_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            disabled=['Kod'] if group_text is None else ['Kod', 'Beskrivning'],
            column_config={
                'Ekonomisk livslängd': st.column_config.NumberColumn(
                    'Ekonomisk livslängd',
                    min_value=1,
                    max_value=100,
                    step=1,
                    format="%d år"
                ),
                'Maximal livslängd': st.column_config.NumberColumn(
                    'Maximal livslängd',
                    min_value=1,
                    max_value=150,
                    step=1,
                    format="%d år"
                )
            },
            key="lifetime_editor"
        )
        
        # Detect changes
        changes_made = not edited_df.equals(current_values)
        
        if changes_made:
            # Validate all rows
            invalid_rows = edited_df[edited_df['Maximal livslängd'] < edited_df['Ekonomisk livslängd']]
            if not invalid_rows.empty:
                st.error(f"⚠ {len(invalid_rows)} rad(er) har maximal livslängd < ekonomisk livslängd. Detta måste korrigeras.")
            
            # Show what changed
            st.markdown("**Ändringar som kommer appliceras:**")
            
            # Compare
            comparison = current_values.copy()
            comparison['Ekdep (ny)'] = edited_df['Ekonomisk livslängd']
            comparison['Maxdep (ny)'] = edited_df['Maximal livslängd']
            comparison['Ekdep Δ'] = comparison['Ekdep (ny)'] - comparison['Ekonomisk livslängd']
            comparison['Maxdep Δ'] = comparison['Maxdep (ny)'] - comparison['Maximal livslängd']
            
            # Filter to only changed rows
            changed_rows = comparison[(comparison['Ekdep Δ'] != 0) | (comparison['Maxdep Δ'] != 0)]
            
            if not changed_rows.empty:
                display_cols = ['Kod']
                if group_text:
                    display_cols.append('Beskrivning')
                display_cols.extend(['Ekonomisk livslängd', 'Ekdep (ny)', 'Ekdep Δ', 
                                   'Maximal livslängd', 'Maxdep (ny)', 'Maxdep Δ'])
                
                st.dataframe(changed_rows[display_cols], use_container_width=True, hide_index=True)
                
                # Apply button
                if not invalid_rows.empty:
                    st.warning("Korrigera valideringsfelen innan du kan applicera")
                else:
                    if st.button(f"Applicera ändringar på {len(changed_rows)} {group_text if group_text else 'kategori(er)'}", type="primary"):
                        # Apply changes to original dataframe
                        modified_data = capbase_data.copy()
                        
                        for _, row in changed_rows.iterrows():
                            code = row['Kod']
                            new_ekdep = row['Ekdep (ny)']
                            new_maxdep = row['Maxdep (ny)']
                            
                            # Apply to all matching rows
                            mask = modified_data[group_encode] == code
                            modified_data.loc[mask, 'ekdep'] = new_ekdep
                            modified_data.loc[mask, 'maxdep'] = new_maxdep
                        
                        # Store in session state
                        st.session_state.lifetime_adjustments = {
                            'level': 'subcat' if use_subcat else 'cat',
                            'changes': changed_rows.to_dict('records'),
                            'data': modified_data
                        }
                        
                        st.rerun()
            else:
                st.info("Inga ändringar detekterade")

        
        # Show active adjustments status if they exist
        if 'lifetime_adjustments' in st.session_state and st.session_state.lifetime_adjustments:
            st.markdown("---")
            st.markdown("### ✓ Aktiva justeringar (används i beräkningen)")
            
            adjustments = st.session_state.lifetime_adjustments
            level_text = "subkategorinivå" if adjustments['level'] == 'subcat' else "kategorinivå"
            
            st.success(f"**Justeringar aktiva på {level_text}** - {len(adjustments['changes'])} ändringar applicerade")
            
            # Show which changes are active
            changes_df = pd.DataFrame(adjustments['changes'])
            
            # Select relevant columns to display
            display_cols = ['Kod']
            if 'Beskrivning' in changes_df.columns:
                display_cols.append('Beskrivning')
            display_cols.extend(['Ekonomisk livslängd', 'Ekdep (ny)', 'Ekdep Δ', 
                               'Maximal livslängd', 'Maxdep (ny)', 'Maxdep Δ'])
            
            available_cols = [col for col in display_cols if col in changes_df.columns]
            st.dataframe(changes_df[available_cols], use_container_width=True, hide_index=True)
            
            st.warning("⚠ **OBS:** Detta är ett scenario för intern analys, inte officiella regulatoriska värden")
        
        # Reset button if adjustments exist
        if 'lifetime_adjustments' in st.session_state and st.session_state.lifetime_adjustments:
            st.markdown("---")
            if st.button("Återställ till originalvärden"):
                st.session_state.lifetime_adjustments = {}
                st.rerun()
    
    # Return modified data if it exists in session state, otherwise original
    if 'lifetime_adjustments' in st.session_state and st.session_state.lifetime_adjustments:
        return st.session_state.lifetime_adjustments['data']
    else:
        return capbase_data