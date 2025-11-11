"""
parameter_adjustments.py - Parameterjusteringar för scenarioanalys

Funktioner för att justera:
- Normvärden (procentuellt per cat/subcat)
- Livslängder (ekonomisk/maximal per cat/subcat)
"""

import pandas as pd
import streamlit as st
from typing import Dict, Optional


# ============================================================================
# NORMVÄRDEJUSTERINGAR
# ============================================================================

def apply_normvalue_adjustments(
    capbase_data: pd.DataFrame, 
    adjustments: Dict[str, Dict[int, float]],
    level: str = 'cat'
) -> pd.DataFrame:
    """
    Applicerar procentuella normvärdejusteringar.
    
    Args:
        capbase_data: DataFrame med nuav_2022, cat_encode, subcat_encode
        adjustments: Dict med {code: multiplier}, ex: {5: 1.15, 7: 0.90}
        level: 'cat' eller 'subcat'
    
    Returns:
        DataFrame med justerade nuav_2022-värden
    
    Example:
        # Öka kategori 5 med 15%, minska kategori 7 med 10%
        adjust = {5: 1.15, 7: 0.90}
        df_adjusted = apply_normvalue_adjustments(df, adjust, level='cat')
    """
    df = capbase_data.copy()
    
    encode_col = f'{level}_encode'
    
    if encode_col not in df.columns:
        raise ValueError(f"Kolumn '{encode_col}' saknas i data")
    
    for code, multiplier in adjustments.items():
        mask = df[encode_col] == code
        df.loc[mask, 'nuav_2022'] *= multiplier
    
    return df


def render_normvalue_adjustment_ui(capbase_data: pd.DataFrame) -> Optional[Dict]:
    """
    Renderar UI för normvärdejustering.
    
    Returns:
        Dict med justeringar {level: str, adjustments: Dict[int, float]}
        eller None om inga justeringar
    """
    st.markdown("#### Justera normvärden (Parameters ID: 1.X.1)")
    with st.expander("Justera normvärden (procentuellt)", expanded=False):
        st.info("Justera NUAV för scenarioanalys genom procentuella förändringar. "
                "+15% → 1.15x, -10% → 0.90x")
        
        required_cols = ['cat_encode', 'cat', 'nuav_2022']
        missing_cols = [col for col in required_cols if col not in capbase_data.columns]
        if missing_cols:
            st.error(f"Data saknar obligatoriska kolumner: {', '.join(missing_cols)}")
            return None
        
        has_subcat = 'subcat_encode' in capbase_data.columns and 'subcat' in capbase_data.columns
        
        # Välj justeringsnivå
        st.markdown("**Välj justeringsnivå:**")
        
        if has_subcat:
            agg_level = st.radio(
                "Justera på:",
                ["Kategorinivå (cat)", "Subkategorinivå (subcat)"],
                horizontal=True,
                key="normvalue_agg_level"
            )
            use_subcat = (agg_level == "Subkategorinivå (subcat)")
        else:
            st.caption("Data innehåller endast kategorinivå")
            use_subcat = False
        
        # Bestäm gruppering
        if use_subcat:
            group_encode = 'subcat_encode'
            group_text = 'subcat'
            level = 'subcat'
        else:
            group_encode = 'cat_encode'
            group_text = 'cat'
            level = 'cat'
        
        # Aggregera nuvarande NUAV per vald nivå
        current_values = capbase_data.groupby([group_encode, group_text]).agg({
            'nuav_2022': 'sum'
        }).reset_index()
        
        current_values = current_values.rename(columns={
            group_encode: 'Kod',
            group_text: 'Beskrivning',
            'nuav_2022': 'Nuvarande NUAV (tkr)'
        })
        
        current_values = current_values.sort_values('Kod').reset_index(drop=True)
        
        # Lägg till justeringskolumn
        current_values['Justering (%)'] = 0
        
        # Redigerbar tabell
        st.markdown("**Redigera värden:**")
        st.caption("Ange procentuell förändring (positiv eller negativ)")
        
        edited_df = st.data_editor(
            current_values,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            disabled=['Kod', 'Beskrivning', 'Nuvarande NUAV (tkr)'],
            column_config={
                'Nuvarande NUAV (tkr)': st.column_config.NumberColumn(
                    'Nuvarande NUAV (tkr)',
                    format="%.0f"
                ),
                'Justering (%)': st.column_config.NumberColumn(
                    'Justering (%)',
                    min_value=-50,
                    max_value=100,
                    step=1,
                    format="%d"
                )
            },
            key="normvalue_editor"
        )
        
        # Detektera ändringar
        changes_made = not edited_df.equals(current_values)
        
        if changes_made:
            # Filtrera till endast ändrade rader
            changed_rows = edited_df[edited_df['Justering (%)'] != 0].copy()
            
            if not changed_rows.empty:
                # Visa vad som kommer ändras
                st.markdown("**Ändringar som kommer appliceras:**")
                
                changed_rows['Ny NUAV (tkr)'] = (
                    changed_rows['Nuvarande NUAV (tkr)'] * 
                    (1 + changed_rows['Justering (%)'] / 100)
                )
                changed_rows['Förändring (tkr)'] = (
                    changed_rows['Ny NUAV (tkr)'] - 
                    changed_rows['Nuvarande NUAV (tkr)']
                )
                
                display_cols = ['Kod', 'Beskrivning', 'Nuvarande NUAV (tkr)', 
                              'Justering (%)', 'Ny NUAV (tkr)', 'Förändring (tkr)']
                st.dataframe(changed_rows[display_cols], use_container_width=True, hide_index=True)
                
                # Konvertera till adjustment dict
                adjustments = {}
                for _, row in changed_rows.iterrows():
                    code = int(row['Kod'])
                    multiplier = 1 + (row['Justering (%)'] / 100)
                    adjustments[code] = multiplier
                
                # Spara i session state
                st.session_state.normvalue_adjustments = {
                    'level': level,
                    'adjustments': adjustments,
                    'changes': changed_rows.to_dict('records')
                }
                
                st.success(f"✓ {len(adjustments)} ändringar redo att appliceras")
                st.warning("⚠️ Detta är ett scenario för intern analys")
            else:
                st.info("Inga ändringar detekterade")
        
        # Visa aktiva justeringar
        if 'normvalue_adjustments' in st.session_state and st.session_state.normvalue_adjustments:
            st.markdown("---")
            st.markdown("### ✓ Aktiva justeringar")
            
            adjustments = st.session_state.normvalue_adjustments
            level_text = "subkategorinivå" if adjustments['level'] == 'subcat' else "kategorinivå"
            
            st.success(f"**Justeringar aktiva på {level_text}** - {len(adjustments['adjustments'])} ändringar")
            
            changes_df = pd.DataFrame(adjustments['changes'])
            display_cols = ['Kod', 'Beskrivning', 'Justering (%)', 'Ny NUAV (tkr)', 'Förändring (tkr)']
            available_cols = [col for col in display_cols if col in changes_df.columns]
            st.dataframe(changes_df[available_cols], use_container_width=True, hide_index=True)
            
            if st.button("Återställ normvärdejusteringar", key="reset_normvalue"):
                st.session_state.normvalue_adjustments = {}
                st.rerun()
        
        # Returnera justeringar om de finns
        if 'normvalue_adjustments' in st.session_state and st.session_state.normvalue_adjustments:
            return st.session_state.normvalue_adjustments
        
        return None


# ============================================================================
# LIVSLÄNGDSJUSTERINGAR
# ============================================================================

def apply_lifetime_adjustments(
    capbase_data: pd.DataFrame,
    adjustments: Dict[str, Dict[int, Dict[str, int]]],
    level: str = 'cat'
) -> pd.DataFrame:
    """
    Applicerar livslängdsjusteringar.
    
    Args:
        capbase_data: DataFrame med ekdep, maxdep, cat_encode, subcat_encode
        adjustments: Dict med {code: {'ekdep': new_val, 'maxdep': new_val}}
        level: 'cat' eller 'subcat'
    
    Returns:
        DataFrame med justerade ekdep/maxdep-värden
    
    Example:
        # Ändra kategori 5 till ekdep=25, maxdep=30
        adjust = {5: {'ekdep': 25, 'maxdep': 30}}
        df_adjusted = apply_lifetime_adjustments(df, adjust, level='cat')
    """
    df = capbase_data.copy()
    
    encode_col = f'{level}_encode'
    
    if encode_col not in df.columns:
        raise ValueError(f"Kolumn '{encode_col}' saknas i data")
    
    for code, values in adjustments.items():
        mask = df[encode_col] == code
        if 'ekdep' in values:
            df.loc[mask, 'ekdep'] = values['ekdep']
        if 'maxdep' in values:
            df.loc[mask, 'maxdep'] = values['maxdep']
    
    return df


def render_lifetime_adjustment_ui(capbase_data: pd.DataFrame) -> Optional[Dict]:
    """
    Renderar UI för livslängdsjustering.
    
    Returns:
        Dict med justeringar {level: str, adjustments: Dict[int, Dict]}
        eller None om inga justeringar
    """
    st.markdown("#### Justera livslängder (Tabell 1, ID: 1.1.1 - 1.17.2)")
    with st.expander("Justera ekonomisk/maximal livslängd", expanded=False):
        st.info("För scenarioanalys: Testa hur ändringar i regulatoriska livslängder påverkar kapitalkostnaden")
        
        required_cols = ['cat_encode', 'cat', 'ekdep', 'maxdep']
        missing_cols = [col for col in required_cols if col not in capbase_data.columns]
        if missing_cols:
            st.error(f"Data saknar obligatoriska kolumner: {', '.join(missing_cols)}")
            return None
        
        has_subcat = 'subcat_encode' in capbase_data.columns and 'subcat' in capbase_data.columns
        
        # Välj justeringsnivå
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
        
        # Bestäm gruppering
        if use_subcat:
            group_encode = 'subcat_encode'
            group_text = 'subcat'
            level = 'subcat'
        else:
            group_encode = 'cat_encode'
            group_text = 'cat'
            level = 'cat'
        
        # Aggregera nuvarande värden
        agg_dict = {'ekdep': 'first', 'maxdep': 'first'}
        current_values = capbase_data.groupby([group_encode, group_text]).agg(agg_dict).reset_index()
        
        current_values = current_values.rename(columns={
            group_encode: 'Kod',
            group_text: 'Beskrivning',
            'ekdep': 'Ekonomisk livslängd (ID: X.1)',
            'maxdep': 'Maximal livslängd (ID: X.2)'
        })
        
        current_values = current_values.sort_values('Kod').reset_index(drop=True)
        
        # Redigerbar tabell
        st.markdown("**Redigera värden:**")
        st.caption("Ändra värdena direkt i tabellen")
        
        edited_df = st.data_editor(
            current_values,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            disabled=['Kod', 'Beskrivning'],
            column_config={
                'Ekonomisk livslängd (ID: X.1)': st.column_config.NumberColumn(
                    'Ekonomisk livslängd (ID: X.1)',
                    min_value=1,
                    max_value=100,
                    step=1,
                    format="%d år"
                ),
                'Maximal livslängd (ID: X.2)': st.column_config.NumberColumn(
                    'Maximal livslängd (ID: X.2)',
                    min_value=1,
                    max_value=150,
                    step=1,
                    format="%d år"
                )
            },
            key="lifetime_editor"
        )
        
        # Detektera ändringar
        changes_made = not edited_df.equals(current_values)
        
        if changes_made:
            # Validera
            invalid_rows = edited_df[edited_df['Maximal livslängd'] < edited_df['Ekonomisk livslängd']]
            if not invalid_rows.empty:
                st.error(f"⚠️ {len(invalid_rows)} rad(er) har maximal livslängd < ekonomisk livslängd")
            
            # Visa ändringar
            st.markdown("**Ändringar som kommer appliceras:**")
            
            comparison = current_values.copy()
            comparison['Ekdep (ny)'] = edited_df['Ekonomisk livslängd']
            comparison['Maxdep (ny)'] = edited_df['Maximal livslängd']
            comparison['Ekdep Δ'] = comparison['Ekdep (ny)'] - comparison['Ekonomisk livslängd']
            comparison['Maxdep Δ'] = comparison['Maxdep (ny)'] - comparison['Maximal livslängd']
            
            changed_rows = comparison[(comparison['Ekdep Δ'] != 0) | (comparison['Maxdep Δ'] != 0)]
            
            if not changed_rows.empty:
                display_cols = ['Kod', 'Beskrivning', 'Ekonomisk livslängd', 'Ekdep (ny)', 'Ekdep Δ',
                              'Maximal livslängd', 'Maxdep (ny)', 'Maxdep Δ']
                st.dataframe(changed_rows[display_cols], use_container_width=True, hide_index=True)
                
                if not invalid_rows.empty:
                    st.warning("Korrigera valideringsfelen innan du kan applicera")
                else:
                    # Konvertera till adjustment dict
                    adjustments = {}
                    for _, row in changed_rows.iterrows():
                        code = int(row['Kod'])
                        adjustments[code] = {
                            'ekdep': int(row['Ekdep (ny)']),
                            'maxdep': int(row['Maxdep (ny)'])
                        }
                    
                    # Spara i session state
                    st.session_state.lifetime_adjustments = {
                        'level': level,
                        'adjustments': adjustments,
                        'changes': changed_rows.to_dict('records')
                    }
                    
                    st.success(f"✓ {len(adjustments)} ändringar redo att appliceras")
                    st.warning("⚠️ Detta är ett scenario för intern analys")
            else:
                st.info("Inga ändringar detekterade")
        
        # Visa aktiva justeringar
        if 'lifetime_adjustments' in st.session_state and st.session_state.lifetime_adjustments:
            st.markdown("---")
            st.markdown("### ✓ Aktiva justeringar")
            
            adjustments = st.session_state.lifetime_adjustments
            level_text = "subkategorinivå" if adjustments['level'] == 'subcat' else "kategorinivå"
            
            st.success(f"**Justeringar aktiva på {level_text}** - {len(adjustments['adjustments'])} ändringar")
            
            changes_df = pd.DataFrame(adjustments['changes'])
            display_cols = ['Kod', 'Beskrivning', 'Ekonomisk livslängd', 'Ekdep (ny)', 'Ekdep Δ',
                          'Maximal livslängd', 'Maxdep (ny)', 'Maxdep Δ']
            available_cols = [col for col in display_cols if col in changes_df.columns]
            st.dataframe(changes_df[available_cols], use_container_width=True, hide_index=True)
            
            if st.button("Återställ livslängdsjusteringar", key="reset_lifetime"):
                st.session_state.lifetime_adjustments = {}
                st.rerun()
        
        # Returnera justeringar om de finns
        if 'lifetime_adjustments' in st.session_state and st.session_state.lifetime_adjustments:
            return st.session_state.lifetime_adjustments
        
        return None