"""
foretag/view/intaktsram_tabs/oversikt.py
Översikt-tab för intäktsram-dekomposition
"""

import streamlit as st
import pandas as pd


def show_oversikt_tab(entity_data: pd.Series):
    """
    Visar översikt-tab med nyckeltal och komponenttabell.
    
    Args:
        entity_data: Series med data för vald entitet (lokalnät)
    """
    
    st.subheader("Översikt")
    
    intaktsram = entity_data.get('Intaktsram_Total', 0)
    kapitalkostnad = entity_data.get('Kapitalkostnad_Total', 0)
    paverkbara = entity_data.get('Paverkbara_Kostnader', 0)
    opaverkbara = entity_data.get('Opaverkbara_Kostnader', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Intäktsram", f"{intaktsram:,.0f} tkr".replace(",", " "))
    
    with col2:
        st.metric("Kapitalkostnad", f"{kapitalkostnad:,.0f} tkr".replace(",", " "))
    
    with col3:
        kapitalandel = (kapitalkostnad / intaktsram * 100) if intaktsram > 0 else 0
        st.metric("Kapitalandel", f"{kapitalandel:.1f}%")
    
    with col4:
        lopande = paverkbara + opaverkbara
        st.metric("Löpande kostnader", f"{lopande:,.0f} tkr".replace(",", " "))
    
    st.markdown("---")
    
    st.write("**Komponenter:**")
    
    components_data = {
        'Komponent': [
            'Påverkbara kostnader',
            'Opåverkbara kostnader',
            'Flexibilitetstjänster',
            'Avbrottsersättning',
            'Kapitalkostnad'
        ],
        'Belopp (tkr)': [
            f"{paverkbara:,.0f}".replace(",", " "),
            f"{opaverkbara:,.0f}".replace(",", " "),
            f"{entity_data.get('Flexibilitetstjanster', 0):,.0f}".replace(",", " "),
            f"{entity_data.get('Avbrottsersattning_12_24h', 0):,.0f}".replace(",", " "),
            f"{kapitalkostnad:,.0f}".replace(",", " ")
        ],
        'Andel (%)': [
            f"{(paverkbara / intaktsram * 100):.1f}%" if intaktsram > 0 else "0%",
            f"{(opaverkbara / intaktsram * 100):.1f}%" if intaktsram > 0 else "0%",
            f"{(entity_data.get('Flexibilitetstjanster', 0) / intaktsram * 100):.1f}%" if intaktsram > 0 else "0%",
            f"{(entity_data.get('Avbrottsersattning_12_24h', 0) / intaktsram * 100):.1f}%" if intaktsram > 0 else "0%",
            f"{(kapitalkostnad / intaktsram * 100):.1f}%" if intaktsram > 0 else "0%"
        ]
    }
    
    df_components = pd.DataFrame(components_data)
    st.dataframe(df_components, use_container_width=True, hide_index=True)
    
    if entity_data.get('Uppdaterad_Kapitalkostnad', False) or entity_data.get('Uppdaterad_Paverkbara', False):
        st.markdown("---")
        st.info("Vissa komponenter är modifierade genom scenarier")
        
        if entity_data.get('Uppdaterad_Kapitalkostnad', False):
            st.caption(f"Kapitalkostnad: {entity_data.get('Källa_Kapitalkostnad', 'Modifierad')}")
        
        if entity_data.get('Uppdaterad_Paverkbara', False):
            st.caption(f"Påverkbara kostnader: {entity_data.get('Källa_Paverkbara', 'Modifierad')}")