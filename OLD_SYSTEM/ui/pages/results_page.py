"""
Results Page - Steg 4
Visar resultat med breakdown och visualiseringar
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, Optional


def create_waterfall_chart(results_data: Dict[str, float]) -> go.Figure:
    """
    Skapar waterfall-diagram för intäktsram breakdown.
    
    Args:
        results_data: Dict med komponenter och värden
        
    Returns:
        Plotly figure
    """
    kapitalkostnad = results_data.get('kapitalkostnad', 0)
    opaverkbara = results_data.get('opaverkbara', 0)
    paverkbara_fore = results_data.get('paverkbara_fore', 0)
    effektiviseringskrav = results_data.get('effektiviseringskrav', 0)
    paverkbara_efter = paverkbara_fore - effektiviseringskrav
    kvalitetsjustering = results_data.get('kvalitetsjustering', 0)
    total = kapitalkostnad + opaverkbara + paverkbara_efter + kvalitetsjustering
    
    fig = go.Figure(go.Waterfall(
        name="Intäktsram",
        orientation="v",
        measure=["relative", "relative", "relative", "relative", "relative", "total"],
        x=["Kapitalkostnad", "Opåverkbara", "Påverkbara (före)", 
           "Effektiviseringskrav", "Kvalitet", "Total intäktsram"],
        y=[kapitalkostnad, opaverkbara, paverkbara_fore, 
           -effektiviseringskrav, kvalitetsjustering, total],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#1f4e79"}},
        decreasing={"marker": {"color": "#c65d47"}},
        totals={"marker": {"color": "#2c5f8d"}}
    ))
    
    fig.update_layout(
        title="Intäktsram breakdown",
        showlegend=False,
        height=500,
        yaxis_title="Tkr",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1f4e79')
    )
    
    return fig


def render_results_page(
    case_definition: Dict[str, Any],
    results: Optional[Dict[str, Any]] = None
) -> None:
    """
    Renderar results-sida med breakdown och visualiseringar.
    
    Args:
        case_definition: Case definition
        results: Beräknade resultat (optional)
    """
    st.title("Resultat")
    
    case_name = case_definition.get('name', 'Unnamed case')
    st.markdown(f"**Case:** {case_name}")
    
    if results is None:
        st.info("Inga resultat än. Kör beräkningen först.")
        if st.button("← Tillbaka till konfiguration"):
            st.session_state.page = 'config'
            st.rerun()
        return
    
    st.markdown("---")
    
    intaktsram_data = results.get('intaktsram', {})
    
    if intaktsram_data:
        total_intaktsram = intaktsram_data.get('total', 0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total intäktsram",
                f"{total_intaktsram:,.0f} tkr"
            )
        
        with col2:
            baseline = results.get('baseline_intaktsram', total_intaktsram)
            delta = total_intaktsram - baseline
            st.metric(
                "Förändring",
                f"{delta:+,.0f} tkr",
                delta=f"{delta / baseline * 100:+.2f}%" if baseline > 0 else None
            )
        
        with col3:
            st.metric(
                "Baseline",
                f"{baseline:,.0f} tkr"
            )
        
        st.markdown("---")
        
        st.markdown("### Komponenter")
        
        components_df = pd.DataFrame([
            {
                'Komponent': 'Kapitalkostnad',
                'Värde (tkr)': intaktsram_data.get('kapitalkostnad', 0),
                'Andel (%)': intaktsram_data.get('kapitalkostnad', 0) / total_intaktsram * 100 if total_intaktsram > 0 else 0
            },
            {
                'Komponent': 'Opåverkbara kostnader',
                'Värde (tkr)': intaktsram_data.get('opaverkbara', 0),
                'Andel (%)': intaktsram_data.get('opaverkbara', 0) / total_intaktsram * 100 if total_intaktsram > 0 else 0
            },
            {
                'Komponent': 'Påverkbara (före effkrav)',
                'Värde (tkr)': intaktsram_data.get('paverkbara_fore', 0),
                'Andel (%)': intaktsram_data.get('paverkbara_fore', 0) / total_intaktsram * 100 if total_intaktsram > 0 else 0
            },
            {
                'Komponent': 'Effektiviseringskrav',
                'Värde (tkr)': -intaktsram_data.get('effektiviseringskrav', 0),
                'Andel (%)': -intaktsram_data.get('effektiviseringskrav', 0) / total_intaktsram * 100 if total_intaktsram > 0 else 0
            },
            {
                'Komponent': 'Påverkbara (efter effkrav)',
                'Värde (tkr)': intaktsram_data.get('paverkbara_efter', 0),
                'Andel (%)': intaktsram_data.get('paverkbara_efter', 0) / total_intaktsram * 100 if total_intaktsram > 0 else 0
            },
            {
                'Komponent': 'Kvalitetsjustering',
                'Värde (tkr)': intaktsram_data.get('kvalitetsjustering', 0),
                'Andel (%)': intaktsram_data.get('kvalitetsjustering', 0) / total_intaktsram * 100 if total_intaktsram > 0 else 0
            }
        ])
        
        st.dataframe(
            components_df.style.format({
                'Värde (tkr)': '{:,.0f}',
                'Andel (%)': '{:.2f}%'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        
        st.markdown("### Visualisering")
        
        waterfall_data = {
            'kapitalkostnad': intaktsram_data.get('kapitalkostnad', 0),
            'opaverkbara': intaktsram_data.get('opaverkbara', 0),
            'paverkbara_fore': intaktsram_data.get('paverkbara_fore', 0),
            'effektiviseringskrav': intaktsram_data.get('effektiviseringskrav', 0),
            'kvalitetsjustering': intaktsram_data.get('kvalitetsjustering', 0)
        }
        
        fig = create_waterfall_chart(waterfall_data)
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.warning("Ingen intäktsram-data i resultat")
    
    st.markdown("---")
    
    st.markdown("### Metadata")
    
    # Prefer canonical case_definition fields for metadata display
    metadata = {
        'parameters': case_definition.get('parameters', {}),
        'modules': case_definition.get('modules', {}),
        'module_configs': case_definition.get('module_configs', {}),
    }

    if metadata:
        col1, col2 = st.columns(2)

        with col1:
            st.json(metadata, expanded=False)
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("← Tillbaka", use_container_width=True):
            st.session_state.page = 'config'
            st.rerun()
    
    with col2:
        if st.button("Exportera Excel", use_container_width=True):
            st.info("Export-funktionalitet implementeras senare")
    
    with col3:
        if st.button("Spara case", use_container_width=True):
            from ui.components.case_management import save_case
            
            if save_case(case_name, case_definition, results):
                st.success("Case sparat!")
    
    with col4:
        if st.button("Nytt case", type="primary", use_container_width=True):
            for key in ['case_definition', 'case_results', 'current_case_name']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.page = 'setup'
            st.rerun()