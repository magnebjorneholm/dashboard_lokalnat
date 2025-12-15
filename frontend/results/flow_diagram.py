"""
Flow Diagram komponent.

Visar intäktsramsberäkning som flödesdiagram.
"""

import streamlit as st
from streamlit.components.v1 import html
from typing import Any, Dict

from frontend.common.formatting import format_tkr, format_number


def render(case: Any) -> None:
    """
    Renderar intäktsramsflödesdiagram.
    
    Args:
        case: PipelineResult med intäktsramsdata
    """
    st.subheader("Intäktsramsberäkning")
    
    # Hämta intäktsramskomponenter
    ir = case.post_dea.user_intaktsram
    
    # Generera och visa diagram
    diagram_html = generate_flow_diagram_html(ir)
    html(diagram_html, height=650, scrolling=True)


def generate_flow_diagram_html(ir: Dict[str, float]) -> str:
    """
    Genererar HTML för flödesdiagram.
    
    Args:
        ir: Dict med intäktsramskomponenter
        
    Returns:
        HTML-sträng för diagrammet
    """
    # Extrahera värden (med fallback till 0)
    paverkbara = ir.get("Paverkbara_Total", 0)
    opaverkbara = ir.get("Opaverkbara_Total", 0)
    effkrav = ir.get("Effektiviseringskrav", 0)
    lopande = ir.get("Lopande_Total", 0)
    kapitalkostnader = ir.get("Kapitalkostnader_Total", 0)
    intaktsram = ir.get("Intaktsram_Total", 0)
    
    # Formatera värden
    def fmt(val: float) -> str:
        return f"{val:,.0f}".replace(",", " ")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .flow-container {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                background: #fafafa;
            }}
            .flow-box {{
                background: white;
                border: 2px solid #0066CC;
                border-radius: 8px;
                padding: 15px 20px;
                text-align: center;
                margin: 10px;
                display: inline-block;
                min-width: 180px;
            }}
            .flow-box.highlight {{
                background: #0066CC;
                color: white;
            }}
            .flow-box.negative {{
                border-color: #e74c3c;
            }}
            .flow-label {{
                font-size: 12px;
                color: #666;
                margin-bottom: 5px;
            }}
            .flow-box.highlight .flow-label {{
                color: rgba(255,255,255,0.8);
            }}
            .flow-value {{
                font-size: 18px;
                font-weight: bold;
            }}
            .flow-row {{
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 15px 0;
            }}
            .flow-arrow {{
                font-size: 24px;
                color: #0066CC;
                margin: 0 10px;
            }}
            .flow-arrow.down {{
                display: block;
                text-align: center;
                margin: 10px 0;
            }}
            .flow-section {{
                margin: 20px 0;
            }}
            .flow-section-title {{
                font-size: 14px;
                color: #333;
                font-weight: bold;
                margin-bottom: 10px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="flow-container">
            <!-- Löpande kostnader -->
            <div class="flow-section">
                <div class="flow-section-title">Löpande kostnader</div>
                <div class="flow-row">
                    <div class="flow-box">
                        <div class="flow-label">1. Påverkbara kostnader</div>
                        <div class="flow-value">{fmt(paverkbara)} tkr</div>
                    </div>
                    <span class="flow-arrow">+</span>
                    <div class="flow-box">
                        <div class="flow-label">2. Ej påverkbara kostnader</div>
                        <div class="flow-value">{fmt(opaverkbara)} tkr</div>
                    </div>
                </div>
                <div class="flow-arrow down">↓</div>
                <div class="flow-row">
                    <div class="flow-box negative">
                        <div class="flow-label">4. Effektiviseringskrav</div>
                        <div class="flow-value">{fmt(-effkrav)} tkr</div>
                    </div>
                </div>
                <div class="flow-arrow down">↓</div>
                <div class="flow-row">
                    <div class="flow-box">
                        <div class="flow-label">8. Löpande kostnader</div>
                        <div class="flow-value">{fmt(lopande)} tkr</div>
                    </div>
                </div>
            </div>
            
            <!-- Kapitalkostnader -->
            <div class="flow-section">
                <div class="flow-section-title">Kapitalkostnader</div>
                <div class="flow-row">
                    <div class="flow-box">
                        <div class="flow-label">9. Kapitalkostnader</div>
                        <div class="flow-value">{fmt(kapitalkostnader)} tkr</div>
                    </div>
                </div>
            </div>
            
            <!-- Total -->
            <div class="flow-section">
                <div class="flow-section-title">Total intäktsram</div>
                <div class="flow-arrow down">↓</div>
                <div class="flow-row">
                    <div class="flow-box highlight">
                        <div class="flow-label">11. Intäktsram</div>
                        <div class="flow-value">{fmt(intaktsram)} tkr</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content
