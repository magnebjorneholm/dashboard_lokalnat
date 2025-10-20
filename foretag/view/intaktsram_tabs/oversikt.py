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
    
    st.subheader("placeholder")