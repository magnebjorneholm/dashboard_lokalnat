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
    df_all_companies: pd.DataFrame  # 148 companies with capital_cost_2024, controllable_cost_average, volumes
    dea_baseline: pd.DataFrame      # Baseline DEA results from Ei
    reconciliation: pd.DataFrame    # REId/id_network mapping (also has DMU)
    wacc: float                     # Baseline WACC (0.0453)
    
    # SDF data for Post-DEA
    sdf_ir: pd.DataFrame            # Sheet "IR 2024-2027"
    sdf_controllable: pd.DataFrame  # Sheet "Påverkbara" (controllable costs)

    # Grunddata (detailed cost data from parquet files)
    controllable_detail: pd.DataFrame     # From controllable_a.parquet
    controllable_meta: pd.DataFrame       # From controllable_meta.parquet
    non_controllable_detail: pd.DataFrame # From non_controllable_a.parquet


@dataclass(frozen=True)
class PreDeaStageOutput:
    """
    Output from Pre-DEA stage.
    
    Contains metadata about both data source (capbase_source) and
    calculation method (capex_method) for traceability and correct
    handling in subsequent stages.
    
    WACC chain (3.1.X -> 3.2.X -> wacc_used):
    - wacc_input_method: How WACC was specified ("capm", "derived", "direct", "baseline")
    - wacc_inputs: Base parameters (3.1.X) if method is "capm"
    - wacc_derived: Derived values (3.2.X) if method is "capm" or "derived"
    """
    df_all_companies: pd.DataFrame
    capbase_source: str  # "baseline", "var_scaled", "kent_upload"
    capex_method: str    # "baseline", "parameter_change"
    capex_modified: bool
    opex_modified: bool = False  # True if controllable category overrides applied
    wacc_used: Optional[float] = None
    user_id_network: Optional[int] = None
    
    # WACC calculation chain for M3 output display
    wacc_input_method: str = "baseline"  # "capm", "derived", "direct", "baseline"
    wacc_inputs: Optional[dict] = None   # 3.1.X parameters (if capm)
    wacc_derived: Optional[dict] = None  # 3.2.X derived values (if capm or derived)
    
    # Category-level data for M1/M2 output display
    # Structure: (id_network, cat_encode, time) with nuav/dep/return columns
    df_by_category: Optional[pd.DataFrame] = None


@dataclass(frozen=True)
class DeaStageOutput:
    """
    Output from DEA stage.
    DEA results for all 148 companies.
    """
    dea_results: pd.DataFrame  # 148 rows: REId, dea_efficiency, potential, is_outlier
    dea_method: str            # "baseline", "baseline_recalculated", "dea"
    dea_executed: bool         # True if new DEA was run


@dataclass(frozen=True)
class ExtractionStageOutput:
    """
    Output from Extraction stage.
    Extracted values for user's company.
    """
    user_reid: str
    company_name: str
    
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
    user_revenue_frame: pd.Series  # All components for user (incl. RevenueFrame_Total)
    user_eff_req_pct: float        # Annual efficiency requirement for user

    # For all 148 companies (for comparison/analysis)
    all_revenue_frames: pd.DataFrame  # Complete revenue frames for all companies
    all_eff_reqs: pd.DataFrame        # Efficiency requirements for all companies
    
    # Incentive adjustments (None if incentive data missing)
    all_incentives: Optional[pd.DataFrame] = None
    
    # Detailed per-year incentive breakdown for user (User Manual Table 10)
    # Columns: year, loss_incentive_a, loss_incentive, util_incentive_a, util_incentive,
    #          inc_inter, inter_incentive_a, inter_incentive, incentive_total_year,
    #          total_before_agg_cap, inc_ait_*, inc_aif_*, max_adj, ret_period
    user_incentive_details: Optional[pd.DataFrame] = None