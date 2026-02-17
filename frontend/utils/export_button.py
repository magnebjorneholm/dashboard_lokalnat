"""
frontend/utils/export_button.py

Export-knapp komponent fÃ¶r resultatvyn.
"""

import streamlit as st
from pipeline.export_excel import create_case_export, get_export_filename


def render_export_button(
    user_reid: str,
    company_name: str,
    baseline_result,
    case_result,
    ui_config: dict
):
    """
    Renderar export-knapp fÃ¶r Excel-nedladdning.
    
    Args:
        user_reid: AnvÃ¤ndarens REId
        company_name: Company name
        baseline_result: Baseline pipeline-resultat
        case_result: Case pipeline-resultat
        ui_config: UI-konfiguration
    """
    
    if st.button("Export to Excel", type="secondary", width='stretch'):
        try:
            with st.spinner("Creating Excel file..."):
                excel_data = create_case_export(
                    user_reid=user_reid,
                    company_name=company_name,
                    baseline_result=baseline_result,
                    case_result=case_result,
                    ui_config=ui_config
                )
                filename = get_export_filename(user_reid)
            
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                width='stretch'
            )
            st.success(f"File ready: {filename}")
            
        except Exception as e:
            st.error(f"Could not create Excel: {e}")