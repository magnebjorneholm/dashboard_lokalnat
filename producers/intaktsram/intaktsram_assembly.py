"""
Intäktsram assembly producer
Sammanställer total intäktsram från alla komponenter
"""

import pandas as pd
import numpy as np
import math
from typing import Dict, Any, Tuple, Optional
import warnings


def excel_half_up_round(x: float) -> int:
    """Excel-exakt half-up avrundning"""
    return int(math.floor(float(x) + 0.5))


def calculate_paverkbara_with_effkrav(
    effkrav_data: pd.DataFrame,
    ir_baseline: pd.DataFrame,
    capex_data: pd.DataFrame,
    method: str = 'OPEX'
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Beräknar påverkbara kostnader med effektiviseringskrav.
    
    Implementerar Ei:s Excel-exakta metod med stöd för både OPEX och TOTEX.
    
    Args:
        effkrav_data: DataFrame med Effkrav_proc från effektiviseringskrav producer
        ir_baseline: DataFrame med baseline-data (B_raw, Adj, e_base)
        capex_data: DataFrame med Kapitalkostnad_Total per REId
        method: 'OPEX' (traditionell) eller 'TOTEX' (inkl. CAPEX)
        
    Returns:
        Tuple med (export_data, metadata)
    """
    if method not in ['OPEX', 'TOTEX']:
        raise ValueError(f"Method måste vara 'OPEX' eller 'TOTEX', fick '{method}'")
    
    required_effkrav_cols = ['REId', 'Effkrav_proc']
    missing_cols = [col for col in required_effkrav_cols if col not in effkrav_data.columns]
    if missing_cols:
        raise ValueError(f"Saknade kolumner i effkrav_data: {missing_cols}")
    
    required_baseline_cols = ['REId', 'B_raw', 'e_base']
    missing_cols = [col for col in required_baseline_cols if col not in ir_baseline.columns]
    if missing_cols:
        raise ValueError(f"Saknade kolumner i ir_baseline: {missing_cols}")
    
    export_data = ir_baseline.merge(
        effkrav_data[['REId', 'Effkrav_proc']], 
        on='REId', 
        how='inner'
    )
    
    if method == 'TOTEX':
        required_capex_cols = ['REId', 'Kapitalkostnad_Total']
        missing_cols = [col for col in required_capex_cols if col not in capex_data.columns]
        if missing_cols:
            raise ValueError(f"Saknade kolumner i capex_data: {missing_cols}")
        
        export_data = export_data.merge(
            capex_data[['REId', 'Kapitalkostnad_Total']], 
            on='REId', 
            how='left'
        )
        
        export_data['Kapitalkostnad_Total'] = export_data['Kapitalkostnad_Total'].fillna(0)
    
    complete_mask = export_data[['B_raw', 'e_base']].notna().all(axis=1)
    n_incomplete = (~complete_mask).sum()
    
    if n_incomplete > 0:
        warnings.warn(f"{n_incomplete} REId saknar baseline-data och exkluderas")
    
    export_data = export_data[complete_mask].copy()
    if export_data.empty:
        raise ValueError("Ingen REId har komplett baseline-data")
    
    DT_opex = export_data['B_raw'].astype(np.float64)
    DU_opex = export_data.get('Adj', 0).astype(np.float64).fillna(0.0)
    e_base = export_data['e_base'].astype(np.float64)
    e_scn = export_data['Effkrav_proc'].astype(np.float64)
    
    Delta_opex = DU_opex / 4.0
    
    if method == 'OPEX':
        DT = DT_opex
        Delta = Delta_opex
        B = DT + Delta
        
    elif method == 'TOTEX':
        CAPEX_periodsumma = export_data['Kapitalkostnad_Total'].astype(np.float64)
        B_capex = CAPEX_periodsumma / 4.0
        
        DT = DT_opex + B_capex
        Delta = Delta_opex
        B = DT + Delta
        
        export_data['CAPEX_periodsumma'] = CAPEX_periodsumma
        export_data['CAPEX_arsbas'] = B_capex
    
    def calculate_yearly_values(DT_series, DU_series, e_series):
        """Beräknar årsvärden med Excel-exakt precision"""
        results = []
        
        for dt, du, e in zip(DT_series, DU_series, e_series):
            delta = du / 4.0
            b = dt + delta
            
            yearly = []
            inc = []
            avdrag = []
            
            for t in range(4):
                inc_t = b * ((1 - e) ** t)
                avdrag_t = b * ((1 - e) ** (t + 1))
                year_t = excel_half_up_round(inc_t - avdrag_t)
                
                yearly.append(year_t)
                inc.append(inc_t)
                avdrag.append(avdrag_t)
            
            results.append({
                'years': yearly,
                'total': sum(yearly),
                'inc': inc,
                'avdrag': avdrag
            })
        
        return results
    
    scn_results = calculate_yearly_values(DT, DU_opex, e_scn)
    base_results = calculate_yearly_values(DT, DU_opex, e_base)
    
    y2024_scn = np.array([r['years'][0] for r in scn_results])
    y2025_scn = np.array([r['years'][1] for r in scn_results])
    y2026_scn = np.array([r['years'][2] for r in scn_results])
    y2027_scn = np.array([r['years'][3] for r in scn_results])
    total_4yr_scn = np.array([r['total'] for r in scn_results])
    
    y2024_base = np.array([r['years'][0] for r in base_results])
    y2025_base = np.array([r['years'][1] for r in base_results])
    y2026_base = np.array([r['years'][2] for r in base_results])
    y2027_base = np.array([r['years'][3] for r in base_results])
    total_4yr_base = np.array([r['total'] for r in base_results])
    
    export_data['Paverkbara_Baseline_4yr'] = total_4yr_base
    export_data['Paverkbara_Target'] = total_4yr_scn
    export_data['Total_Reduction_tkr'] = total_4yr_base - total_4yr_scn
    export_data['Effektiviseringskrav'] = e_scn
    export_data['Method'] = method
    
    export_data['Y2024_scenario'] = y2024_scn
    export_data['Y2025_scenario'] = y2025_scn
    export_data['Y2026_scenario'] = y2026_scn
    export_data['Y2027_scenario'] = y2027_scn
    
    export_data['Y2024_baseline'] = y2024_base
    export_data['Y2025_baseline'] = y2025_base
    export_data['Y2026_baseline'] = y2026_base
    export_data['Y2027_baseline'] = y2027_base
    
    metadata = {
        'n_companies': len(export_data),
        'n_excluded': n_incomplete,
        'method': method,
        'total_baseline_tkr': float(export_data['Paverkbara_Baseline_4yr'].sum()),
        'total_target_tkr': float(export_data['Paverkbara_Target'].sum()),
        'total_reduction_tkr': float(export_data['Total_Reduction_tkr'].sum()),
        'mean_effkrav_pct': float(export_data['Effektiviseringskrav'].mean() * 100)
    }
    
    if method == 'TOTEX':
        metadata['mean_capex_arsbas_tkr'] = float(export_data['CAPEX_arsbas'].mean())
        metadata['total_capex_period_tkr'] = float(export_data['CAPEX_periodsumma'].sum())
    
    return export_data, metadata


def assemble_intaktsram(
    capex_data: pd.DataFrame,
    opex_data: pd.DataFrame,
    volumes_data: pd.DataFrame,
    efficiency_result: Optional[Dict[str, Any]] = None,
    quality_data: Optional[pd.DataFrame] = None,
    effkrav_method: str = 'OPEX'
) -> Dict[str, Any]:
    """
    Producer för sammanställning av total intäktsram.
    
    Args:
        capex_data: DataFrame med Kapitalkostnad_Total per REId
        opex_data: DataFrame med opåverkbara och påverkbara baseline per REId
        volumes_data: DataFrame med volymer per REId
        efficiency_result: Dict från produce_effektiviseringskrav (optional)
        quality_data: DataFrame med kvalitetsjustering (optional)
        effkrav_method: 'OPEX' eller 'TOTEX'
        
    Returns:
        Dict med:
            - data: DataFrame med total intäktsram breakdown per REId
            - metadata: Dict med aggregerad information
    """
    required_capex_cols = ['REId', 'Kapitalkostnad_Total']
    missing_cols = [col for col in required_capex_cols if col not in capex_data.columns]
    if missing_cols:
        raise ValueError(f"Saknade kolumner i capex_data: {missing_cols}")
    
    required_opex_cols = ['REId', 'Opaverkbara_Kostnader']
    missing_cols = [col for col in required_opex_cols if col not in opex_data.columns]
    if missing_cols:
        raise ValueError(f"Saknade kolumner i opex_data: {missing_cols}")
    
    result_df = capex_data[['REId', 'Kapitalkostnad_Total']].copy()
    
    result_df = result_df.merge(
        opex_data[['REId', 'Opaverkbara_Kostnader']], 
        on='REId', 
        how='left'
    )
    
    result_df['Opaverkbara_Kostnader'] = result_df['Opaverkbara_Kostnader'].fillna(0)
    
    if efficiency_result is not None:
        effkrav_data = efficiency_result['data']
        ir_baseline = opex_data[['REId', 'B_raw', 'Adj', 'e_base']].copy()
        
        paverkbara_data, pav_metadata = calculate_paverkbara_with_effkrav(
            effkrav_data=effkrav_data,
            ir_baseline=ir_baseline,
            capex_data=capex_data,
            method=effkrav_method
        )
        
        result_df = result_df.merge(
            paverkbara_data[['REId', 'Paverkbara_Target', 'Total_Reduction_tkr']], 
            on='REId', 
            how='left'
        )
        
        result_df['Paverkbara_Kostnader'] = result_df['Paverkbara_Target'].fillna(0)
        result_df['Effektiviseringskrav_tkr'] = result_df['Total_Reduction_tkr'].fillna(0)
        
    else:
        paverkbara_baseline = opex_data.get('Paverkbara_Baseline', 0)
        result_df['Paverkbara_Kostnader'] = paverkbara_baseline
        result_df['Effektiviseringskrav_tkr'] = 0
        pav_metadata = {'method': 'baseline', 'n_companies': 0}
    
    if quality_data is not None and 'Kvalitetsjustering' in quality_data.columns:
        result_df = result_df.merge(
            quality_data[['REId', 'Kvalitetsjustering']], 
            on='REId', 
            how='left'
        )
        result_df['Kvalitetsjustering'] = result_df['Kvalitetsjustering'].fillna(0)
    else:
        result_df['Kvalitetsjustering'] = 0
    
    result_df['Intaktsram_Total'] = (
        result_df['Kapitalkostnad_Total'] +
        result_df['Opaverkbara_Kostnader'] +
        result_df['Paverkbara_Kostnader'] +
        result_df['Kvalitetsjustering']
    )
    
    metadata = {
        'source': 'assembled',
        'method': effkrav_method,
        'n_companies': len(result_df),
        'total_kapitalkostnad_tkr': float(result_df['Kapitalkostnad_Total'].sum()),
        'total_opaverkbara_tkr': float(result_df['Opaverkbara_Kostnader'].sum()),
        'total_paverkbara_tkr': float(result_df['Paverkbara_Kostnader'].sum()),
        'total_effektiviseringskrav_tkr': float(result_df['Effektiviseringskrav_tkr'].sum()),
        'total_kvalitetsjustering_tkr': float(result_df['Kvalitetsjustering'].sum()),
        'total_intaktsram_tkr': float(result_df['Intaktsram_Total'].sum()),
        'has_efficiency': efficiency_result is not None,
        'has_quality': quality_data is not None
    }
    
    if efficiency_result is not None:
        metadata['paverkbara_metadata'] = pav_metadata
        metadata['efficiency_metadata'] = efficiency_result.get('metadata', {})
    
    return {
        'data': result_df,
        'metadata': metadata
    }