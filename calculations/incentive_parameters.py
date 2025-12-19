"""
calculations/incentive_parameters.py

Parametrar for kvalitets- och natincitament enligt Bilaga 4 (Ei).
Varden hamtade fran 2_set_parameters.do.

Kundtypsmappning (SNI):
  1 = Jordbruk
  2 = Industri
  3 = Handel/tjanster
  4 = Offentlig verksamhet
  5 = Hushall
  6 = Granspunkt
"""

from typing import Dict, Tuple

# KPI - prisjustering till 2022 ars priser
KPI: Dict[int, float] = {
    2024: 1.1546,
    2025: 1.1546,
    2026: 1.1546,
    2027: 1.1546,
}

# Natforlustkostnad (kr/MWh)
K_NF: Dict[int, float] = {
    2024: 753.44,
    2025: 753.44,
    2026: 753.44,
    2027: 753.44,
}

# Begransningar
ADJ_MAX_AGG: float = 1/3          # Max 1/3 av avkastning per incitament
ADJ_MAX_CEMI4: float = 0.25       # Max 25% CEMI4-korrigering
SHARING_NETLOSS: float = 0.75    # Delningsfaktor natforlust

# AIT-kostnader (kr/kWh) per (ann, sni)
# ann: 'a' = aviserade (planned), 'o' = oaviserade (unplanned)
AIT_COSTS: Dict[Tuple[str, int], float] = {
    # Oaviserade (unplanned)
    ('o', 1): 34.35,    # Jordbruk
    ('o', 2): 159.96,   # Industri
    ('o', 3): 175.06,   # Handel/tjanster
    ('o', 4): 96.97,    # Offentlig v.
    ('o', 5): 5.84,     # Hushall
    ('o', 6): 96.01,    # Granspunkt
    # Aviserade (planned)
    ('a', 1): 14.10,    # Jordbruk
    ('a', 2): 76.00,    # Industri
    ('a', 3): 79.31,    # Handel/tjanster
    ('a', 4): 43.70,    # Offentlig v.
    ('a', 5): 4.98,     # Hushall
    ('a', 6): 45.16,    # Granspunkt
}

# AIF-kostnader (kr/kW) per (ann, sni)
AIF_COSTS: Dict[Tuple[str, int], float] = {
    # Oaviserade (unplanned)
    ('o', 1): 9.78,     # Jordbruk
    ('o', 2): 70.75,    # Industri
    ('o', 3): 17.78,    # Handel/tjanster
    ('o', 4): 7.65,     # Offentlig v.
    ('o', 5): 1.95,     # Hushall
    ('o', 6): 22.18,    # Granspunkt
    # Aviserade (planned)
    ('a', 1): 1.72,     # Jordbruk
    ('a', 2): 20.71,    # Industri
    ('a', 3): 5.94,     # Handel/tjanster
    ('a', 4): 0.92,     # Offentlig v.
    ('a', 5): 1.85,     # Hushall
    ('a', 6): 7.08,     # Granspunkt
}

# REIds som saknar fullstandig incitamentdata
# Dessa far NaN i berakningen, ersatts med 0 i slutresultat med flagga
MISSING_DATA_IDS: list = [139, 168, 177, 3050]

# Kundtypsbeskrivningar (for dokumentation/UI)
SNI_LABELS: Dict[int, str] = {
    1: "Jordbruk",
    2: "Industri",
    3: "Handel/tjanster",
    4: "Offentlig verksamhet",
    5: "Hushall",
    6: "Granspunkt",
}