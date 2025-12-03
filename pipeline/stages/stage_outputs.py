"""
pipeline/stages/stage_outputs.py

Output dataclasses för varje pipeline stage.
Alla outputs är frozen (immutable) för att säkerställa data integrity.
"""

from dataclasses import dataclass
import pandas as pd
from typing import Optional


@dataclass(frozen=True)
class BaselineStageOutput:
    """
    Output från Baseline stage.
    Konverterar BaselineData till stage-format.
    """
    df_all_companies: pd.DataFrame  # 148 företag med CAPEX, OPEX, volumes
    dea_baseline: pd.DataFrame      # Baseline DEA-resultat från Ei
    reconciliation: pd.DataFrame    # REId/id_network mapping (har även DMU)
    wacc: float                     # Baseline WACC (0.0453)
    
    # SDF-data för Post-DEA
    sdf_ir: pd.DataFrame            # Sheet "IR 2024-2027"
    sdf_paverkbara: pd.DataFrame    # Sheet "Påverkbara"


@dataclass(frozen=True)
class PreDeaStageOutput:
    """
    Output från Pre-DEA stage.
    DataFrame med alla 148 företag, potentiellt modifierad CAPEX.
    """
    df_all_companies: pd.DataFrame  # 148 rows, potentially modified CAPEX/OPEX
    capex_method: str               # Metod som användes: baseline, wacc_scaling, etc.
    capex_modified: bool            # True om CAPEX ändrades från baseline


@dataclass(frozen=True)
class DeaStageOutput:
    """
    Output från DEA stage.
    DEA-resultat för alla 148 företag.
    """
    dea_results: pd.DataFrame       # 148 rows: REId, efficiency, potential, is_outlier (har även DMU)
    dea_method: str                 # Metod: baseline eller dea
    dea_executed: bool              # True om ny DEA kördes (annars baseline)


@dataclass(frozen=True)
class ExtractionStageOutput:
    """
    Output från Extraction stage.
    Extraherade värden för användarens företag.
    """
    user_reid: str  # REId för företaget (ex: "REL00001")
    foretag: str
    
    # Från Pre-DEA
    capex: float
    opex: float
    totex: float
    
    # Volumes
    cu: float
    mw: float
    ns: float
    
    # Från DEA
    efficiency: Optional[float]
    potential: float
    is_outlier: bool


@dataclass(frozen=True)
class PostDeaStageOutput:
    """
    Output från Post-DEA stage.
    Effektiviseringskrav, påverkbara kostnader, och komplett intäktsram.
    """
    user_reid: str  # REId för användarens företag
    user_intaktsram: pd.Series  # Alla komponenter för användaren (inkl. Intaktsram_Total)
    user_effkrav_proc: float  # Årligt effektiviseringskrav för användaren
    
    # För alla 148 företag (för jämförelse/analys)
    all_intaktsram: pd.DataFrame  # Kompletta intäktsramar för alla företag
    all_effkrav: pd.DataFrame  # Effektiviseringskrav för alla företag