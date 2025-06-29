# app/run_logger.py

import os
import yaml # type: ignore
import pandas as pd
from datetime import datetime

RUNS_DIR = "runs"

def save_run(modellnamn: str, parametrar: dict, df_resultat: pd.DataFrame):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_id = f"{modellnamn.lower()}_{timestamp}"
    path = os.path.join(RUNS_DIR, run_id)
    os.makedirs(path, exist_ok=True)

    # YAML
    meta = {
        "modell": modellnamn,
        "timestamp": timestamp,
        "parametrar": parametrar,
    }
    with open(os.path.join(path, "params.yaml"), "w") as f:
        yaml.dump(meta, f)

    # Resultat
    df_resultat.to_feather(os.path.join(path, "result.feather"))

import matplotlib.pyplot as plt
import pandas as pd
import os
import yaml # type: ignore

def list_runs():
    return sorted(os.listdir("runs"))

def load_run(run_id):
    path = os.path.join("runs", run_id)
    with open(os.path.join(path, "params.yaml")) as f:
        params = yaml.safe_load(f)
    df = pd.read_feather(os.path.join(path, "result.feather"))
    return params, df

def compare_runs(run_id_a, run_id_b):
    params_a, df_a = load_run(run_id_a)
    params_b, df_b = load_run(run_id_b)

    # Säkerställ att företagsnamn matchar
    merged = df_a[["Företag", "Effektivitet"]].rename(columns={"Effektivitet": "Eff_A"}).merge(
        df_b[["Företag", "Effektivitet"]].rename(columns={"Effektivitet": "Eff_B"}),
        on="Företag",
        how="inner"
    )

    if merged.empty:
        raise ValueError("Inga gemensamma företag hittades mellan körningarna.")

    # Korrelation
    corr = merged["Eff_A"].corr(merged["Eff_B"])
    print(f"Korrelation (Pearson) mellan effektivitet A och B: {corr:.4f}")

    # Skillnader
    merged["Diff"] = merged["Eff_B"] - merged["Eff_A"]
    print("\nTopp 5 största skillnader:")
    print(merged.sort_values("Diff", key=abs, ascending=False).head())

    # Scatterplot
    plt.figure(figsize=(6, 6))
    plt.scatter(merged["Eff_A"], merged["Eff_B"], alpha=0.7)
    plt.xlabel("Effektivitet - Körning A")
    plt.ylabel("Effektivitet - Körning B")
    plt.title("Effektivitet A vs B")
    plt.plot([0, 1], [0, 1], color="gray", linestyle="--")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    return merged
