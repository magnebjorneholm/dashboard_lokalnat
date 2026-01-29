"""
calculations/wacc_calculator.py

WACC-beräkning enligt Ei-metodik (CAPM).
Extraherad från tidigare calculations.py för användning i Regumetrica.

Baserat på Energimarknadsinspektionens metodik för WACC-beräkning
enligt regulatory framework 2024-2027.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


# Ei:s kalkylränta för 2024-2027 (real, före skatt)
BASELINE_WACC: float = 0.0453


@dataclass
class CAPMInputs:
    """
    Input-parametrar för WACC-beräkning enligt Ei-metodik.
    
    Alla räntesatser och premier anges som decimaler (0.0453 = 4.53%).
    Parameter-IDs enligt User Manual kapitel 3.1.
    """
    # 3.1.1 Debt ratio (skuldsättningsgrad)
    debt_ratio: float = 0.36
    
    # 3.1.2 Asset beta (tillgångsbeta, obelanad)
    asset_beta: float = 0.37
    
    # 3.1.3 Risk-free rate (riskfri ränta, nominell)
    risk_free_rate: float = 0.0287
    
    # 3.1.4 Market risk premium (marknadsriskpremie)
    market_risk_premium: float = 0.0668
    
    # 3.1.5 Credit risk premium (kreditriskpremie)
    credit_risk_premium: float = 0.0114
    
    # 3.1.6 Tax rate (bolagsskatt)
    tax_rate: float = 0.206
    
    # 3.1.7 Inflation (CPIF-prognos)
    inflation: float = 0.0202


@dataclass
class WACCResult:
    """
    Resultat från WACC-beräkning.
    
    Innehåller mellansteg och slutresultat för transparens.
    Parameter-IDs enligt User Manual kapitel 3.2.
    """
    # 3.2.1 Equity beta (aktiebeta, belanad) - beräknad via Hamada
    equity_beta: float
    
    # 3.2.2 Nominal cost of equity after tax
    cost_of_equity_nominal: float
    
    # 3.2.3 Nominal cost of debt after tax
    cost_of_debt_nominal: float
    
    # 3.2.4 Nominal WACC before tax
    wacc_nominal_pre_tax: float
    
    # 3.2.5 Real WACC before tax (detta är värdet som används i pipeline)
    wacc_real_pre_tax: float


def _hamada(beta_asset: float, debt_ratio: float, tax_rate: float) -> float:
    """
    Hamada-formel för att konvertera tillgångsbeta till aktiebeta.
    
    Formel: β_E = β_A * (1 + (1-T) * D/E)
    där D/E = S/(1-S)
    
    Args:
        beta_asset: Tillgångsbeta (obelanad beta)
        debt_ratio: Skuldsättningsgrad D/(D+E)
        tax_rate: Bolagsskatt
        
    Returns:
        Aktiebeta (belanad beta)
    """
    d_over_e = debt_ratio / max(1e-12, (1 - debt_ratio))
    return beta_asset * (1 + (1 - tax_rate) * d_over_e)


def calculate_wacc(inputs: CAPMInputs) -> WACCResult:
    """
    Beräknar WACC enligt Ei-metodik.
    
    Beräkningskedja:
    1. Hamada: Konvertera asset beta till equity beta
    2. CAPM: Beräkna kostnad för eget kapital (nominell, efter skatt)
    3. Beräkna kostnad för skuld (nominell, före skatt)
    4. WACC: Viktat genomsnitt (nominell, före skatt)
    5. Fisher: Omräkning till real nivå
    
    Args:
        inputs: CAPMInputs med alla parametrar
        
    Returns:
        WACCResult med alla mellansteg och slutresultat
        
    Raises:
        ValueError: Om parametrar är utanför giltiga intervall
    """
    # Validering
    if not (0 <= inputs.debt_ratio < 1):
        raise ValueError(f"debt_ratio måste vara 0 ≤ S < 1, fick {inputs.debt_ratio}")
    
    if not (0 <= inputs.tax_rate < 1):
        raise ValueError(f"tax_rate måste vara 0 ≤ T < 1, fick {inputs.tax_rate}")
    
    # 1. Hamada: Asset beta → Equity beta (3.2.1)
    equity_beta = _hamada(inputs.asset_beta, inputs.debt_ratio, inputs.tax_rate)
    
    # 2. CAPM: Kostnad för eget kapital (nominell, efter skatt) (3.2.2)
    cost_of_equity_nominal = inputs.risk_free_rate + equity_beta * inputs.market_risk_premium
    
    # 3. Kostnad för skuld (nominell, före skatt → efter skatt för WACC) (3.2.3)
    cost_of_debt_nominal = inputs.risk_free_rate + inputs.credit_risk_premium
    
    # 4. WACC nominell före skatt (3.2.4)
    # Först beräkna efter skatt, sedan konvertera till före skatt
    wacc_nominal_after_tax = (
        (1 - inputs.debt_ratio) * cost_of_equity_nominal + 
        inputs.debt_ratio * cost_of_debt_nominal * (1 - inputs.tax_rate)
    )
    wacc_nominal_pre_tax = wacc_nominal_after_tax / (1 - inputs.tax_rate)
    
    # 5. Fisher: Nominell → Real (3.2.5)
    wacc_real_pre_tax = (1 + wacc_nominal_pre_tax) / (1 + inputs.inflation) - 1
    
    return WACCResult(
        equity_beta=equity_beta,
        cost_of_equity_nominal=cost_of_equity_nominal,
        cost_of_debt_nominal=cost_of_debt_nominal,
        wacc_nominal_pre_tax=wacc_nominal_pre_tax,
        wacc_real_pre_tax=wacc_real_pre_tax,
    )


def calculate_wacc_simple(
    debt_ratio: float = 0.36,
    asset_beta: float = 0.37,
    risk_free_rate: float = 0.0287,
    market_risk_premium: float = 0.0668,
    credit_risk_premium: float = 0.0114,
    tax_rate: float = 0.206,
    inflation: float = 0.0202,
) -> float:
    """
    Förenklad WACC-beräkning som returnerar endast real WACC före skatt.
    
    Convenience-funktion för snabb beräkning utan att skapa dataclasses.
    
    Returns:
        Real WACC före skatt (t.ex. 0.0453 för 4.53%)
    """
    inputs = CAPMInputs(
        debt_ratio=debt_ratio,
        asset_beta=asset_beta,
        risk_free_rate=risk_free_rate,
        market_risk_premium=market_risk_premium,
        credit_risk_premium=credit_risk_premium,
        tax_rate=tax_rate,
        inflation=inflation,
    )
    result = calculate_wacc(inputs)
    return result.wacc_real_pre_tax


# Verifiera att baseline-parametrar ger baseline WACC
if __name__ == "__main__":
    result = calculate_wacc(CAPMInputs())
    print(f"Baseline WACC-beräkning:")
    print(f"  Equity beta (3.2.1):        {result.equity_beta:.4f}")
    print(f"  Cost of equity (3.2.2):     {result.cost_of_equity_nominal:.4f} ({result.cost_of_equity_nominal*100:.2f}%)")
    print(f"  Cost of debt (3.2.3):       {result.cost_of_debt_nominal:.4f} ({result.cost_of_debt_nominal*100:.2f}%)")
    print(f"  WACC nominal pre-tax (3.2.4): {result.wacc_nominal_pre_tax:.4f} ({result.wacc_nominal_pre_tax*100:.2f}%)")
    print(f"  WACC real pre-tax (3.2.5):  {result.wacc_real_pre_tax:.4f} ({result.wacc_real_pre_tax*100:.2f}%)")
    print(f"  Förväntat (BASELINE_WACC):  {BASELINE_WACC:.4f} ({BASELINE_WACC*100:.2f}%)")
    print(f"  Differens:                  {abs(result.wacc_real_pre_tax - BASELINE_WACC):.6f}")