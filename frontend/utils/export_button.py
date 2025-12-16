"""
frontend/utils/export_button.py

Export-knapp komponent för resultatvyn.
"""

import streamlit as st
from .export_excel import create_case_export, get_export_filename


def render_export_button(
    user_reid: str,
    foretag: str,
    baseline_result,
    case_result,
    ui_config: dict
):
    """
    Renderar export-knapp för Excel-nedladdning.
    
    Args:
        user_reid: Användarens REId
        foretag: Företagsnamn
        baseline_result: Baseline pipeline-resultat
        case_result: Case pipeline-resultat
        ui_config: UI-konfiguration
    """
    
    if st.button("Exportera till Excel", type="secondary", use_container_width=True):
        try:
            with st.spinner("Skapar Excel-fil..."):
                excel_data = create_case_export(
                    user_reid=user_reid,
                    foretag=foretag,
                    baseline_result=baseline_result,
                    case_result=case_result,
                    ui_config=ui_config
                )
                filename = get_export_filename(user_reid)
            
            st.download_button(
                label="Ladda ner Excel",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            st.success(f"Fil redo: {filename}")
            
        except Exception as e:
            st.error(f"Kunde inte skapa Excel: {e}")