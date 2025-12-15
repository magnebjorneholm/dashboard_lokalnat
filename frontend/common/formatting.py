"""
Svensk talformatering för Regumetrica UI.

Hanterar tusentalsavgränsare, procent och valutaformat.
"""


def format_tkr(value: float) -> str:
    """
    Svensk talformatering med tusentalsavgränsare.
    
    Args:
        value: Värde i tkr
        
    Returns:
        Formaterad sträng, t.ex. "1 234 567 tkr"
    """
    return f"{value:,.0f}".replace(",", " ") + " tkr"


def format_percent(value: float, decimals: int = 2) -> str:
    """
    Formatera som procent med svenskt decimalkomma.
    
    Args:
        value: Värde som decimal (t.ex. 0.0453 för 4.53%)
        decimals: Antal decimaler
        
    Returns:
        Formaterad sträng, t.ex. "4,53%"
    """
    formatted = f"{value * 100:.{decimals}f}"
    return formatted.replace(".", ",") + "%"


def format_number(value: float, decimals: int = 0) -> str:
    """
    Svensk talformatering utan enhet.
    
    Args:
        value: Numeriskt värde
        decimals: Antal decimaler
        
    Returns:
        Formaterad sträng med svenska konventioner
    """
    if decimals == 0:
        return f"{value:,.0f}".replace(",", " ")
    else:
        # Formatera med decimaler
        formatted = f"{value:,.{decimals}f}"
        # Byt tusentalskomma till mellanslag, decimalkomma till komma
        parts = formatted.split(".")
        integer_part = parts[0].replace(",", " ")
        decimal_part = parts[1] if len(parts) > 1 else ""
        return f"{integer_part},{decimal_part}" if decimal_part else integer_part


def format_delta(value: float, unit: str = "tkr") -> str:
    """
    Formatera delta-värde med +/- prefix.
    
    Args:
        value: Delta-värde
        unit: Enhet (default "tkr")
        
    Returns:
        Formaterad sträng, t.ex. "+1 234 tkr" eller "-567 tkr"
    """
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:,.0f}".replace(",", " ") + f" {unit}"
