# app/__init__.py

"""
Init-fil för app-paketet.
Gör det möjligt att importera modeller, dataläsare, loggning och analysfunktioner.
"""

# Gör centrala funktioner lättåtkomliga (valfritt)
from .data_loader import load_data
from .dea_model import run_dea_model
from .pystoned_model import run_pystoned_model
from .run_logger import save_run, load_run, list_runs

