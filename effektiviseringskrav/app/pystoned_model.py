import pandas as pd
import numpy as np
from pystoned import CNLS, StoNED
from effektiviseringskrav.app.run_logger import save_run

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
    - Outliers får sina krav baserat på θ1 (första körningen).
    """
    df = df.copy()
    x = df[input_cols].to_numpy()
    y = df[output_cols].to_numpy()

    # Första skattning (alla med)
    cnls1 = CNLS.CNLS(y=y, x=x, rts=rts, fun=fun, cet=cet)
    cnls1.optimize(solver="local" if cet == "mult" else None)
    stoned1 = StoNED.StoNED(cnls1)
    stoned1.get_technical_inefficiency(method="QLE")
    u_hat1 = stoned1.get_technical_inefficiency(method="KDE")
    theta1 = 1 / (1 + u_hat1)

    # Outlieridentifiering
    if outlier_filter:
        q25 = np.percentile(theta1, 25)
        q75 = np.percentile(theta1, 75)
        threshold = q25 - 2 * (q75 - q25)
        mask = theta1 >= threshold
        df["is_outlier"] = ~mask
    else:
        mask = np.ones(len(df), dtype=bool)
        df["is_outlier"] = False

    # Andra skattning utan outliers
    x_clean = x[mask]
    y_clean = y[mask]
    cnls2 = CNLS.CNLS(y=y_clean, x=x_clean, rts=rts, fun=fun, cet=cet)
    cnls2.optimize(solver="local" if cet == "mult" else None)
    stoned2 = StoNED.StoNED(cnls2)
    stoned2.get_technical_inefficiency(method="QLE")
    u_hat2 = stoned2.get_technical_inefficiency(method="KDE")
    theta2 = 1 / (1 + u_hat2)

    # Tilldela theta och krav
    result_theta = []
    result_krav = []
    j = 0

    for i, is_outlier in enumerate(df["is_outlier"]):
        if is_outlier:
            t = theta1[i]
        else:
            t = theta2[j]
            j += 1

        result_theta.append(t)

        if kravmetod == "absolut":
            revred = 1 - t
            revred_compress = np.clip(revred, trunkering_min, trunkering_max)
            krav = ((1 + revred_compress / 4) ** 0.25) - 1
        elif kravmetod == "percentilbaserat":
            revred_all = 1 - theta2
            r10, r90 = np.percentile(revred_all, 10), np.percentile(revred_all, 90)
            revred_raw = 1 - t
            revred_scaled = (revred_raw - r10) / (r90 - r10)
            revred_scaled = np.clip(revred_scaled, 0, 1)
            revred_compress = revred_scaled * (trunkering_max - trunkering_min) + trunkering_min
            krav = ((1 + revred_compress / 4) ** 0.25) - 1
        else:
            raise ValueError(f"Ogiltig kravmetod: {kravmetod}")

        result_krav.append(krav)

    df["Effektivitet"] = result_theta
    df["Effkrav_proc"] = result_krav
    df["Kravmetod"] = kravmetod

    # Konvertera till float för loggning
    df_for_loggning = df.copy()
    for col in ["Effektivitet", "Effkrav_proc"]:
        if col in df_for_loggning.columns:
            df_for_loggning[col] = pd.to_numeric(df_for_loggning[col], errors="coerce")

    save_run("PyStoned", {
        "rts": rts,
        "fun": fun,
        "cet": cet,
        "input_cols": input_cols,
        "output_cols": output_cols,
        "trunkering_min": trunkering_min,
        "trunkering_max": trunkering_max,
        "outlier_filter": outlier_filter,
        "kravmetod": kravmetod
    }, df_for_loggning)

    return df
