import pandas as pd

def load_data(filepath):
    try:
        df = pd.read_excel(filepath, sheet_name="Körning", engine="openpyxl")
    except Exception as e:
        raise RuntimeError(f"Fel vid inläsning av fil: {e}")

    # Kontrollera att viktiga kolumner finns
    expected_cols = [
        'DMU', 'REId', 'Företag',
        'OPEXp', 'CAPEX', 'CU',
        'MW', 'NS', 'MWhl', 'MWhh'
    ]
    missing_cols = [col for col in expected_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Följande kolumner saknas i Excel-filen: {missing_cols}")

    # Ingen filtrering av nollor eller NaN – låt modellerna själva hantera det
    df.reset_index(drop=True, inplace=True)
    return df
