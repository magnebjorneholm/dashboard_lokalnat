"""
frontend/utils/diagram_utils.py

Generates interactive HTML diagram for revenue frame decomposition.
Minimalist consulting style. Variable-IDs follow Regumetrica User Manual.

Supports OPEX and TOTEX efficiency layouts:
- OPEX: Single efficiency requirement reducing controllable costs
- TOTEX: Split OPEX/CAPEX efficiency reducing both sides
"""

from typing import Dict


VARIABLE_IDS = {
    'paverkbara': '40.1',
    'ej_paverkbara': '40.2',
    'kapitalbas': '11.1',
    'effektivisering': '50.4',
    'opex_effektivisering': '50.4.1',
    'capex_effektivisering': '50.4.2',
    'avskrivningar': '20.1',
    'avkastning': '30.1',
    'kvalitet': '30.5',
    'lopande': '',
    'kapitalkostnader': '30.1',
    'other_adjustments': '',
    'intaktsram': '60.1',
}


# Shared CSS for both layouts
_SHARED_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    background: #F8FAFC;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    padding: 16px;
    -webkit-font-smoothing: antialiased;
}
.box {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    padding: 12px 16px;
    text-align: center;
    position: absolute;
    border-radius: 4px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    cursor: default;
    z-index: 10;
}
.box:hover {
    border-color: #94A3B8;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.box.modified {
    border-left: 3px solid #2563EB;
}
.box.modified:hover {
    border-color: #2563EB;
    border-left-width: 3px;
}
.box.result {
    background: #F8FAFC;
    border-color: #CBD5E1;
}
.box-id {
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
}
.box.modified .box-id {
    background: #2563EB;
}
.box-id:empty {
    display: none;
}
.box-title {
    font-size: 11px;
    font-weight: 500;
    color: #475569;
    margin-bottom: 4px;
    line-height: 1.3;
}
.box-value {
    font-size: 12px;
    font-weight: 600;
    color: #0F172A;
    font-variant-numeric: tabular-nums;
}
.box.modified .box-value {
    color: #1E40AF;
}
.flow-line {
    position: absolute;
    border-left: 1px solid #CBD5E1;
    z-index: 1;
}
.tooltip {
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
}
.tooltip::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 4px solid transparent;
    border-top-color: #1E293B;
}
.box:hover .tooltip {
    opacity: 1;
}
.tooltip:empty {
    display: none;
}
.flow-line-h {
    position: absolute;
    border-top: 1px solid #CBD5E1;
    z-index: 1;
}
"""


def create_interactive_diagram_html(data: Dict[str, dict]) -> str:
    """Dispatch to OPEX or TOTEX layout based on data['method']."""
    method = data.get('method', 'OPEX')
    if method == 'TOTEX':
        return _create_totex_html(data)
    return _create_opex_html(data)


# =============================================================================
# SHARED HELPERS
# =============================================================================

def _get_component_data(data: Dict, key: str) -> dict:
    comp = data.get(key, {})
    return {
        'value': comp.get('value', 0),
        'baseline': comp.get('baseline', 0),
        'is_modified': comp.get('is_directly_modified', False),
        'source': comp.get('source', 'Baseline')
    }


def _fmt(val):
    return f"{val/1000:,.1f}".replace(",", " ")


def _fmt_signed(val):
    return f"-{_fmt(abs(val))}"


def _create_tooltip(name: str, comp: dict) -> str:
    TOLERANCE = 1
    delta = comp['value'] - comp['baseline']
    if abs(delta) > TOLERANCE:
        if comp['baseline'] != 0:
            delta_pct = (delta / comp['baseline'] * 100)
            sign = "+" if delta >= 0 else ""
            return f"{name} | Delta {sign}{_fmt(delta)} MSEK ({sign}{delta_pct:.1f}%)"
        else:
            return f"{name} | {_fmt(comp['value'])} MSEK"
    return ""


def _box_class(comp: dict) -> str:
    return "modified" if comp['is_modified'] else ""


def _var_id(key: str) -> str:
    return VARIABLE_IDS.get(key, '')


def _box_html(
    key: str,
    title: str,
    comp: dict,
    left: int,
    top: int,
    width: int,
    extra_class: str = "",
    value_fmt: str = None
) -> str:
    """Render a single diagram box."""
    cls = _box_class(comp)
    if extra_class:
        cls = f"{cls} {extra_class}".strip()
    
    if value_fmt is None:
        value_fmt = f"{_fmt(comp['value'])} MSEK"
    
    return (
        f'<div class="box {cls}" style="left: {left}px; top: {top}px; width: {width}px;">'
        f'<div class="box-id">{_var_id(key)}</div>'
        f'<div class="tooltip">{_create_tooltip(title, comp)}</div>'
        f'<div class="box-title">{title}</div>'
        f'<div class="box-value">{value_fmt}</div>'
        f'</div>'
    )


def _flow_line(left: int, top: int, height: int) -> str:
    return f'<div class="flow-line" style="left: {left}px; top: {top}px; height: {height}px;"></div>'


def _flow_line_h(left: int, top: int, width: int) -> str:
    return f'<div class="flow-line-h" style="left: {left}px; top: {top}px; width: {width}px;"></div>'


# =============================================================================
# OPEX LAYOUT (unchanged logic)
# =============================================================================

def _create_opex_html(data: Dict[str, dict]) -> str:
    
    paverkbara = _get_component_data(data, 'paverkbara')
    ej_paverkbara = _get_component_data(data, 'ej_paverkbara')
    kapitalbas = _get_component_data(data, 'kapitalbas')
    effektivisering = _get_component_data(data, 'effektivisering')
    avskrivningar = _get_component_data(data, 'avskrivningar')
    avkastning = _get_component_data(data, 'avkastning')
    kvalitet = _get_component_data(data, 'kvalitet')
    lopande = _get_component_data(data, 'lopande')
    kapitalkostnader = _get_component_data(data, 'kapitalkostnader')
    other_adjustments = _get_component_data(data, 'other_adjustments')
    intaktsram = _get_component_data(data, 'intaktsram')
    
    # Y positions
    y1, y2, y3, y4, y5, y6 = 0, 95, 165, 265, 350, 445
    
    # X positions (580px total width)
    col1, col2, col3, col4 = 0, 150, 310, 450
    
    # Widths
    w_small, w_medium, w_large = 130, 150, 270
    w_wide, w_result = 430, 290
    
    line_left = 75
    line_right = 515
    
    boxes = "\n".join([
        "<!-- ROW 1 -->",
        _box_html('paverkbara', 'Controllable costs', paverkbara, col1, y1, w_small),
        _box_html('ej_paverkbara', 'Non-controllable<br>costs', ej_paverkbara, col2, y1, w_small),
        _box_html('kapitalbas', 'Capital base', kapitalbas, col3, y1, w_large),
        
        "<!-- ROW 2 -->",
        _box_html('effektivisering', 'Efficiency requirement', effektivisering,
                  col1, y2, w_medium, value_fmt=f"{_fmt_signed(effektivisering['value'])} MSEK"),
        _box_html('avskrivningar', 'Depreciation', avskrivningar, col3, y2, w_small),
        _box_html('avkastning', 'Return (WACC)', avkastning, col4, y2, w_small),
        
        "<!-- ROW 3 -->",
        _box_html('kvalitet', 'Quality & incentive<br>adjustment', kvalitet, col4, y3, w_small),
        
        "<!-- ROW 4 -->",
        _box_html('lopande', 'Operating costs', lopande, col1, y4, w_large),
        _box_html('kapitalkostnader', 'Capital costs', kapitalkostnader, col3, y4, w_large),
        
        "<!-- ROW 5 -->",
        _box_html('other_adjustments', 'Other adjustments', other_adjustments, col1 + 75, y5, w_wide),
        
        "<!-- ROW 6 -->",
        _box_html('intaktsram', 'Revenue frame', intaktsram, (580 - w_result) // 2, y6, w_result, extra_class="result"),
    ])
    
    lines = "\n".join([
        "<!-- Flow lines row 1 to row 2 -->",
        _flow_line(line_left, y1 + 52, y2 - y1 - 52),
        _flow_line(col2 + 65, y1 + 52, y4 - y1 - 52),
        _flow_line(col3 + 65, y1 + 52, y2 - y1 - 52),
        _flow_line(line_right, y1 + 52, y2 - y1 - 52),
        
        "<!-- Flow lines row 2 -->",
        _flow_line(line_left, y2 + 52, y4 - y2 - 52),
        _flow_line(col3 + 65, y2 + 52, y4 - y2 - 52),
        _flow_line(line_right, y2 + 52, y3 - y2 - 52),
        
        "<!-- Flow lines row 3 -->",
        _flow_line(line_right, y3 + 58, y4 - y3 - 58),
        
        "<!-- Flow lines row 4-6 -->",
        _flow_line(col1 + 135, y4 + 52, y5 - y4 - 52),
        _flow_line(col3 + 135, y4 + 52, y5 - y4 - 52),
        _flow_line(290, y5 + 52, y6 - y5 - 52),
    ])
    
    return _wrap_html(boxes, lines, 545)


# =============================================================================
# TOTEX LAYOUT
# =============================================================================

def _create_totex_html(data: Dict[str, dict]) -> str:
    
    paverkbara = _get_component_data(data, 'paverkbara')
    ej_paverkbara = _get_component_data(data, 'ej_paverkbara')
    kapitalbas = _get_component_data(data, 'kapitalbas')
    opex_eff = _get_component_data(data, 'opex_effektivisering')
    capex_eff = _get_component_data(data, 'capex_effektivisering')
    avskrivningar = _get_component_data(data, 'avskrivningar')
    avkastning = _get_component_data(data, 'avkastning')
    kvalitet = _get_component_data(data, 'kvalitet')
    lopande = _get_component_data(data, 'lopande')
    kapitalkostnader = _get_component_data(data, 'kapitalkostnader')
    other_adjustments = _get_component_data(data, 'other_adjustments')
    intaktsram = _get_component_data(data, 'intaktsram')
    
    # Y positions -- Dep/Return moved up to make room for fork lines
    y1 = 0       # Row 1: Controllable, Non-contr, Capital base
    y2 = 80      # Row 2: OPEX eff, Depreciation, Return
    y3 = 175     # Row 3: CAPEX eff, Quality
    y4 = 275     # Row 4: Operating costs, Capital costs
    y5 = 360     # Row 5: Other adjustments
    y6 = 455     # Row 6: Revenue frame
    
    # Fork point: halfway between Return bottom and row 3
    box_h = 52
    y_fork = y2 + box_h + (y3 - y2 - box_h) // 2  # = 132 + 21 = 153
    
    # X positions
    col1, col2, col3, col4 = 0, 150, 310, 450
    
    # Widths
    w_small, w_medium, w_large = 130, 150, 270
    w_wide, w_result = 430, 290
    
    # Line x-centers
    line_left = 75              # OPEX flow center
    dep_center = col3 + 65     # 375 - Depreciation center
    ret_center = col4 + 65     # 515 - Return center
    ret_fork_x = col3 + 105   # 415 - Where Return fork enters CAPEX eff (right side of box)
    
    boxes = "\n".join([
        "<!-- ROW 1 -->",
        _box_html('paverkbara', 'Controllable costs', paverkbara, col1, y1, w_small),
        _box_html('ej_paverkbara', 'Non-controllable<br>costs', ej_paverkbara, col2, y1, w_small),
        _box_html('kapitalbas', 'Capital base', kapitalbas, col3, y1, w_large),
        
        "<!-- ROW 2: Dep/Return moved up -->",
        _box_html('opex_effektivisering', 'OPEX efficiency', opex_eff,
                  col1, y2, w_medium, value_fmt=f"{_fmt_signed(opex_eff['value'])} MSEK"),
        _box_html('avskrivningar', 'Depreciation', avskrivningar, col3, y2, w_small),
        _box_html('avkastning', 'Return (WACC)', avkastning, col4, y2, w_small),
        
        "<!-- ROW 3: CAPEX efficiency + Quality -->",
        _box_html('capex_effektivisering', 'CAPEX efficiency', capex_eff,
                  col3, y3, w_small, value_fmt=f"{_fmt_signed(capex_eff['value'])} MSEK"),
        _box_html('kvalitet', 'Quality & incentive<br>adjustment', kvalitet, col4, y3, w_small),
        
        "<!-- ROW 4 -->",
        _box_html('lopande', 'Operating costs', lopande, col1, y4, w_large),
        _box_html('kapitalkostnader', 'Capital costs', kapitalkostnader, col3, y4, w_large),
        
        "<!-- ROW 5 -->",
        _box_html('other_adjustments', 'Other adjustments', other_adjustments, col1 + 75, y5, w_wide),
        
        "<!-- ROW 6 -->",
        _box_html('intaktsram', 'Revenue frame', intaktsram, (580 - w_result) // 2, y6, w_result, extra_class="result"),
    ])
    
    lines = "\n".join([
        "<!-- Row 1 to Row 2 -->",
        _flow_line(line_left, y1 + box_h, y2 - y1 - box_h),
        _flow_line(col2 + 65, y1 + box_h, y4 - y1 - box_h),
        _flow_line(dep_center, y1 + box_h, y2 - y1 - box_h),
        _flow_line(ret_center, y1 + box_h, y2 - y1 - box_h),
        
        "<!-- OPEX eff to Operating costs -->",
        _flow_line(line_left, y2 + box_h, y4 - y2 - box_h),
        
        "<!-- Depreciation straight down to Capital costs -->",
        _flow_line(dep_center, y2 + box_h, y4 - y2 - box_h),
        
        "<!-- Return down to Quality (full length) -->",
        _flow_line(ret_center, y2 + box_h, y3 - y2 - box_h),
        
        "<!-- Return fork: horizontal branch at fork point, vertical into CAPEX eff -->",
        _flow_line_h(ret_fork_x, y_fork, ret_center - ret_fork_x),
        _flow_line(ret_fork_x, y_fork, y3 - y_fork),
        
        "<!-- Quality to Capital costs -->",
        _flow_line(ret_center, y3 + 58, y4 - y3 - 58),
        
        "<!-- Row 4 to Row 5-6 -->",
        _flow_line(col1 + 135, y4 + box_h, y5 - y4 - box_h),
        _flow_line(col3 + 135, y4 + box_h, y5 - y4 - box_h),
        _flow_line(290, y5 + box_h, y6 - y5 - box_h),
    ])
    
    return _wrap_html(boxes, lines, 555)


# =============================================================================
# HTML WRAPPER
# =============================================================================

def _wrap_html(boxes: str, lines: str, height: int) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<style>
{_SHARED_CSS}
.diagram {{
    width: 580px;
    margin: 0 auto;
    position: relative;
    height: {height}px;
}}
</style>
</head>
<body>
<div class="diagram">
{lines}
{boxes}
</div>
</body>
</html>"""