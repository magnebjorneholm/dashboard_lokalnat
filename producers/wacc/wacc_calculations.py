"""
wacc_calculations.py - WACC-beräkningar enligt Ei-metodik
==========================================================

Kopierad från calculations.py - innehåller endast WACC-relaterad kod.
Inga UI-beroenden - ren beräkningslogik.

Baserat på Energimarknadsinspektionens metodik för WACC-beräkning
enligt regulatory framework 2024-2027.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


# ============================================================================
# KONSTANTER
# ============================================================================

# Ei:s kalkylränta för 2024-2027 (real, före skatt)
R_OLD: float = 0.0453


# ============================================================================
# DATASTRUKTURER
# ============================================================================

@dataclass
class EiWaccInputs:
    """
    Input-parametrar för WACC-beräkning enligt Ei-metodik.
    
    Alla räntesatser och premie anges som decimaler (0.0453 = 4.53%).
    """
    # Grundparametrar (nominella)
    rf_nominal: float = 0.0287      # Riskfri ränta (nominell)
    mrp_nominal: float = 0.0668     # Marknadsriskpremie (nominell)
    credit_spread: float = 0.0114   # Kreditriskpremie
    
    # Kapitalstruktur och skatt
    debt_share: float = 0.36        # Skuldsättningsgrad S = D/(D+E)
    tax_rate: float = 0.206         # Bolagsskatt T
    
    # Omräkning till real nivå
    inflation: float = 0.0202       # KPIF-inflation
    
    # Beta-inmatning (antingen beta_asset ELLER beta_equity)
    beta_asset: Optional[float] = 0.37   # Tillgångsbeta (obelanad)
    beta_equity: Optional[float] = None  # Aktiebeta (belanad)


# ============================================================================
# WACC-BERÄKNINGAR
# ============================================================================

def _hamada(beta_a: float, S: float, T: float) -> float:
    """
    Hamada-formel för att konvertera tillgångsbeta till aktiebeta.
    
    Formel: β_E = β_A × (1 + (1-T) × D/E)
    där D/E = S/(1-S)
    
    Args:
        beta_a: Tillgångsbeta (obelanad beta)
        S: Skuldsättningsgrad D/(D+E)
        T: Bolagsskatt
        
    Returns:
        Aktiebeta (belanad beta)
    """
    d_over_e = S / max(1e-12, (1 - S))
    return beta_a * (1 + (1 - T) * d_over_e)


def ei_wacc_real_pre_tax(inp: EiWaccInputs) -> Tuple[float, float, float, float]:
    """
    Beräknar WACC enligt Ei-metodik.
    
    Beräkningskedja:
    1. CAPM för eget kapital (nominell, efter skatt)
    2. Skuldränta (nominell, före skatt)
    3. WACC (nominell, före skatt via omräkning)
    4. Fisher-omräkning till real nivå
    
    Args:
        inp: EiWaccInputs med alla nödvändiga parametrar
        
    Returns:
        Tuple med (Re_nominell, Rd_nominell, WACC_nominell_pre, WACC_real_pre)
        där alla värden är decimaler (0.05 = 5%)
        
    Raises:
        ValueError: Om både beta_asset och beta_equity saknas,
                   eller om parametrar är utanför giltiga intervall
    """
    # Validering
    if inp.beta_equity is None and inp.beta_asset is None:
        raise ValueError("Måste ange antingen beta_asset eller beta_equity")
    
    if not (0 <= inp.debt_share < 1):
        raise ValueError(f"debt_share måste vara 0 ≤ S < 1, fick {inp.debt_share}")
    
    if not (0 <= inp.tax_rate < 1):
        raise ValueError(f"tax_rate måste vara 0 ≤ T < 1, fick {inp.tax_rate}")
    
    # Bestäm aktiebeta
    if inp.beta_equity is not None:
        beta_e = inp.beta_equity
    else:
        beta_e = _hamada(inp.beta_asset, inp.debt_share, inp.tax_rate)
    
    # 1. Kostnad för eget kapital (nominell, efter skatt) - CAPM
    Re_nom = inp.rf_nominal + beta_e * inp.mrp_nominal
    
    # 2. Kostnad för skuld (nominell, före skatt)
    Rd_nom = inp.rf_nominal + inp.credit_spread
    
    # 3. WACC nominell - först efter skatt, sedan före skatt
    wacc_nom_after = (1 - inp.debt_share) * Re_nom + inp.debt_share * Rd_nom * (1 - inp.tax_rate)
    wacc_nom_pre = wacc_nom_after / (1 - inp.tax_rate)
    
    # 4. Fisher-omräkning till real nivå
    wacc_real_pre = (1 + wacc_nom_pre) / (1 + inp.inflation) - 1
    
    return Re_nom, Rd_nom, wacc_nom_pre, wacc_real_pre
