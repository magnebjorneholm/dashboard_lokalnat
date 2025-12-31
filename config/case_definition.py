"""
config/case_definition.py

Dataclasses för case definition.
Definierar strukturen för alla pipeline-konfigurationer.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
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
    """Configuration for Pre-DEA stage"""
    method: CapexMethod = CapexMethod.BASELINE
    
    # WACC-scaling specifikt
    wacc: Optional[float] = None
    
    # Parameter change specifikt
    normvalue_adjustments: Optional[Dict[int, float]] = None  # {cat_encode: multiplier}
    lifetime_adjustments: Optional[Dict[int, Dict[str, int]]] = None  # {cat_encode: {'ekdep': X, 'maxdep': Y}}
    
    # KENT upload specifikt
    kent_file_path: Optional[str] = None
    kent_file_bytes: Optional[bytes] = None  # Uppladdad KENT Excel-fil som bytes
    kent_user_id_network: Optional[int] = None  # id_network for det uppladdade foretagets data


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
class IncentiveConfig:
    """
    Configuration för incitamentjusteringar (3.3-3.6).
    
    Fullständig parametrisering av kvalitets-, nätförlust- och 
    belastningsjustering enligt Ei's metodik.
    
    Parametrar kan vara:
    - Enkla värden (float/bool)
    - Dict per år: {2024: X, 2025: Y, ...}
    - Dict per kundtyp: {('o', 1): X, ('a', 1): Y, ...}
    """
    # === 3.3 Kvalitetsincitament ===
    
    # KPI-faktorer per år (prisjustering till 2022 års priser)
    # Dict[int, float] = {year: factor}
    kpi: Optional[Dict[int, float]] = field(default_factory=lambda: {
        2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546
    })
    
    # AIT-kostnader per kundtyp (kr/kWh)
    # Dict[Tuple[str, int], float] = {(ann, sni): kostnad}
    # ann: 'a' = aviserade, 'o' = oaviserade
    # sni: 1-6 (kundtyp)
    ait_costs: Optional[Dict[Tuple[str, int], float]] = field(default_factory=lambda: {
        ('o', 1): 34.35, ('o', 2): 159.96, ('o', 3): 175.06,
        ('o', 4): 96.97, ('o', 5): 5.84, ('o', 6): 96.01,
        ('a', 1): 14.10, ('a', 2): 76.00, ('a', 3): 79.31,
        ('a', 4): 43.70, ('a', 5): 4.98, ('a', 6): 45.16,
    })
    
    # AIF-kostnader per kundtyp (kr/kW)
    # Samma struktur som ait_costs
    aif_costs: Optional[Dict[Tuple[str, int], float]] = field(default_factory=lambda: {
        ('o', 1): 9.78, ('o', 2): 70.75, ('o', 3): 17.78,
        ('o', 4): 7.65, ('o', 5): 1.95, ('o', 6): 22.18,
        ('a', 1): 1.72, ('a', 2): 20.71, ('a', 3): 5.94,
        ('a', 4): 0.92, ('a', 5): 1.85, ('a', 6): 7.08,
    })
    
    # Max CEMI4-korrigering (andel, 0-1)
    adj_max_cemi4: float = 0.25
    
    # === 3.4 Nätförlustincitament ===
    
    # Elpris per år (kr/MWh)
    # Dict[int, float] = {year: pris}
    k_nf: Optional[Dict[int, float]] = field(default_factory=lambda: {
        2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44
    })
    
    # Delningsfaktor nätförlust (andel som tillfaller företaget)
    sharing_netloss: float = 0.75
    
    # === 3.6 Begränsningar ===
    
    # Max aggregerat incitament per år (andel av avkastning)
    adj_max_agg: float = 1/3
    
    # === Aktivera/inaktivera ===
    
    enable_quality: bool = True
    enable_netloss: bool = True
    enable_load: bool = True
    
    # === Variabel-overrides (företagsspecifika) ===
    # 
    # Dessa overrides appliceras ENDAST på användarens företag.
    # Värdet appliceras på ALLA år (2024-2027).
    # Om None -> använd baseline från all_adjust_vars.csv
    # 
    # Struktur: Dict[str, float] där nyckel är kolumnnamn
    # Exempel:
    # {
    #     "nf_obs": 0.045,        # Nätförlust observerad
    #     "ug_obs": 0.65,         # Utnyttjandegrad observerad
    #     "ait_o_1_obs": 12.5,    # AIT oaviserad jordbruk
    #     "ame_2": 150000,        # ÅME industri
    # }
    variable_overrides: Optional[Dict[str, float]] = None


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
    
    # Incitamentjusteringar
    incentive: IncentiveConfig = field(default_factory=IncentiveConfig)


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