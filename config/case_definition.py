"""
config/case_definition.py

Dataclasses för case definition.
Definierar strukturen för alla pipeline-konfigurationer.

REFAKTORISERAD: Separerar CapbaseSource (datakälla) från CapexMethod (beräkningsmetod).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum

import pandas as pd


# =============================================================================
# ENUMS FÖR PRE-DEA STAGE
# =============================================================================

class CapbaseSource(str, Enum):
    """
    Källa för användarens capbase_a data.
    
    Påverkar endast det inloggade företagets data (Variables).
    Övriga 147 företag använder alltid baseline.
    """
    BASELINE = "baseline"          # Använd baseline från capbase_a_mini.parquet
    RAB_MODIFIED = "rab_modified"  # RAB-editor ändringar från session state
    KENT_UPLOAD = "kent_upload"    # Uppladdad KENT Excel-fil (konverteras via steg 1-4)


class CapexMethod(str, Enum):
    """
    Beräkningsmetod för kapitalkostnad.
    
    Appliceras uniformt på alla 148 företag (Parameters).
    """
    BASELINE = "baseline"              # Ingen parameterändring, baseline WACC
    WACC_SCALING = "wacc_scaling"      # Skala avkastning med ny WACC
    PARAMETER_CHANGE = "parameter_change"  # Ändra normvärden/livslängder, kör KENT 5-8


class EfficiencyMethod(str, Enum):
    """Metoder för effektivitetsanalys (DEA stage)."""
    BASELINE = "baseline"
    DEA = "dea"
    # Fas 2: SFA = "sfa"
    # Fas 2: STONED = "stoned"


class PaverkbaraMethod(str, Enum):
    """Metod för påverkbara kostnader (Post-DEA)."""
    OPEX = "OPEX"
    TOTEX = "TOTEX"


# =============================================================================
# CONFIG DATACLASSES PER STAGE
# =============================================================================

@dataclass
class PreDeaConfig:
    """
    Configuration för Pre-DEA stage.
    
    Separerar två koncept:
    1. capbase_source - Var användarens capbase_a kommer ifrån (Variables)
    2. method - Hur beräkningen görs för alla företag (Parameters)
    
    Dataflöde:
    - BASELINE source: Ingen förberedelse, använd befintlig data
    - RAB_MODIFIED source: Från session state (redan capbase_a format)
    - KENT_UPLOAD source: Konvertera via kent_capbase_prep.py (steg 1-4)
    - Sedan körs vald method (steg 5-8 om behövs)
    
    Kombinationsmatris (9 kombinationer):
    ┌─────────────────┬──────────────┬────────────────┬───────────────────┐
    │ Source \ Method │ BASELINE     │ WACC_SCALING   │ PARAMETER_CHANGE  │
    ├─────────────────┼──────────────┼────────────────┼───────────────────┤
    │ BASELINE        │ Direkt       │ Skala alla     │ KENT 5-8 alla     │
    │ RAB_MODIFIED    │ KENT för usr │ KENT+skala     │ Ersätt+KENT alla  │
    │ KENT_UPLOAD     │ KENT för usr │ KENT+skala     │ Ersätt+KENT alla  │
    └─────────────────┴──────────────┴────────────────┴───────────────────┘
    """
    
    # === Dataförsörjning (per företag) ===
    capbase_source: CapbaseSource = CapbaseSource.BASELINE
    
    # RAB-editor specifikt (om source = RAB_MODIFIED)
    rab_user_capbase: Optional[Any] = None  # DataFrame, använder Any för att undvika pd import-problem
    
    # KENT-upload specifikt (om source = KENT_UPLOAD)
    kent_file_bytes: Optional[bytes] = None
    kent_user_id_network: Optional[int] = None
    
    # === Beräkningsmetod (uniformt för alla) ===
    method: CapexMethod = CapexMethod.BASELINE
    
    # WACC för beräkningar (None = använd baseline 0.0453)
    wacc: Optional[float] = None
    
    # Parameter change specifikt (normvärden/livslängder)
    normvalue_adjustments: Optional[Dict[int, float]] = None  # {cat_encode: multiplier}
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None  # {cat_encode: {'ekdep': X, 'maxdep': Y}}


@dataclass
class DeaConfig:
    """Configuration för DEA stage."""
    method: EfficiencyMethod = EfficiencyMethod.BASELINE
    
    # Custom DEA model specification
    inputs: List[str] = field(default_factory=lambda: ['Kapitalkostnad_2024', 'OPEXp'])
    outputs: List[str] = field(default_factory=lambda: ['CU', 'MW', 'NS', 'MWhl', 'MWhh'])
    rts: str = "crs"  # "crs" eller "vrs"
    orientation: str = "input"  # "input" eller "output"
    
    # Outlier detection parameters (IQR-metod)
    q_lower: float = 25.0
    q_upper: float = 75.0
    multiplier: float = 2.0


@dataclass
class IncentiveConfig:
    """
    Configuration för incitamentjusteringar (3.3-3.6).
    
    Fullständig parametrisering av kvalitets-, nätförlust- och 
    belastningsjustering enligt Ei's metodik.
    """
    # KPI-faktorer per år {year: factor}
    kpi: Optional[Dict[int, float]] = None
    
    # Elpris per år för nätförlust {year: kr/MWh}
    k_nf: Optional[Dict[int, float]] = None
    
    # Delningsfaktor för nätförlust
    sharing_netloss: float = 0.75
    
    # Max aggregerat incitament (andel av avkastning)
    adj_max_agg: float = 1/3
    
    # CEMI4-korrigering max
    adj_max_cemi4: float = 0.25
    
    # AIT/AIF kostnader per kundtyp
    ait_costs: Optional[Dict[Tuple[str, int], float]] = None
    aif_costs: Optional[Dict[Tuple[str, int], float]] = None
    
    # On/off switchar
    enable_quality: bool = True
    enable_netloss: bool = True
    enable_load: bool = True
    
    # Variable overrides (för företagsspecifika justeringar)
    variable_overrides: Optional[Dict[str, float]] = None


@dataclass
class PostDeaConfig:
    """Configuration för Post-DEA stage."""
    # Effektiviseringskrav
    trunkering_min: float = 0.01
    trunkering_max: float = 0.30
    outlier_krav: float = 0.01
    kunddelning: float = 0.50
    realiseringstid: int = 8
    tillsynsperiod: int = 4
    
    # Påverkbara kostnader
    paverkbara_method: PaverkbaraMethod = PaverkbaraMethod.OPEX
    
    # Incitament
    incentive: IncentiveConfig = field(default_factory=IncentiveConfig)


@dataclass
class CaseDefinition:
    """
    Komplett case definition.
    Innehåller konfiguration för alla pipeline stages.
    """
    name: str
    user_reid: str  # REId för användarens företag (ex: "REL00001")
    
    pre_dea: PreDeaConfig = field(default_factory=PreDeaConfig)
    dea: DeaConfig = field(default_factory=DeaConfig)
    post_dea: PostDeaConfig = field(default_factory=PostDeaConfig)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def get_baseline_config(user_reid: str) -> CaseDefinition:
    """
    Skapar baseline case configuration.
    
    Args:
        user_reid: Användarens REId (ex: "REL00001")
        
    Returns:
        CaseDefinition med alla baseline-inställningar
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


def create_wacc_scaling_config(user_reid: str, new_wacc: float) -> CaseDefinition:
    """
    Skapar config för WACC-skalning.
    
    Args:
        user_reid: Användarens REId
        new_wacc: Ny WACC (real, före skatt)
        
    Returns:
        CaseDefinition för WACC-skalning
    """
    return CaseDefinition(
        name=f"WACC {new_wacc:.2%}",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.WACC_SCALING,
            wacc=new_wacc
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )


def create_rab_modified_config(
    user_reid: str,
    rab_user_capbase: Any,  # pd.DataFrame
    method: CapexMethod = CapexMethod.BASELINE,
    wacc: Optional[float] = None,
    normvalue_adjustments: Optional[Dict[int, float]] = None,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None
) -> CaseDefinition:
    """
    Skapar config för RAB-editor med valfri beräkningsmetod.
    
    Args:
        user_reid: Användarens REId
        rab_user_capbase: Modifierad capbase_a DataFrame från RAB-editor
        method: Beräkningsmetod (BASELINE, WACC_SCALING, PARAMETER_CHANGE)
        wacc: WACC om method != BASELINE
        normvalue_adjustments: Normvärdesjusteringar om PARAMETER_CHANGE
        lifetime_adjustments: Livslängdsjusteringar om PARAMETER_CHANGE
        
    Returns:
        CaseDefinition för RAB-editor
    """
    return CaseDefinition(
        name=f"RAB Modified ({method.value})",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.RAB_MODIFIED,
            rab_user_capbase=rab_user_capbase,
            method=method,
            wacc=wacc,
            normvalue_adjustments=normvalue_adjustments,
            lifetime_adjustments=lifetime_adjustments
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )


def create_kent_upload_config(
    user_reid: str,
    kent_file_bytes: bytes,
    kent_user_id_network: int,
    method: CapexMethod = CapexMethod.BASELINE,
    wacc: Optional[float] = None,
    normvalue_adjustments: Optional[Dict[int, float]] = None,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None
) -> CaseDefinition:
    """
    Skapar config för KENT-upload med valfri beräkningsmetod.
    
    Args:
        user_reid: Användarens REId
        kent_file_bytes: KENT Excel-fil som bytes
        kent_user_id_network: Användarens id_network
        method: Beräkningsmetod (BASELINE, WACC_SCALING, PARAMETER_CHANGE)
        wacc: WACC om method != BASELINE
        normvalue_adjustments: Normvärdesjusteringar om PARAMETER_CHANGE
        lifetime_adjustments: Livslängdsjusteringar om PARAMETER_CHANGE
        
    Returns:
        CaseDefinition för KENT-upload
    """
    return CaseDefinition(
        name=f"KENT Upload ({method.value})",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.KENT_UPLOAD,
            kent_file_bytes=kent_file_bytes,
            kent_user_id_network=kent_user_id_network,
            method=method,
            wacc=wacc,
            normvalue_adjustments=normvalue_adjustments,
            lifetime_adjustments=lifetime_adjustments
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )


def create_parameter_change_config(
    user_reid: str,
    normvalue_adjustments: Optional[Dict[int, float]] = None,
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None,
    wacc: Optional[float] = None
) -> CaseDefinition:
    """
    Skapar config för parameter-ändringar (utan KENT-upload eller RAB-editor).
    
    Args:
        user_reid: Användarens REId
        normvalue_adjustments: Dict {cat_encode: multiplier}
        lifetime_adjustments: Dict {cat_encode: {'ekdep': X, 'maxdep': Y}}
        wacc: WACC att använda (default: baseline 0.0453)
        
    Returns:
        CaseDefinition för parameter-ändringar
    """
    return CaseDefinition(
        name="Parameter ändringar",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(
            capbase_source=CapbaseSource.BASELINE,
            method=CapexMethod.PARAMETER_CHANGE,
            wacc=wacc,
            normvalue_adjustments=normvalue_adjustments,
            lifetime_adjustments=lifetime_adjustments
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )