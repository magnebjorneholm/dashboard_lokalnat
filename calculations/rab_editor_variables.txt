"""
calculations/rab_editor_variables.py

Dataclasses and variable definitions for RAB editor.

Defines which variables are editable per valuation type (vtype),
how NUAV is calculated, and validation rules.

Structure:
- BaseComponent: Common fields for all components
- NormvärderadKomponent (vtype=4)
- AnnatSkäligtVärdeKomponent (vtype=1)
- AnskaffningsvärdeKomponent (vtype=2)
- InvesteringKomponent (vtype=5)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal
from enum import IntEnum


# =============================================================================
# CONSTANTS
# =============================================================================

class VType(IntEnum):
    """Valuation methods per regulation 2018:1520."""
    ANNAT_SKÄLIGT_VÄRDE = 1
    ANSKAFFNINGSVÄRDE = 2
    BOKFÖRT_VÄRDE = 3  # Not present in sample data
    NORMVÄRDE = 4
    INVESTERING = 5


# Time codes for regulatory period 2024-2027
TIMECODE_PERIOD_START = 229  # 2024 H1
TIMECODE_PERIOD_END = 236    # 2027 H2

# Half-year to time code mapping
HALFYEAR_TO_TIMECODE: Dict[str, int] = {
    "2024 H1": 229, "2024 H2": 230,
    "2025 H1": 231, "2025 H2": 232,
    "2026 H1": 233, "2026 H2": 234,
    "2027 H1": 235, "2027 H2": 236,
}

TIMECODE_TO_HALFYEAR: Dict[int, str] = {v: k for k, v in HALFYEAR_TO_TIMECODE.items()}


# =============================================================================
# TIME CODE HELPERS
# =============================================================================

def timecode_to_year(timecode: int) -> float:
    """
    Convert time code to year.
    
    Time code = (year - 1910) × 2 + half
    where half = 1 (H1) or 2 (H2)
    
    Args:
        timecode: Time code (e.g. 229 for 2024 H1)
    
    Returns:
        Year as float (e.g. 2024.0 for H1, 2024.5 for H2)
    """
    return 1910 + (timecode - 1) / 2


def year_to_timecode(year: int, half: int = 1) -> int:
    """
    Convert year to time code.
    
    Args:
        year: Year (e.g. 2024)
        half: Half-year (1 or 2)
    
    Returns:
        Time code (e.g. 229 for 2024 H1)
    """
    return (year - 1910) * 2 + half


# =============================================================================
# CATEGORIES AND LIFETIMES
# =============================================================================

@dataclass(frozen=True)
class Kategori:
    """
    Asset category with baseline lifetimes.
    
    Lifetimes in half-years per Ei methodology.
    """
    cat_encode: int
    namn: str
    ekdep: int  # Economic lifetime (half-years)
    maxdep: int  # Maximum lifetime (half-years)
    enhet: str  # Typical unit: "km" or "st"


# The 17 categories per 4 kap 3 § EIFS 2023:4
KATEGORIER: Dict[int, Kategori] = {
    1: Kategori(1, "Andra markarbeten och byggnader, linjekoncession", 100, 124, "st"),
    2: Kategori(2, "Annan ledning, linjekoncession", 100, 124, "km"),
    3: Kategori(3, "Annan ledning, områdeskoncession", 100, 124, "km"),
    4: Kategori(4, "Annan luftledning, linjekoncession", 100, 124, "km"),
    5: Kategori(5, "It-system", 20, 24, "st"),
    6: Kategori(6, "Kabelskåp", 60, 74, "st"),
    7: Kategori(7, "Ledning med spänning om 220 kV eller mer (ej luftledning), linjekoncession", 80, 100, "km"),
    8: Kategori(8, "Luftledning med spänning om 220 kV eller mer, linjekoncession", 120, 150, "km"),
    9: Kategori(9, "Luftledning, områdeskoncession", 80, 100, "km"),
    10: Kategori(10, "Markarbeten och byggnader, 220 kV+, linjekoncession", 80, 100, "st"),
    11: Kategori(11, "Markarbeten och byggnader, områdeskoncession", 100, 124, "st"),
    12: Kategori(12, "Mätare", 20, 24, "st"),
    13: Kategori(13, "Nätstation", 80, 100, "st"),
    14: Kategori(14, "Shuntreaktor", 80, 100, "st"),
    15: Kategori(15, "Styr- och kontrollutrustning", 30, 36, "st"),
    16: Kategori(16, "Ställverk utan sekundärapparater", 80, 100, "st"),
    17: Kategori(17, "Transformator", 100, 124, "st"),
}


# =============================================================================
# VARIABLE DEFINITIONS
# =============================================================================

@dataclass
class VariabelDefinition:
    """
    Definition of a variable for RAB editor.
    
    Used to generate UI and validation.
    """
    namn: str                    # Internal column name in capbase_a
    visningsnamn: str            # Display name in UI
    datatyp: str                 # "float", "int", "str"
    redigerbar: bool             # If field is editable
    källa: str                   # "KENT", "Normvärdeslista", "Beräknad", "System"
    beskrivning: str             # Description
    enhet: Optional[str] = None  # E.g. "kr", "km", "st"
    min_värde: Optional[float] = None
    max_värde: Optional[float] = None


# =============================================================================
# VTYPE=4: NORMVÄRDE COMPONENTS (96% of data)
# =============================================================================

@dataclass
class NormvärderadKomponent:
    """
    Component valued with normvärde (vtype=4).
    
    NUAV formula: nuav_2022 = normvärde × count_comp
    
    Standard method for ~96% of all components.
    Normvärde is looked up from Ei's normvärdeslista based on
    techspec (technical specification) and volt (voltage level).
    """
    # Identification (not editable)
    id_component: int
    id_network: int
    cat_encode: int
    cat: str
    subcat_encode: int
    subcat: str
    
    # Editable fields
    count_comp: float           # Count or length
    time_from: int              # Time code for commissioning
    techspec: str               # Technical specification (dropdown)
    volt: str                   # Voltage level (dropdown if multiple exist)
    
    # Lookup from normvärdeslista (not directly editable)
    id_comptype: str            # Normvärde code (e.g. NG14514)
    normvärde: float            # Normvärde in SEK per unit
    
    # Calculated fields
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1              # Ownership: 1=owned
    capbase_existing: int = 1   # Always 1 for existing
    vtype: int = field(default=4, init=False)
    
    def __post_init__(self):
        """Calculate nuav_2022 from normvärde and count_comp."""
        self.nuav_2022 = self.normvärde * self.count_comp


NORMVÄRDERAD_VARIABLER: List[VariabelDefinition] = [
    VariabelDefinition(
        namn="count_comp",
        visningsnamn="Antal/längd",
        datatyp="float",
        redigerbar=True,
        källa="KENT",
        beskrivning="Antal enheter eller längd i km. Multipliceras med normvärde för att ge NUAV.",
        enhet="km eller st",
        min_värde=0.0001,
    ),
    VariabelDefinition(
        namn="time_from",
        visningsnamn="Idrifttagandeår",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="År då anläggningen ursprungligen togs i bruk. Lagras som tidskod internt.",
        min_värde=1910,
        max_värde=2023,
    ),
    VariabelDefinition(
        namn="techspec",
        visningsnamn="Teknisk specifikation",
        datatyp="str",
        redigerbar=True,
        källa="KENT",
        beskrivning="Teknisk beskrivning (t.ex. 'PEX 3x240 mm²'). Bestämmer normvärde via lookup.",
    ),
    VariabelDefinition(
        namn="volt",
        visningsnamn="Spänning",
        datatyp="str",
        redigerbar=True,
        källa="KENT",
        beskrivning="Spänningsnivå i kV. Kan påverka normvärde om samma techspec finns för flera spänningar.",
        enhet="kV",
    ),
    VariabelDefinition(
        namn="normvärde",
        visningsnamn="Normvärde",
        datatyp="float",
        redigerbar=False,
        källa="Normvärdeslista",
        beskrivning="Ei:s fastställda normvärde per enhet i 2022 års prisnivå. Slås upp via techspec+volt.",
        enhet="kr/enhet",
    ),
    VariabelDefinition(
        namn="nuav_2022",
        visningsnamn="NUAV",
        datatyp="float",
        redigerbar=False,
        källa="Beräknad",
        beskrivning="Nuanskaffningsvärde = normvärde × count_comp",
        enhet="kr",
    ),
]


# =============================================================================
# VTYPE=1: ANNAT SKÄLIGT VÄRDE (~1.4% of data)
# =============================================================================

@dataclass
class AnnatSkäligtVärdeKomponent:
    """
    Component valued with annat skäligt värde (vtype=1).
    
    NUAV formula: nuav_2022 = annatskäligtvärde × count_comp
    
    Used when normvärde, anskaffningsvärde and bokfört värde are missing.
    Value should correspond to nuanskaffningsvärde in 2022 price level.
    """
    # Identification
    id_component: int
    id_network: int
    cat_encode: int             # Editable
    cat: str
    subcat_encode: int
    subcat: str                 # Editable
    
    # Editable fields
    annatskäligtvärde: float    # Value per unit in SEK
    count_comp: float           # Number of units
    time_from: int              # Time code for commissioning
    
    # Calculated fields
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1
    capbase_existing: int = 1
    vtype: int = field(default=1, init=False)
    
    def __post_init__(self):
        """Calculate nuav_2022 from annatskäligtvärde and count_comp."""
        self.nuav_2022 = self.annatskäligtvärde * self.count_comp


ANNAT_SKÄLIGT_VÄRDE_VARIABLER: List[VariabelDefinition] = [
    VariabelDefinition(
        namn="annatskäligtvärde",
        visningsnamn="Annat skäligt värde",
        datatyp="float",
        redigerbar=True,
        källa="KENT",
        beskrivning="Skäligt värde per enhet i 2022 års prisnivå. Används när övriga metoder ej är tillämpliga.",
        enhet="kr/enhet",
        min_värde=0,
    ),
    VariabelDefinition(
        namn="count_comp",
        visningsnamn="Antal",
        datatyp="float",
        redigerbar=True,
        källa="KENT",
        beskrivning="Antal enheter.",
        enhet="st",
        min_värde=0.0001,
    ),
    VariabelDefinition(
        namn="time_from",
        visningsnamn="Idrifttagandeår",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="År då anläggningen ursprungligen togs i bruk.",
        min_värde=1910,
        max_värde=2023,
    ),
    VariabelDefinition(
        namn="cat_encode",
        visningsnamn="Kategori",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="Anläggningskategori (1-17). Bestämmer livslängder.",
    ),
    VariabelDefinition(
        namn="nuav_2022",
        visningsnamn="NUAV",
        datatyp="float",
        redigerbar=False,
        källa="Beräknad",
        beskrivning="Nuanskaffningsvärde = annatskäligtvärde × count_comp",
        enhet="kr",
    ),
]


# =============================================================================
# VTYPE=2: ANSKAFFNINGSVÄRDE (~0.1% of data)
# =============================================================================

@dataclass
class AnskaffningsvärdeKomponent:
    """
    Component valued with anskaffningsvärde (vtype=2).
    
    NUAV formula: nuav_2022 = rapporteradnuav
    
    Anskaffningsvärde is indexed to 2022 price level using BKI
    (Byggkostnadsindex). Requires special justification and verification.
    """
    # Identification
    id_component: int
    id_network: int
    cat_encode: int             # Editable
    cat: str
    subcat_encode: int
    subcat: str                 # Editable
    
    # Editable fields
    anskaffningsvärde: float    # Original value in acquisition year price level
    rapporteradnuav: float      # Indexed value in 2022 price level
    time_from: int              # Time code for commissioning (= acquisition year)
    
    # Calculated fields (nuav_2022 = rapporteradnuav directly)
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1
    capbase_existing: int = 1
    vtype: int = field(default=2, init=False)
    
    def __post_init__(self):
        """Set nuav_2022 to rapporteradnuav."""
        self.nuav_2022 = self.rapporteradnuav


ANSKAFFNINGSVÄRDE_VARIABLER: List[VariabelDefinition] = [
    VariabelDefinition(
        namn="anskaffningsvärde",
        visningsnamn="Ursprungligt anskaffningsvärde",
        datatyp="float",
        redigerbar=True,
        källa="KENT",
        beskrivning="Utgift för förvärv/tillverkning i anskaffningsårets prisnivå. Ska kunna verifieras.",
        enhet="kr",
        min_värde=0,
    ),
    VariabelDefinition(
        namn="rapporteradnuav",
        visningsnamn="Rapporterad NUAV",
        datatyp="float",
        redigerbar=True,
        källa="KENT",
        beskrivning="Anskaffningsvärde uppräknat till 2022 års prisnivå med BKI.",
        enhet="kr",
        min_värde=0,
    ),
    VariabelDefinition(
        namn="time_from",
        visningsnamn="Anskaffningsår",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="År då anläggningen anskaffades. Används för indexuppräkning.",
        min_värde=1910,
        max_värde=2023,
    ),
    VariabelDefinition(
        namn="cat_encode",
        visningsnamn="Kategori",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="Anläggningskategori (1-17). Bestämmer livslängder.",
    ),
    VariabelDefinition(
        namn="nuav_2022",
        visningsnamn="NUAV",
        datatyp="float",
        redigerbar=False,
        källa="Beräknad",
        beskrivning="Nuanskaffningsvärde = rapporteradnuav (redan indexuppräknat)",
        enhet="kr",
    ),
]


# =============================================================================
# VTYPE=5: INVESTMENTS AND RETIREMENTS (~2.5% of data)
# =============================================================================

@dataclass
class InvesteringKomponent:
    """
    Investment or retirement (vtype=5).
    
    NUAV formula: nuav_2022 = value_invest
    
    In the data, value_invest is already signed:
    - Positive for investments (increases capital base)
    - Negative for retirements (decreases capital base)
    
    The invest field is a flag: 1=investment, -1=retirement.
    
    In the UI, user enters amount as positive and selects type,
    then backend sets value_invest = amount × invest.
    
    Applies to planned changes during regulatory period 2024-2027.
    """
    # Identification
    id_component: int
    id_network: int
    cat_encode: int             # Editable
    cat: str
    subcat_encode: int
    subcat: str                 # Editable
    
    # Editable fields
    value_invest: float         # Total value (positive=inv, negative=ret)
    time_invest: int            # Time code for investment/retirement (229-236)
    invest: Literal[-1, 1]      # 1=investment, -1=retirement (flag)
    count_comp: float = 1.0     # Count (for reference)
    
    # Calculated fields
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1
    capbase_existing: int = 0   # Always 0 for investments/retirements
    vtype: int = field(default=5, init=False)
    
    # time_from is set to time_invest for new investments
    time_from: int = field(init=False)
    
    def __post_init__(self):
        """nuav_2022 = value_invest (already signed in data)."""
        self.nuav_2022 = self.value_invest
        self.time_from = self.time_invest


INVESTERING_VARIABLER: List[VariabelDefinition] = [
    VariabelDefinition(
        namn="invest",
        visningsnamn="Typ",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="Flagga: 1 = Investering, -1 = Utrangering. Styr tecknet på value_invest.",
    ),
    VariabelDefinition(
        namn="value_invest",
        visningsnamn="Totalvärde",
        datatyp="float",
        redigerbar=True,
        källa="KENT",
        beskrivning="Investeringens värde (positivt) eller utrangeringens värde (negativt). I UI anges belopp positivt, sedan sätter backend tecken via invest-flaggan.",
        enhet="kr",
    ),
    VariabelDefinition(
        namn="time_invest",
        visningsnamn="Halvår",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="Halvår för investering/utrangering (2024 H1 - 2027 H2). Tidskod 229-236.",
        min_värde=229,
        max_värde=236,
    ),
    VariabelDefinition(
        namn="cat_encode",
        visningsnamn="Kategori",
        datatyp="int",
        redigerbar=True,
        källa="KENT",
        beskrivning="Anläggningskategori (1-17). Bestämmer livslängder.",
    ),
    VariabelDefinition(
        namn="subcat",
        visningsnamn="Underkategori",
        datatyp="str",
        redigerbar=True,
        källa="KENT",
        beskrivning="Typ av anläggning (fritext eller dropdown).",
    ),
    VariabelDefinition(
        namn="count_comp",
        visningsnamn="Antal",
        datatyp="float",
        redigerbar=True,
        källa="KENT",
        beskrivning="Antal enheter (för referens, påverkar ej NUAV för vtype=5).",
        enhet="st",
        min_värde=0,
    ),
    VariabelDefinition(
        namn="nuav_2022",
        visningsnamn="NUAV",
        datatyp="float",
        redigerbar=False,
        källa="Beräknad",
        beskrivning="Nuanskaffningsvärde = value_invest (redan teckensatt).",
        enhet="kr",
    ),
]


# =============================================================================
# SUMMARY: VARIABLES PER VTYPE
# =============================================================================

VARIABLER_PER_VTYPE: Dict[int, List[VariabelDefinition]] = {
    VType.NORMVÄRDE: NORMVÄRDERAD_VARIABLER,
    VType.ANNAT_SKÄLIGT_VÄRDE: ANNAT_SKÄLIGT_VÄRDE_VARIABLER,
    VType.ANSKAFFNINGSVÄRDE: ANSKAFFNINGSVÄRDE_VARIABLER,
    VType.INVESTERING: INVESTERING_VARIABLER,
}

# UI display names for vtypes
VTYPE_NAMN: Dict[int, str] = {
    VType.ANNAT_SKÄLIGT_VÄRDE: "Annat skäligt värde",
    VType.ANSKAFFNINGSVÄRDE: "Anskaffningsvärde",
    VType.BOKFÖRT_VÄRDE: "Bokfört värde",
    VType.NORMVÄRDE: "Normvärde",
    VType.INVESTERING: "Investment/Retirement",
}


# =============================================================================
# NUAV CALCULATION (for backend)
# =============================================================================

def beräkna_nuav_2022(
    vtype: int,
    count_comp: float = 0,
    normvärde: float = 0,
    annatskäligtvärde: float = 0,
    rapporteradnuav: float = 0,
    value_invest: float = 0,
    invest: int = 1,
) -> float:
    """
    Calculate nuav_2022 based on vtype.
    
    This function is used in backend to calculate NUAV
    after user makes changes in RAB editor.
    
    Args:
        vtype: Valuation method (1, 2, 4, or 5)
        count_comp: Quantity/length (for vtype 1 and 4)
        normvärde: Normvärde per unit (for vtype 4)
        annatskäligtvärde: Annat skäligt värde per unit (for vtype 1)
        rapporteradnuav: Reported NUAV (for vtype 2)
        value_invest: Investment value, already signed (for vtype 5)
        invest: Investment flag, 1 or -1 (for vtype 5, not used in calculation)
    
    Returns:
        Calculated nuav_2022
    
    Raises:
        ValueError: If invalid vtype
    """
    if vtype == VType.NORMVÄRDE:
        return normvärde * count_comp
    elif vtype == VType.ANNAT_SKÄLIGT_VÄRDE:
        return annatskäligtvärde * count_comp
    elif vtype == VType.ANSKAFFNINGSVÄRDE:
        return rapporteradnuav
    elif vtype == VType.INVESTERING:
        return value_invest  # Already signed in data
    else:
        raise ValueError(f"Invalid vtype: {vtype}")


def get_redigerbara_fält(vtype: int) -> List[str]:
    """
    Return list of editable field names for given vtype.
    
    Args:
        vtype: Valuation method (1, 2, 4, or 5)
    
    Returns:
        List of column names that are editable
    """
    variabler = VARIABLER_PER_VTYPE.get(vtype, [])
    return [v.namn for v in variabler if v.redigerbar]


def get_nuav_inputs(vtype: int) -> List[str]:
    """
    Return list of fields used for NUAV calculation.
    
    Args:
        vtype: Valuation method
    
    Returns:
        List of column names used in NUAV formula
    """
    if vtype == VType.NORMVÄRDE:
        return ["normvärde", "count_comp"]
    elif vtype == VType.ANNAT_SKÄLIGT_VÄRDE:
        return ["annatskäligtvärde", "count_comp"]
    elif vtype == VType.ANSKAFFNINGSVÄRDE:
        return ["rapporteradnuav"]
    elif vtype == VType.INVESTERING:
        return ["value_invest"]  # Already signed
    else:
        return []


# =============================================================================
# VALIDATION
# =============================================================================

def validera_komponent(vtype: int, data: dict) -> List[str]:
    """
    Validate component data according to vtype-specific rules.
    
    Args:
        vtype: Valuation method
        data: Dict with component data
    
    Returns:
        List of error messages (empty if valid)
    """
    fel = []
    
    # Common validation
    if "time_from" in data:
        year = timecode_to_year(data["time_from"])
        if year < 1910 or year > 2023:
            fel.append(f"Invalid commissioning year: {year}")
    
    # vtype-specific validation
    if vtype == VType.NORMVÄRDE:
        if data.get("count_comp", 0) <= 0:
            fel.append("Quantity must be > 0")
        if data.get("normvärde", 0) <= 0:
            fel.append("Normvärde missing or invalid")
    
    elif vtype == VType.ANNAT_SKÄLIGT_VÄRDE:
        if data.get("count_comp", 0) <= 0:
            fel.append("Count must be > 0")
        if data.get("annatskäligtvärde", 0) <= 0:
            fel.append("Annat skäligt värde must be > 0")
    
    elif vtype == VType.ANSKAFFNINGSVÄRDE:
        if data.get("rapporteradnuav", 0) <= 0:
            fel.append("Reported NUAV must be > 0")
    
    elif vtype == VType.INVESTERING:
        if data.get("value_invest", 0) == 0:
            fel.append("Investment value cannot be 0")
        if data.get("invest") not in [-1, 1]:
            fel.append("Invest must be 1 (investment) or -1 (retirement)")
        # Check that sign matches flag
        value = data.get("value_invest", 0)
        invest_flag = data.get("invest", 1)
        if invest_flag == 1 and value < 0:
            fel.append("Investment should have positive value_invest")
        if invest_flag == -1 and value > 0:
            fel.append("Retirement should have negative value_invest")
        time_invest = data.get("time_invest", 0)
        if time_invest < TIMECODE_PERIOD_START or time_invest > TIMECODE_PERIOD_END:
            fel.append(f"Half-year must be within 2024-2027 (time code {TIMECODE_PERIOD_START}-{TIMECODE_PERIOD_END})")
    
    return fel