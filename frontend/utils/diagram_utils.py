"""
frontend/utils/diagram_utils.py

Generates interactive HTML diagram for revenue frame decomposition.
English labels, compact size.
"""

from typing import Dict


def create_interactive_diagram_html(data: Dict[str, dict]) -> str:
    """
    Creates interactive HTML visualization following Ei structure.
    
    Args:
        data: Dict with components where each component has:
              {'value': float, 'baseline': float, 'is_directly_modified': bool, 'source': str}
    """
    
    def get_component_data(key: str):
        """Get component data with fallback."""
        comp = data.get(key, {})
        return {
            'value': comp.get('value', 0),
            'baseline': comp.get('baseline', 0),
            'is_modified': comp.get('is_directly_modified', False),
            'source': comp.get('source', 'Baseline')
        }
    
    # Extract all components
    paverkbara = get_component_data('paverkbara')
    ej_paverkbara = get_component_data('ej_paverkbara')
    kapitalbas = get_component_data('kapitalbas')
    effektivisering = get_component_data('effektivisering')
    avskrivningar = get_component_data('avskrivningar')
    avkastning = get_component_data('avkastning')
    kvalitet = get_component_data('kvalitet')
    lopande = get_component_data('lopande')
    kapitalkostnader = get_component_data('kapitalkostnader')
    other_adjustments = get_component_data('other_adjustments')
    intaktsram = get_component_data('intaktsram')
    
    def fmt(val):
        """Format tkr to MSEK with space as thousands separator."""
        return f"{val/1000:,.1f}".replace(",", " ")
    
    def create_tooltip(name: str, comp: dict) -> str:
        """
        Create tooltip text.
        - Scenario (has delta): Show only delta
        - Baseline (no delta): No tooltip (empty string)
        """
        TOLERANCE = 1  # Tolerance level for significant delta in MSEK
        delta = comp['value'] - comp['baseline']

        if abs(delta) > TOLERANCE:
            if comp['baseline'] != 0:
                delta_pct = (delta / comp['baseline'] * 100)
                sign = "+" if delta >= 0 else ""
                return f"{name} | Delta {sign}{fmt(delta)} MSEK ({sign}{delta_pct:.1f}%)"
            else:
                return f"{name} | {fmt(comp['value'])} MSEK"
        return ""
    
    def get_box_class(comp: dict) -> str:
        """Return CSS class based on whether component is directly modified."""
        return "box-modified" if comp['is_modified'] else ""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                background-color: #F5F7FA; 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
                padding: 20px 15px 15px 15px; 
            }
            
            .diagram-wrapper {
                transform: scale(0.78);
                transform-origin: top center;
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
                padding: 14px 18px;
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
            }
            
            .box-modified {
                border-color: #FF8800 !important;
                background: linear-gradient(135deg, #FFF8F0 0%, #FFFFFF 100%);
            }
            
            .box-modified:hover {
                box-shadow: 0 8px 24px rgba(255,136,0,0.5);
            }
            
            .box-input {
                border-color: #0066CC;
                background: linear-gradient(135deg, #F0F7FF 0%, #FFFFFF 100%);
            }
            
            .box-calculation {
                border-color: #FFB347;
                background: linear-gradient(135deg, #FFF9F0 0%, #FFFFFF 100%);
            }
            
            .box-intermediate {
                border-color: #0066CC;
                background: linear-gradient(135deg, #F0F7FF 0%, #FFFFFF 100%);
            }
            
            .box-result {
                border-color: #0088FF;
                border-width: 4px;
                background: linear-gradient(135deg, #E6F3FF 0%, #F0F8FF 100%);
            }
            
            .box-title {
                font-size: 13px;
                font-weight: 600;
                color: #1E3A5F;
                margin-bottom: 6px;
                line-height: 1.3;
            }
            
            .box-value {
                font-size: 12px;
                font-weight: 700;
                color: #0066CC;
                font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
            }
            
            .box-modified .box-value {
                color: #E67300;
            }
            
            .badge {
                position: absolute;
                top: -12px;
                left: -12px;
                width: 26px;
                height: 26px;
                background: #0066CC;
                color: white;
                font-size: 12px;
                font-weight: 700;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                z-index: 100;
            }
            
            .box-modified .badge {
                background: #FF8800;
            }
            
            .flow-line {
                position: absolute;
                border-left: 3px dashed #B8D4E8;
                opacity: 0.7;
                transition: all 0.3s ease;
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
                font-size: 11px;
                font-weight: 500;
                white-space: nowrap;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.3s ease, transform 0.3s ease;
                z-index: 1000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }
            
            .box-modified::after {
                background: #FF8800;
            }
            
            .box:hover::after {
                opacity: 1;
                transform: translateX(-50%) translateY(-5px);
            }
            
            .box[data-tooltip=""]::after {
                display: none;
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
                    boxes: ['box-other-adj'],
                    lines: ['line-lopande'],
                    color: '#0088FF'
                },
                'box-kapitalkostnader': {
                    boxes: ['box-other-adj'],
                    lines: ['line-kapitalkostnader'],
                    color: '#0088FF'
                },
                'box-other-adj': {
                    boxes: ['box-intaktsram'],
                    lines: ['line-other-adj'],
                    color: '#0088FF'
                }
            };
            
            document.addEventListener('DOMContentLoaded', function() {
                Object.keys(connections).forEach(boxClass => {
                    const boxes = document.querySelectorAll('.' + boxClass);
                    
                    boxes.forEach(box => {
                        box.addEventListener('mouseenter', function() {
                            const conn = connections[boxClass];
                            const isModified = box.classList.contains('box-modified');
                            const hoverColor = isModified ? '#FF8800' : '#0088FF';
                            
                            conn.boxes.forEach(targetClass => {
                                document.querySelectorAll('.' + targetClass).forEach(el => {
                                    el.style.borderColor = hoverColor;
                                    const shadowColor = isModified ? 'rgba(255, 136, 0, 0.5)' : 'rgba(0, 136, 255, 0.5)';
                                    el.style.boxShadow = `0 0 24px ${shadowColor}`;
                                });
                            });
                            
                            conn.lines.forEach(lineClass => {
                                document.querySelectorAll('.' + lineClass).forEach(line => {
                                    line.style.opacity = '1';
                                    line.style.borderLeftWidth = '4px';
                                    line.style.borderLeftColor = hoverColor;
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
        <div class="diagram-wrapper">
        <div class="diagram">
    """
    
    # Y positions for rows
    y1 = 0
    y2 = 120
    y3 = 225
    y4 = 330
    y5 = 435
    y6 = 540
    
    # X positions
    x_left = 15
    x_mid_left = 225
    x_mid_right = 488
    x_right = 698
    
    # ROW 1: INPUT COMPONENTS
    html += f"""
        <div class="box box-input box-paverkbara {get_box_class(paverkbara)}" style="left: {x_left}px; top: {y1}px; width: 173px;" 
             data-tooltip="{create_tooltip('Controllable costs', paverkbara)}">
            <div class="badge">1</div>
            <div class="box-title">Controllable<br>costs</div>
            <div class="box-value">{fmt(paverkbara['value'])} MSEK</div>
        </div>
        
        <div class="box box-input box-ej-paverkbara {get_box_class(ej_paverkbara)}" style="left: {x_mid_left}px; top: {y1}px; width: 188px;"
             data-tooltip="{create_tooltip('Non-controllable costs', ej_paverkbara)}">
            <div class="badge">2</div>
            <div class="box-title">Non-controllable<br>costs</div>
            <div class="box-value">{fmt(ej_paverkbara['value'])} MSEK</div>
        </div>
        
        <div class="box box-input box-kapitalbas {get_box_class(kapitalbas)}" style="left: {x_mid_right}px; top: {y1}px; width: 398px;"
             data-tooltip="{create_tooltip('Capital base', kapitalbas)}">
            <div class="badge">3</div>
            <div class="box-title">Capital base</div>
            <div class="box-value">{fmt(kapitalbas['value'])} MSEK</div>
        </div>
    """
    
    # Flow lines from row 1
    html += f'<div class="flow-line line-paverkbara" style="left: {x_left + 86}px; top: {y1 + 65}px; height: {y2 - y1 - 65}px;"></div>'
    html += f'<div class="flow-line line-ej-paverkbara" style="left: {x_mid_left + 94}px; top: {y1 + 65}px; height: {y4 - y1 - 65}px;"></div>'
    html += f'<div class="flow-line line-kapitalbas-1" style="left: {x_mid_right + 98}px; top: {y1 + 65}px; height: {y2 - y1 - 65}px;"></div>'
    html += f'<div class="flow-line line-kapitalbas-2" style="left: {x_mid_right + 293}px; top: {y1 + 65}px; height: {y2 - y1 - 65}px;"></div>'
    
    # ROW 2: CALCULATION COMPONENTS
    html += f"""
        <div class="box box-calculation box-effektivisering {get_box_class(effektivisering)}" style="left: {x_left}px; top: {y2}px; width: 263px;"
             data-tooltip="{create_tooltip('Efficiency requirement', effektivisering)}">
            <div class="badge">4</div>
            <div class="box-title">Efficiency requirement</div>
            <div class="box-value">-{fmt(effektivisering['value'])} MSEK</div>
        </div>
        
        <div class="box box-calculation box-avskrivningar {get_box_class(avskrivningar)}" style="left: {x_mid_right}px; top: {y2}px; width: 180px;"
             data-tooltip="{create_tooltip('Depreciation', avskrivningar)}">
            <div class="badge">5</div>
            <div class="box-title">Depreciation</div>
            <div class="box-value">{fmt(avskrivningar['value'])} MSEK</div>
        </div>
        
        <div class="box box-calculation box-avkastning {get_box_class(avkastning)}" style="left: {x_right}px; top: {y2}px; width: 188px;"
             data-tooltip="{create_tooltip('Return (WACC)', avkastning)}">
            <div class="badge">6</div>
            <div class="box-title">Return<br>(WACC)</div>
            <div class="box-value">{fmt(avkastning['value'])} MSEK</div>
        </div>
    """
    
    # Flow lines from row 2
    html += f'<div class="flow-line line-effektivisering" style="left: {x_left + 131}px; top: {y2 + 65}px; height: {y4 - y2 - 65}px;"></div>'
    html += f'<div class="flow-line line-avskrivningar" style="left: {x_mid_right + 90}px; top: {y2 + 65}px; height: {y4 - y2 - 65}px;"></div>'
    html += f'<div class="flow-line line-avkastning" style="left: {x_right + 94}px; top: {y2 + 65}px; height: {y3 - y2 - 65}px;"></div>'
    
    # ROW 3: QUALITY ADJUSTMENT
    html += f"""
        <div class="box box-calculation box-kvalitet {get_box_class(kvalitet)}" style="left: {x_right - 83}px; top: {y3}px; width: 270px;"
             data-tooltip="{create_tooltip('Quality adjustment', kvalitet)}">
            <div class="badge">7</div>
            <div class="box-title">Quality &amp; incentive<br>adjustment</div>
            <div class="box-value">{fmt(kvalitet['value'])} MSEK</div>
        </div>
    """
    
    html += f'<div class="flow-line line-kvalitet" style="left: {x_right + 41}px; top: {y3 + 65}px; height: {y4 - y3 - 65}px;"></div>'
    
    # ROW 4: INTERMEDIATE SUMS
    html += f"""
        <div class="box box-intermediate box-lopande {get_box_class(lopande)}" style="left: {x_left}px; top: {y4}px; width: 398px;"
             data-tooltip="{create_tooltip('Operating costs', lopande)}">
            <div class="badge">8</div>
            <div class="box-title">Operating costs</div>
            <div class="box-value">{fmt(lopande['value'])} MSEK</div>
        </div>
        
        <div class="box box-intermediate box-kapitalkostnader {get_box_class(kapitalkostnader)}" style="left: {x_mid_right}px; top: {y4}px; width: 398px;"
             data-tooltip="{create_tooltip('Capital costs', kapitalkostnader)}">
            <div class="badge">9</div>
            <div class="box-title">Capital costs</div>
            <div class="box-value">{fmt(kapitalkostnader['value'])} MSEK</div>
        </div>
    """
    
    html += f'<div class="flow-line line-lopande" style="left: {x_left + 199}px; top: {y4 + 65}px; height: {y5 - y4 - 65}px;"></div>'
    html += f'<div class="flow-line line-kapitalkostnader" style="left: {x_mid_right + 199}px; top: {y4 + 65}px; height: {y5 - y4 - 65}px;"></div>'
    
    # ROW 5: OTHER ADJUSTMENTS
    html += f"""
        <div class="box box-intermediate box-other-adj {get_box_class(other_adjustments)}" style="left: {x_left + 75}px; top: {y5}px; width: 638px;"
             data-tooltip="{create_tooltip('Other adjustments', other_adjustments)}">
            <div class="badge">10</div>
            <div class="box-title">Other adjustments</div>
            <div class="box-value">{fmt(other_adjustments['value'])} MSEK</div>
        </div>
    """
    
    html += f'<div class="flow-line line-other-adj" style="left: 450px; top: {y5 + 65}px; height: {y6 - y5 - 65}px;"></div>'
    
    # ROW 6: FINAL RESULT
    html += f"""
        <div class="box box-result box-intaktsram {get_box_class(intaktsram)}" style="left: 225px; top: {y6}px; width: 450px;"
             data-tooltip="{create_tooltip('Revenue frame', intaktsram)}">
            <div class="badge">11</div>
            <div class="box-title" style="font-size: 15px; font-weight: 700;">Revenue frame</div>
            <div class="box-value" style="font-size: 13px;">{fmt(intaktsram['value'])} MSEK</div>
        </div>
    """
    
    html += """
        </div>
        </div>
    </body>
    </html>
    """
    
    return html