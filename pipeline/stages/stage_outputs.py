"""
pipeline/stages/stage_outputs.py

Output dataclasses för varje pipeline stage.
Alla outputs är frozen (immutable) för att säkerställa data integrity.

REFAKTORISERAD: PreDeaStageOutput innehåller nu metadata om både 
capbase_source och capex_method.
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
    df_all_companies: pd.DataFrame  # 148 företag med Kapitalkostnad_2024, OPEXp, volumes
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
    
    Innehåller metadata om både datakälla (capbase_source) och 
    beräkningsmetod (capex_method) för spårbarhet och korrekt
    hantering i efterföljande stages.
    
    Attributes:
        df_all_companies: DataFrame med alla 148 företag, potentiellt
            modifierad Kapitalkostnad_2024/OPEXp.
        capbase_source: Källa för användarens data:
            - "baseline": Baseline capbase_a
            - "kent_upload": Uppladdad KENT-fil
        capex_method: Beräkningsmetod som användes:
            - "baseline": Ingen parameterändring
            - "wacc_scaling": Skalad avkastning
            - "parameter_change": Nya normvärden/livslängder
        capex_modified: True om Kapitalkostnad_2024 ändrades från baseline.
        wacc_used: WACC som användes (för post_dea periodsumma-beräkning).
        user_id_network: Användarens id_network (för spårbarhet).
    """
    df_all_companies: pd.DataFrame
    capbase_source: str
    capex_method: str
    capex_modified: bool
    wacc_used: Optional[float] = None
    user_id_network: Optional[int] = None


@dataclass(frozen=True)
class DeaStageOutput:
    """
    Output från DEA stage.
    DEA-resultat för alla 148 företag.
    """
    dea_results: pd.DataFrame       # 148 rows: REId, efficiency, potential, is_outlier
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
    Effektiviseringskrav, incitamentjusteringar, påverkbara kostnader,
    och komplett intäktsram.
    """
    user_reid: str  # REId för användarens företag
    user_intaktsram: pd.Series  # Alla komponenter för användaren (inkl. Intaktsram_Total)
    user_effkrav_proc: float  # Årligt effektiviseringskrav för användaren
    
    # För alla 148 företag (för jämförelse/analys)
    all_intaktsram: pd.DataFrame  # Kompletta intäktsramar för alla företag
    all_effkrav: pd.DataFrame  # Effektiviseringskrav för alla företag
    
    # Incitamentjusteringar (nytt)
    # None om incitamentdata saknas
    all_incentives: Optional[pd.DataFrame] = None
    # Kolumner: REId, Kvalitetsjustering_Total, Natforlustjustering_Total,
    #           Belastningsjustering_Total, Incitamentjustering_Total,
    #           Missing_Incentive_Data (bool)