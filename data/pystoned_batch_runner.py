# pystoned_batch_runner.py

"""
Modellspecifikation:
- Modell: Stochastic nonparametric envelopment of data (StoNED)
- Output: CU (antal kunder)
- Input: TOTEX (OPEXp + CAPEX)
- RTS: CRS (constant returns to scale)
- Funktionsform: Produktion
- CET: Additiv teknologi
- Ineffektivitetsskattning: QLE

Motivation:
Proof-of-concept för att kunna köra pystoned-modellen som batch-process
utan att Streamlit hänger sig vid tunga optimeringar.
"""

import pandas as pd
import numpy as np
from pystoned import CNLS, StoNED

# === Läs in data ===
df = pd.read_excel("data/Data_modeller.xlsx", sheet_name="Körning", engine="openpyxl")

# Skapa TOTEX om det inte finns
if "TOTEX" not in df.columns:
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]

df = df[["REId", "CU", "TOTEX"]].dropna()

# === Förbered input/output ===
y = df[["CU"]].to_numpy()
x = df[["TOTEX"]].to_numpy()

# === Kör CNLS och StoNED ===
cnls = CNLS.CNLS(y=y, x=x, rts="crs", fun="prod", cet="addi")
cnls.optimize(solver=None)  # default solver

model = StoNED.StoNED(cnls)

u_hat = model.get_technical_inefficiency(method="QLE")
eff = 1 / (1 + u_hat)

# === Spara resultat ===
df["Effektivitet"] = eff
df["u_hat"] = u_hat
df.to_excel("pystoned_resultat.xlsx", index=False)
print("✅ Klart! Resultat sparat till 'pystoned_resultat.xlsx'")
