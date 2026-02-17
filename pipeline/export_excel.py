"""
frontend/utils/export_excel.py

Simplified export - dumps all available DataFrames from pipeline results.
User formats as needed in Excel.
"""

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime
from typing import Dict, Any
from io import BytesIO

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")


def create_case_export(
    user_reid: str,
    company_name: str,
    baseline_result,
    case_result,
    ui_config: Dict[str, Any]
) -> BytesIO:
    """Export all available DataFrames from pipeline results."""
    wb = Workbook()
    wb.remove(wb.active)

    _create_info_sheet(wb, user_reid, company_name, ui_config)
    _dump_pipeline_result(wb, case_result, prefix="case")
    _dump_pipeline_result(wb, baseline_result, prefix="bl")
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def get_export_filename(user_reid: str) -> str:
    """Generate filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"regumetrica_{user_reid}_{timestamp}.xlsx"


def _create_info_sheet(wb: Workbook, user_reid: str, company_name: str, ui_config: Dict):
    """Create metadata/info sheet."""
    ws = wb.create_sheet("Info")

    info_rows = [
        ("Company", f"{company_name} ({user_reid})"),
        ("Exported", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("", ""),
        ("Configuration", ""),
    ]
    
    for row_idx, (key, val) in enumerate(info_rows, 1):
        ws.cell(row=row_idx, column=1, value=key)
        ws.cell(row=row_idx, column=2, value=val)
    
    # Flatten ui_config
    row = len(info_rows) + 1
    for section, params in ui_config.items():
        if isinstance(params, dict):
            for key, val in params.items():
                ws.cell(row=row, column=1, value=f"{section}.{key}")
                ws.cell(row=row, column=2, value=_format_value(val))
                row += 1
        else:
            ws.cell(row=row, column=1, value=section)
            ws.cell(row=row, column=2, value=_format_value(params))
            row += 1
    
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 50


def _format_value(val) -> str:
    """Format value for display in info sheet."""
    if val is None:
        return ""
    if isinstance(val, dict):
        return str(val)
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    if isinstance(val, float):
        return f"{val:.6g}"
    return str(val)


def _dump_pipeline_result(wb: Workbook, result, prefix: str):
    """Recursively find and dump all DataFrames/Series in result."""
    if result is None:
        return
    
    if hasattr(result, '__dataclass_fields__'):
        for field in result.__dataclass_fields__:
            val = getattr(result, field, None)
            _dump_field(wb, val, f"{prefix}_{field}")
    elif hasattr(result, '__dict__'):
        for key, val in result.__dict__.items():
            if not key.startswith('_'):
                _dump_field(wb, val, f"{prefix}_{key}")
    elif isinstance(result, dict):
        for key, val in result.items():
            _dump_field(wb, val, f"{prefix}_{key}")


def _dump_field(wb: Workbook, val, name: str):
    """Dump a single field if it's a DataFrame, Series, or nested structure."""
    if val is None:
        return
    
    if isinstance(val, pd.DataFrame):
        if not val.empty:
            _create_df_sheet(wb, val, name)
    elif isinstance(val, pd.Series):
        _create_df_sheet(wb, val.to_frame().T, name)
    elif hasattr(val, '__dataclass_fields__') or isinstance(val, dict):
        _dump_pipeline_result(wb, val, name)


def _create_df_sheet(wb: Workbook, df: pd.DataFrame, name: str):
    """Create sheet from DataFrame."""
    sheet_name = _sanitize_sheet_name(name)
    
    # Handle duplicate names
    existing = [ws.title for ws in wb.worksheets]
    if sheet_name in existing:
        i = 2
        while f"{sheet_name[:28]}_{i}" in existing:
            i += 1
        sheet_name = f"{sheet_name[:28]}_{i}"
    
    ws = wb.create_sheet(sheet_name)
    _write_df(ws, df)


def _sanitize_sheet_name(name: str) -> str:
    """Sanitize name for Excel sheet (max 31 chars, no special chars)."""
    invalid = ['/', '\\', '?', '*', '[', ']', ':']
    for char in invalid:
        name = name.replace(char, '_')
    return name[:31]


def _write_df(ws, df: pd.DataFrame):
    """Write DataFrame to sheet with minimal formatting."""
    # Headers
    for col, header in enumerate(df.columns, 1):
        cell = ws.cell(row=1, column=col, value=str(header))
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center')
    
    # Data
    for row_idx, row_data in enumerate(df.itertuples(index=False), 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            
            if pd.isna(value):
                cell.value = None
            elif isinstance(value, (int, float)):
                cell.value = value
            else:
                cell.value = str(value)
    
    # Auto-width columns
    for col_idx, col_name in enumerate(df.columns, 1):
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        width = max(10, min(30, len(str(col_name)) + 2))
        ws.column_dimensions[col_letter].width = width