"""
Pre-compute StoNED efficiency scores for Regumetrica.

Runs multiplicative CNLS cost frontier via NEOS (knitro), then decomposes
residuals with multiple methods (QLE, MOM, KDE). Saves to data/stoned/.

Optimization: models sharing the same RTS reuse a single CNLS solve.
  - VRS CNLS  -> M1 (QLE), M3 (MOM), M4 (KDE)
  - CRS CNLS  -> M2 (QLE)

Usage:
    python scripts/precompute_stoned.py
    python scripts/precompute_stoned.py --models M1 M3
    python scripts/precompute_stoned.py --dry-run
"""

import argparse
import json
import sys
from datetime import datetime
from math import pi
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize as opt
from scipy import stats

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pystoned import CNLS
from pystoned.constant import (
    CET_MULT, FUN_COST, RTS_VRS, RTS_CRS,
    RED_MOM, RED_QLE, RED_KDE,
)

from config.column_names import (
    COL_REID,
    COL_COMPANY_NAME,
    COL_TOTEX,
    COL_DEA_EFFICIENCY,
    COL_DEA_SUPER_EFF,
    COL_DEA_POTENTIAL,
    COL_IS_OUTLIER,
)
from data_loaders.baseline_data import _load_data_modeller

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NEOS_EMAIL = "magne.bjorneholm@gmail.com"
OUTLIER_REIDS = ["REL00024", "REL00257", "REL00965", "REL00193"]
STONED_DIR = PROJECT_ROOT / "data" / "stoned"

COST_COL = COL_TOTEX
OUTPUT_COLS = ["CU", "MW", "NS", "MWhl", "MWhh"]

DECOMP_LABELS = {
    RED_QLE: "QLE",
    RED_MOM: "MoM",
    RED_KDE: "KDE",
}

MODEL_SPECS = {
    "M1": {"rts": RTS_VRS, "decomp": RED_QLE, "label": "StoNED TOTEX (VRS, QLE)"},
    "M2": {"rts": RTS_CRS, "decomp": RED_QLE, "label": "StoNED TOTEX (CRS, QLE)"},
    "M3": {"rts": RTS_VRS, "decomp": RED_MOM, "label": "StoNED TOTEX (VRS, MoM)"},
    "M4": {"rts": RTS_VRS, "decomp": RED_KDE, "label": "StoNED TOTEX (VRS, KDE)"},
}


# ---------------------------------------------------------------------------
# Residual decomposition (replaces buggy pyStoNED methods)
# ---------------------------------------------------------------------------


def _decompose_mom(residual):
    """Method of Moments decomposition (FUN_COST, half-normal).

    Returns (sigma_u, sigma_v, mu) or raises ValueError.
    """
    centered = residual - np.mean(residual)
    M2 = np.mean(centered ** 2)
    M3 = np.mean(centered ** 3)

    # FUN_COST: M3 should be positive (right-skew from inefficiency)
    if M3 < 0:
        M3 = 1e-5

    sigma_u = (-M3 / ((2 / pi) ** 0.5 * (1 - 4 / pi))) ** (1 / 3)
    sigma_v_sq = M2 - ((pi - 2) / pi) * sigma_u ** 2

    if sigma_v_sq <= 0:
        raise ValueError(
            f"MoM: sigma_v^2 = {sigma_v_sq:.6f} <= 0 "
            f"(M2={M2:.6f}, sigma_u={sigma_u:.6f}). "
            "Data doesn't support half-normal decomposition."
        )

    sigma_v = sigma_v_sq ** 0.5
    mu = (sigma_u ** 2 * 2 / pi) ** 0.5
    return float(sigma_u), float(sigma_v), float(mu)


def _decompose_qle(residual):
    """Quasi-likelihood decomposition (FUN_COST, half-normal).

    Fixes pyStoNED bug where math.sqrt fails on numpy 0-d arrays.
    Returns (sigma_u, sigma_v, mu).
    """
    def neg_log_likelihood(lamda_arr, eps):
        lamda = float(lamda_arr[0]) if hasattr(lamda_arr, '__len__') else float(lamda_arr)
        sigma = np.sqrt(
            np.mean(eps ** 2) / (1 - 2 * lamda ** 2 / (pi * (1 + lamda ** 2)))
        )
        mu_val = np.sqrt(2 / pi) * sigma * lamda / np.sqrt(1 + lamda ** 2)
        epsilon = eps - mu_val
        pn = stats.norm.cdf(-epsilon * lamda / sigma)
        pn = np.maximum(pn, 1e-10)
        return -(-len(epsilon) * np.log(sigma) + np.sum(np.log(pn))
                 - 0.5 * np.sum(epsilon ** 2) / sigma ** 2)

    # FUN_COST: negate residuals for estimation
    result = opt.minimize(neg_log_likelihood, x0=[1.0], args=(-residual,), method='BFGS')
    lamda = float(result.x[0])

    sigma = np.sqrt(float(
        np.mean(residual ** 2) / (1 - 2 * lamda ** 2 / (pi * (1 + lamda ** 2)))
    ))
    sigma_v = np.sqrt(sigma ** 2 / (1 + lamda ** 2))
    sigma_u = sigma_v * lamda
    mu = np.sqrt(2 / pi) * sigma * lamda / np.sqrt(1 + lamda ** 2)

    return float(sigma_u), float(sigma_v), float(mu)


def _decompose_kde(residual):
    """Kernel density decomposition (FUN_COST, half-normal).

    pyStoNED's KDE only estimates mu. We derive sigma_u/sigma_v from mu.
    Returns (sigma_u, sigma_v, mu).
    """
    x = np.sort(residual)
    n = len(x)

    # Silverman bandwidth
    s = min(np.std(x, ddof=1), stats.iqr(x, interpolation='midpoint'))
    h = 1.06 * s * n ** (-1 / 5)

    # Gaussian kernel density
    kernel_density = np.zeros(n)
    for i in range(n):
        kernel_density[i] = np.sum(
            stats.norm.pdf((x[i] - x) / h)
        ) / (n * h)

    # Derivative of kernel density
    derivative = np.zeros(n)
    for i in range(n - 1):
        derivative[i + 1] = (kernel_density[i + 1] - kernel_density[i]) / (x[i + 1] - x[i])

    # FUN_COST: mode of inefficiency distribution is at max derivative
    mu = float(np.max(derivative))
    if mu <= 0:
        mu = 1e-6

    # Derive sigma_u from mu: for half-normal, E[u] = mu = sqrt(2/pi) * sigma_u
    sigma_u = mu / np.sqrt(2 / pi)

    # Derive sigma_v from variance: Var(eps) = sigma_u^2 * (1 - 2/pi) + sigma_v^2
    var_eps = np.var(residual)
    sigma_v_sq = var_eps - sigma_u ** 2 * (1 - 2 / pi)

    if sigma_v_sq <= 0:
        raise ValueError(
            f"KDE: sigma_v^2 = {sigma_v_sq:.6f} <= 0 "
            f"(var={var_eps:.6f}, sigma_u={sigma_u:.6f}). "
            "Kernel estimate too large for variance."
        )

    sigma_v = np.sqrt(sigma_v_sq)
    return float(sigma_u), float(sigma_v), float(mu)


def _jlms_technical_inefficiency(residual, sigma_u, sigma_v, mu):
    """JLMS estimator of firm-level technical inefficiency (FUN_COST, CET_MULT).

    Returns exp(E[u|epsilon]) >= 1 for each firm.
    """
    epsilon = residual + mu  # FUN_COST: adjust for mean
    sigma = sigma_u * sigma_v / np.sqrt(sigma_u ** 2 + sigma_v ** 2)
    mu_star = epsilon * sigma_u / (sigma_v * np.sqrt(sigma_u ** 2 + sigma_v ** 2))

    Eu = sigma * (stats.norm.pdf(mu_star) / (1 - stats.norm.cdf(-mu_star) + 1e-6) + mu_star)
    return np.exp(Eu)  # CET_MULT, FUN_COST


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def load_estimation_data():
    """Load baseline data and split into estimation sample + outliers."""
    df_raw = _load_data_modeller()
    outlier_mask = df_raw[COL_REID].isin(OUTLIER_REIDS)
    df_estimation = df_raw[~outlier_mask].reset_index(drop=True)

    print(f"Loaded {len(df_raw)} companies, estimation sample: {len(df_estimation)}")
    for reid in OUTLIER_REIDS:
        row = df_raw.loc[df_raw[COL_REID] == reid]
        name = row.iloc[0][COL_COMPANY_NAME] if len(row) else "NOT FOUND"
        print(f"  Excluded: {reid} ({name})")

    return df_raw, df_estimation


def run_cnls(df, rts):
    """Run CNLS optimisation via NEOS. Returns solved CNLS model or None."""
    rts_label = "VRS" if rts == RTS_VRS else "CRS"
    print(f"\n{'=' * 60}")
    print(f"  CNLS optimisation: TOTEX, {rts_label}, {len(df)} firms")
    print(f"  Sending to NEOS (knitro)...")
    print(f"{'=' * 60}")

    y = df[COST_COL].values.astype(float)
    x = df[OUTPUT_COLS].values.astype(float)

    if np.any(y <= 0):
        print(f"  SKIP: {(y <= 0).sum()} non-positive cost values")
        return None

    try:
        model = CNLS.CNLS(y=y, x=x, z=None, cet=CET_MULT, fun=FUN_COST, rts=rts)
        model.optimize(NEOS_EMAIL)

        if model.optimization_status == 0:
            print("  FAILED: optimisation did not complete")
            return None

        print(f"  CNLS solved (status={model.optimization_status})")
        return model

    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return None


def decompose(cnls_model, decomp_method, model_id):
    """Decompose CNLS residuals using our own implementations.

    Returns result dict or None.
    """
    label = DECOMP_LABELS.get(decomp_method, decomp_method)
    print(f"\n  Decomposing {model_id} with {label}...")

    residual = np.array(cnls_model.get_residual())

    try:
        if decomp_method == RED_MOM:
            sigma_u, sigma_v, mu = _decompose_mom(residual)
        elif decomp_method == RED_QLE:
            sigma_u, sigma_v, mu = _decompose_qle(residual)
        elif decomp_method == RED_KDE:
            sigma_u, sigma_v, mu = _decompose_kde(residual)
        else:
            raise ValueError(f"Unknown decomposition method: {decomp_method}")

        tech_ineff = _jlms_technical_inefficiency(residual, sigma_u, sigma_v, mu)
        efficiency = 1.0 / tech_ineff
        potential = 1.0 - efficiency

        print(f"    sigma_u={sigma_u:.4f}  sigma_v={sigma_v:.4f}  "
              f"lambda={sigma_u / sigma_v:.4f}")
        print(f"    Efficiency: [{efficiency.min():.4f}, "
              f"{np.median(efficiency):.4f}, {efficiency.max():.4f}]")

        return {
            "efficiency": efficiency,
            "potential": potential,
            "sigma_u": sigma_u,
            "sigma_v": sigma_v,
            "mu": mu,
            "n_firms": len(residual),
        }

    except Exception as e:
        print(f"    FAILED: {e}")
        return None


def validate(result):
    """Return list of issues; empty list = pass."""
    issues = []
    eff = result["efficiency"]

    # Check for NaN
    n_nan = np.isnan(eff).sum()
    if n_nan > 0:
        issues.append(f"{n_nan} firms with NaN efficiency")
        return issues

    if result["sigma_u"] <= 0:
        issues.append(f"sigma_u={result['sigma_u']:.4f} <= 0")
    if result["sigma_v"] <= 0:
        issues.append(f"sigma_v={result['sigma_v']:.4f} <= 0")
    if np.isnan(result["sigma_v"]):
        issues.append("sigma_v is NaN")
    if (eff < 0.05).any():
        issues.append(f"{(eff < 0.05).sum()} firms with efficiency < 5%")
    if np.std(eff) < 0.02:
        issues.append(f"Very low spread (std={np.std(eff):.4f})")
    if np.median(eff) > 0.99:
        issues.append(f"Nearly all efficient (median={np.median(eff):.4f})")
    return issues


def build_full_df(df_all, df_estimation, result):
    """Build 148-row DataFrame matching DeaStageOutput.dea_results."""
    df_out = df_all[[COL_REID]].copy()
    df_out[COL_DEA_EFFICIENCY] = np.nan
    df_out[COL_DEA_SUPER_EFF] = np.nan
    df_out[COL_DEA_POTENTIAL] = np.nan
    df_out[COL_IS_OUTLIER] = False

    estimation_reids = df_estimation[COL_REID].values
    for i, reid in enumerate(estimation_reids):
        mask = df_out[COL_REID] == reid
        df_out.loc[mask, COL_DEA_EFFICIENCY] = result["efficiency"][i]
        df_out.loc[mask, COL_DEA_POTENTIAL] = result["potential"][i]

    outlier_mask = df_out[COL_REID].isin(OUTLIER_REIDS)
    df_out.loc[outlier_mask, COL_IS_OUTLIER] = True
    df_out.loc[outlier_mask, COL_DEA_POTENTIAL] = 1.0

    return df_out


def save_results(model_id, spec, result, df_all, df_estimation):
    """Save parquet + return registry entry."""
    STONED_DIR.mkdir(parents=True, exist_ok=True)

    df_result = build_full_df(df_all, df_estimation, result)
    path = STONED_DIR / f"{model_id}.parquet"
    df_result.to_parquet(path, index=False)
    print(f"    Saved {path} ({len(df_result)} rows)")

    eff = result["efficiency"]
    decomp_label = DECOMP_LABELS.get(spec["decomp"], spec["decomp"])
    return {
        "model_id": model_id,
        "label": spec["label"],
        "description": f"Cost: {COST_COL}, Outputs: {', '.join(OUTPUT_COLS)}, Decomp: {decomp_label}",
        "cost_variable": COST_COL,
        "output_variables": OUTPUT_COLS,
        "rts": spec["rts"],
        "cet": "mult",
        "fun": "cost",
        "decomposition": decomp_label,
        "sigma_u": round(result["sigma_u"], 6),
        "sigma_v": round(result["sigma_v"], 6),
        "mu": round(result["mu"], 6),
        "lambda_ratio": round(result["sigma_u"] / result["sigma_v"], 4),
        "n_firms": result["n_firms"],
        "n_excluded_ex_ante": len(OUTLIER_REIDS),
        "eff_min": round(float(eff.min()), 4),
        "eff_median": round(float(np.median(eff)), 4),
        "eff_max": round(float(eff.max()), 4),
        "computed_at": datetime.now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Pre-compute StoNED models")
    parser.add_argument(
        "--models", nargs="*", default=None,
        help="Model IDs to run (default: all). E.g. --models M1 M3",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show specs without running",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Save results even if validation fails",
    )
    args = parser.parse_args()

    specs = MODEL_SPECS
    if args.models:
        specs = {k: v for k, v in specs.items() if k in args.models}
        unknown = set(args.models) - set(MODEL_SPECS.keys())
        if unknown:
            print(f"Unknown model IDs: {unknown}")
            print(f"Available: {list(MODEL_SPECS.keys())}")
            sys.exit(1)

    print("All models: CET_MULT, FUN_COST, TOTEX, 5 outputs, half-normal, NEOS/knitro")
    print(f"\nModels to run: {list(specs.keys())}")
    for mid, s in specs.items():
        print(f"  {mid}: {s['label']}")

    if args.dry_run:
        print("\n--dry-run: exiting without running.")
        return

    df_raw, df_estimation = load_estimation_data()

    # Group models by RTS to share CNLS solves
    rts_groups: dict[str, list[str]] = {}
    for mid, s in specs.items():
        rts_groups.setdefault(s["rts"], []).append(mid)

    registry = {}
    failed = []
    cnls_cache: dict[str, CNLS.CNLS] = {}

    for rts, model_ids in rts_groups.items():
        # Run CNLS once per RTS
        if rts not in cnls_cache:
            cnls_model = run_cnls(df_estimation, rts)
            if cnls_model is None:
                failed.extend(model_ids)
                continue
            cnls_cache[rts] = cnls_model
        else:
            cnls_model = cnls_cache[rts]

        # Decompose with each method
        for model_id in model_ids:
            spec = specs[model_id]
            result = decompose(cnls_model, spec["decomp"], model_id)

            if result is None:
                failed.append(model_id)
                continue

            issues = validate(result)
            if issues:
                print(f"    VALIDATION WARNING for {model_id}:")
                for issue in issues:
                    print(f"      - {issue}")
                if not args.force:
                    failed.append(model_id)
                    continue
                print(f"    Saving anyway (--force)")
            else:
                print(f"    VALIDATION PASSED")
            entry = save_results(model_id, spec, result, df_raw, df_estimation)
            registry[model_id] = entry

    # Save registry (clean slate)
    STONED_DIR.mkdir(parents=True, exist_ok=True)
    registry_path = STONED_DIR / "models.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"DONE: {len(registry)} saved, {len(failed)} failed")
    print(f"{'=' * 60}")
    for mid, r in registry.items():
        print(f"  {mid}: {r['label']}")
        print(f"       eff=[{r['eff_min']:.3f}, {r['eff_median']:.3f}, {r['eff_max']:.3f}]  "
              f"sigma_u={r['sigma_u']:.4f}  sigma_v={r['sigma_v']:.4f}  "
              f"lambda={r['lambda_ratio']:.4f}")
    if failed:
        print(f"\n  Failed: {failed}")
    print(f"\nRegistry: {registry_path}")


if __name__ == "__main__":
    main()
