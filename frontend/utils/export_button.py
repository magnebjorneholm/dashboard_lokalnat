"""
frontend/utils/export_button.py

Export button component for results view.
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
    Renders export button for Excel download.
    
    Args:
        user_reid: User's REId
        foretag: Company name
        baseline_result: Baseline pipeline result
        case_result: Case pipeline result
        ui_config: UI configuration
    """
    
    if st.button("Export to Excel", type="secondary", use_container_width=True):
        try:
            with st.spinner("Generating Excel file..."):
                excel_data = create_case_export(
                    user_reid=user_reid,
                    foretag=foretag,
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
                use_container_width=True
            )
            st.success(f"File ready: {filename}")
            
        except Exception as e:
            st.error(f"Failed to generate Excel: {e}")