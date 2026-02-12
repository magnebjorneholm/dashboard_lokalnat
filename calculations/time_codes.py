"""
time_codes.py

Tidskodskonstanter för KENT-beräkningar.
Ei använder HALVÅRS-tidskoder där 229 = 2024H1, 230 = 2024H2, etc.
"""

# Halvår till tidskod
HALFYEAR_TO_TIMECODE = {
    '2024H1': 229, '2024H2': 230,
    '2025H1': 231, '2025H2': 232,
    '2026H1': 233, '2026H2': 234,
    '2027H1': 235, '2027H2': 236,
}

# Tidskod till halvår
TIMECODE_TO_HALFYEAR = {v: k for k, v in HALFYEAR_TO_TIMECODE.items()}

# År till tidskoder (två halvår per år)
YEAR_TO_TIMECODES = {
    2024: [229, 230],
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236],
}

# Alla tidskoder för tillsynsperioden 2024-2027
PERIOD_2024_2027_CODES = list(range(229, 237))  # 229-236 = 8 halvår

# Tillsynsperiodens år
SUPERVISION_YEARS = [2024, 2025, 2026, 2027]

# Första tidskoden för varje år
YEAR_TO_FIRST_TIMECODE = {
    2024: 229,
    2025: 231,
    2026: 233,
    2027: 235,
}


def timecode_to_year(timecode: int) -> int:
    """Konvertera tidskod till år. Ex: 229 → 2024, 230 → 2024, 231 → 2025."""
    return 2024 + (timecode - 229) // 2


def timecode_to_halfyear(timecode: int) -> int:
    """Konvertera tidskod till halvår (1 eller 2). Ex: 229 → 1, 230 → 2."""
    return ((timecode - 229) % 2) + 1


def timecode_to_label(timecode: int) -> str:
    """Konvertera tidskod till läsbar label. Ex: 229 → '2024H1'."""
    year = timecode_to_year(timecode)
    half = timecode_to_halfyear(timecode)
    return f"{year}H{half}"


def year_to_timecodes(year: int) -> list:
    """Hämta tidskoder för ett år. Ex: 2024 → [229, 230]."""
    return YEAR_TO_TIMECODES.get(year, [])