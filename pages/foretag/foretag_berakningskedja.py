# pages/foretag_berakningskedja.py
# Sida för företagsspecifik beräkningskedja

import streamlit as st

# Import från vår företagsmodul
from foretag.view.foretag_berakningskedja import show_foretag_berakningskedja

# Autentisering sköts redan i show_foretag_berakningskedja()
# så vi kan direkt köra huvudfunktionen
show_foretag_berakningskedja()