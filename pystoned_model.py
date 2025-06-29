# pystoned_model.py

import pandas as pd
import numpy as np
from pystoned import CNLS, StoNED

def run_pystoned_model(
    df: pd.DataFrame,
    rts: str = "crs",
    fun: str = "prod",
    cet: str = "addi",
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3
) -> pd.DataFrame:
    """
    Kör en StoNED-modell med parametrar.
    
    Parametrar:
        df: indata med kolumnerna OPEXp, CAPEX, CU
        rts: skalavkastning ("crs", "vrs", etc.)
        fun: typ av funktion ("prod", "cost")
        cet: typ av teknik ("addi", "mult", etc.)
        trunkering_min: nedre gräns för intäktsreduktion
        trunkering_max: övre gräns för intäktsreduktion

    Returnerar:
        DataFrame med kolumnerna Effektivitet och Effkrav_proc
    """
    df = df.copy()

    x = df[["OPEXp", "CAPEX"]].to_numpy()
    y = df[["CU"]].to_numpy()  # output = antal kunder

    # 1. Estimera CNLS-produktionsfront
    cnls = CNLS.CNLS(
        y=y,
        x=x,
        rts=rts,
        fun=fun,
        cet=cet
    )
    if cet == "mult":
        cnls.optimize(solver="local")  # krävs för multiplicativ teknologi
    else:
        cnls.optimize()


    # 2. StoNED med QLE och KDE
    stoned = StoNED.StoNED(cnls)
    stoned.get_technical_inefficiency(method="QLE")
    u_hat = stoned.get_technical_inefficiency(method="KDE")
    theta = 1 / (1 + u_hat)

    # 3. Trunkering av effektivitetskrav
    revred = 1 - theta
    revred_compress = np.clip(revred, trunkering_min, trunkering_max)
    effkrav_proc = ((1 + revred_compress / 4) ** 0.25) - 1

    df["Effektivitet"] = theta
    df["Effkrav_proc"] = effkrav_proc

    return df
