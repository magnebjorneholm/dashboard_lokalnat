import pandas as pd
import numpy as np
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, value
from app.run_logger import save_run

def run_dea_model(
    df: pd.DataFrame,
    rts: str = "crs",
    trunkering_min: float = 0.162416,
    trunkering_max: float = 0.3,
    input_cols: list = ["CAPEX", "OPEXp"],
    output_cols: list = ["CU", "MW", "NS", "MWhl", "MWhh"],
    outlier_filter: bool = True
) -> pd.DataFrame:
    """
    Kör DEA med eller utan outlierfiltrering.
    """
    df = df.copy()
    df["CAPEX"] = pd.to_numeric(df["CAPEX"], errors="coerce")
    df["OPEXp"] = pd.to_numeric(df["OPEXp"], errors="coerce")

    inputs = df[input_cols].values
    outputs = df[output_cols].values

    def run_super_efficiency_dea(inputs, outputs, rts):
        n = len(inputs)
        eff = []
        for i in range(n):
            model = LpProblem(name=f"DEA_SUPER_DMUi_{i}", sense=LpMinimize)
            theta = LpVariable("theta", lowBound=0)
            lambdas = [LpVariable(f"lambda_{j}", lowBound=0) for j in range(n)]
            model += theta

            for r in range(outputs.shape[1]):
                model += lpSum(lambdas[j] * outputs[j][r] for j in range(n) if j != i) >= outputs[i][r]

            for k in range(inputs.shape[1]):
                model += lpSum(lambdas[j] * inputs[j][k] for j in range(n) if j != i) <= theta * inputs[i][k]

            if rts == "vrs":
                model += lpSum(lambdas[j] for j in range(n) if j != i) == 1

            model.solve()
            eff.append(value(theta))
        return np.array(eff)

    if not outlier_filter:
        # Kör utan outlierfilter
        eff = run_super_efficiency_dea(inputs, outputs, rts)
        effektivitet = np.minimum(eff, 1)
        revred = 1 - effektivitet
        revred_compress = np.clip(revred, trunkering_min, trunkering_max)
        effkrav_proc = ((1 + revred_compress / 4) ** 0.25) - 1

        df["Effektivitet"] = effektivitet
        df["Supereffektivitet"] = eff
        df["Effkrav_proc"] = effkrav_proc
        df["is_outlier"] = False
    else:
        # Kör med outlierfilter (standard)
        eff1 = run_super_efficiency_dea(inputs, outputs, rts)
        q75 = np.percentile(eff1, 75)
        q25 = np.percentile(eff1, 25)
        threshold = q75 + 2 * (q75 - q25)
        non_outlier_mask = eff1 <= threshold
        df["is_outlier"] = ~non_outlier_mask

        inputs_clean = inputs[non_outlier_mask]
        outputs_clean = outputs[non_outlier_mask]
        eff2 = run_super_efficiency_dea(inputs_clean, outputs_clean, rts)

        result_effektivitet = []
        result_supereffektivitet = []
        result_effkrav_proc = []

        j = 0
        for is_outlier in df["is_outlier"]:
            if is_outlier:
                result_effektivitet.append(np.nan)
                result_supereffektivitet.append(np.nan)
                result_effkrav_proc.append(np.nan)
            else:
                theta = eff2[j]
                effektivitet = min(theta, 1)
                revred = 1 - effektivitet
                revred_compress = np.clip(revred, trunkering_min, trunkering_max)
                effkrav = ((1 + revred_compress / 4) ** 0.25) - 1

                result_effektivitet.append(effektivitet)
                result_supereffektivitet.append(theta)
                result_effkrav_proc.append(effkrav)
                j += 1

        df["Effektivitet"] = result_effektivitet
        df["Supereffektivitet"] = result_supereffektivitet
        df["Effkrav_proc"] = result_effkrav_proc

    # Logga körning
    save_run("DEA", {
        "rts": rts,
        "input_cols": input_cols,
        "output_cols": output_cols,
        "trunkering_min": trunkering_min,
        "trunkering_max": trunkering_max,
        "outlier_filter": outlier_filter
    }, df)

    return df
