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
    Kör DEA med eller utan outlierfiltrering enligt EI:s metod.
    """
    df = df.copy()
    df[input_cols] = df[input_cols].apply(pd.to_numeric, errors="coerce")

    inputs = df[input_cols].values
    outputs = df[output_cols].values

    def run_super_efficiency_dea(inputs, outputs, rts):
        n = len(inputs)
        eff = []
        for i in range(n):
            if np.any(np.isnan(inputs[i])) or np.any(np.isnan(outputs[i])):
                eff.append("OUTLIER")
                continue

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

            try:
                model.solve()
                score = value(theta)
                if score is None or np.isnan(score):
                    score = "OUTLIER"
            except:
                score = "OUTLIER"

            eff.append(score)
        return eff

    # === Första körning ===
    eff1 = run_super_efficiency_dea(inputs, outputs, rts)
    df["supereff1"] = eff1

    theta_valid = [e for e in eff1 if isinstance(e, (int, float)) and not np.isnan(e)]
    q75 = np.percentile(theta_valid, 75)
    q25 = np.percentile(theta_valid, 25)
    threshold = q75 + 2 * (q75 - q25)
    df["is_outlier"] = [e > threshold if isinstance(e, (int, float)) else True for e in eff1]

    # === Andra körning (exkludera outliers) ===
    df_clean = df[~df["is_outlier"]].reset_index(drop=True)
    inputs_clean = df_clean[input_cols].values
    outputs_clean = df_clean[output_cols].values
    eff2 = run_super_efficiency_dea(inputs_clean, outputs_clean, rts)

    result_effektivitet = []
    result_supereffektivitet = []
    result_potential = []
    result_effkrav_proc = []

    j = 0
    for i, is_outlier in enumerate(df["is_outlier"]):
        if is_outlier:
                result_effektivitet.append(0.0)
                result_supereffektivitet.append(0.0)
                result_potential.append(1.0)
                result_effkrav_proc.append(0.01)  # 1 % per år, inte 100 %
        else:
            theta = eff2[j]
            if isinstance(theta, (int, float)) and not np.isnan(theta):
                effektivitet = min(theta, 1)
                revred = 1 - effektivitet
                revred_compress = np.clip(revred, trunkering_min, trunkering_max)
                revred_compress_yearly = ((1 + revred_compress / 4) ** 0.25) - 1

                result_effektivitet.append(effektivitet)
                result_supereffektivitet.append(theta)
                result_potential.append(revred)
                result_effkrav_proc.append(revred_compress_yearly)
            else:
                result_effektivitet.append(np.nan)
                result_supereffektivitet.append(np.nan)
                result_potential.append(np.nan)
                result_effkrav_proc.append(np.nan)
            j += 1

    df["Effektivitet"] = result_effektivitet
    df["Supereffektivitet"] = result_supereffektivitet
    df["potential"] = result_potential
    df["Effkrav_proc"] = result_effkrav_proc

    # Konvertera OUTLIER till NaN inför loggning (för pyarrow/feather-kompatibilitet)
    df_for_loggning = df.copy()
    for col in ["supereff1", "Effektivitet", "Supereffektivitet", "Effkrav_proc", "potential"]:
        if col in df_for_loggning.columns:
            df_for_loggning[col] = pd.to_numeric(df_for_loggning[col], errors="coerce")

    save_run("DEA", {
        "rts": rts,
        "input_cols": input_cols,
        "output_cols": output_cols,
        "trunkering_min": trunkering_min,
        "trunkering_max": trunkering_max,
        "outlier_filter": outlier_filter
    }, df_for_loggning)

    return df
