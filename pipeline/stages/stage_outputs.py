"""
pipeline/stages/stage_outputs.py

Output dataclasses for each pipeline stage.
All outputs are frozen (immutable) to ensure data integrity.
"""

from dataclasses import dataclass
import pandas as pd
from typing import Optional


@dataclass(frozen=True)
class BaselineStageOutput:
    """
    Output from Baseline stage.
    Converts BaselineData to stage format.
    """
    df_all_companies: pd.DataFrame  # 148 companies with Kapitalkostnad_2024, OPEXp, volumes
    dea_baseline: pd.DataFrame      # Baseline DEA results from Ei
    reconciliation: pd.DataFrame    # REId/id_network mapping (also has DMU)
    wacc: float                     # Baseline WACC (0.0453)
    
    # SDF data for Post-DEA
    sdf_ir: pd.DataFrame            # Sheet "IR 2024-2027"
    sdf_paverkbara: pd.DataFrame    # Sheet "Paverkbara"


@dataclass(frozen=True)
class PreDeaStageOutput:
    """
    Output from Pre-DEA stage.
    
    Contains metadata about both data source (capbase_source) and
    calculation method (capex_method) for traceability and correct
    handling in subsequent stages.
    """
    df_all_companies: pd.DataFrame
    capbase_source: str  # "baseline", "var_scaled", "kent_upload"
    capex_method: str    # "baseline", "wacc_scaling", "parameter_change"
    capex_modified: bool
    wacc_used: Optional[float] = None
    user_id_network: Optional[int] = None


@dataclass(frozen=True)
class DeaStageOutput:
    """
    Output from DEA stage.
    DEA results for all 148 companies.
    """
    dea_results: pd.DataFrame  # 148 rows: REId, Effektivitet, potential, is_outlier
    dea_method: str            # "baseline", "baseline_recalculated", "dea"
    dea_executed: bool         # True if new DEA was run


@dataclass(frozen=True)
class ExtractionStageOutput:
    """
    Output from Extraction stage.
    Extracted values for user's company.
    """
    user_reid: str
    foretag: str
    
    # From Pre-DEA
    capex: float
    opex: float
    totex: float
    
    # Volumes
    cu: float
    mw: float
    ns: float
    
    # From DEA
    efficiency: Optional[float]
    potential: float
    is_outlier: bool


@dataclass(frozen=True)
class PostDeaStageOutput:
    """
    Output from Post-DEA stage.
    Efficiency requirements, incentive adjustments, adjustable costs,
    and complete revenue frame.
    """
    user_reid: str
    user_intaktsram: pd.Series  # All components for user (incl. Intaktsram_Total)
    user_effkrav_proc: float    # Annual efficiency requirement for user
    
    # For all 148 companies (for comparison/analysis)
    all_intaktsram: pd.DataFrame   # Complete revenue frames for all companies
    all_effkrav: pd.DataFrame      # Efficiency requirements for all companies
    
    # Incentive adjustments (None if incentive data missing)
    all_incentives: Optional[pd.DataFrame] = None