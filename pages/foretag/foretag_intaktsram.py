import streamlit as st

# Import från vår företagsmodul
from foretag.view.intaktsram import show_foretag_ir_dekomposition

# Autentisering sköts redan i show_foretag_effektivitet()
# så vi kan direkt köra huvudfunktionen
show_foretag_ir_dekomposition()