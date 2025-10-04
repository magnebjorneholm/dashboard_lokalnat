"""
calculations.py - Ren beräkningslogik för kapitalbas
================================================

Innehåller WACC-beräkningar, scenarioanalys och periodfiltrering.
Inga UI-beroenden - kan användas av både Streamlit och Dash.

Baserat på Energimarknadsinspektionens metodik för WACC-beräkning
enligt regulatory framework 2024-2027.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import pandas as pd
import math


# ============================================================================
# KONSTANTER
# ============================================================================

# Ei:s kalkylränta för 2024-2027 (real, före skatt)
R_OLD: float = 0.0453

# Tecken för formatering
NBSP = "\u202f"  # Non-breaking space
MINUS = "\u2212"  # Minus tecken

# Mappning mellan år och tidskoder (halvår)
# Tid 229 = 2024H1, 230 = 2024H2, osv.
TIME_LABEL_TO_CODE = {
    "2024h1": 229, "2024h2": 230,
    "2025h1": 231, "2025h2": 232,
    "2026h1": 233, "2026h2": 234,
    "2027h1": 235, "2027h2": 236,
}

CODE_TO_TIME_LABEL = {v: k for k, v in TIME_LABEL_TO_CODE.items()}

# Årskoder för filtrering
YEAR_TO_CODES = {
    2024: [229, 230],
    2025: [231, 232],
    2026: [233, 234],
    2027: [235, 236]
}


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
    Beräknar WACC enligt Energimarknadsinspektionens metodik.
    
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


# ============================================================================
# SCENARIOBERÄKNINGAR
# ============================================================================

def apply_interest_scenario(df: pd.DataFrame, r_new: float) -> pd.DataFrame:
    """
    Applicerar nytt räntescenario på kapitalkostnadsdata.
    
    Skalar ENDAST avkastningskomponenter (return_ord, return_tail) med 
    förhållandet r_new/R_OLD. Avskrivningar (dep_ord, dep_tail) lämnas 
    oförändrade eftersom de inte påverkas av WACC.
    
    Skapar nya kolumner:
    - return_ord_new: Skalad ordinarie avkastning
    - return_tail_new: Skalad svansavkastning  
    - capcost_sum_new: Ny total kapitalkostnad
    
    Args:
        df: DataFrame med kolumner return_ord, return_tail, dep_ord, dep_tail
        r_new: Ny kalkylränta (real, före skatt)
        
    Returns:
        DataFrame med originalkolumner + nya scenariokolumner
        
    Raises:
        ValueError: Om r_new inte är ändligt tal
    """
    if not (isinstance(r_new, (float, int)) and math.isfinite(r_new)):
        raise ValueError(f"r_new måste vara ändligt tal, fick {r_new}")
    
    scale = float(r_new) / R_OLD
    out = df.copy()
    
    # Skala avkastningskomponenter
    out["return_ord_new"] = out["return_ord"] * scale
    out["return_tail_new"] = out["return_tail"] * scale
    
    # Beräkna ny total kapitalkostnad
    out["capcost_sum_new"] = (
        out["dep_ord"].astype("float64")
        + out["dep_tail"].astype("float64")
        + out["return_ord_new"].astype("float64")
        + out["return_tail_new"].astype("float64")
    )
    
    return out


# ============================================================================
# PERIODFILTRERING
# ============================================================================

def get_period_df(df: pd.DataFrame, years: tuple = (2024, 2025, 2026, 2027)) -> pd.DataFrame:
    """
    Filtrerar DataFrame till specificerade år.
    
    Konverterar år till tidskoder (halvår) och filtrerar på kolumnen 'time'.
    Exempel: år 2024 → tidskoder [229, 230] för H1 och H2.
    
    Args:
        df: DataFrame med kolumn 'time' innehållande tidskoder
        years: Tuple med år att inkludera
        
    Returns:
        Filtrerad DataFrame med endast rader för specificerade år
        
    Raises:
        ValueError: Om 'time'-kolumn saknas i DataFrame
        KeyError: Om något år saknas i YEAR_TO_CODES
    """
    if 'time' not in df.columns:
        raise ValueError("DataFrame måste innehålla kolumn 'time'")
    
    codes = []
    for year in years:
        if year not in YEAR_TO_CODES:
            raise KeyError(f"År {year} finns inte i YEAR_TO_CODES. Giltiga år: {list(YEAR_TO_CODES.keys())}")
        codes.extend(YEAR_TO_CODES[year])
    
    return df[df["time"].isin(codes)].copy()


# ============================================================================
# HJÄLPFUNKTIONER
# ============================================================================

def format_wacc_tag(r_new: float) -> str:
    """
    Formaterar WACC-värde till tag för filnamn.
    
    Exempel: 0.0475 → "0p0475"
    
    Args:
        r_new: WACC-värde som decimal
        
    Returns:
        Formaterad sträng med 'p' istället för '.'
    """
    return f"{float(r_new):.4f}".replace(".", "p")


def fmt_msek_from_tkr(x, decimals: int = 3) -> str:
    """
    Formaterar tkr till MSEK-sträng för visning.
    
    Args:
        x: Värde i tkr
        decimals: Antal decimaler
        
    Returns:
        Formaterad sträng med non-breaking space som tusentalsavskiljare
    """
    v = pd.to_numeric(x, errors="coerce")
    v = 0.0 if pd.isna(v) else float(v)
    s = f"{v/1000.0:,.{decimals}f}".replace(",", NBSP)
    return s


def fmt_msek_delta_from_tkr(x, decimals: int = 3) -> str:
    """
    Formaterar delta-värde från tkr till MSEK med tecken.
    
    Args:
        x: Delta-värde i tkr
        decimals: Antal decimaler
        
    Returns:
        Formaterad sträng med +/− prefix
    """
    v = pd.to_numeric(x, errors="coerce")
    v = 0.0 if pd.isna(v) else float(v)
    sign = "+" if v >= 0 else MINUS
    s = f"{abs(v)/1000.0:,.{decimals}f}".replace(",", NBSP)
    return f"{sign}{s}"


def fmt_msek_delta_from_tkr_tol(x, decimals: int = 3, tol_tkr: int = 1) -> str:
    """
    Formaterar delta-värde med toleranströskel.
    
    Om absoluta värdet är under tröskeln visas "≈0.000" istället.
    
    Args:
        x: Delta-värde i tkr
        decimals: Antal decimaler
        tol_tkr: Toleranströskel i tkr
        
    Returns:
        Formaterad sträng eller "≈0.000" om under tröskel
    """
    try:
        v = float(x)
    except (ValueError, TypeError):
        v = 0.0
    
    return "≈0.000" if abs(v) <= tol_tkr else fmt_msek_delta_from_tkr(v, decimals)


# ============================================================================
# TESTER (kör som __main__ för att validera)
# ============================================================================

if __name__ == "__main__":
    """
    Enkla tester för att validera beräkningar.
    """
    print("Testing calculations.py...")
    print("=" * 60)
    
    # Test 1: WACC-beräkning med Ei-defaults
    print("\nTest 1: WACC med Ei-defaults")
    inputs = EiWaccInputs()
    Re, Rd, Wn, Wr = ei_wacc_real_pre_tax(inputs)
    print(f"Re (nominell, efter skatt): {Re:.4f} ({Re*100:.2f}%)")
    print(f"Rd (nominell, före skatt):  {Rd:.4f} ({Rd*100:.2f}%)")
    print(f"WACC (nominell, före skatt): {Wn:.4f} ({Wn*100:.2f}%)")
    print(f"WACC (real, före skatt):     {Wr:.4f} ({Wr*100:.2f}%)")
    print(f"Förväntat Wr ≈ 0.0453 (R_OLD): {'✓' if abs(Wr - R_OLD) < 0.0001 else '✗'}")
    
    # Test 2: Scenarioberäkning
    print("\nTest 2: Scenarioberäkning")
    test_df = pd.DataFrame({
        'return_ord': [100.0, 200.0],
        'return_tail': [50.0, 75.0],
        'dep_ord': [300.0, 400.0],
        'dep_tail': [25.0, 30.0]
    })
    r_new = 0.05
    result = apply_interest_scenario(test_df, r_new)
    scale_expected = r_new / R_OLD
    print(f"Skalningsfaktor: {scale_expected:.4f}")
    print(f"return_ord_new[0]: {result['return_ord_new'].iloc[0]:.2f} (förväntat: {100.0 * scale_expected:.2f})")
    print(f"dep_ord oförändrad: {'✓' if result['dep_ord'].iloc[0] == 300.0 else '✗'}")
    
    # Test 3: Periodfiltrering
    print("\nTest 3: Periodfiltrering")
    test_df = pd.DataFrame({
        'time': [229, 230, 231, 232, 233, 234, 235, 236],
        'value': range(8)
    })
    filtered = get_period_df(test_df, years=(2024, 2025))
    print(f"Filtrerade rader för 2024-2025: {len(filtered)} (förväntat: 4)")
    print(f"Tidskoder: {sorted(filtered['time'].tolist())} (förväntat: [229, 230, 231, 232])")
    
    # Test 4: Format-funktioner
    print("\nTest 4: Formatering")
    print(f"WACC-tag för 0.0475: '{format_wacc_tag(0.0475)}' (förväntat: '0p0475')")
    print(f"1234567 tkr → MSEK: '{fmt_msek_from_tkr(1234567)}' (förväntat: '1234.567')")
    print(f"Delta +500 tkr: '{fmt_msek_delta_from_tkr(500)}' (förväntat: '+0.500')")
    print(f"Delta 0.5 tkr med tol=1: '{fmt_msek_delta_from_tkr_tol(0.5)}' (förväntat: '≈0.000')")
    
    print("\n" + "=" * 60)
    print("Alla tester slutförda. Kontrollera manuellt att resultaten stämmer.")