import streamlit as st
import pandas as pd
from kapitalbas.beräkningsfiler.age_reg_backend import (  # KORRIGERAD IMPORT
    validate_baseline_before_anything,
    create_component_snapshot,
    baseline_validation_from_snapshot,
    calculate_dep_tail_new,
    test_all_scenarios
)



def render_component_overrides(snapshot_df, selected_category=None):
    """Separat expander för komponent-overrides - FIXAD VERSION"""
    with st.expander("🔬 Avancerat: Kategori-tid specifika overrides"):
        st.write("Sätt absolut ålder för specifika kategori-tidskombinationer (överrider kategori + global)")
        
        component_overrides = {}
        
        # Filtrera på kategori om vald
        if selected_category:
            filtered_snapshot = snapshot_df[snapshot_df['cat_encode'] == selected_category]
        else:
            filtered_snapshot = snapshot_df
            
        # Gruppera per kategori-tid för att visa aggregerade värden
        cat_time_summary = (filtered_snapshot.groupby(['cat_encode', 'time'])
                           .agg({
                               'age_component': 'mean',  # Genomsnittlig ålder
                               'nuav_tail_kSEK': 'sum',  # Total NUAV
                               'id_component': 'nunique',  # Antal komponenter
                               'maxdep_kat': 'first'
                           })
                           .reset_index())
            
        if len(cat_time_summary) < 20:  # Visa bara för mindre dataset
            for _, row in cat_time_summary.iterrows():
                cat = int(row['cat_encode'])
                time = int(row['time'])
                key = f"{cat}_{time}"
                avg_age = row['age_component']
                total_nuav = row['nuav_tail_kSEK']
                n_components = int(row['id_component'])
                maxdep = int(row['maxdep_kat'])
                
                st.write(f"**Kategori {cat}, Period {time}:**")
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    if st.checkbox(f"Override kat {cat}, tid {time}", key=f"comp_check_{key}"):
                        new_age = st.number_input(
                            f"Ny ålder för kat {cat}, tid {time}:",
                            min_value=1,
                            max_value=maxdep,  # FIX: Använd rätt fältnamn
                            value=int(avg_age),
                            key=f"comp_age_{key}"
                        )
                        component_overrides[key] = new_age
                
                with col2:
                    st.metric("Avg ålder", f"{avg_age:.1f}")
                    st.metric("Komponenter", n_components)
                    st.metric("NUAV", f"{total_nuav:.0f} kSEK")

        # Spara overrides i session state
        st.session_state['age_reg_component_overrides'] = component_overrides
        
        # FIX: Returnera overrides
        return component_overrides


def show_age_reg_view():
    """
    Huvudfunktion för age_reg sektion i dashboard
    """
    st.header("🔧 Age_reg Parametrisering")
    st.write("Justera regulatoriska åldrar och se påverkan på kapitalkostnader")
    
    # === GRUND-VALIDERING (Obligatorisk) ===
    st.subheader("1. Ground-truth Validering")
    st.write("Kontrollerar att vi kan replikera capcost_a.dep_tail exakt från komponentnivå")
    
    if st.button("🔍 Kör grund-validering"):
        with st.spinner("Validerar..."):
            baseline_ok = validate_baseline_before_anything()
            
            if not baseline_ok:
                st.error("⚠️ Ground-truth validering misslyckades. Åtgärda innan fortsättning.")
                st.stop()
    
    st.divider()
    
    # === NÄTVÄLJARE ===
    st.subheader("2. Välj nät för analys") 
    
    # Hämta tillgängliga nät från sample-data
    available_networks = get_available_networks()
    selected_network = st.selectbox(
        "Välj nät:", 
        available_networks,
        format_func=lambda x: f"Nät {x}"
    )
    
    # Årsväljare
    time_range = [229, 230, 231, 232, 233, 234, 235, 236]
    selected_years = st.multiselect(
        "Välj år:", 
        time_range, 
        default=time_range[:4],  # Första 4 åren som default
        format_func=lambda x: f"20{24 + (x-229)//2}h{((x-229)%2)+1}"  # FIX: Korrekt årsmapping
    )
    
    if not selected_years:
        st.warning("Välj minst ett år för analys")
        return
    
    st.divider()
    
    # === SKAPA SNAPSHOT OCH VALIDERA ===
    st.subheader("3. Snapshot och validering")
    
    if st.button("📸 Skapa komponent-snapshot"):
        with st.spinner(f"Skapar snapshot för nät {selected_network}..."):
            snapshot = create_component_snapshot(selected_network)
            
            if len(snapshot) == 0:
                st.error(f"Inga tail-komponenter hittades för nät {selected_network}")
                return
            
            st.session_state['age_reg_snapshot'] = snapshot
            st.success(f"✅ Snapshot skapat: {len(snapshot)} komponent-tid kombinationer")
            
            # Visa snapshot-översikt
            st.write("**Snapshot översikt:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Kategorier", snapshot['cat_encode'].nunique())
            with col2: 
                st.metric("Komponenter", snapshot['id_component'].nunique())  # FIX: Rätt kolumn
            with col3:
                st.metric("Total NUAV", f"{snapshot['nuav_tail_kSEK'].sum():.0f} kSEK")
            
            # Validera snapshot
            st.write("**Snapshot-validering:**")
            snapshot_valid = baseline_validation_from_snapshot(snapshot)
            
            if snapshot_valid:
                st.session_state['snapshot_validated'] = True
    
    # Kontrollera att snapshot finns och är validerat
    if 'age_reg_snapshot' not in st.session_state:
        st.info("👆 Skapa snapshot för att fortsätta")
        return
        
    if not st.session_state.get('snapshot_validated', False):
        st.warning("⚠️ Snapshot inte validerat - fortsätt med försiktighet")
    
    snapshot = st.session_state['age_reg_snapshot']
    
    st.divider()
    
    # === ÅLDERSFÖRDELNING ===
    st.subheader("4. Nuvarande åldersfördelning")
    
    show_age_distribution(snapshot, selected_years)
    
    st.divider()
    
    # === PARAMETRISERINGSSEKTION ===
    st.subheader("5. Justera regulatoriska åldrar")
    
    # Baseline-check indikator
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✅ Δ=0 Check"):
            result_baseline = calculate_dep_tail_new(snapshot, global_offset=0)
            if len(result_baseline) > 0 and all(result_baseline['delta_kSEK'] == 0):
                st.success("✅ Baseline OK")
            else:
                st.error("❌ Baseline FAIL")
    
    # Global justering
    st.write("**Global justering:**")
    global_offset = st.slider(
        "Justera alla åldrar (år):", 
        min_value=-5, 
        max_value=5, 
        value=0,
        help="Positiv = äldre komponenter, lägre avskrivning"
    )
    
    # Kategori-justeringar
    st.write("**Kategori-specifika justeringar:**")
    available_categories = sorted(snapshot['cat_encode'].unique())
    
    category_adjustments = {}
    
    with st.expander("🔧 Kategori-offsets", expanded=len(available_categories) <= 5):
        for cat in available_categories:
            cat_name = get_category_name(cat)  # TODO: Implementera kategorinamn-lookup
            
            # Visa statistik för kategorin
            cat_data = snapshot[snapshot['cat_encode'] == cat]
            avg_age = cat_data['age_component'].mean()
            total_nuav = cat_data['nuav_tail_kSEK'].sum()
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                offset = st.slider(
                    f"Kategori {cat} ({cat_name}):",
                    min_value=-10,
                    max_value=10, 
                    value=0,
                    key=f"cat_offset_{cat}",
                    help=f"Avg ålder: {avg_age:.1f}, NUAV: {total_nuav:.0f} kSEK"
                )
                
                if offset != 0:
                    category_adjustments[cat] = offset
            
            with col2:
                st.metric("Avg ålder", f"{avg_age:.1f}")
    
    # Komponent-overrides (avancerat)
    component_overrides = render_component_overrides(snapshot, selected_category=None)
    
    st.divider()
    
    # === BERÄKNING OCH RESULTAT ===
    st.subheader("6. Beräkna nya kapitalkostnader")
    
    if st.button("🚀 Beräkna påverkan"):
        with st.spinner("Beräknar nya dep_tail värden..."):
            
            # Kör beräkning
            results = calculate_dep_tail_new(
                snapshot,
                global_offset=global_offset,
                offset_by_cat=category_adjustments if category_adjustments else None,
                override_by_cat_time=component_overrides if component_overrides else None  # RENAMED parameter
            )
            
            if len(results) == 0:
                st.error("Inga resultat genererade")
                return
            
            # Spara resultat
            st.session_state['age_reg_results'] = results
            
            # Visa resultat
            display_results(results, selected_years)
    
    # Visa sparade resultat om de finns
    if 'age_reg_results' in st.session_state:
        st.subheader("💾 Senaste resultat") 
        display_results(st.session_state['age_reg_results'], selected_years)
    
    st.divider()
    
    # === TESTSVIT ===
    with st.expander("🧪 Testsvit (utveckling)"):
        st.write("Kör alla testfall för att validera age_reg logik")
        
        if st.button("🔬 Kör alla tester"):
            test_all_scenarios(selected_network)


def get_available_networks() -> list[int]:
    """Hämta tillgängliga nät från sample-data"""
    try:
        depr_sample = st.session_state["depreciation_compress_sample"]
        return sorted(depr_sample['id_network'].unique().tolist())
    except Exception as e:
        st.error(f"Kunde inte hämta nät: {e}")
        return [1, 3035]  # Fallback från CSV


def get_category_name(cat_encode: int) -> str:
    """
    TODO: Implementera lookup från kategorimappning
    För nu: returnera enkel beskrivning
    """
    category_names = {
        1: "Transformatorer",
        2: "Ledningar",
        3: "Stationer", 
        # Lägg till fler från din kategorimappning
    }
    return category_names.get(cat_encode, f"Kategori_{cat_encode}")


def show_age_distribution(snapshot: pd.DataFrame, selected_years: list[int]):
    """Visa åldersfördelning per kategori - FIXAD VERSION"""
    
    # Filtrera på valda år
    filtered_snapshot = snapshot[snapshot['time'].isin(selected_years)]
    
    if len(filtered_snapshot) == 0:
        st.warning("Inga data för valda år")
        return
    
    # Gruppera per kategori och visa fördelning
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Per kategori:**")
        cat_summary = (filtered_snapshot.groupby('cat_encode')
                      .agg({
                          'age_component': ['mean', 'min', 'max'],  # FIX: Rätt kolumnnamn
                          'nuav_tail_kSEK': 'sum',
                          'id_component': 'nunique'  # FIX: Rätt kolumnnamn
                      })
                      .round(1))
        
        # Platta till kolumnnamn
        cat_summary.columns = ['Avg_ålder', 'Min_ålder', 'Max_ålder', 'Total_NUAV_kSEK', 'Antal_komp']
        st.dataframe(cat_summary)
    
    with col2:
        st.write("**Åldershistogram:**")
        import plotly.express as px
        
        # Skapa histogram över åldrar viktade med NUAV
        hist_data = []
        for _, row in filtered_snapshot.iterrows():
            # Lägg till en rad per kSEK för viktning i histogram
            weight = max(1, int(row['nuav_tail_kSEK'] / 100))  # Skala ned för prestanda
            hist_data.extend([row['age_component']] * weight)
        
        if hist_data:
            fig = px.histogram(
                x=hist_data,
                nbins=20,
                title="NUAV-viktad åldersfördelning",
                labels={'x': 'Ålder (år)', 'y': 'NUAV-vikt'}
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)


def display_results(results: pd.DataFrame, selected_years: list[int]):
    """Visa beräkningsresultat i tabellformat"""
    
    # Filtrera resultat på valda år
    filtered_results = results[results['time'].isin(selected_years)]
    
    if len(filtered_results) == 0:
        st.warning("Inga resultat för valda år")
        return
    
    # Huvudresultattabell
    st.write("**Resultat per kategori och år:**")
    
    # Formatera för visning
    display_df = filtered_results.copy()
    display_df['År'] = display_df['time'].apply(lambda x: f"20{24 + (x-229)//2}h{((x-229)%2)+1}")
    display_df['Kategori'] = display_df['cat_encode'].apply(get_category_name)
    
    # Välj kolumner för visning
    display_cols = [
        'År', 'Kategori', 'cat_encode',
        'dep_tail_base_kSEK', 'dep_tail_new_kSEK', 'delta_kSEK'
    ]
    
    display_df = display_df[display_cols].rename(columns={
        'dep_tail_base_kSEK': 'Bas (kSEK)',
        'dep_tail_new_kSEK': 'Ny (kSEK)', 
        'delta_kSEK': 'Δ (kSEK)',
        'cat_encode': 'Cat#'
    })
    
    # Styla tabell med färgkodning
    def style_delta(val):
        if val > 0:
            return 'color: red'
        elif val < 0:
            return 'color: green'
        return ''
    
    styled_df = display_df.style.format({
        'Bas (kSEK)': '{:.0f}',
        'Ny (kSEK)': '{:.0f}',
        'Δ (kSEK)': '{:+.0f}'
    }).applymap(style_delta, subset=['Δ (kSEK)'])
    
    st.dataframe(styled_df, use_container_width=True)
    
    # Sammanfattningsstatistik
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_base = filtered_results['dep_tail_base_kSEK'].sum()
        st.metric("Total bas", f"{total_base:.0f} kSEK")
    
    with col2:
        total_new = filtered_results['dep_tail_new_kSEK'].sum() 
        st.metric("Total ny", f"{total_new:.0f} kSEK")
    
    with col3:
        total_delta = filtered_results['delta_kSEK'].sum()
        st.metric("Total Δ", f"{total_delta:+.0f} kSEK")
        
    with col4:
        if total_base > 0:
            pct_change = (total_delta / total_base) * 100
            st.metric("Δ %", f"{pct_change:+.1f}%")
    
    # Visa påverkade kategorier
    changed_cats = filtered_results[filtered_results['delta_kSEK'] != 0]
    if len(changed_cats) > 0:
        st.write(f"**Påverkade kategorier:** {len(changed_cats)} av {len(filtered_results)}")
        
        # Top förändringar
        top_changes = changed_cats.nlargest(3, 'delta_kSEK')[['cat_encode', 'delta_kSEK']]
        if len(top_changes) > 0:
            st.write("Största ökningar:", ", ".join([f"Cat {row['cat_encode']}: +{row['delta_kSEK']:.0f}" for _, row in top_changes.iterrows()]))
            
        bottom_changes = changed_cats.nsmallest(3, 'delta_kSEK')[['cat_encode', 'delta_kSEK']]
        if len(bottom_changes) > 0:
            st.write("Största minskningar:", ", ".join([f"Cat {row['cat_encode']}: {row['delta_kSEK']:.0f}" for _, row in bottom_changes.iterrows()]))
    
    # Export-möjlighet
    st.download_button(
        label="📥 Ladda ned resultat (CSV)",
        data=display_df.to_csv(index=False),
        file_name=f"age_reg_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )