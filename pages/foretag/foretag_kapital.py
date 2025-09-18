# pages/foretag_kapital.py
# Sida för företagsspecifik kapitalvy

import streamlit as st

# Import från våra företagsmoduler
from foretag.view.kapital import show_foretag_kapital

# Autentisering sköts redan i show_foretag_kapital()
# så vi kan direkt köra huvudfunktionen
show_foretag_kapital()