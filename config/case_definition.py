"""
config/case_definition.py

Dataclasses for case definition.
Defines structure for all pipeline configurations.

UPDATED: Replaced RAB_MODIFIED with VAR_SCALED for simplified asset base handling.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum

import pandas as pd


# =============================================================================
# ENUMS FOR PRE-DEA STAGE
# =============================================================================

class CapbaseSource(str, Enum):
    """
    Source for user's capbase_a data.
    
    Affects only the logged-in company's data (Variables).
    Other 147 companies always use baseline.
    """
    BASELINE = "baseline"        # Use baseline from capbase_a.parquet
    VAR_SCALED = "var_scaled"    # Variable scaling applied to ordinarie components
    KENT_UPLOAD = "kent_upload"  # Uploaded KENT Excel file (converted via steps 1-4)


class CapexMethod(str, Enum):
    """
    Calculation method for capital costs.
    
    Applied uniformly to all 148 companies (Parameters).
    """
    BASELINE = "baseline"              # No parameter change, baseline WACC
    PARAMETER_CHANGE = "parameter_change"  # Any parameter change (WACC/normvalues/lifetimes), run KENT 5-8


class EfficiencyMethod(str, Enum):
    """Methods for efficiency analysis (DEA stage)."""
    BASELINE = "baseline"
    DEA = "dea"
    # Phase 2: SFA = "sfa"
    # Phase 2: STONED = "stoned"


class ControllableMethod(str, Enum):
    """Method for controllable costs (Post-DEA)."""
    OPEX = "OPEX"
    TOTEX = "TOTEX"


# =============================================================================
# REID CONVERSION
# =============================================================================

def reid_to_id_network(reid: str) -> int:
    """
    Convert REId to id_network.

    Ex: "REL00886" -> 886

    This is the single source of truth for this conversion.
    Raises ValueError on invalid input.
    """
    try:
        numeric_part = reid.replace("REL", "").lstrip("0")
        if not numeric_part:
            return 0
        return int(numeric_part)
    except (ValueError, AttributeError):
        raise ValueError(f"Could not convert REId to id_network: {reid}")


# =============================================================================
# CONFIG DATACLASSES PER STAGE
# =============================================================================

@dataclass
class PreDeaConfig:
    """
    Configuration for Pre-DEA stage.
    
    Separates two concepts:
    1. capbase_source - Where user's capbase_a comes from (Variables)
    2. method - How calculation is done for all companies (Parameters)
    
    Data flow:
    - BASELINE source: No preparation, use existing data
    - VAR_SCALED source: Apply variable scaling to ordinarie components
    - KENT_UPLOAD source: Convert via kent_capbase_prep.py (steps 1-4)
    - Then run selected method (steps 5-8 if needed)
    
    Combination matrix (6 combinations):
    +------------------+--------------+-------------------+
    | Source \ Method  | BASELINE     | PARAMETER_CHANGE  |
    +------------------+--------------+-------------------+
    | BASELINE         | Direct       | KENT 5-8 all      |
    | VAR_SCALED       | KENT for usr | Replace+KENT all  |
    | KENT_UPLOAD      | KENT for usr | Replace+KENT all  |
    +------------------+--------------+-------------------+
    
    Note: WACC changes now use PARAMETER_CHANGE for full precision.
    """
    
    # === Data supply (per company) ===
    capbase_source: CapbaseSource = CapbaseSource.BASELINE
    
    # Variable scaling (if source = VAR_SCALED)
    user_capbase_scaled: Optional[Any] = None  # DataFrame with scaled ordinarie
    
    # KENT upload specific (if source = KENT_UPLOAD)
    kent_file_bytes: Optional[bytes] = None
    kent_user_id_network: Optional[int] = None
    
    # === Calculation method (uniform for all) ===
    method: CapexMethod = CapexMethod.BASELINE
    
    # WACC for calculations (None = use baseline 0.0453)
    wacc: Optional[float] = None
    
    # Parameter change specific (normvalues/lifetimes)
    normvalue_adjustments: Optional[Dict[int, float]] = None  # {cat_encode: multiplier}
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None  # {cat_encode: {'ekdep': X, 'maxdep': Y}}
    
    # === M4 OPEX: parameter scaling (all 148 companies) and variable override (user only) ===
    opex_scaling: Optional[float] = None    # 4.1.1: None = 1.0 (no scaling)
    opex_override: Optional[float] = None   # 40.1.1: annual OPEXp in tkr (trumps scaling for user)

    # === WACC input specification (for M3 output display) ===
    # How WACC was specified: "capm", "derived", "direct", "baseline"
    wacc_input_method: str = "baseline"
    
    # CAPM base parameters (3.1.X) - used if wacc_input_method == "capm"
    wacc_capm_inputs: Optional[Dict[str, float]] = None
    # Keys: debt_ratio, asset_beta, risk_free_rate, market_risk_premium,
    #       credit_risk_premium, tax_rate, inflation
    
    # Derived parameters (3.2.X) - used if wacc_input_method == "derived"
    wacc_derived_inputs: Optional[Dict[str, float]] = None
    # Keys: cost_of_equity, cost_of_debt, debt_ratio, tax_rate, inflation


@dataclass
class DeaConfig:
    """Configuration for DEA stage."""
    method: EfficiencyMethod = EfficiencyMethod.BASELINE
    
    # Custom DEA model specification
    inputs: List[str] = field(default_factory=lambda: ['capital_cost_2024', 'controllable_cost_average'])
    outputs: List[str] = field(default_factory=lambda: ['CU', 'MW', 'NS', 'MWhl', 'MWhh'])
    rts: str = "crs"  # "crs" or "vrs"
    orientation: str = "input"  # "input" or "output"
    
    # Outlier detection parameters (IQR method)
    q_lower: float = 25.0
    q_upper: float = 75.0
    multiplier: float = 2.0


@dataclass
class IncentiveConfig:
    """
    Configuration for incentive adjustments (3.3-3.6).
    
    Full parameterization of quality, network loss and
    load adjustment according to Ei methodology.
    """
    # KPI factors per year {year: factor}
    kpi: Optional[Dict[int, float]] = None
    
    # Electricity price per year for network loss {year: kr/MWh}
    k_nf: Optional[Dict[int, float]] = None
    
    # Sharing factor for network loss
    sharing_netloss: float = 0.75
    
    # Max aggregate incentive (share of return)
    adj_max_agg: float = 1/3
    
    # CEMI4 correction max
    adj_max_cemi4: float = 0.25
    
    # AIT/AIF costs per customer type
    ait_costs: Optional[Dict[Tuple[str, int], float]] = None
    aif_costs: Optional[Dict[Tuple[str, int], float]] = None
    
    # On/off switches
    enable_quality: bool = True
    enable_netloss: bool = True
    enable_load: bool = True
    
    # Variable overrides (for company-specific adjustments)
    variable_overrides: Optional[Dict[str, float]] = None


@dataclass
class PostDeaConfig:
    """Configuration for Post-DEA stage."""
    # Efficiency requirements
    # None = auto-derive from outlier_req (ensures consistent minimum annual req)
    truncation_min: Optional[float] = None
    truncation_max: float = 0.30
    outlier_req: float = 0.01
    customer_sharing: float = 0.50
    realization_time: int = 8
    supervision_period: int = 4

    # Controllable costs
    controllable_method: ControllableMethod = ControllableMethod.OPEX

    # M4 OPEX: parameter scaling (all cos) and variable overrides (user only)
    flex_scaling: Optional[float] = None              # 4.1.2: None = 1.0
    non_adj_scaling: Optional[float] = None           # 4.1.3: None = 1.0
    flex_override: Optional[float] = None             # 40.1.2: period total in tkr
    non_controllable_override: Optional[float] = None # 40.2.1: period total in tkr

    # Incentives
    incentive: IncentiveConfig = field(default_factory=IncentiveConfig)


@dataclass
class CaseDefinition:
    """
    Complete case definition.
    Contains configuration for all pipeline stages.
    """
    name: str
    user_reid: str  # REId for user's company (ex: "REL00001")
    
    pre_dea: PreDeaConfig = field(default_factory=PreDeaConfig)
    dea: DeaConfig = field(default_factory=DeaConfig)
    post_dea: PostDeaConfig = field(default_factory=PostDeaConfig)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_baseline_config(user_reid: str) -> CaseDefinition:
    """
    Create baseline case configuration.
    
    Args:
        user_reid: User's REId (ex: "REL00001")
        
    Returns:
        CaseDefinition with all baseline settings
    """
    return CaseDefinition(
        name="Baseline",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.BASELINE
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )