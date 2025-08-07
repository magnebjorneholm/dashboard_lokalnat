# kpi_simulering.py
# (1) Modellspecifikation: Simulerar kapitalbas enligt förmögenhetsbevarande princip, d.v.s. anskaffningsvärde * KPI-index.
# (2) Motivation: Ei har som mål att gå från nuanskaffningsvärdering (kapacitetsbevarande) till förmögenhetsbevarande 2028–2031.

import pandas as pd

# Mockad KPI-serie med basår 2024 = 113.7 (kan ersättas med SCB-data senare)
KPI_INDEX = {
    2016: 100.0,
    2017: 101.5,
    2018: 103.2,
    2019: 105.0,
    2020: 106.4,
    2021: 108.7,
    2022: 111.0,
    2023: 112.3,
    2024: 113.7
}

KPI_2024 = KPI_INDEX[2024]


def simulera_kapitalbas_kpi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tar in komponentdata och returnerar en DataFrame med:
    - Simulerad KPI-baserad kapitalbas (kapitalbas_kpi)
    - Skillnad jämfört med nuanskaffningsvärde (diff_kpi_vs_nuav)
    - Alla nödvändiga kolumner för analys och visualisering
    """
    df = df.copy()

    # Mappa investeringsår
    df = df.dropna(subset=["time_invest"])

    # Säkerställ rätt datatyp för mapping
    year_map = {
        227.0: 2015, 228.0: 2016, 229.0: 2017,
        230.0: 2018, 231.0: 2019, 232.0: 2020,
        233.0: 2021, 234.0: 2022, 235.0: 2023, 236.0: 2024
    }
    df["year_invest"] = df["time_invest"].map(year_map)

    # Filtrera bort rader utan investeringsår eller anskaffningsvärde
    df = df.dropna(subset=["year_invest", "anskaffningsvärde"])

    # Tilldela KPI-index per investeringsår
    df["kpi_invest"] = df["year_invest"].map(KPI_INDEX)

    # Räkna ut KPI-justerad kapitalbas
    df["kapitalbas_kpi"] = df["anskaffningsvärde"] * (KPI_2024 / df["kpi_invest"])

    # Skillnad mot nuanskaffningsvärde (positivt = överskattning i BKI-baserad modell)
    df["diff_kpi_vs_nuav"] = df["kapitalbas_kpi"] - df["nuav"]

    return df[
        ["id_network", "cat", "subcat", "anskaffningsvärde", "nuav",
         "kapitalbas_kpi", "diff_kpi_vs_nuav", "year_invest"]
    ]
