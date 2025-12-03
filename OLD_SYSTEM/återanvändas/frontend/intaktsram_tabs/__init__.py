"""
Tab-moduler för intäktsram-dekomposition
Fas 1: Subtab-struktur med direkt session_state-uppdatering
"""

from .oversikt import show_oversikt_tab
from .kapitalkostnad import show_kapitalkostnad_tab
from .effektiviseringskrav import show_effektiviseringskrav_tab

__all__ = ['show_oversikt_tab', 'show_kapitalkostnad_tab', 'show_effektiviseringskrav_tab']