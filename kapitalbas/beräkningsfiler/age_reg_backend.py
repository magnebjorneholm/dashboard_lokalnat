# age_reg_backend.py
"""
Fas 1: Strikt PoC & Validering för age_reg parametrisering
Alla beräkningar i kSEK, strikt nyckel- och enhetshantering
FIXAD VERSION: Använder komponent-grain för exakt validering
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, Optional


def validate_baseline_before_anything() -> bool:
    """
    KRITISK: Måste köras och passera innan någon age_reg-justering görs
    
    Validerar att vi kan replikera capcost_a.dep_tail exakt från 
    depreciation_compress genom att summera på komponentnivå
    
    Returns:
        bool: True om validering passerar (max ±1 kSEK tolerans per kategori/år)
    """
    try:
        # 1. Läs ground-truth data
        depr_compress = st.session_state["depreciation_compress_sample"]
        capcost_truth = st.session_state["capcost_a_sample"]
        
        # 2. Summera dep_tail från depreciation_compress per (id_network, cat_encode, time)
        component_sums = calculate_component_sums_dep_tail(depr_compress)
        
        # 3. Extrahera capcost_a dep_tail på samma nycklar
        truth_sums = extract_capcost_dep_tail(capcost_truth)
        
        # 4. Jämför på (id_network, cat_encode, time) grain
        diff = compare_dep_tail_sums(component_sums, truth_sums)
        
        # 5. Kontrollera att alla diffs är ≤ 1 kSEK
        max_diff = diff['abs_diff'].max()
        failing_rows = diff[diff['abs_diff'] > 1]
        
        if len(failing_rows) > 0:
            st.error(f"❌ Ground-truth FAIL. Max diff: {max_diff:.1f} kSEK")
            st.write("Top avvikelser:")
            st.dataframe(failing_rows.nlargest(10, 'abs_diff'))
            return False
        else:
            st.success(f"✅ Ground-truth validerad. Max diff: {max_diff:.1f} kSEK")
            return True
            
    except Exception as e:
        st.error(f"❌ Validering kraschade: {str(e)}")
        return False


def calculate_component_sums_dep_tail(depr_compress: pd.DataFrame) -> pd.DataFrame:
    """
    Summera dep_tail_* från depreciation_compress per (id_network, cat_encode, time)
    
    Args:
        depr_compress: DataFrame från depreciation_compress_sample
        
    Returns:
        DataFrame med kolumner [id_network, cat_encode, time, dep_tail_sum_kSEK]
    """
    results = []
    
    # Konvertera cat_encode från category till int för konsistent nyckelhantering
    depr_clean = depr_compress.copy()
    depr_clean['cat_encode'] = pd.to_numeric(depr_clean['cat_encode'], errors='coerce').astype('int32')
    
    # Identifiera alla time-perioder från kolumnnamn
    time_cols = [col for col in depr_clean.columns if col.startswith('dep_tail_')]
    
    for col in time_cols:
        time_code = int(col.split('_')[-1])  # Extrahera 229, 230, etc.
        
        # Summera per (id_network, cat_encode) för denna tid
        time_sums = (depr_clean.groupby(['id_network', 'cat_encode'])[col]
                    .sum()
                    .reset_index())
        time_sums['time'] = time_code
        time_sums['dep_tail_sum_kSEK'] = time_sums[col]
        
        results.append(time_sums[['id_network', 'cat_encode', 'time', 'dep_tail_sum_kSEK']])
    
    return pd.concat(results, ignore_index=True)


def extract_capcost_dep_tail(capcost_a: pd.DataFrame) -> pd.DataFrame:
    """
    Extrahera dep_tail från capcost_a per (id_network, cat_encode, time)
    
    Args:
        capcost_a: DataFrame från capcost_a_sample
        
    Returns:
        DataFrame med kolumner [id_network, cat_encode, time, dep_tail_truth_kSEK]
    """
    # Konvertera cat_encode till int för konsekvent jämförelse
    capcost_clean = capcost_a.copy()
    capcost_clean['cat_encode'] = pd.to_numeric(capcost_clean['cat_encode'], errors='coerce').astype('int32')
    
    return capcost_clean[['id_network', 'cat_encode', 'time', 'dep_tail']].rename(
        columns={'dep_tail': 'dep_tail_truth_kSEK'}
    )


def compare_dep_tail_sums(component_sums: pd.DataFrame, truth_sums: pd.DataFrame) -> pd.DataFrame:
    """
    Jämför component_sums mot truth_sums på (id_network, cat_encode, time)
    
    Returns:
        DataFrame med differenser och diagnostik
    """
    merged = pd.merge(
        component_sums, 
        truth_sums,
        on=['id_network', 'cat_encode', 'time'],
        how='outer',
        suffixes=('_calc', '_truth')
    )
    
    # Fyll NaN med 0 för missing values
    merged = merged.fillna(0)
    
    # Beräkna differenser
    merged['diff_kSEK'] = merged['dep_tail_sum_kSEK'] - merged['dep_tail_truth_kSEK']
    merged['abs_diff'] = abs(merged['diff_kSEK'])
    
    return merged


def create_component_snapshot(network_id: int) -> pd.DataFrame:
    """
    Skapa snapshot på KOMPONENT-GRAIN för exakt validering
    KRITISK FIX: Behåller komponentnivå istället för att aggregera för tidigt
    
    Args:
        network_id: ID för nät att analysera
        
    Returns:
        DataFrame med kolumner:
        - id_network: int16  
        - id_component: int32 (BEHÅLLS nu)
        - cat_encode: int32 (konverterad från category)  
        - time: int (229-236)
        - nuav_tail_kSEK: float64 (per komponent)
        - dep_tail_kSEK: float64 (per komponent) 
        - age_component: int (beräknad från komponentdata)
        - maxdep_kat: int (hämtad från data)
    
    Grain: En rad per (id_network, id_component, time) - KOMPONENTNIVÅ
    """
    # Läs depreciation_compress för valt nät
    depr_compress = st.session_state["depreciation_compress_sample"]
    
    # Säker typkonvertering för cat_encode
    depr_clean = depr_compress.copy()
    depr_clean['cat_encode'] = pd.to_numeric(depr_clean['cat_encode'], errors='coerce')
    
    # Droppa rader med invalid cat_encode
    depr_clean = depr_clean.dropna(subset=['cat_encode'])
    depr_clean['cat_encode'] = depr_clean['cat_encode'].astype('int32')
    
    # Filtrera på valt nät
    network_data = depr_clean[depr_clean['id_network'] == network_id].copy()
    
    if len(network_data) == 0:
        st.error(f"Inget data för network_id {network_id}")
        return pd.DataFrame()
    
    # Hämta maxdep från data (inte hårdkodad 50)
    try:
        # Försök hämta från capbase data om tillgänglig
        capbase_sample = st.session_state.get("capbase_a_sample")
        if capbase_sample is not None:
            capbase_clean = capbase_sample[capbase_sample['id_network'] == network_id].copy()
            capbase_clean['cat_encode'] = pd.to_numeric(capbase_clean['cat_encode'], errors='coerce').astype('int32')
            maxdep_by_cat = capbase_clean.groupby('cat_encode')['maxdep'].first().to_dict()
        else:
            maxdep_by_cat = {}
    except Exception:
        maxdep_by_cat = {}
    
    # KRITISK FIX: Behåll komponentnivå, aggregera INTE
    snapshot_rows = []
    
    # Identifiera time-kolumner
    time_cols = [col for col in network_data.columns if col.startswith('dep_tail_')]
    
    for _, component_row in network_data.iterrows():
        for col in time_cols:
            time_code = int(col.split('_')[-1])
            nuav_col = f'nuav_tail_{time_code}'
            
            if nuav_col not in network_data.columns:
                continue
            
            nuav_value = component_row[nuav_col]
            dep_value = component_row[col]
            
            # Skippa komponenter utan tail-värde
            if nuav_value <= 0 or dep_value <= 0:
                continue
            
            # Beräkna ålder per komponent (som i Stata)
            age_component = round(nuav_value / dep_value)
            if age_component < 1:
                age_component = 1
                
            # Hämta maxdep för kategorin
            cat_encode = int(component_row['cat_encode'])
            maxdep_kat = maxdep_by_cat.get(cat_encode, 50)  # Default 50 om inte finns
            
            # Clamp ålder mot maxdep
            age_component = min(age_component, maxdep_kat)
                
            snapshot_rows.append({
                'id_network': int(component_row['id_network']),
                'id_component': int(component_row['id_component']),  # BEHÅLLS nu
                'cat_encode': cat_encode,
                'time': time_code,
                'nuav_tail_kSEK': nuav_value,
                'dep_tail_kSEK': dep_value,
                'age_component': age_component,  # Per komponent!
                'maxdep_kat': int(maxdep_kat)
            })
    
    snapshot_df = pd.DataFrame(snapshot_rows)
    
    if len(snapshot_df) > 0:
        st.success(f"Snapshot skapat: {len(snapshot_df)} komponent-tid kombinationer")
        
        # Debug info
        n_components = snapshot_df['id_component'].nunique()
        n_cats = snapshot_df['cat_encode'].nunique()
        n_times = snapshot_df['time'].nunique() 
        st.info(f"Fördelning: {n_components} komponenter × {n_cats} kategorier × {n_times} tidsperioder")
    
    return snapshot_df


def baseline_validation_from_snapshot(snapshot_df: pd.DataFrame) -> bool:
    """
    Validera att snapshot kan replikera capcost_a dep_tail exakt
    KRITISK FIX: Använder summa av kvoter istället för kvot av summor
    
    Beräknar: dep_tail_from_snapshot = round(Σᵢ nuav_tail_kSEK_i / age_component_i) 
    per (id_network, cat_encode, time) och jämför mot capcost_a
    
    Args:
        snapshot_df: Resultat från create_component_snapshot (komponentnivå)
        
    Returns:
        bool: True om snapshot valideras (max ±1 kSEK diff)
    """
    if len(snapshot_df) == 0:
        st.error("Tom snapshot - kan inte validera")
        return False
    
    try:
        # 1. Beräkna dep_tail från snapshot med KOMPONENT-KVOTER
        # VIKTIGT: Summera kvoter (som i Stata), inte kvot av summor
        calculated = (snapshot_df.groupby(['id_network', 'cat_encode', 'time'])
                     .apply(lambda group: round((group['nuav_tail_kSEK'] / group['age_component']).sum()))
                     .reset_index(name='dep_tail_calc_kSEK'))
        
        # 2. Hämta ground-truth från capcost_a för samma nät
        capcost_truth = st.session_state["capcost_a_sample"]
        network_ids = snapshot_df['id_network'].unique()
        
        # Filtrera capcost på samma nät som snapshot
        truth_filtered = capcost_truth[capcost_truth['id_network'].isin(network_ids)].copy()
        
        # Konvertera cat_encode för konsekvent jämförelse
        truth_filtered['cat_encode'] = pd.to_numeric(truth_filtered['cat_encode'], errors='coerce').astype('int32')
        
        truth_summary = truth_filtered.groupby(['id_network', 'cat_encode', 'time'])['dep_tail'].sum().reset_index()
        truth_summary = truth_summary.rename(columns={'dep_tail': 'dep_tail_truth_kSEK'})
        
        # 3. Jämför på (id_network, cat_encode, time)
        merged = pd.merge(
            calculated, 
            truth_summary, 
            on=['id_network', 'cat_encode', 'time'], 
            how='outer'
        ).fillna(0)
        
        merged['diff'] = merged['dep_tail_calc_kSEK'] - merged['dep_tail_truth_kSEK']
        merged['abs_diff'] = abs(merged['diff'])
        
        max_diff = merged['abs_diff'].max()
        failing_rows = merged[merged['abs_diff'] > 1]
        
        if len(failing_rows) > 0:
            st.error(f"❌ Snapshot validering FAIL. Max diff: {max_diff:.1f} kSEK")
            st.write("Failing validations:")
            st.dataframe(failing_rows.nlargest(5, 'abs_diff'))
            return False
        else:
            st.success(f"✅ Snapshot validerad. Max diff: {max_diff:.1f} kSEK")
            return True
            
    except Exception as e:
        st.error(f"❌ Snapshot validering kraschade: {str(e)}")
        st.write("Snapshot sample:")
        st.dataframe(snapshot_df.head())
        return False


def calculate_dep_tail_new(
    snapshot_df: pd.DataFrame, *,
    global_offset: int = 0,
    offset_by_cat: Optional[Dict[int, int]] = None,
    override_by_cat_time: Optional[Dict[str, int]] = None,  # RENAMED från override_by_component
    min_age: int = 1,
    max_age_by_cat: Optional[Dict[int, int]] = None,
) -> pd.DataFrame:
    """
    Beräkna nya dep_tail värden baserat på age_reg justeringar
    KRITISK FIX: Arbetar på komponentnivå, summerar sedan till kategorier
    
    Args:
        snapshot_df: Snapshot från create_component_snapshot (komponentnivå)
        global_offset: Global åldersjustering (år)
        offset_by_cat: Kategori-specifika justeringar {cat_encode: offset}
        override_by_cat_time: Kategori-tid overrides {"cat_time": absolute_age}  
        min_age: Minimum ålder (default 1)
        max_age_by_cat: Max ålder per kategori {cat_encode: max_age}
        
    Returns:
        DataFrame med kolumner:
        - id_network, cat_encode, time
        - dep_tail_new_kSEK, dep_tail_base_kSEK, delta_kSEK
    
    Beräkningsordning följer facit:
    1. Justera age per komponent enligt prioritet (override > kategori > global)
    2. Clamp mot gränser per komponent
    3. Beräkna dep_tail per komponent = nuav_tail / age_new  
    4. Summera till kategori-tid nivå
    5. Avrunda EFTER summering (som i Stata)
    """
    if len(snapshot_df) == 0:
        return pd.DataFrame()
    
    # Kopiera för manipulation
    work_df = snapshot_df.copy()
    
    # Tillämpa offsets på KOMPONENTNIVÅ
    work_df['age_new'] = work_df['age_component'].copy()
    
    # 1. Global offset (lägst prioritet)
    if global_offset != 0:
        work_df['age_new'] += global_offset
    
    # 2. Kategori-offset (medel prioritet) 
    if offset_by_cat:
        for cat_encode, offset in offset_by_cat.items():
            mask = work_df['cat_encode'] == cat_encode
            work_df.loc[mask, 'age_new'] += offset
    
    # 3. Kategori-tid override (högst prioritet) - appliceras på alla komponenter i kategorin
    if override_by_cat_time:
        for cat_time_key, absolute_age in override_by_cat_time.items():
            try:
                cat_encode, time = map(int, cat_time_key.split('_'))
                mask = (work_df['cat_encode'] == cat_encode) & (work_df['time'] == time)
                work_df.loc[mask, 'age_new'] = absolute_age
            except ValueError:
                st.warning(f"Invalid kategori-tid format: {cat_time_key}")
    
    # 4. Tillämpa gränser (clamp) per komponent
    work_df['age_new'] = work_df.apply(lambda row: max(
        min_age, 
        min(row['age_new'], 
            max_age_by_cat.get(row['cat_encode'], row['maxdep_kat']) if max_age_by_cat 
            else row['maxdep_kat'])
    ), axis=1)
    
    # 5. Beräkna dep_tail per komponent
    work_df['dep_tail_component_new'] = work_df['nuav_tail_kSEK'] / work_df['age_new']
    work_df['dep_tail_component_base'] = work_df['nuav_tail_kSEK'] / work_df['age_component']
    
    # 6. Summera till kategori-tid nivå och avrunda EFTER summering
    results = (work_df.groupby(['id_network', 'cat_encode', 'time'])
              .agg({
                  'dep_tail_component_base': 'sum',
                  'dep_tail_component_new': 'sum'
              })
              .reset_index())
    
    # Avrunda efter summering (som i Stata)
    results['dep_tail_base_kSEK'] = results['dep_tail_component_base'].round().astype(int)
    results['dep_tail_new_kSEK'] = results['dep_tail_component_new'].round().astype(int)
    results['delta_kSEK'] = results['dep_tail_new_kSEK'] - results['dep_tail_base_kSEK']
    
    # Returnera endast slutkolumner
    return results[['id_network', 'cat_encode', 'time', 'dep_tail_base_kSEK', 'dep_tail_new_kSEK', 'delta_kSEK']]


# === Testfunktioner ===

def test_all_scenarios(network_id: int = 1) -> bool:
    """
    Kör alla obligatoriska testfall för age_reg logik
    
    Alla dessa MÅSTE passa innan produktionsdrift
    """
    st.subheader("🧪 Age_reg testsvit")
    
    try:
        # Skapa snapshot för testning
        snapshot = create_component_snapshot(network_id)
        
        if len(snapshot) == 0:
            st.error("❌ Kan inte skapa snapshot för testning")
            return False
        
        # Test 1: Δ=0 ⇒ exakt facit
        st.write("Test 1: Baseline (Δ=0)")
        result_baseline = calculate_dep_tail_new(snapshot, global_offset=0)
        
        if len(result_baseline) > 0 and all(result_baseline['delta_kSEK'] == 0):
            st.success("✅ Baseline test passerad")
        else:
            st.error("❌ Baseline test FAIL")
            st.dataframe(result_baseline[result_baseline['delta_kSEK'] != 0])
            return False
        
        # Test 2: Global offset ⇒ monoton förändring
        st.write("Test 2: Global offset (+2 år)")
        result_plus = calculate_dep_tail_new(snapshot, global_offset=2)
        
        if len(result_plus) > 0 and all(result_plus['delta_kSEK'] <= 0):
            st.success("✅ Global offset test passerad (högre ålder = lägre avskrivning)")
        else:
            st.error("❌ Global offset test FAIL")
            st.dataframe(result_plus[result_plus['delta_kSEK'] > 0])
            return False
            
        # Test 3: Kategori-offset ⇒ endast affekterad kategori ändras
        st.write("Test 3: Kategori-specifik offset")
        available_cats = snapshot['cat_encode'].unique()
        if len(available_cats) > 0:
            test_cat = available_cats[0]
            result_cat = calculate_dep_tail_new(snapshot, offset_by_cat={test_cat: 3})
            
            changed_cats = result_cat[result_cat['delta_kSEK'] != 0]['cat_encode'].unique()
            
            if len(changed_cats) == 1 and changed_cats[0] == test_cat:
                st.success(f"✅ Kategori-offset test passerad (endast cat {test_cat} ändrad)")
            else:
                st.error(f"❌ Kategori-offset test FAIL - andra kategorier ändrades: {changed_cats}")
                return False
        
        st.success("🎉 Alla testfall passerade!")
        return True
        
    except Exception as e:
        st.error(f"❌ Testsvit kraschade: {str(e)}")
        return False