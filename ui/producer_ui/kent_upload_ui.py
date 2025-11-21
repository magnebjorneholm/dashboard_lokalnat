"""
KENT upload UI
Extraherat från kapitalkostnad.py
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any


def render_kent_upload_ui() -> Optional[Dict[str, Any]]:
    """
    Renderar UI för KENT-filuppladdning.
    
    Returns:
        Dict med uppladdad KENT-data eller None
    """
    st.markdown("**KENT-filuppladdning**")
    st.caption("Ladda upp KENT-fil för full kapitalbas-beräkning")
    
    uploaded_file = st.file_uploader(
        "Välj KENT-fil (.xlsx)",
        type=['xlsx'],
        help="KENT-inrapporteringsfil från Ei:s mall"
    )
    
    if uploaded_file is not None:
        try:
            with st.spinner("Läser KENT-fil..."):
                from producers.kapitalkostnad.capbase_prep import build_capbase_a_from_kent
                
                capbase_a = build_capbase_a_from_kent(uploaded_file)
                
                if capbase_a is not None and not capbase_a.empty:
                    st.success(f"KENT-fil laddad: {len(capbase_a)} rader")
                    
                    with st.expander("Visa data"):
                        st.dataframe(capbase_a.head(10))
                    
                    return {
                        'data': capbase_a,
                        'filename': uploaded_file.name
                    }
                else:
                    st.error("Kunde inte läsa KENT-fil")
                    return None
        
        except Exception as e:
            st.error(f"Fel vid läsning av KENT-fil: {e}")
            return None
    
    return None