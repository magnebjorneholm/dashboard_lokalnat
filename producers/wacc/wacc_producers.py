"""
wacc_producers.py - Producer wrappers för WACC-beräkning
=========================================================

Wrappers som anropar wacc_calculations.py och returnerar WACC-värden
enligt producer interface-kontraktet.
"""

from typing import Dict, Any, Optional

# Hantera både modulimport och direktkörning
try:
    from .wacc_calculations import EiWaccInputs, ei_wacc_real_pre_tax
except ImportError:
    from wacc_calculations import EiWaccInputs, ei_wacc_real_pre_tax


def produce_wacc_from_capm(
    parameters: Dict[str, Any],
    baseline_data: Optional[Dict[str, Any]] = None
) -> float:
    """
    Producer för WACC-beräkning från CAPM-komponenter.
    
    Beräknar WACC (real, före skatt) från användarens parametrar enligt 
    Ei:s CAPM-metodik.
    
    Args:
        parameters: Dict med WACC-komponenter:
            - rf_nominal: Riskfri ränta (nominell)
            - mrp_nominal: Marknadsriskpremie (nominell)
            - credit_spread: Kreditriskpremie
            - debt_share: Skuldsättningsgrad
            - tax_rate: Bolagsskatt
            - inflation: KPIF-inflation
            - beta_asset: Tillgångsbeta (obelanad) - valfritt
            - beta_equity: Aktiebeta (belanad) - valfritt
        baseline_data: Oanvänd (för interface-kompatibilitet)
        
    Returns:
        WACC (real, före skatt) som decimal (0.0453 = 4.53%)
        
    Raises:
        KeyError: Om nödvändiga parametrar saknas
        ValueError: Om parametervärden är ogiltiga
        
    Example:
        >>> params = {
        ...     'rf_nominal': 0.0287,
        ...     'mrp_nominal': 0.0668,
        ...     'credit_spread': 0.0114,
        ...     'debt_share': 0.36,
        ...     'tax_rate': 0.206,
        ...     'inflation': 0.0202,
        ...     'beta_asset': 0.37
        ... }
        >>> wacc = produce_wacc_from_capm(params)
        >>> print(f"{wacc:.4f}")  # 0.0453
    """
    # Validera att nödvändiga parametrar finns
    required = ['rf_nominal', 'mrp_nominal', 'credit_spread', 
                'debt_share', 'tax_rate', 'inflation']
    missing = [p for p in required if p not in parameters]
    if missing:
        raise KeyError(f"Saknade WACC-parametrar: {missing}")
    
    # Beta måste anges som antingen beta_asset eller beta_equity
    has_beta_a = 'beta_asset' in parameters and parameters['beta_asset'] is not None
    has_beta_e = 'beta_equity' in parameters and parameters['beta_equity'] is not None
    
    if not (has_beta_a or has_beta_e):
        raise KeyError("Måste ange antingen 'beta_asset' eller 'beta_equity'")
    
    # Bygg inputs-objekt
    inputs = EiWaccInputs(
        rf_nominal=float(parameters['rf_nominal']),
        mrp_nominal=float(parameters['mrp_nominal']),
        credit_spread=float(parameters['credit_spread']),
        debt_share=float(parameters['debt_share']),
        tax_rate=float(parameters['tax_rate']),
        inflation=float(parameters['inflation']),
        beta_asset=float(parameters['beta_asset']) if has_beta_a else None,
        beta_equity=float(parameters['beta_equity']) if has_beta_e else None
    )
    
    # Beräkna WACC
    _, _, _, wacc_real_pre = ei_wacc_real_pre_tax(inputs)
    
    return wacc_real_pre
