"""
config/case_definition.py

Dataclasses för case definition.
Definierar strukturen för alla pipeline-konfigurationer.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


# Enums för metodval
class CapexMethod(str, Enum):
    """Metoder för kapitalkostnadsberäkning (Pre-DEA)"""
    BASELINE = "baseline"
    WACC_SCALING = "wacc_scaling"
    PARAMETER_CHANGE = "parameter_change"
    KENT_UPLOAD = "kent_upload"


class EfficiencyMethod(str, Enum):
    """Metoder för effektivitetsanalys (DEA stage)"""
    BASELINE = "baseline"
    DEA = "dea"
    # Fas 2: SFA = "sfa"
    # Fas 2: STONED = "stoned"


class PaverkbaraMethod(str, Enum):
    """Metod för påverkbara kostnader (Post-DEA)"""
    OPEX = "OPEX"
    TOTEX = "TOTEX"


# Config dataclasses per stage
@dataclass
class PreDeaConfig:
    """Configuration för Pre-DEA stage"""
    method: CapexMethod = CapexMethod.BASELINE
    
    # WACC-scaling specifikt
    wacc: Optional[float] = None
    
    # Parameter change specifikt
    normvalue_adjustments: Optional[Dict[int, float]] = None  # {cat_encode: multiplier}
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None  # {cat_encode: {'ekdep': X, 'maxdep': Y}}
    
    # KENT upload specifikt
    kent_file_path: Optional[str] = None


@dataclass
class DeaConfig:
    """Configuration för DEA stage"""
    method: EfficiencyMethod = EfficiencyMethod.BASELINE
    
    # Custom DEA model specification
    inputs: List[str] = field(default_factory=lambda: ['Kapitalkostnad_2024', 'OPEXp'])
    outputs: List[str] = field(default_factory=lambda: ['CU', 'MW', 'NS', 'MWhl', 'MWhh'])
    rts: str = "crs"  # "crs" eller "vrs"
    orientation: str = "input"  # "input" eller "output"
    
    # Outlier detection parameters (IQR-metod)
    q_lower: float = 25.0  # Nedre percentil
    q_upper: float = 75.0  # Övre percentil
    multiplier: float = 2.0  # IQR multiplier


@dataclass
class PostDeaConfig:
    """Configuration för Post-DEA stage"""
    # Effektiviseringskrav - trunkering
    trunkering_min: float = 0.162416      # Min potential för trunkering (16.24%)
    trunkering_max: float = 0.30          # Max potential för trunkering (30%)
    outlier_krav: float = 0.01            # Fast årligt krav för outliers (1%)
    
    # Effektiviseringskrav - omräkningsparametrar (enligt Ei's metod)
    kunddelning: float = 0.50             # Andel som tillfaller kunder (50%)
    realiseringstid: int = 8              # År för att uppnå full effektivisering
    tillsynsperiod: int = 4               # Längd på tillsynsperiod i år
    
    # Påverkbara kostnader
    paverkbara_method: PaverkbaraMethod = PaverkbaraMethod.OPEX


@dataclass
class CaseDefinition:
    """Complete case definition"""
    name: str
    user_reid: str  # REId för användarens företag (ex: "REL00001")
    
    # Stage configs
    pre_dea: PreDeaConfig = field(default_factory=PreDeaConfig)
    dea: DeaConfig = field(default_factory=DeaConfig)
    post_dea: PostDeaConfig = field(default_factory=PostDeaConfig)


def get_baseline_config(user_reid: str) -> CaseDefinition:
    """
    Create baseline config (alla defaults).
    
    Args:
        user_reid: Användarens REId (ex: "REL00001")
        
    Returns:
        CaseDefinition med alla baseline-inställningar
    """
    return CaseDefinition(
        name="Baseline",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )


def create_wacc_scaling_config(user_reid: str, new_wacc: float) -> CaseDefinition:
    """
    Create config för WACC-skalning.
    
    Args:
        user_reid: Användarens REId (ex: "REL00001")
        new_wacc: Ny WACC (real, före skatt)
        
    Returns:
        CaseDefinition för WACC-skalning
    """
    return CaseDefinition(
        name=f"WACC {new_wacc:.2%}",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(
            method=CapexMethod.WACC_SCALING,
            wacc=new_wacc
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
    Create config för parameter-ändringar.
    
    Args:
        user_reid: Användarens REId (ex: "REL00001")
        normvalue_adjustments: Dict {cat_encode: multiplier} ex {5: 1.2, 7: 0.9}
        lifetime_adjustments: Dict {cat_encode: {'ekdep': X, 'maxdep': Y}}
        wacc: WACC att använda (default: baseline 0.0453)
        
    Returns:
        CaseDefinition för parameter-ändringar
    """
    return CaseDefinition(
        name="Parameter ändringar",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(
            method=CapexMethod.PARAMETER_CHANGE,
            wacc=wacc,
            normvalue_adjustments=normvalue_adjustments,
            lifetime_adjustments=lifetime_adjustments
        ),
        dea=DeaConfig(method=EfficiencyMethod.BASELINE),
        post_dea=PostDeaConfig()
    )


def create_custom_dea_config(
    user_reid: str,
    inputs: List[str],
    outputs: List[str],
    rts: str = "VRS",
    orientation: str = "input"
) -> CaseDefinition:
    """
    Create config för custom DEA-modell.
    
    Args:
        user_reid: Användarens REId (ex: "REL00001")
        inputs: Lista med input-variabler
        outputs: Lista med output-variabler
        rts: Returns to scale ("VRS" eller "CRS")
        orientation: "input" eller "output"
        
    Returns:
        CaseDefinition för custom DEA
    """
    return CaseDefinition(
        name="Custom DEA",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=inputs,
            outputs=outputs,
            rts=rts,
            orientation=orientation
        ),
        post_dea=PostDeaConfig()
    )


def create_baseline_dea_config(user_reid: str) -> CaseDefinition:
    """
    Create config för DEA med Ei's baseline-specifikation.
    
    Denna spec ska ge EXAKT samma resultat som EIs_DEA.xlsx.
    
    Baseline spec:
    - Inputs: Kapitalkostnad_2024, OPEXp
    - Outputs: CU, MW, NS, MWhl, MWhh
    - RTS: CRS (Constant Returns to Scale)
    - Orientation: input
    - Outliers: Q25, Q75, multiplier=2.0
    
    Args:
        user_reid: Användarens REId (ex: "REL00001")
        
    Returns:
        CaseDefinition för baseline DEA (ska matcha Ei's resultat)
    """
    return CaseDefinition(
        name="Baseline DEA",
        user_reid=user_reid,
        pre_dea=PreDeaConfig(method=CapexMethod.BASELINE),
        dea=DeaConfig(
            method=EfficiencyMethod.DEA,
            inputs=['Kapitalkostnad_2024', 'OPEXp'],
            outputs=['CU', 'MW', 'NS', 'MWhl', 'MWhh'],
            rts='crs',
            orientation='input',
            q_lower=25.0,
            q_upper=75.0,
            multiplier=2.0
        ),
        post_dea=PostDeaConfig()
    )