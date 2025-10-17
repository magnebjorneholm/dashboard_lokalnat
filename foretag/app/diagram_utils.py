"""
foretag/app/diagram_utils.py
Genererar interaktivt HTML-diagram för intäktsram-dekomposition
"""

from typing import Dict


def create_interactive_diagram_html(data: Dict[str, float]) -> str:
    """
    Skapar interaktiv HTML-visualisering enligt Ei-struktur.
    
    Args:
        data: Dict med komponenter (paverkbara, ej_paverkbara, kapitalbas, etc.)
        
    Returns:
        HTML-sträng för rendering med components.html()
    """
    
    paverkbara = data.get('paverkbara', 0)
    ej_paverkbara = data.get('ej_paverkbara', 0)
    kapitalbas = data.get('kapitalbas', 0)
    effektivisering = abs(data.get('effektivisering', 0))
    avskrivningar = data.get('avskrivningar', 0)
    avkastning = data.get('avkastning', 0)
    kvalitet = data.get('kvalitet', 0)
    
    lopande = paverkbara + ej_paverkbara - effektivisering
    kapitalkostnader = avskrivningar + avkastning + kvalitet
    intaktsram = lopande + kapitalkostnader
    
    def fmt(val):
        return f"{val:,.0f}".replace(",", " ")
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                background-color: #F5F7FA; 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                padding: 50px 25px 25px 25px; 
            }
            
            .diagram {
                width: 900px;
                margin: 0 auto;
                position: relative;
                height: 665px;
            }
            
            .box {
                background: white;
                border: 3px solid;
                padding: 18px 22px;
                text-align: center;
                position: absolute;
                border-radius: 6px;
                box-shadow: 0 3px 10px rgba(0,0,0,0.12);
                transition: all 0.3s ease;
                cursor: pointer;
                z-index: 50;
            }
            
            .box:hover {
                transform: translateY(-3px) scale(1.02);
                box-shadow: 0 8px 24px rgba(0,102,204,0.4);
                z-index: 100;
                border-color: #0088FF !important;
            }
            
            .box-input {
                border-color: #0066CC !important;
                background: linear-gradient(135deg, #ffffff 0%, #f0f7ff 100%) !important;
            }
            
            .box-calculation {
                border-color: #4A5F7F !important;
                background: linear-gradient(135deg, #ffffff 0%, #f5f6f8 100%) !important;
            }
            
            .box-intermediate {
                border-color: #1E3A5F !important;
                background: linear-gradient(135deg, #ffffff 0%, #eef2f7 100%) !important;
            }
            
            .box-result {
                border-color: #0066CC !important;
                background: linear-gradient(135deg, #d4e9ff 0%, #eef6ff 100%) !important;
                border-width: 4px !important;
            }
            
            .box-title {
                font-size: 14px;
                font-weight: 600;
                color: #2C3E50;
                line-height: 1.4;
                margin-bottom: 8px;
            }
            
            .box-value {
                font-size: 13px;
                color: #1E3A5F;
                font-weight: 500;
                margin-top: 4px;
            }
            
            .badge {
                position: absolute;
                top: -10px;
                left: 8px;
                width: 22px;
                height: 22px;
                border-radius: 50%;
                background: #1E3A5F;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                font-weight: 600;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                z-index: 60;
            }
            
            .flow-line {
                position: absolute;
                border-left: 2px dashed #4A5F7F;
                opacity: 0.35;
                transition: all 0.3s ease;
                pointer-events: none;
                z-index: 1;
            }
            
            .box::after {
                content: attr(data-tooltip);
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%) translateY(-10px);
                background: #1E3A5F;
                color: #FFFFFF;
                padding: 8px 14px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: 500;
                white-space: nowrap;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.3s ease, transform 0.3s ease;
                z-index: 1000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }
            
            .box:hover::after {
                opacity: 1;
                transform: translateX(-50%) translateY(-5px);
            }
        </style>
        <script>
            const connections = {
                'box-paverkbara': {
                    boxes: ['box-effektivisering', 'box-lopande'],
                    lines: ['line-paverkbara', 'line-effektivisering'],
                    color: '#0088FF'
                },
                'box-ej-paverkbara': {
                    boxes: ['box-lopande'],
                    lines: ['line-ej-paverkbara'],
                    color: '#0088FF'
                },
                'box-kapitalbas': {
                    boxes: ['box-avskrivningar', 'box-avkastning', 'box-kvalitet', 'box-kapitalkostnader'],
                    lines: ['line-kapitalbas-1', 'line-kapitalbas-2', 'line-avskrivningar', 'line-avkastning', 'line-kvalitet'],
                    color: '#0088FF'
                },
                'box-effektivisering': {
                    boxes: ['box-lopande'],
                    lines: ['line-effektivisering'],
                    color: '#0088FF'
                },
                'box-avskrivningar': {
                    boxes: ['box-kapitalkostnader'],
                    lines: ['line-avskrivningar'],
                    color: '#0088FF'
                },
                'box-avkastning': {
                    boxes: ['box-kvalitet', 'box-kapitalkostnader'],
                    lines: ['line-avkastning', 'line-kvalitet'],
                    color: '#0088FF'
                },
                'box-kvalitet': {
                    boxes: ['box-kapitalkostnader'],
                    lines: ['line-kvalitet'],
                    color: '#0088FF'
                },
                'box-lopande': {
                    boxes: ['box-justering'],
                    lines: ['line-lopande'],
                    color: '#0088FF'
                },
                'box-kapitalkostnader': {
                    boxes: ['box-justering'],
                    lines: ['line-kapitalkostnader'],
                    color: '#0088FF'
                },
                'box-justering': {
                    boxes: ['box-intaktsram'],
                    lines: ['line-justering'],
                    color: '#0088FF'
                }
            };
            
            document.addEventListener('DOMContentLoaded', function() {
                Object.keys(connections).forEach(boxClass => {
                    const boxes = document.querySelectorAll('.' + boxClass);
                    
                    boxes.forEach(box => {
                        box.addEventListener('mouseenter', function() {
                            const conn = connections[boxClass];
                            
                            conn.boxes.forEach(targetClass => {
                                document.querySelectorAll('.' + targetClass).forEach(el => {
                                    el.style.borderColor = conn.color;
                                    el.style.boxShadow = `0 0 24px rgba(0, 136, 255, 0.5)`;
                                    el.style.background = 'linear-gradient(135deg, #E3F2FF 0%, #F0F9FF 100%)';
                                });
                            });
                            
                            conn.lines.forEach(lineClass => {
                                document.querySelectorAll('.' + lineClass).forEach(line => {
                                    line.style.opacity = '1';
                                    line.style.borderLeftWidth = '4px';
                                    line.style.borderLeftColor = conn.color;
                                    line.style.borderLeftStyle = 'solid';
                                });
                            });
                        });
                        
                        box.addEventListener('mouseleave', function() {
                            const conn = connections[boxClass];
                            
                            conn.boxes.forEach(targetClass => {
                                document.querySelectorAll('.' + targetClass).forEach(el => {
                                    el.style.borderColor = '';
                                    el.style.boxShadow = '';
                                    el.style.background = '';
                                });
                            });
                            
                            conn.lines.forEach(lineClass => {
                                document.querySelectorAll('.' + lineClass).forEach(line => {
                                    line.style.opacity = '';
                                    line.style.borderLeftWidth = '';
                                    line.style.borderLeftColor = '';
                                    line.style.borderLeftStyle = '';
                                });
                            });
                        });
                    });
                });
            });
        </script>
    </head>
    <body>
        <div class="diagram">
    """
    
    y1 = 0
    y2 = 120
    y3 = 225
    y4 = 330
    y5 = 435
    y6 = 540
    
    x_left = 15
    x_mid_left = 225
    x_mid_right = 488
    x_right = 698
    
    html += f"""
        <div class="box box-input box-paverkbara" style="left: {x_left}px; top: {y1}px; width: 173px;" 
             data-tooltip="Påverkar: Effektiviseringskrav, Löpande kostnader">
            <div class="badge">1</div>
            <div class="box-title">Påverkbara<br>kostnader</div>
            <div class="box-value">{fmt(paverkbara)} tkr</div>
        </div>
        
        <div class="box box-input box-ej-paverkbara" style="left: {x_mid_left}px; top: {y1}px; width: 188px;"
             data-tooltip="Påverkar: Löpande kostnader">
            <div class="badge">2</div>
            <div class="box-title">Ej påverkbara<br>kostnader</div>
            <div class="box-value">{fmt(ej_paverkbara)} tkr</div>
        </div>
        
        <div class="box box-input box-kapitalbas" style="left: {x_mid_right}px; top: {y1}px; width: 398px;"
             data-tooltip="Påverkar: Avskrivningar, Avkastning">
            <div class="badge">3</div>
            <div class="box-title">Kapitalbas</div>
            <div class="box-value">{fmt(kapitalbas)} tkr</div>
        </div>
    """
    
    html += f'<div class="flow-line line-paverkbara" style="left: {x_left + 86}px; top: {y1 + 65}px; height: {y2 - y1 - 65}px;"></div>'
    html += f'<div class="flow-line line-ej-paverkbara" style="left: {x_mid_left + 94}px; top: {y1 + 65}px; height: {y4 - y1 - 65}px;"></div>'
    html += f'<div class="flow-line line-kapitalbas-1" style="left: {x_mid_right + 98}px; top: {y1 + 65}px; height: {y2 - y1 - 65}px;"></div>'
    html += f'<div class="flow-line line-kapitalbas-2" style="left: {x_mid_right + 293}px; top: {y1 + 65}px; height: {y2 - y1 - 65}px;"></div>'
    
    html += f"""
        <div class="box box-calculation box-effektivisering" style="left: {x_left}px; top: {y2}px; width: 263px;"
             data-tooltip="Påverkar: Löpande kostnader (minskning)">
            <div class="badge">4</div>
            <div class="box-title">Effektiviseringskrav</div>
            <div class="box-value">-{fmt(effektivisering)} tkr</div>
        </div>
        
        <div class="box box-calculation box-avskrivningar" style="left: {x_mid_right}px; top: {y2}px; width: 180px;"
             data-tooltip="Påverkar: Kapitalkostnader">
            <div class="badge">5</div>
            <div class="box-title">Avskrivningar</div>
            <div class="box-value">{fmt(avskrivningar)} tkr</div>
        </div>
        
        <div class="box box-calculation box-avkastning" style="left: {x_right}px; top: {y2}px; width: 188px;"
             data-tooltip="Påverkar: Kvalitetsjustering">
            <div class="badge">6</div>
            <div class="box-title">Avkastning<br>(WACC)</div>
            <div class="box-value">{fmt(avkastning)} tkr</div>
        </div>
    """
    
    html += f'<div class="flow-line line-effektivisering" style="left: {x_left + 131}px; top: {y2 + 65}px; height: {y4 - y2 - 65}px;"></div>'
    html += f'<div class="flow-line line-avskrivningar" style="left: {x_mid_right + 90}px; top: {y2 + 65}px; height: {y4 - y2 - 65}px;"></div>'
    html += f'<div class="flow-line line-avkastning" style="left: {x_right + 94}px; top: {y2 + 65}px; height: {y3 - y2 - 65}px;"></div>'
    
    html += f"""
        <div class="box box-calculation box-kvalitet" style="left: {x_right - 83}px; top: {y3}px; width: 270px;"
             data-tooltip="Påverkar: Kapitalkostnader">
            <div class="badge">7</div>
            <div class="box-title">Justering med avseende<br>på kvalitet</div>
            <div class="box-value">{fmt(kvalitet)} tkr</div>
        </div>
    """
    
    html += f'<div class="flow-line line-kvalitet" style="left: {x_right + 41}px; top: {y3 + 65}px; height: {y4 - y3 - 65}px;"></div>'
    
    html += f"""
        <div class="box box-intermediate box-lopande" style="left: {x_left}px; top: {y4}px; width: 398px;"
             data-tooltip="Påverkar: Justering tidigare perioder, Intäktsram">
            <div class="badge">8</div>
            <div class="box-title">Löpande kostnader</div>
            <div class="box-value">{fmt(lopande)} tkr</div>
        </div>
        
        <div class="box box-intermediate box-kapitalkostnader" style="left: {x_mid_right}px; top: {y4}px; width: 398px;"
             data-tooltip="Påverkar: Justering tidigare perioder, Intäktsram">
            <div class="badge">9</div>
            <div class="box-title">Kapitalkostnader</div>
            <div class="box-value">{fmt(kapitalkostnader)} tkr</div>
        </div>
    """
    
    html += f'<div class="flow-line line-lopande" style="left: {x_left + 199}px; top: {y4 + 65}px; height: {y5 - y4 - 65}px;"></div>'
    html += f'<div class="flow-line line-kapitalkostnader" style="left: {x_mid_right + 199}px; top: {y4 + 65}px; height: {y5 - y4 - 65}px;"></div>'
    
    html += f"""
        <div class="box box-intermediate box-justering" style="left: {x_left + 75}px; top: {y5}px; width: 638px;"
             data-tooltip="Påverkar: Intäktsram (slutlig justering)">
            <div class="badge">10</div>
            <div class="box-title">Justering för tidigare perioders över-<br>respektive underdebitering</div>
        </div>
    """
    
    html += f'<div class="flow-line line-justering" style="left: 450px; top: {y5 + 65}px; height: {y6 - y5 - 65}px;"></div>'
    
    html += f"""
        <div class="box box-result box-intaktsram" style="left: 225px; top: {y6}px; width: 450px;"
             data-tooltip="Slutlig intäktsram för perioden">
            <div class="badge">11</div>
            <div class="box-title" style="font-size: 16px; font-weight: 700;">Intäktsram</div>
            <div class="box-value" style="font-size: 14px;">{fmt(intaktsram)} tkr</div>
        </div>
    """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    return html