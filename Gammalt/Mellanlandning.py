import pandas as pd
import numpy as np
from pystoned import CNLS, StoNED

def run_pystoned_model(
    df: pd.DataFrame,
    rts: str = "crs",
    fun: str = "prod",
    cet: str = "addi",
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    input_cols: list = ["OPEXp", "CAPEX"],
    output_cols: list = ["CU"],
    outlier_filter: bool = True,
    kravmetod: str = "absolut"  # "absolut" eller "percentilbaserat"
) -> pd.DataFrame:
    """
    Kör en StoNED-modell (PyStoned) med möjlighet att välja metod
    för effektivitetskravsberäkning: 'absolut' eller 'percentilbaserat'.

    - Effektivitet θ = 1 / (1 + u_hat) beräknas via KDE.
    - Outliers identifieras via boxplotregel på θ.
    - Effektivitetskrav härleds antingen från θ direkt eller via rankskala.
    """
    df = df.copy()
    x = df[input_cols].to_numpy()
    y = df[output_cols].to_numpy()

    # Första skattning
    cnls1 = CNLS.CNLS(y=y, x=x, rts=rts, fun=fun, cet=cet)
    cnls1.optimize(solver="local" if cet == "mult" else None)
    stoned1 = StoNED.StoNED(cnls1)
    stoned1.get_technical_inefficiency(method="QLE")
    u_hat1 = stoned1.get_technical_inefficiency(method="KDE")
    theta1 = 1 / (1 + u_hat1)

    if outlier_filter:
        q25 = np.percentile(theta1, 25)
        q75 = np.percentile(theta1, 75)
        threshold = q25 - 2 * (q75 - q25)
        mask = theta1 >= threshold
        df["is_outlier"] = ~mask
        x = x[mask]
        y = y[mask]
    else:
        df["is_outlier"] = False
        mask = np.ones(len(df), dtype=bool)

    # Andra skattning utan outliers
    cnls2 = CNLS.CNLS(y=y, x=x, rts=rts, fun=fun, cet=cet)
    cnls2.optimize(solver="local" if cet == "mult" else None)
    stoned2 = StoNED.StoNED(cnls2)
    stoned2.get_technical_inefficiency(method="QLE")
    u_hat2 = stoned2.get_technical_inefficiency(method="KDE")
    theta2 = 1 / (1 + u_hat2)

    # Förkräva krav
    result_theta = []
    result_krav = []
    j = 0

    for is_outlier in df["is_outlier"]:
        if is_outlier:
            result_theta.append(np.nan)
            result_krav.append(np.nan)
        else:
            t = theta2[j]
            result_theta.append(t)

            if kravmetod == "absolut":
                revred = 1 - t
                revred_compress = np.clip(revred, trunkering_min, trunkering_max)
                krav = ((1 + revred_compress / 4) ** 0.25) - 1

            elif kravmetod == "percentilbaserat":
                revred_all = 1 - theta2  # ineffektivitet för alla DMUs
                r10, r90 = np.percentile(revred_all, 10), np.percentile(revred_all, 90)

                # Skala företags ineffektivitet till revred ∈ [trunk_min, trunk_max]
                revred_raw = revred_all[j]
                revred_scaled = (revred_raw - r10) / (r90 - r10)
                revred_scaled = np.clip(revred_scaled, 0, 1)
                revred_compress = revred_scaled * (trunkering_max - trunkering_min) + trunkering_min

                # Använd DEA-formeln för att räkna ut kravet
                krav = ((1 + revred_compress / 4) ** 0.25) - 1

            else:
                raise ValueError(f"Ogiltig kravmetod: {kravmetod}")

            result_krav.append(krav)
            j += 1

    df["Effektivitet"] = result_theta
    df["Effkrav_proc"] = result_krav
    df["Kravmetod"] = kravmetod
    return df
