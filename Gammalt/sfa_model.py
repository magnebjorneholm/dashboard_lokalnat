import pandas as pd
import numpy as np
import subprocess
import os

def run_sfa_model(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    vars_required = ['DMU', 'Företag', 'OPEXp', 'CAPEX', 'MW', 'NS', 'MWhl', 'CU', 'MWhh']
    df = df[(df[vars_required[2:]] > 0).all(axis=1)].copy()

    # 1. Skriv indata till Excel
    os.makedirs("output", exist_ok=True)
    df[vars_required].to_excel("output/sfa_input.xlsx", index=False)

    # 2. Kör R-skript
    try:
        subprocess.run(["Rscript", "app/sfa_r_model.R"], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("R-scriptet misslyckades. Kontrollera sfa_r_model.R") from e

    # 3. Läs tillbaka resultat
    result = pd.read_excel("output/sfa_result.xlsx")
    return result
