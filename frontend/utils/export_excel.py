"""
frontend/utils/export_excel.py

Export av case-resultat till Excel.
Skapar en fil med 4 flikar: Sammanfattning, Intäktsram, Effektivitet, Konfiguration.
"""

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING
from io import BytesIO

if TYPE_CHECKING:
    from pipeline.stages.stage_outputs import (
        ExtractionStageOutput,
        PreDeaStageOutput,
        DeaStageOutput,
        PostDeaStageOutput,
    )

# Styling
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
DELTA_POS_FILL = PatternFill("solid", fgColor="C6EFCE")
DELTA_NEG_FILL = PatternFill("solid", fgColor="FFC7CE")


class PipelineResultAdapter:
    """
    Adapter för att extrahera data från pipeline-resultat.
    Hanterar både objekt med attribut och dicts.
    """
    def __init__(self, result):
        self.result = result
    
    @property
    def extraction(self):
        return self._get_stage('extraction')
    
    @property
    def pre_dea(self):
        return self._get_stage('pre_dea')
    
    @property
    def dea(self):
        return self._get_stage('dea')
    
    @property
    def post_dea(self):
        return self._get_stage('post_dea')
    
    def _get_stage(self, name: str):
        if hasattr(self.result, name):
            return getattr(self.result, name)
        elif isinstance(self.result, dict):
            return self.result.get(name)
        return None


def create_case_export(
    user_reid: str,
    foretag: str,
    baseline_result,
    case_result,
    ui_config: Dict[str, Any]
) -> BytesIO:
    """
    Skapar Excel-export av case-resultat.
    
    Args:
        user_reid: Användarens REId
        foretag: Företagsnamn
        baseline_result: Baseline pipeline-resultat (objekt med .extraction, .pre_dea, etc.)
        case_result: Case pipeline-resultat (objekt med .extraction, .pre_dea, etc.)
        ui_config: UI-konfiguration (parametrar)
    
    Returns:
        BytesIO med Excel-fil redo för nedladdning
    """
    wb = Workbook()
    wb.remove(wb.active)
    
    # Wrap resultat för enhetlig åtkomst
    baseline = PipelineResultAdapter(baseline_result)
    case = PipelineResultAdapter(case_result)
    
    _create_summary_sheet(wb, user_reid, foretag, baseline, case)
    _create_intaktsram_sheet(wb, baseline, case)
    _create_efficiency_sheet(wb, baseline, case)
    _create_config_sheet(wb, ui_config, case)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return output


def get_export_filename(user_reid: str) -> str:
    """Genererar filnamn med timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"regumetrica_case_{user_reid}_{timestamp}.xlsx"


def _create_summary_sheet(
    wb: Workbook,
    user_reid: str,
    foretag: str,
    baseline: PipelineResultAdapter,
    case: PipelineResultAdapter
):
    """Skapar sammanfattningsflik med baseline vs case."""
    ws = wb.create_sheet("Sammanfattning")
    
    # Rubrik
    ws['A1'] = "Regumetrica - Case Resultat"
    ws['A1'].font = Font(bold=True, size=14)
    ws.merge_cells('A1:E1')
    
    ws['A3'] = "Företag:"
    ws['B3'] = f"{foretag} ({user_reid})"
    ws['A4'] = "Exportdatum:"
    ws['B4'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Metadata
    ws['A6'] = "Case metadata"
    ws['A6'].font = Font(bold=True)
    
    case_pre_dea = case.pre_dea
    case_dea = case.dea
    
    ws['A7'] = "CAPEX-metod:"
    ws['B7'] = _get_attr(case_pre_dea, 'capex_method', 'baseline')
    ws['A8'] = "DEA-metod:"
    ws['B8'] = _get_attr(case_dea, 'dea_method', 'baseline')
    ws['A9'] = "DEA körd:"
    ws['B9'] = "Ja" if _get_attr(case_dea, 'dea_executed', False) else "Nej"
    
    # Jämförelsetabell
    ws['A11'] = "Jämförelse: Baseline vs Case"
    ws['A11'].font = Font(bold=True)
    
    headers = ['Variabel', 'Baseline', 'Case', 'Delta', 'Delta %']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=12, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center')
    
    # Hämta intäktsram-data
    baseline_ir = _get_attr(baseline.post_dea, 'user_intaktsram', None)
    case_ir = _get_attr(case.post_dea, 'user_intaktsram', None)
    baseline_effkrav = _get_attr(baseline.post_dea, 'user_effkrav_proc', 0)
    case_effkrav = _get_attr(case.post_dea, 'user_effkrav_proc', 0)
    
    # Data-rader
    comparison_data = [
        ('Kapitalkostnad_Total', 'tkr'),
        ('Paverkbara_Periodsumma', 'tkr'),
        ('Opaverkbara_Kostnader', 'tkr'),
        ('Intaktsram_Total', 'tkr'),
    ]
    
    row = 13
    for key, unit in comparison_data:
        baseline_val = _get_series_value(baseline_ir, key)
        case_val = _get_series_value(case_ir, key)
        delta, delta_pct = _calc_delta(baseline_val, case_val)
        
        ws.cell(row=row, column=1, value=f"{key} ({unit})")
        ws.cell(row=row, column=2, value=baseline_val).number_format = '#,##0'
        ws.cell(row=row, column=3, value=case_val).number_format = '#,##0'
        
        delta_cell = ws.cell(row=row, column=4, value=delta)
        delta_cell.number_format = '#,##0'
        if delta and delta > 0:
            delta_cell.fill = DELTA_POS_FILL
        elif delta and delta < 0:
            delta_cell.fill = DELTA_NEG_FILL
        
        pct_cell = ws.cell(row=row, column=5, value=delta_pct)
        pct_cell.number_format = '0.00%'
        
        row += 1
    
    # Effektivitetskrav
    ws.cell(row=row, column=1, value="Effkrav_proc")
    ws.cell(row=row, column=2, value=baseline_effkrav).number_format = '0.00%'
    ws.cell(row=row, column=3, value=case_effkrav).number_format = '0.00%'
    delta_effkrav = case_effkrav - baseline_effkrav if baseline_effkrav and case_effkrav else None
    ws.cell(row=row, column=4, value=delta_effkrav).number_format = '0.00%'
    
    # Kolumnbredder
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 12


def _create_intaktsram_sheet(
    wb: Workbook, 
    baseline: PipelineResultAdapter, 
    case: PipelineResultAdapter
):
    """Skapar intäktsram-flik med alla företag."""
    ws = wb.create_sheet("Intäktsram")
    
    baseline_df = _get_attr(baseline.post_dea, 'all_intaktsram', None)
    case_df = _get_attr(case.post_dea, 'all_intaktsram', None)
    
    if baseline_df is None or case_df is None:
        ws['A1'] = "Data saknas"
        return
    
    if not isinstance(baseline_df, pd.DataFrame) or not isinstance(case_df, pd.DataFrame):
        ws['A1'] = "Data är inte DataFrame"
        return
    
    baseline_df = baseline_df.copy()
    case_df = case_df.copy()
    
    # Filtrera till REL-företag
    if 'REId' in baseline_df.columns:
        baseline_df = baseline_df[baseline_df['REId'].str.startswith('REL', na=False)].copy()
    if 'REId' in case_df.columns:
        case_df = case_df[case_df['REId'].str.startswith('REL', na=False)].copy()
    
    # Välj kolumner
    keep_cols = ['REId', 'Kapitalkostnad_Total', 'Paverkbara_Periodsumma', 
                 'Opaverkbara_Kostnader', 'Intaktsram_Total']
    
    baseline_cols = [c for c in keep_cols if c in baseline_df.columns]
    case_cols = [c for c in keep_cols if c in case_df.columns]
    
    if not baseline_cols or not case_cols:
        ws['A1'] = "Kolumner saknas"
        return
    
    baseline_df = baseline_df[baseline_cols].copy()
    case_df = case_df[case_cols].copy()
    
    # Merge
    merged = baseline_df.merge(
        case_df, 
        on='REId', 
        suffixes=('_Baseline', '_Case'),
        how='outer'
    )
    
    # Beräkna delta för Intäktsram
    if 'Intaktsram_Total_Baseline' in merged.columns and 'Intaktsram_Total_Case' in merged.columns:
        merged['Delta'] = merged['Intaktsram_Total_Case'] - merged['Intaktsram_Total_Baseline']
        merged['Delta%'] = merged['Delta'] / merged['Intaktsram_Total_Baseline']
    
    _write_dataframe_to_sheet(ws, merged)


def _create_efficiency_sheet(
    wb: Workbook,
    baseline: PipelineResultAdapter,
    case: PipelineResultAdapter
):
    """Skapar effektivitetsflik med DEA-resultat."""
    ws = wb.create_sheet("Effektivitet")
    
    baseline_effkrav = _get_attr(baseline.post_dea, 'all_effkrav', None)
    case_effkrav = _get_attr(case.post_dea, 'all_effkrav', None)
    
    if baseline_effkrav is None or case_effkrav is None:
        ws['A1'] = "Effektivitetsdata saknas"
        return
    
    if not isinstance(baseline_effkrav, pd.DataFrame) or not isinstance(case_effkrav, pd.DataFrame):
        ws['A1'] = "Data är inte DataFrame"
        return
    
    baseline_effkrav = baseline_effkrav.copy()
    case_effkrav = case_effkrav.copy()
    
    # Filtrera till REL-företag
    if 'REId' in baseline_effkrav.columns:
        baseline_effkrav = baseline_effkrav[baseline_effkrav['REId'].str.startswith('REL', na=False)].copy()
    if 'REId' in case_effkrav.columns:
        case_effkrav = case_effkrav[case_effkrav['REId'].str.startswith('REL', na=False)].copy()
    
    # Välj kolumner
    keep_cols = ['REId', 'Effektivitet', 'Potential', 'Effkrav_arlig', 'is_outlier']
    baseline_cols = [c for c in keep_cols if c in baseline_effkrav.columns]
    case_cols = [c for c in keep_cols if c in case_effkrav.columns]
    
    if not baseline_cols or not case_cols:
        ws['A1'] = "Kolumner saknas"
        return
    
    baseline_effkrav = baseline_effkrav[baseline_cols].copy()
    case_effkrav = case_effkrav[case_cols].copy()
    
    # Merge
    merged = baseline_effkrav.merge(
        case_effkrav,
        on='REId',
        suffixes=('_Baseline', '_Case'),
        how='outer'
    )
    
    _write_dataframe_to_sheet(ws, merged)


def _create_config_sheet(
    wb: Workbook, 
    ui_config: Dict, 
    case: PipelineResultAdapter
):
    """Skapar konfigurationsflik med alla parametrar."""
    ws = wb.create_sheet("Konfiguration")
    
    ws['A1'] = "Case Konfiguration"
    ws['A1'].font = Font(bold=True, size=14)
    
    row = 3
    
    # M1: Normvärden
    ws.cell(row=row, column=1, value="M1: Regulatory Asset Base").font = Font(bold=True)
    row += 1
    m1 = ui_config.get('m1_asset_base', {})
    normvalue_adj = m1.get('normvalue_adjustments')
    if normvalue_adj:
        ws.cell(row=row, column=1, value="Nivå:")
        ws.cell(row=row, column=2, value=m1.get('normvalue_level', 'cat'))
        row += 1
        for cat, mult in normvalue_adj.items():
            pct = (float(mult) - 1) * 100
            ws.cell(row=row, column=1, value=f"Kategori {cat}:")
            ws.cell(row=row, column=2, value=f"{pct:+.0f}%")
            row += 1
    else:
        ws.cell(row=row, column=1, value="Inga ändringar (baseline)")
        row += 1
    
    row += 1
    
    # M2: Livslängder
    ws.cell(row=row, column=1, value="M2: Depreciation").font = Font(bold=True)
    row += 1
    m2 = ui_config.get('m2_depreciation', {})
    lifetime_adj = m2.get('lifetime_adjustments')
    if lifetime_adj:
        ws.cell(row=row, column=1, value="Nivå:")
        ws.cell(row=row, column=2, value=m2.get('lifetime_level', 'cat'))
        row += 1
        for cat, vals in lifetime_adj.items():
            changes = ', '.join([f"{k}={v}" for k, v in vals.items()])
            ws.cell(row=row, column=1, value=f"Kategori {cat}:")
            ws.cell(row=row, column=2, value=changes)
            row += 1
    else:
        ws.cell(row=row, column=1, value="Inga ändringar (baseline)")
        row += 1
    
    row += 1
    
    # M3: WACC
    ws.cell(row=row, column=1, value="M3: Cost of Capital").font = Font(bold=True)
    row += 1
    m3 = ui_config.get('m3_cost_of_capital', {})
    wacc = m3.get('wacc_override')
    if wacc:
        ws.cell(row=row, column=1, value="WACC (3.2.5):")
        ws.cell(row=row, column=2, value=wacc).number_format = '0.00%'
    else:
        ws.cell(row=row, column=1, value="WACC (3.2.5):")
        ws.cell(row=row, column=2, value="Baseline (4.53%)")
    row += 2
    
    # M3: Quality Adjustments (Incitament)
    ws.cell(row=row, column=1, value="M3: Quality Adjustments (3.3-3.6)").font = Font(bold=True)
    row += 1
    m3q = ui_config.get('m3_quality_adjustments', {})
    
    # Baseline-värden för incitament
    BASELINE_INC = {
        'kpi': 17.0,
        'k_nf': 0.50,
        'sharing_netloss': 0.5,
        'adj_max_agg': 1/3,
        'adj_max_cemi4': 1/3,
    }
    
    # 3.3.1 KPI
    val = m3q.get('kpi')
    ws.cell(row=row, column=1, value="Kvalitetsprisindex (3.3.1):")
    if val is not None:
        ws.cell(row=row, column=2, value=f"{val} kr/kW")
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_INC['kpi']} kr/kW)")
    row += 1
    
    # 3.4.1 K_NF
    val = m3q.get('k_nf')
    ws.cell(row=row, column=1, value="Nätförlustkostnad (3.4.1):")
    if val is not None:
        ws.cell(row=row, column=2, value=f"{val} kr/kWh")
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_INC['k_nf']} kr/kWh)")
    row += 1
    
    # 3.4.2 Delning nätförlust
    val = m3q.get('sharing_netloss')
    ws.cell(row=row, column=1, value="Delning nätförlust (3.4.2):")
    if val is not None:
        ws.cell(row=row, column=2, value=val).number_format = '0.00'
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_INC['sharing_netloss']})")
    row += 1
    
    # 3.5.1 Max aggregerat
    val = m3q.get('adj_max_agg')
    ws.cell(row=row, column=1, value="Max agg. incitament (3.5.1):")
    if val is not None:
        ws.cell(row=row, column=2, value=val).number_format = '0.000'
    else:
        ws.cell(row=row, column=2, value=f"Baseline (1/3)")
    row += 1
    
    # 3.5.2 Max per delincitament
    val = m3q.get('adj_max_cemi4')
    ws.cell(row=row, column=1, value="Max per delincitament (3.5.2):")
    if val is not None:
        ws.cell(row=row, column=2, value=val).number_format = '0.000'
    else:
        ws.cell(row=row, column=2, value=f"Baseline (1/3)")
    row += 1
    
    # Aktiverade incitament
    enable_quality = m3q.get('enable_quality', True)
    enable_netloss = m3q.get('enable_netloss', True)
    enable_load = m3q.get('enable_load', True)
    
    ws.cell(row=row, column=1, value="Kvalitetsincitament (3.6.1):")
    ws.cell(row=row, column=2, value="Aktiverat" if enable_quality else "Inaktiverat")
    row += 1
    
    ws.cell(row=row, column=1, value="Nätförlustincitament (3.6.2):")
    ws.cell(row=row, column=2, value="Aktiverat" if enable_netloss else "Inaktiverat")
    row += 1
    
    ws.cell(row=row, column=1, value="Belastningsincitament (3.6.3):")
    ws.cell(row=row, column=2, value="Aktiverat" if enable_load else "Inaktiverat")
    row += 2
    
    # M4: Operating Expenditures
    ws.cell(row=row, column=1, value="M4: Operating Expenditures").font = Font(bold=True)
    row += 1
    m4 = ui_config.get('m4_operating_exp', {})
    paverkbara_method = m4.get('paverkbara_method', 'OPEX')
    ws.cell(row=row, column=1, value="Påverkbara metod (5.4.1):")
    ws.cell(row=row, column=2, value=paverkbara_method)
    row += 2
    
    # M5: Efficiency Incentive
    ws.cell(row=row, column=1, value="M5: Efficiency Incentive").font = Font(bold=True)
    row += 1
    m5 = ui_config.get('m5_efficiency', {})
    
    # Baseline-värden för jämförelse
    BASELINE_M5 = {
        'trunkering_max': 0.30,
        'trunkering_min': 0.162416,
        'outlier_krav': 0.01,
        'kunddelning': 0.50,
        'realiseringstid': 8,
        'tillsynsperiod': 4,
    }
    
    # 5.2.1 Max potential
    val = m5.get('trunkering_max')
    ws.cell(row=row, column=1, value="Max potential (5.2.1):")
    if val is not None:
        ws.cell(row=row, column=2, value=val).number_format = '0.00%'
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_M5['trunkering_max']:.0%})")
    row += 1
    
    # 5.2.2 Min potential trunkering
    val = m5.get('trunkering_min')
    ws.cell(row=row, column=1, value="Min potential trunkering (5.2.2):")
    if val is not None:
        ws.cell(row=row, column=2, value=val).number_format = '0.00%'
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_M5['trunkering_min']:.2%})")
    row += 1
    
    # 5.2.3 Realiseringstid
    val = m5.get('realiseringstid')
    ws.cell(row=row, column=1, value="Realiseringstid (5.2.3):")
    if val is not None:
        ws.cell(row=row, column=2, value=f"{val} år")
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_M5['realiseringstid']} år)")
    row += 1
    
    # 5.2.4 Kunddelning
    val = m5.get('kunddelning')
    ws.cell(row=row, column=1, value="Kunddelning (5.2.4):")
    if val is not None:
        ws.cell(row=row, column=2, value=val).number_format = '0%'
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_M5['kunddelning']:.0%})")
    row += 1
    
    # 5.2.5 Tillsynsperiod
    val = m5.get('tillsynsperiod')
    ws.cell(row=row, column=1, value="Tillsynsperiod (5.2.5):")
    if val is not None:
        ws.cell(row=row, column=2, value=f"{val} år")
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_M5['tillsynsperiod']} år)")
    row += 1
    
    # 5.3.1 Outlier-krav
    val = m5.get('outlier_krav')
    ws.cell(row=row, column=1, value="Outlier-krav (5.3.1):")
    if val is not None:
        ws.cell(row=row, column=2, value=val).number_format = '0.00%'
    else:
        ws.cell(row=row, column=2, value=f"Baseline ({BASELINE_M5['outlier_krav']:.0%})")
    row += 2
    
    # DEA info (Add-on: Benchmarking)
    ws.cell(row=row, column=1, value="Add-on: Benchmarking (DEA)").font = Font(bold=True)
    row += 1
    case_dea = case.dea
    addon = ui_config.get('addon_benchmarking', {})
    
    ws.cell(row=row, column=1, value="Metod:")
    ws.cell(row=row, column=2, value=_get_attr(case_dea, 'dea_method', 'baseline'))
    row += 1
    
    ws.cell(row=row, column=1, value="DEA körd:")
    ws.cell(row=row, column=2, value="Ja" if _get_attr(case_dea, 'dea_executed', False) else "Nej")
    row += 1
    
    if addon.get('dea_method') == 'custom':
        ws.cell(row=row, column=1, value="Inputs:")
        ws.cell(row=row, column=2, value=', '.join(addon.get('dea_inputs', [])))
        row += 1
        ws.cell(row=row, column=1, value="Outputs:")
        ws.cell(row=row, column=2, value=', '.join(addon.get('dea_outputs', [])))
        row += 1
        ws.cell(row=row, column=1, value="RTS:")
        ws.cell(row=row, column=2, value=addon.get('dea_rts', 'crs').upper())
        row += 1
        ws.cell(row=row, column=1, value="Outlier multiplier (5.1.1):")
        ws.cell(row=row, column=2, value=addon.get('dea_multiplier', 2.0))
    
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 35


def _write_dataframe_to_sheet(ws, df: pd.DataFrame):
    """Skriver DataFrame till worksheet med formatering."""
    for col, header in enumerate(df.columns, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center')
    
    for row_idx, row_data in enumerate(df.itertuples(index=False), 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            col_name = df.columns[col_idx - 1]
            if 'Delta%' in col_name or 'Effkrav' in col_name or 'Effektivitet' in col_name or 'Potential' in col_name:
                cell.number_format = '0.00%'
            elif any(x in col_name for x in ['Kapitalkostnad', 'Intäktsram', 'Påverkbara', 'Opåverkbara', 'Delta']):
                cell.number_format = '#,##0'
    
    for col_idx, col_name in enumerate(df.columns, 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = max(12, len(str(col_name)) + 2)


def _get_attr(obj, name: str, default=None):
    """Hämtar attribut från objekt eller dict."""
    if obj is None:
        return default
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def _get_series_value(series, key: str):
    """Hämtar värde från pandas Series eller dict."""
    if series is None:
        return None
    if isinstance(series, pd.Series):
        return series.get(key) if key in series.index else None
    if isinstance(series, dict):
        return series.get(key)
    if hasattr(series, key):
        return getattr(series, key)
    return None


def _calc_delta(baseline, case):
    """Beräknar delta och delta%."""
    if baseline is None or case is None:
        return None, None
    try:
        baseline = float(baseline)
        case = float(case)
        delta = case - baseline
        delta_pct = delta / baseline if baseline != 0 else None
        return delta, delta_pct
    except (ValueError, TypeError):
        return None, None