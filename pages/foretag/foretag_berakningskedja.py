# pages/foretag_berakningskedja.py
# Sida för företagsspecifik beräkningskedja

import streamlit as st

# Import från vår företagsmodul
from kapitalkostnad.frontend.kent_full_pipeline import show_kent_full_pipeline

# Autentisering sköts redan i show_kent_full_pipeline()
show_kent_full_pipeline()