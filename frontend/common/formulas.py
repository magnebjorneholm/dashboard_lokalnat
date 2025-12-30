"""
frontend/common/formulas.py

LaTeX formulas for Regumetrica UI.
Organized by module and calculation chain.

Usage:
    from frontend.common.formulas import FORMULA_WACC_REAL
    st.latex(FORMULA_WACC_REAL)

Verified against:
- wacc_calculations.py
- dea_calculations.py
- effektiviseringskrav.py
- kent_calculations.py
- incentive_calculations.py
- Bilaga 4 (Ei)
- Regumetrica UM 2.pdf
"""

# =============================================================================
# M3: WACC - Cost of Capital (wacc_calculations.py)
# =============================================================================
# Calculation chain: Hamada → CAPM → Cost of debt → WACC nom → Fisher → WACC real
# Used in: m3_cost_of_capital.py, pre_dea.py (WACC scaling)

# 3.2.1 Hamada formula: Converts asset beta to equity beta
# Accounts for leverage and tax shield
FORMULA_HAMADA = r"\beta_E = \beta_A \times \left(1 + (1 - \tau) \times \frac{S}{1-S}\right)"

# Hamada with variable explanation
FORMULA_HAMADA_EXPLAINED = r"""
\beta_E = \beta_A \times \left(1 + (1 - \tau) \times \frac{S}{1-S}\right)
"""

# 3.2.2 CAPM: Cost of equity (nominal, after tax)
# Classic Capital Asset Pricing Model
FORMULA_CAPM = r"R_e = R_f + \beta_E \times MRP"

# CAPM with full variable names
FORMULA_CAPM_FULL = r"R_e^{nom} = R_f + \beta_E \times MRP"

# 3.2.3 Cost of debt (nominal, pre-tax)
FORMULA_COST_OF_DEBT = r"R_d = R_f + \text{credit spread}"

# 3.2.4 WACC nominal after tax
# Weighted average of cost of equity and debt
FORMULA_WACC_NOMINAL_AFTER_TAX = r"WACC_{nom}^{post} = (1-S) \times R_e + S \times R_d \times (1-\tau)"

# 3.2.4 WACC nominal pre-tax
# Grossed up to compensate for tax deduction
FORMULA_WACC_NOMINAL_BEFORE_TAX = r"WACC_{nom}^{pre} = \frac{WACC_{nom}^{post}}{1 - \tau}"

# Complete WACC formula (combines above)
FORMULA_WACC_NOMINAL_COMPLETE = r"WACC_{nom} = \frac{(1-S) \times R_e + S \times R_d \times (1-\tau)}{1 - \tau}"

# 3.2.5 Fisher equation: Nominal → Real
# Conversion from nominal to real rate
FORMULA_FISHER = r"WACC_{real} = \frac{1 + WACC_{nom}}{1 + \pi} - 1"

# Alternative notation for Fisher
FORMULA_FISHER_ALT = r"r_{real} = \frac{1 + r_{nom}}{1 + \pi} - 1"

# Complete WACC calculation in one step (for summary)
FORMULA_WACC_COMPLETE = r"""
WACC_{real} = \frac{1 + \frac{(1-S) \times R_e + S \times R_d \times (1-\tau)}{1-\tau}}{1 + \pi} - 1
"""

# Variable descriptions for WACC
WACC_VARIABLE_DESCRIPTIONS = {
    "beta_A": "Asset beta (unlevered)",
    "beta_E": "Equity beta (levered)",
    "S": "Debt ratio D/(D+E)",
    "tau": "Corporate tax rate",
    "R_f": "Risk-free rate",
    "R_e": "Cost of equity",
    "R_d": "Cost of debt",
    "MRP": "Market risk premium",
    "pi": "Inflation (CPIF)",
}


# =============================================================================
# M3: Derived parameters - Alternative WACC input
# =============================================================================
# For users who want to specify Re, Rd, S, τ, π directly

FORMULA_WACC_FROM_DERIVED = r"WACC_{real} = \frac{1 + \frac{(1-S) \times R_e + S \times R_d \times (1-\tau)}{1-\tau}}{1 + \pi} - 1"


# =============================================================================
# M5: Efficiency requirement (effektiviseringskrav.py)
# =============================================================================
# Calculation chain: DEA potential → Truncation → Total eff → Annual requirement
# Used in: m5_efficiency.py, post_dea.py

# Total efficiency gain over regulatory period
# Combines truncated potential with customer sharing and realization time
FORMULA_TOTAL_EFFICIENCY = r"\text{Total eff.} = \text{potential}_{trunc} \times \text{customer share} \times \frac{\text{reg. period}}{\text{realization time}}"

# Annual efficiency requirement (compound)
# Distributes total efficiency evenly over regulatory period
FORMULA_ANNUAL_EFFICIENCY_REQ = r"\text{Eff. req.}_{annual} = \left(1 + \text{Total eff.}\right)^{\frac{1}{\text{reg. period}}} - 1"

# Combined formula for annual requirement
FORMULA_EFFICIENCY_COMPLETE = r"""
\text{Eff. req.} = \left(1 + \text{potential}_{trunc} \times \text{customer share} \times \frac{\text{reg. period}}{\text{realization time}}\right)^{\frac{1}{\text{reg. period}}} - 1
"""

# With baseline values (for illustration)
FORMULA_EFFICIENCY_WITH_BASELINE = r"""
\text{Eff. req.} = \left(1 + \min(\max(\text{pot}, 0.162), 0.30) \times 0.5 \times \frac{4}{8}\right)^{\frac{1}{4}} - 1
"""

# Max annual requirement (at 30% potential)
# Note: Ei uses 1.82% in documentation (rounded down from 1.827%)
FORMULA_MAX_EFFICIENCY_REQ = r"\text{Max eff. req.} = \left(1 + 0.30 \times 0.50 \times \frac{4}{8}\right)^{0.25} - 1 \approx 1.83\%"


# =============================================================================
# Benchmarking: DEA (dea_calculations.py)
# =============================================================================
# Calculation chain: LP optimization → Super-efficiency → Outlier identification
# Used in: benchmarking.py, dea.py

# DEA input-oriented LP formulation (CRS, Super-efficiency)
# Minimizes input scaling θ to reach frontier
# Note: j ≠ i means DMU i is excluded from reference set (super-efficiency)
FORMULA_DEA_LP = r"""
\begin{aligned}
\min_{\theta, \lambda} \quad & \theta \\
\text{s.t.} \quad & \sum_{j \neq i} \lambda_j x_j \leq \theta x_i \\
& \sum_{j \neq i} \lambda_j y_j \geq y_i \\
& \lambda_j \geq 0
\end{aligned}
"""

# Standard DEA (includes all DMUs in reference set)
FORMULA_DEA_LP_STANDARD = r"""
\begin{aligned}
\min_{\theta, \lambda} \quad & \theta \\
\text{s.t.} \quad & \sum_{j} \lambda_j x_j \leq \theta x_i \\
& \sum_{j} \lambda_j y_j \geq y_i \\
& \lambda_j \geq 0
\end{aligned}
"""

# Compact DEA formulation (for inline display)
FORMULA_DEA_COMPACT = r"\theta^* = \min\{\theta : \sum_j \lambda_j x_j \leq \theta x_0, \sum_j \lambda_j y_j \geq y_0, \lambda \geq 0\}"

# VRS constraint (for variable returns to scale)
FORMULA_DEA_VRS_CONSTRAINT = r"\sum_{j} \lambda_j = 1"

# Efficiency potential
FORMULA_EFFICIENCY_POTENTIAL = r"\text{potential} = 1 - \theta"

# Outlier threshold (IQR method)
FORMULA_OUTLIER_THRESHOLD = r"\text{threshold} = Q_{75} + k \times (Q_{75} - Q_{25})"

# Outlier threshold with default k=2
FORMULA_OUTLIER_THRESHOLD_DEFAULT = r"\text{threshold} = Q_3 + 2 \times IQR"

# =============================================================================
# Incentives: Quality (incentive_calculations.py)
# =============================================================================
# Calculation chain: AIT/AIF norm → Outcome → Difference → Cost → Adjustment
# Used in: m3_cost_of_capital.py (quality section), post_dea.py
# Source: Bilaga 4 (Ei)

# AIT definition (Average Interruption Time)
# Power-weighted average interruption time
FORMULA_AIT_DEFINITION = r"AIT_j^k = \frac{ILE_j^k}{\sum_i P_i} = \frac{\sum_i (P_i \times d_{i,j})}{\sum_i P_i}"

# AIF definition (Average Interruption Frequency)
# Power-weighted average interruption frequency
FORMULA_AIF_DEFINITION = r"AIF_j^k = \frac{ILEffekt_j^k}{\sum_i P_i} = \frac{\sum_i P_i \times n_{i,j}}{\sum_i P_i}"

# ILE (Non-delivered energy) per interruption
# d = interruption duration in hours, P = annual average power in kW
FORMULA_ILE = r"ILE = d \times P"

# ILEffekt (Non-delivered power)
# Sum of disconnected power during interruptions
FORMULA_ILEFFEKT = r"ILEffekt = \sum_{\text{interruptions}} P"

# Annual average power
FORMULA_ANNUAL_AVERAGE_POWER = r"P = \frac{E}{t_y}"

# Quality cost for AIT (per customer type and outage type)
# Uses annual average power for customer type
FORMULA_QUALITY_COST_AIT = r"K_{AIT,j}^k = (AIT_{norm,j}^k - AIT_{actual,j}^k) \times \bar{P}^k \times v_{ILE,j}^k"

# Quality cost for AIF (per customer type and outage type)
FORMULA_QUALITY_COST_AIF = r"K_{AIF,j}^k = (AIF_{norm,j}^k - AIF_{actual,j}^k) \times \bar{P}^k \times v_{ILEffekt,j}^k"

# Total quality adjustment per year
FORMULA_QUALITY_TOTAL = r"\text{Quality}_{year} = \sum_j \sum_k (K_{AIT,j}^k + K_{AIF,j}^k) \times KPI"

# Quality adjustment with CEMI4 correction
FORMULA_QUALITY_WITH_CEMI = r"\text{Quality}_{adj} = \text{Quality} \times (1 - \min(adj_{CEMI4}, \Delta CEMI4))"


# =============================================================================
# Incentives: Network loss (incentive_calculations.py)
# =============================================================================
# Calculation chain: Loss norm → Observed → Difference → Cost
# Used in: m3_cost_of_capital.py (network loss section), post_dea.py

# Network loss incentive per year
FORMULA_NETLOSS_INCENTIVE = r"\text{Netloss}_{year} = (\text{loss}_{norm} - \text{loss}_{actual}) \times k_{NF} \times s_{NF}"

# With variable explanation
FORMULA_NETLOSS_INCENTIVE_EXPLAINED = r"""
\text{Inc}_{NF} = (\text{Loss}_{norm} - \text{Loss}_{actual}) \times k_{NF} \times s
"""

# Network loss share (definition)
FORMULA_NETLOSS_SHARE = r"\text{Loss \%} = \frac{E_{in} - E_{out}}{E_{in}}"


# =============================================================================
# Incentives: Utilization (incentive_calculations.py)
# =============================================================================
# Calculation chain: Utilization rate norm → Observed → Difference → Cost
# Used in: m3_cost_of_capital.py (utilization section), post_dea.py

# Utilization incentive per year
FORMULA_LOAD_INCENTIVE = r"\text{Utilization}_{year} = (UR_{actual} - UR_{norm}) \times k_{upstream}"

# Utilization rate (definition)
FORMULA_UTILIZATION_RATE = r"UR = \frac{\bar{P}_{day}}{P_{max,4}}"


# =============================================================================
# Incentives: Caps (incentive_calculations.py)
# =============================================================================
# Calculation chain: Calculate sub-incentives → Apply individual cap → Sum → Total cap
# Used in: post_dea.py

# Cap on individual incentive
FORMULA_INCENTIVE_CAP_INDIVIDUAL = r"|Inc_i| \leq \frac{1}{3} \times R_{year}"

# Cap on total incentive per year
FORMULA_INCENTIVE_CAP_TOTAL = r"\left|\sum_i Inc_i\right| \leq \frac{1}{3} \times R_{year}"

# Total incentive adjustment with cap
FORMULA_INCENTIVE_TOTAL_WITH_CAP = r"""
\text{Inc}_{total} = \text{clip}\left(\sum_i Inc_i, -\frac{R}{3}, \frac{R}{3}\right)
"""


# =============================================================================
# Revenue frame: Assembly (intaktsram_assembly.py)
# =============================================================================
# Calculation chain: Components → Summation → Total revenue frame
# Used in: post_dea.py, 2_results.py

# Total revenue frame (main formula)
FORMULA_INTAKTSRAM_TOTAL = r"""
RF = \text{Adjustable} + \text{Non-adjustable} + \text{Capital cost} + \text{Incentives}
"""

# Revenue frame with all components
FORMULA_INTAKTSRAM_COMPLETE = r"""
RF = C_{adj} + C_{non-adj} + (D + R) + (Inc_{qual} + Inc_{NF} + Inc_{util})
"""

# Adjustable costs after efficiency requirement
FORMULA_PAVERKBARA_AFTER_EFFKRAV = r"""
C_{adj,new} = C_{adj,baseline} \times \prod_{t=1}^{4} (1 - \text{eff.req}_t)
"""


# =============================================================================
# Norm levels: Quality indicators (incentive_parameters.py)
# =============================================================================
# From Bilaga 4 - curve fitting for norm levels

# Norm level as function of customer density (T)
# T = number of customers per km of line
FORMULA_NORM_AIT = r"AIT_j^k(T) = \alpha_{j,AIT}^k + \frac{\beta_{j,AIT}^k}{\gamma_{j,AIT}^k + T}"

FORMULA_NORM_AIF = r"AIF_j^k(T) = \alpha_{j,AIF}^k + \frac{\beta_{j,AIF}^k}{\gamma_{j,AIF}^k + T}"

# General form (for documentation)
FORMULA_NORM_GENERAL = r"Y(T) = \alpha + \frac{\beta}{\gamma + T}"

# Parameters vary by customer type (k) and outage type (j), see Bilaga 4, Table 2
# k ∈ {Household, Industry, Agriculture, Trade/services, Public, Border point}
# j ∈ {unannounced, announced}


# =============================================================================
# Variable glossary (for documentation)
# =============================================================================

VARIABLE_GLOSSARY = {
    # WACC
    "beta_A": ("β_A", "Asset beta (unlevered)"),
    "beta_E": ("β_E", "Equity beta (levered)"),
    "S": ("S", "Debt ratio D/(D+E)"),
    "tau": ("τ", "Corporate tax rate"),
    "R_f": ("R_f", "Risk-free rate (10-year government bond)"),
    "R_e": ("R_e", "Cost of equity"),
    "R_d": ("R_d", "Cost of debt"),
    "MRP": ("MRP", "Market risk premium"),
    "pi": ("π", "Inflation (CPIF forecast)"),
    
    # DEA
    "theta": ("θ", "Efficiency score (1 = efficient)"),
    "lambda": ("λ", "Weights for reference firms"),
    "x": ("x", "Input vector (costs)"),
    "y": ("y", "Output vector (volumes)"),
    
    # Efficiency requirement
    "pot": ("pot", "Efficiency potential (1 - θ)"),
    "k": ("k", "Customer sharing factor"),
    "T_p": ("T_p", "Regulatory period (years)"),
    "T_r": ("T_r", "Realization time (years)"),
    
    # Capital base
    "NUAV": ("NUAV", "Current replacement value"),
    "T_ek": ("T_ek", "Economic lifetime (half-years)"),
    "D": ("D", "Depreciation (capital consumption)"),
    "R": ("R", "Return (capital tied up)"),
    
    # Incentives
    "AIT": ("AIT", "Average Interruption Time"),
    "AIF": ("AIF", "Average Interruption Frequency"),
    "ILE": ("ILE", "Non-delivered energy (kWh)"),
    "ILEffekt": ("ILEffekt", "Non-delivered power (kW)"),
    "P": ("P", "Annual average power (kW)"),
    "d": ("d", "Interruption duration (hours)"),
    "k_NF": ("k_NF", "Network loss cost (SEK/MWh)"),
    "s_NF": ("s", "Network loss sharing factor"),
    "UG": ("UR", "Utilization rate"),
    "CEMI4": ("CEMI4", "Share of customers with ≥4 interruptions"),
}


# =============================================================================
# Helper functions for UI
# =============================================================================

def get_formula_with_caption(formula_key: str) -> tuple:
    """
    Returns formula and description for a given key.
    
    Usage:
        formula, caption = get_formula_with_caption("WACC_REAL")
        st.latex(formula)
        st.caption(caption)
    """
    formulas_with_captions = {
        "HAMADA": (FORMULA_HAMADA, "Hamada formula: converts asset beta to equity beta"),
        "CAPM": (FORMULA_CAPM, "CAPM: cost of equity"),
        "FISHER": (FORMULA_FISHER, "Fisher equation: nominal to real rate"),
        "WACC_NOMINAL": (FORMULA_WACC_NOMINAL_COMPLETE, "WACC nominal pre-tax"),
        "WACC_REAL": (FORMULA_FISHER, "WACC real pre-tax"),
        "EFFICIENCY_REQ": (FORMULA_ANNUAL_EFFICIENCY_REQ, "Annual efficiency requirement"),
        "DEA": (FORMULA_DEA_COMPACT, "DEA input-oriented optimization"),
        "DEA_SUPER": (FORMULA_DEA_LP, "DEA super-efficiency (excludes DMU i)"),
        "QUALITY_AIT": (FORMULA_QUALITY_COST_AIT, "Quality cost based on AIT"),
        "QUALITY_AIF": (FORMULA_QUALITY_COST_AIF, "Quality cost based on AIF"),
        "NETLOSS": (FORMULA_NETLOSS_INCENTIVE, "Network loss incentive"),
        "LOAD": (FORMULA_LOAD_INCENTIVE, "Utilization rate incentive"),
        "INTAKTSRAM": (FORMULA_INTAKTSRAM_TOTAL, "Total revenue frame"),
        "NORM_AIT": (FORMULA_NORM_AIT, "Norm level AIT as function of customer density"),
        "NORM_AIF": (FORMULA_NORM_AIF, "Norm level AIF as function of customer density"),
    }
    return formulas_with_captions.get(formula_key, (None, None))


def get_all_formula_keys() -> list:
    """Returns all available formula keys."""
    return [
        "HAMADA", "CAPM", "FISHER", "WACC_NOMINAL", "WACC_REAL",
        "EFFICIENCY_REQ", "DEA", "DEA_SUPER",
        "QUALITY_AIT", "QUALITY_AIF", "NETLOSS", "LOAD",
        "INTAKTSRAM", "NORM_AIT", "NORM_AIF"
    ]