# kapitalbas_app/utils.py
# Gemensam årsmappning och hjälpfunktioner

# Bestäm en gång för hela projektet om 236 = 2023 eller 2024
YEAR_MAP = {
    229: 2016, 230: 2017, 231: 2018, 232: 2019,
    233: 2020, 234: 2021, 235: 2022, 236: 2023
}

def map_year(df, time_col="time", year_col="year"):
    """Mappar intern tidskod till år enligt YEAR_MAP."""
    df = df.copy()
    df[year_col] = df[time_col].map(YEAR_MAP).astype(int)
    return df
