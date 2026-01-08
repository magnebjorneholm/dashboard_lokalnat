"""
calculations/rab_editor_variables.py

Dataklasser och variabeldefinitioner för RAB-editor.

Definierar vilka variabler som är redigerbara per värdetyp (vtype),
hur NUAV beräknas, och valideringsregler.

Struktur:
- BaseComponent: Gemensamma fält för alla komponenter
- NormvärderadKomponent (vtype=4): 96% av data
- AnnatSkäligtVärdeKomponent (vtype=1): ~1.4% av data  
- AnskaffningsvärdeKomponent (vtype=2): ~0.1% av data
- InvesteringKomponent (vtype=5): ~2.5% av data
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal
from enum import IntEnum


# =============================================================================
# KONSTANTER
# =============================================================================

class VType(IntEnum):
    """Värderingsmetoder enligt förordning 2018:1520."""
    ANNAT_SKÄLIGT_VÄRDE = 1
    ANSKAFFNINGSVÄRDE = 2
    BOKFÖRT_VÄRDE = 3  # Förekommer ej i exempeldata
    NORMVÄRDE = 4
    INVESTERING = 5


# Tidskoder för tillsynsperioden 2024-2027
TIMECODE_PERIOD_START = 229  # 2024 H1
TIMECODE_PERIOD_END = 236    # 2027 H2

# Mappning halvår till tidskod
HALFYEAR_TO_TIMECODE: Dict[str, int] = {
    "2024 H1": 229, "2024 H2": 230,
    "2025 H1": 231, "2025 H2": 232,
    "2026 H1": 233, "2026 H2": 234,
    "2027 H1": 235, "2027 H2": 236,
}

TIMECODE_TO_HALFYEAR: Dict[int, str] = {v: k for k, v in HALFYEAR_TO_TIMECODE.items()}


# =============================================================================
# HJÄLPFUNKTIONER FÖR TIDSKODER
# =============================================================================

def timecode_to_year(timecode: int) -> float:
    """
    Konverterar tidskod till år.
    
    Tidskod = (år - 1910) × 2 + halvår
    där halvår = 1 (H1) eller 2 (H2)
    
    Args:
        timecode: Tidskod (t.ex. 229 för 2024 H1)
    
    Returns:
        År som float (t.ex. 2024.0 för H1, 2024.5 för H2)
    """
    return 1910 + (timecode - 1) / 2


def year_to_timecode(year: int, half: int = 1) -> int:
    """
    Konverterar år till tidskod.
    
    Args:
        year: År (t.ex. 2024)
        half: Halvår (1 eller 2)
    
    Returns:
        Tidskod (t.ex. 229 för 2024 H1)
    """
    return (year - 1910) * 2 + half


# =============================================================================
# KATEGORIER OCH LIVSLÄNGDER
# =============================================================================

@dataclass(frozen=True)
class Kategori:
    """
    Anläggningskategori med baseline-livslängder.
    
    Livslängder anges i halvår enligt Ei:s metoddokument.
    """
    cat_encode: int
    namn: str
    ekdep: int  # Ekonomisk livslängd (halvår)
    maxdep: int  # Maximal livslängd (halvår)
    enhet: str  # Typisk enhet: "km" eller "st"


# De 17 kategorierna enligt 4 kap 3 § EIFS 2023:4
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
# VARIABELDEFINITIONER
# =============================================================================

@dataclass
class VariabelDefinition:
    """
    Definition av en variabel för RAB-editor.
    
    Används för att generera UI och validering.
    """
    namn: str                    # Internt kolumnnamn i capbase_a
    visningsnamn: str            # Namn i UI
    datatyp: str                 # "float", "int", "str"
    redigerbar: bool             # Om fältet kan redigeras
    källa: str                   # "KENT", "Normvärdeslista", "Beräknad", "System"
    beskrivning: str             # Förklaring
    enhet: Optional[str] = None  # T.ex. "kr", "km", "st"
    min_värde: Optional[float] = None
    max_värde: Optional[float] = None


# =============================================================================
# VTYPE=4: NORMVÄRDERADE KOMPONENTER (96% av data)
# =============================================================================

@dataclass
class NormvärderadKomponent:
    """
    Komponent värderad med normvärde (vtype=4).
    
    NUAV-formel: nuav_2022 = normvärde × count_comp
    
    Detta är standardmetoden för ~96% av alla komponenter.
    Normvärdet slås upp från Ei:s normvärdeslista baserat på
    techspec (teknisk specifikation) och volt (spänningsnivå).
    """
    # Identifiering (ej redigerbara)
    id_component: int
    id_network: int
    cat_encode: int
    cat: str
    subcat_encode: int
    subcat: str
    
    # Redigerbara fält
    count_comp: float           # Antal eller längd
    time_from: int              # Tidskod för idrifttagande
    techspec: str               # Teknisk specifikation (dropdown)
    volt: str                   # Spänningsnivå (dropdown om flera finns)
    
    # Lookup från normvärdeslistan (ej direkt redigerbar)
    id_comptype: str            # Normvärdeskod (t.ex. NG14514)
    normvärde: float            # Normvärde i kr per enhet
    
    # Beräknade fält
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1              # Rådighet: 1=ägd
    capbase_existing: int = 1   # Alltid 1 för befintliga
    vtype: int = field(default=4, init=False)
    
    def __post_init__(self):
        """Beräknar nuav_2022 från normvärde och count_comp."""
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
# VTYPE=1: ANNAT SKÄLIGT VÄRDE (~1.4% av data)
# =============================================================================

@dataclass
class AnnatSkäligtVärdeKomponent:
    """
    Komponent värderad med annat skäligt värde (vtype=1).
    
    NUAV-formel: nuav_2022 = annatskäligtvärde × count_comp
    
    Används när normvärde, anskaffningsvärde och bokfört värde saknas.
    Värdet ska motsvara nuanskaffningsvärdet i 2022 års prisnivå.
    """
    # Identifiering
    id_component: int
    id_network: int
    cat_encode: int             # Redigerbar
    cat: str
    subcat_encode: int
    subcat: str                 # Redigerbar
    
    # Redigerbara fält
    annatskäligtvärde: float    # Värde per enhet i kr
    count_comp: float           # Antal enheter
    time_from: int              # Tidskod för idrifttagande
    
    # Beräknade fält
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1
    capbase_existing: int = 1
    vtype: int = field(default=1, init=False)
    
    def __post_init__(self):
        """Beräknar nuav_2022 från annatskäligtvärde och count_comp."""
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
# VTYPE=2: URSPRUNGLIGT ANSKAFFNINGSVÄRDE (~0.1% av data)
# =============================================================================

@dataclass
class AnskaffningsvärdeKomponent:
    """
    Komponent värderad med ursprungligt anskaffningsvärde (vtype=2).
    
    NUAV-formel: nuav_2022 = rapporteradnuav
    
    Anskaffningsvärdet indexuppräknas till 2022 års prisnivå med BKI
    (Byggkostnadsindex). Kräver särskilda skäl och verifikation.
    """
    # Identifiering
    id_component: int
    id_network: int
    cat_encode: int             # Redigerbar
    cat: str
    subcat_encode: int
    subcat: str                 # Redigerbar
    
    # Redigerbara fält
    anskaffningsvärde: float    # Ursprungligt värde i anskaffningsårets prisnivå
    rapporteradnuav: float      # Indexuppräknat värde i 2022 års prisnivå
    time_from: int              # Tidskod för idrifttagande (= anskaffningsår)
    
    # Beräknade fält (nuav_2022 = rapporteradnuav direkt)
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1
    capbase_existing: int = 1
    vtype: int = field(default=2, init=False)
    
    def __post_init__(self):
        """Sätter nuav_2022 till rapporteradnuav."""
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
# VTYPE=5: INVESTERINGAR OCH UTRANGERINGAR (~2.5% av data)
# =============================================================================

@dataclass
class InvesteringKomponent:
    """
    Investering eller utrangering (vtype=5).
    
    NUAV-formel: nuav_2022 = value_invest
    
    I datan är value_invest redan teckensatt:
    - Positivt för investeringar (ökar kapitalbas)
    - Negativt för utrangeringar (minskar kapitalbas)
    
    Fältet invest är en flagga: 1=investering, -1=utrangering.
    
    I UI ska användaren ange belopp som positivt tal och välja typ,
    sedan sätter backend value_invest = belopp × invest.
    
    Gäller för planerade förändringar under tillsynsperioden 2024-2027.
    """
    # Identifiering
    id_component: int
    id_network: int
    cat_encode: int             # Redigerbar
    cat: str
    subcat_encode: int
    subcat: str                 # Redigerbar
    
    # Redigerbara fält
    value_invest: float         # Totalvärde (positivt=inv, negativt=utr)
    time_invest: int            # Tidskod för investering/utrangering (229-236)
    invest: Literal[-1, 1]      # 1=investering, -1=utrangering (flagga)
    count_comp: float = 1.0     # Antal (för referens)
    
    # Beräknade fält
    nuav_2022: float = field(init=False)
    
    # Metadata
    owned: int = 1
    capbase_existing: int = 0   # Alltid 0 för investeringar/utrangeringar
    vtype: int = field(default=5, init=False)
    
    # time_from sätts till time_invest för nya investeringar
    time_from: int = field(init=False)
    
    def __post_init__(self):
        """nuav_2022 = value_invest (redan teckensatt i datan)."""
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
# SAMMANFATTNING: VARIABLER PER VTYPE
# =============================================================================

VARIABLER_PER_VTYPE: Dict[int, List[VariabelDefinition]] = {
    VType.NORMVÄRDE: NORMVÄRDERAD_VARIABLER,
    VType.ANNAT_SKÄLIGT_VÄRDE: ANNAT_SKÄLIGT_VÄRDE_VARIABLER,
    VType.ANSKAFFNINGSVÄRDE: ANSKAFFNINGSVÄRDE_VARIABLER,
    VType.INVESTERING: INVESTERING_VARIABLER,
}

VTYPE_NAMN: Dict[int, str] = {
    VType.ANNAT_SKÄLIGT_VÄRDE: "Annat skäligt värde",
    VType.ANSKAFFNINGSVÄRDE: "Ursprungligt anskaffningsvärde",
    VType.BOKFÖRT_VÄRDE: "Bokfört värde",
    VType.NORMVÄRDE: "Normvärde",
    VType.INVESTERING: "Investering/utrangering",
}


# =============================================================================
# NUAV-BERÄKNING (för backend)
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
    Beräknar nuav_2022 baserat på vtype.
    
    Denna funktion används i backend för att beräkna NUAV
    efter att användaren gjort ändringar i RAB-editor.
    
    Args:
        vtype: Värderingsmetod (1, 2, 4, eller 5)
        count_comp: Antal/längd (för vtype 1 och 4)
        normvärde: Normvärde per enhet (för vtype 4)
        annatskäligtvärde: Annat skäligt värde per enhet (för vtype 1)
        rapporteradnuav: Rapporterad NUAV (för vtype 2)
        value_invest: Investeringsvärde, redan teckensatt (för vtype 5)
        invest: Investeringsflagga, 1 eller -1 (för vtype 5, används ej i beräkning)
    
    Returns:
        Beräknad nuav_2022
    
    Raises:
        ValueError: Om ogiltig vtype
    """
    if vtype == VType.NORMVÄRDE:
        return normvärde * count_comp
    elif vtype == VType.ANNAT_SKÄLIGT_VÄRDE:
        return annatskäligtvärde * count_comp
    elif vtype == VType.ANSKAFFNINGSVÄRDE:
        return rapporteradnuav
    elif vtype == VType.INVESTERING:
        return value_invest  # Redan teckensatt i datan
    else:
        raise ValueError(f"Ogiltig vtype: {vtype}")


def get_redigerbara_fält(vtype: int) -> List[str]:
    """
    Returnerar lista med redigerbara fältnamn för given vtype.
    
    Args:
        vtype: Värderingsmetod (1, 2, 4, eller 5)
    
    Returns:
        Lista med kolumnnamn som är redigerbara
    """
    variabler = VARIABLER_PER_VTYPE.get(vtype, [])
    return [v.namn for v in variabler if v.redigerbar]


def get_nuav_inputs(vtype: int) -> List[str]:
    """
    Returnerar lista med fält som används för NUAV-beräkning.
    
    Args:
        vtype: Värderingsmetod
    
    Returns:
        Lista med kolumnnamn som ingår i NUAV-formeln
    """
    if vtype == VType.NORMVÄRDE:
        return ["normvärde", "count_comp"]
    elif vtype == VType.ANNAT_SKÄLIGT_VÄRDE:
        return ["annatskäligtvärde", "count_comp"]
    elif vtype == VType.ANSKAFFNINGSVÄRDE:
        return ["rapporteradnuav"]
    elif vtype == VType.INVESTERING:
        return ["value_invest"]  # Redan teckensatt
    else:
        return []


# =============================================================================
# VALIDERING
# =============================================================================

def validera_komponent(vtype: int, data: dict) -> List[str]:
    """
    Validerar komponentdata enligt vtype-specifika regler.
    
    Args:
        vtype: Värderingsmetod
        data: Dict med komponentdata
    
    Returns:
        Lista med felmeddelanden (tom om valid)
    """
    fel = []
    
    # Gemensam validering
    if "time_from" in data:
        year = timecode_to_year(data["time_from"])
        if year < 1910 or year > 2023:
            fel.append(f"Ogiltigt idrifttagandeår: {year}")
    
    # vtype-specifik validering
    if vtype == VType.NORMVÄRDE:
        if data.get("count_comp", 0) <= 0:
            fel.append("Antal/längd måste vara > 0")
        if data.get("normvärde", 0) <= 0:
            fel.append("Normvärde saknas eller är ogiltigt")
    
    elif vtype == VType.ANNAT_SKÄLIGT_VÄRDE:
        if data.get("count_comp", 0) <= 0:
            fel.append("Antal måste vara > 0")
        if data.get("annatskäligtvärde", 0) <= 0:
            fel.append("Annat skäligt värde måste vara > 0")
    
    elif vtype == VType.ANSKAFFNINGSVÄRDE:
        if data.get("rapporteradnuav", 0) <= 0:
            fel.append("Rapporterad NUAV måste vara > 0")
    
    elif vtype == VType.INVESTERING:
        if data.get("value_invest", 0) == 0:
            fel.append("Investeringsvärde får inte vara 0")
        if data.get("invest") not in [-1, 1]:
            fel.append("Invest måste vara 1 (investering) eller -1 (utrangering)")
        # Kontrollera att tecken stämmer med flagga
        value = data.get("value_invest", 0)
        invest_flag = data.get("invest", 1)
        if invest_flag == 1 and value < 0:
            fel.append("Investering ska ha positivt value_invest")
        if invest_flag == -1 and value > 0:
            fel.append("Utrangering ska ha negativt value_invest")
        time_invest = data.get("time_invest", 0)
        if time_invest < TIMECODE_PERIOD_START or time_invest > TIMECODE_PERIOD_END:
            fel.append(f"Halvår måste vara inom 2024-2027 (tidskod {TIMECODE_PERIOD_START}-{TIMECODE_PERIOD_END})")
    
    return fel
