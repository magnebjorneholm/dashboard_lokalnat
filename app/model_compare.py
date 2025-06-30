# app/model_compare.py

import pandas as pd
import numpy as np

def normalize_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Skapar kolumner för Rank, Percentil och Eff_rel (baserat på percentil).
    """
    df = df.copy()
    df["Rank"] = df["Effektivitet"].rank(method="min", ascending=True)
    df["Percentil"] = df["Effektivitet"].rank(pct=True)
    df["Eff_rel"] = df["Percentil"]
    return df

def calculate_effkrav(df: pd.DataFrame, trunk_min: float, trunk_max: float, kr_bas_col: str = "OPEXp") -> pd.DataFrame:
    """
    Beräkna effektiviseringskrav i procent och kronor baserat på Eff_rel.
    """
    df = df.copy()
    revred = 1 - df["Eff_rel"]
    revred_compress = np.clip(revred, trunk_min, trunk_max)
    df["Effkrav_proc"] = ((1 + revred_compress / 4) ** 0.25) - 1
    df["Effkrav_kr"] = df[kr_bas_col] * df["Effkrav_proc"]
    return df

def generate_summary_table(
    df: pd.DataFrame,
    trunk_min: float = 0.162416,
    trunk_max: float = 0.3,
    kr_bas_col: str = "OPEXp"
) -> pd.DataFrame:
    """
    Kombinerar normalisering och kravberäkning till en färdig tabell.
    """
    df = normalize_efficiency(df)
    df = calculate_effkrav(df, trunk_min, trunk_max, kr_bas_col)

    cols = [
        "Företag", "Rank", "Percentil", "Effektivitet", "Eff_rel", "Effkrav_proc", "Effkrav_kr"
    ]
    return df[cols].copy()
