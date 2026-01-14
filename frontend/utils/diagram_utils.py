"""
frontend/utils/diagram_utils.py

Generates interactive HTML diagram for revenue frame decomposition.
Minimalist consulting style. Variable-IDs follow Regumetrica User Manual.
"""

from typing import Dict


VARIABLE_IDS = {
    'paverkbara': '40.1',
    'ej_paverkbara': '40.2',
    'kapitalbas': '11.1',
    'effektivisering': '50.4',
    'avskrivningar': '20.1',
    'avkastning': '30.1',
    'kvalitet': '30.5',
    'lopande': '',
    'kapitalkostnader': '30.1',
    'other_adjustments': '',
    'intaktsram': '60.1',
}


def create_interactive_diagram_html(data: Dict[str, dict]) -> str:
    
    def get_component_data(key: str):
        comp = data.get(key, {})
        return {
            'value': comp.get('value', 0),
            'baseline': comp.get('baseline', 0),
            'is_modified': comp.get('is_directly_modified', False),
            'source': comp.get('source', 'Baseline')
        }
    
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
        return f"{val/1000:,.1f}".replace(",", " ")
    
    def fmt_signed(val):
        """Format efficiency as negative deduction."""
        abs_val = abs(val)
        return f"-{fmt(abs_val)}"
    
    def create_tooltip(name: str, comp: dict) -> str:
        TOLERANCE = 1
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
        return "modified" if comp['is_modified'] else ""
    
    def get_var_id(key: str) -> str:
        return VARIABLE_IDS.get(key, '')
    
    y1, y2, y3, y4, y5, y6 = 0, 95, 175, 260, 345, 440
    col1, col2, col3, col4 = 0, 175, 365, 530
    w_small, w_medium, w_large = 150, 175, 315
    w_wide, w_result = 505, 340
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    background: #F8FAFC;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    padding: 16px;
    -webkit-font-smoothing: antialiased;
}}
.diagram {{
    width: 680px;
    margin: 0 auto;
    position: relative;
    height: 540px;
}}
.box {{
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    padding: 12px 16px;
    text-align: center;
    position: absolute;
    border-radius: 4px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    cursor: default;
    z-index: 10;
}}
.box:hover {{
    border-color: #94A3B8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}}
.box.modified {{
    border-left: 3px solid #2563EB;
}}
.box.modified:hover {{
    border-color: #2563EB;
    border-left-width: 3px;
}}
.box.result {{
    background: #F8FAFC;
    border-color: #CBD5E1;
}}
.box-id {{
    position: absolute;
    top: -8px;
    left: -8px;
    height: 18px;
    padding: 0 6px;
    background: #64748B;
    color: #FFFFFF;
    font-size: 9px;
    font-weight: 500;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    white-space: nowrap;
}}
.box.modified .box-id {{
    background: #2563EB;
}}
.box-id:empty {{
    display: none;
}}
.box-title {{
    font-size: 11px;
    font-weight: 500;
    color: #475569;
    margin-bottom: 4px;
    line-height: 1.3;
}}
.box-value {{
    font-size: 12px;
    font-weight: 600;
    color: #0F172A;
    font-variant-numeric: tabular-nums;
}}
.box.modified .box-value {{
    color: #1E40AF;
}}
.flow-line {{
    position: absolute;
    border-left: 1px solid #CBD5E1;
    z-index: 1;
}}
.tooltip {{
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: #1E293B;
    color: #F8FAFC;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 400;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease;
    z-index: 100;
}}
.tooltip::after {{
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 4px solid transparent;
    border-top-color: #1E293B;
}}
.box:hover .tooltip {{
    opacity: 1;
}}
.tooltip:empty {{
    display: none;
}}
</style>
</head>
<body>
<div class="diagram">
    <!-- ROW 1 -->
    <div class="box {get_box_class(paverkbara)}" style="left: {col1}px; top: {y1}px; width: {w_small}px;">
        <div class="box-id">{get_var_id('paverkbara')}</div>
        <div class="tooltip">{create_tooltip('Controllable costs', paverkbara)}</div>
        <div class="box-title">Controllable costs</div>
        <div class="box-value">{fmt(paverkbara['value'])} MSEK</div>
    </div>
    <div class="box {get_box_class(ej_paverkbara)}" style="left: {col2}px; top: {y1}px; width: {w_small}px;">
        <div class="box-id">{get_var_id('ej_paverkbara')}</div>
        <div class="tooltip">{create_tooltip('Non-controllable costs', ej_paverkbara)}</div>
        <div class="box-title">Non-controllable costs</div>
        <div class="box-value">{fmt(ej_paverkbara['value'])} MSEK</div>
    </div>
    <div class="box {get_box_class(kapitalbas)}" style="left: {col3}px; top: {y1}px; width: {w_large}px;">
        <div class="box-id">{get_var_id('kapitalbas')}</div>
        <div class="tooltip">{create_tooltip('Capital base', kapitalbas)}</div>
        <div class="box-title">Capital base</div>
        <div class="box-value">{fmt(kapitalbas['value'])} MSEK</div>
    </div>
    
    <!-- Flow lines row 1 -->
    <div class="flow-line" style="left: {col1 + 75}px; top: {y1 + 52}px; height: {y2 - y1 - 52}px;"></div>
    <div class="flow-line" style="left: {col2 + 75}px; top: {y1 + 52}px; height: {y4 - y1 - 52}px;"></div>
    <div class="flow-line" style="left: {col3 + 78}px; top: {y1 + 52}px; height: {y2 - y1 - 52}px;"></div>
    <div class="flow-line" style="left: {col3 + 236}px; top: {y1 + 52}px; height: {y2 - y1 - 52}px;"></div>
    
    <!-- ROW 2 -->
    <div class="box {get_box_class(effektivisering)}" style="left: {col1}px; top: {y2}px; width: {w_medium}px;">
        <div class="box-id">{get_var_id('effektivisering')}</div>
        <div class="tooltip">{create_tooltip('Efficiency requirement', effektivisering)}</div>
        <div class="box-title">Efficiency requirement</div>
        <div class="box-value">{fmt_signed(effektivisering['value'])} MSEK</div>
    </div>
    <div class="box {get_box_class(avskrivningar)}" style="left: {col3}px; top: {y2}px; width: {w_small}px;">
        <div class="box-id">{get_var_id('avskrivningar')}</div>
        <div class="tooltip">{create_tooltip('Depreciation', avskrivningar)}</div>
        <div class="box-title">Depreciation</div>
        <div class="box-value">{fmt(avskrivningar['value'])} MSEK</div>
    </div>
    <div class="box {get_box_class(avkastning)}" style="left: {col4}px; top: {y2}px; width: {w_small}px;">
        <div class="box-id">{get_var_id('avkastning')}</div>
        <div class="tooltip">{create_tooltip('Return (WACC)', avkastning)}</div>
        <div class="box-title">Return (WACC)</div>
        <div class="box-value">{fmt(avkastning['value'])} MSEK</div>
    </div>
    
    <!-- Flow lines row 2 -->
    <div class="flow-line" style="left: {col1 + 87}px; top: {y2 + 52}px; height: {y4 - y2 - 52}px;"></div>
    <div class="flow-line" style="left: {col3 + 75}px; top: {y2 + 52}px; height: {y4 - y2 - 52}px;"></div>
    <div class="flow-line" style="left: {col4 + 75}px; top: {y2 + 52}px; height: {y3 - y2 - 52}px;"></div>
    
    <!-- ROW 3 -->
    <div class="box {get_box_class(kvalitet)}" style="left: {col4 - 35}px; top: {y3}px; width: {w_medium + 40}px;">
        <div class="box-id">{get_var_id('kvalitet')}</div>
        <div class="tooltip">{create_tooltip('Quality & incentive adjustment', kvalitet)}</div>
        <div class="box-title">Quality & incentive adjustment</div>
        <div class="box-value">{fmt(kvalitet['value'])} MSEK</div>
    </div>
    
    <div class="flow-line" style="left: {col4 + 30}px; top: {y3 + 52}px; height: {y4 - y3 - 52}px;"></div>
    
    <!-- ROW 4 -->
    <div class="box {get_box_class(lopande)}" style="left: {col1}px; top: {y4}px; width: {w_large}px;">
        <div class="box-id">{get_var_id('lopande')}</div>
        <div class="tooltip">{create_tooltip('Operating costs', lopande)}</div>
        <div class="box-title">Operating costs</div>
        <div class="box-value">{fmt(lopande['value'])} MSEK</div>
    </div>
    <div class="box {get_box_class(kapitalkostnader)}" style="left: {col3}px; top: {y4}px; width: {w_large}px;">
        <div class="box-id">{get_var_id('kapitalkostnader')}</div>
        <div class="tooltip">{create_tooltip('Capital costs', kapitalkostnader)}</div>
        <div class="box-title">Capital costs</div>
        <div class="box-value">{fmt(kapitalkostnader['value'])} MSEK</div>
    </div>
    
    <div class="flow-line" style="left: {col1 + 157}px; top: {y4 + 52}px; height: {y5 - y4 - 52}px;"></div>
    <div class="flow-line" style="left: {col3 + 157}px; top: {y4 + 52}px; height: {y5 - y4 - 52}px;"></div>
    
    <!-- ROW 5 -->
    <div class="box {get_box_class(other_adjustments)}" style="left: {col1 + 87}px; top: {y5}px; width: {w_wide}px;">
        <div class="box-id">{get_var_id('other_adjustments')}</div>
        <div class="tooltip">{create_tooltip('Other adjustments', other_adjustments)}</div>
        <div class="box-title">Other adjustments</div>
        <div class="box-value">{fmt(other_adjustments['value'])} MSEK</div>
    </div>
    
    <div class="flow-line" style="left: 340px; top: {y5 + 52}px; height: {y6 - y5 - 52}px;"></div>
    
    <!-- ROW 6 -->
    <div class="box result {get_box_class(intaktsram)}" style="left: {(680 - w_result) // 2}px; top: {y6}px; width: {w_result}px;">
        <div class="box-id">{get_var_id('intaktsram')}</div>
        <div class="tooltip">{create_tooltip('Revenue frame', intaktsram)}</div>
        <div class="box-title">Revenue frame</div>
        <div class="box-value">{fmt(intaktsram['value'])} MSEK</div>
    </div>
</div>
</body>
</html>"""
    
    return html