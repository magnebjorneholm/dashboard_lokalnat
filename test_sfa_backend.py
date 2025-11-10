"""
test_sfa_backend.py
===================
Backend-test av pySFA med riktig elnätsdata.
Single output: CU (antal kunder)
"""

import sys
import numpy as np
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*80)
print("SFA BACKEND-TEST")
print("Single output: CU (antal kunder)")
print("="*80)

# ============================================================================
# STEG 1: LADDA DATA
# ============================================================================
print("\n[1/3] Laddar data från Data_modeller.xlsx...")

from core.data_loader_dea import load_data
from pysfa import SFA

df = load_data("effektivitet/data/Data_modeller.xlsx")
print(f"✓ Data laddad: {len(df)} företag")

# ============================================================================
# STEG 2: FÖRBERED DATA
# ============================================================================
print("\n[2/3] Förbereder data för SFA...")

input_cols = ['OPEXp', 'CAPEX']
output_col = 'CU'

df_clean = df[['DMU', 'Företag'] + input_cols + [output_col]].copy()
df_clean = df_clean.dropna()

for col in input_cols + [output_col]:
    df_clean = df_clean[df_clean[col] > 0]

print(f"✓ Rensat dataset: {len(df_clean)} företag")

x_data = np.log(df_clean[input_cols].values)
y_data = np.log(df_clean[output_col].values)

# ============================================================================
# STEG 3: KÖR SFA
# ============================================================================
print("\n[3/3] Kör SFA-skattning...")

sfa_model = SFA.SFA(
    y=y_data,
    x=x_data,
    fun=SFA.FUN_PROD,
    intercept=True,
    lamda0=1.0,
    method=SFA.TE_teJ
)

sfa_model.optimize()
print("✓ SFA-skattning klar")

# ============================================================================
# RESULTAT
# ============================================================================
print("\n" + "="*80)
print("RESULTAT")
print("="*80)

beta = sfa_model.get_beta()
lambda_val = sfa_model.get_lambda()
te_scores = sfa_model.get_technical_efficiency()

print("\nParameterskattningar:")
print(f"  Intercept: {beta[0]:.4f}")
print(f"  β_OPEXp: {beta[1]:.4f}")
print(f"  β_CAPEX: {beta[2]:.4f}")
print(f"  λ (lambda): {lambda_val:.4f}")
print(f"  σ²: {sfa_model.get_sigma2():.6f}")
print(f"  σᵤ²: {sfa_model.get_sigmau2():.6f}")
print(f"  σᵥ²: {sfa_model.get_sigmav2():.6f}")

print("\nTeknisk effektivitet (TE):")
print(f"  Medel: {np.mean(te_scores):.4f}")
print(f"  Median: {np.median(te_scores):.4f}")
print(f"  Min: {np.min(te_scores):.4f}")
print(f"  Max: {np.max(te_scores):.4f}")

df_result = df_clean.copy()
df_result['TE_SFA'] = te_scores
df_result = df_result.sort_values('TE_SFA', ascending=False)

print("\n" + "="*80)
print("TOPP 15 MEST EFFEKTIVA FÖRETAG")
print("="*80)
print(df_result[['DMU', 'Företag', 'TE_SFA']].head(15).to_string(index=False))

print("\n" + "="*80)
print("15 MINST EFFEKTIVA FÖRETAG")
print("="*80)
print(df_result[['DMU', 'Företag', 'TE_SFA']].tail(15).to_string(index=False))

print("\n" + "="*80)
print("KLART")
print("="*80)