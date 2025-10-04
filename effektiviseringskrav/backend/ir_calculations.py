"""
Backend för IR-påverkbara kostnader beräkningar.
==================================================

Ren beräkningslogik utan UI-beroenden.
Implementerar Ei:s Excel-exakta metod för beräkning av påverkbara kostnader.

DESIGN:
- Tar DataFrames som input, returnerar DataFrames som output
- Inga Streamlit/Dash imports
- Alla fel kastas som exceptions (UI hanterar dem)
- Loggning via warnings eller return-värden, inte st.error()
"""

from pathlib import Path
from typing import Optional, Tuple
import math
import pandas as pd
import numpy as np
import warnings


def excel_half_up_round(x: float) -> int:
    """
    Excel-exakt half-up avrundning.
    
    Args:
        x: Värde att avrunda
        
    Returns:
        Avrundat heltal enligt Excel-standard
        
    Examples:
        >>> excel_half_up_round(2.5)
        3
        >>> excel_half_up_round(2.4)
        2
    """
    return int(math.floor(float(x) + 0.5))


def load_ir_paverkbara_baseline(filepath: str) -> pd.DataFrame:
    """
    Läser baseline-data från 'Påverkbara' arket för korrekt IR-beräkning.
    Använder exakta kolumnpositioner enligt användarspecifikation.
    
    Args:
        filepath: Sökväg till Excel-fil med Påverkbara-ark
        
    Returns:
        DataFrame med kolumner:
            - REId: Redovisningsenhet ID
            - B_raw: Bas för procentberäkning (tkr)
            - Adj: Neonandringar / justeringar (tkr)
            - e_base: Baseline effektiviseringskrav (decimal)
            - mu_factor: Mu-faktor (optional)
            - y2024_excel: Excel-beräknat värde 2024 (för validering)
            - y2025_excel: Excel-beräknat värde 2025 (för validering)
            - y2026_excel: Excel-beräknat värde 2026 (för validering)
            - y2027_excel: Excel-beräknat värde 2027 (för validering)
            - total_excel: Excel-beräknad totalsumma (för validering)
    
    Raises:
        FileNotFoundError: Om fil inte hittas
        ValueError: Om kolumner saknas eller data är ogiltig
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(f"IR baseline-fil hittades inte: {filepath}")
    
    try:
        df_pav = pd.read_excel(filepath, sheet_name="Påverkbara", 
                              header=1, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Kunde inte läsa 'Påverkbara'-arket: {e}")
    
    if df_pav.empty:
        raise ValueError("Påverkbara-arket är tomt")

    def excel_col_to_index(col_str: str) -> int:
        """Konverterar Excel-kolumnnamn (t.ex. 'DT') till 0-baserat index"""
        result = 0
        for char in col_str:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1

    # Kolumnpositioner enligt korrigerad metod
    col_positions = {
        'REId': 'A',
        'B_raw': 'DT',
        'Adj': 'DU',
        'e_base': 'EG',
        'mu_factor': 'EF',
        'y2024_excel': 'EA',
        'y2025_excel': 'EB',
        'y2026_excel': 'EC',
        'y2027_excel': 'ED',
        'total_excel': 'EE'
    }
    
    col_indices = {field: excel_col_to_index(col) for field, col in col_positions.items()}
    
    max_col_index = max(col_indices.values())
    if len(df_pav.columns) <= max_col_index:
        raise ValueError(
            f"Excel-filen har endast {len(df_pav.columns)} kolumner, "
            f"behöver minst {max_col_index + 1}"
        )

    # Bygg DataFrame med våra kolumnnamn
    df_out = pd.DataFrame()
    
    for field, col_index in col_indices.items():
        if col_index < len(df_pav.columns):
            df_out[field] = df_pav.iloc[:, col_index]
        else:
            if field in ['REId', 'B_raw', 'e_base']:
                df_out[field] = pd.Series([np.nan] * len(df_pav))

    if 'REId' not in df_out.columns or df_out['REId'].isna().all():
        raise ValueError("REId-kolumn hittades inte på position A eller är tom")

    # Typning och rensning för numeriska kolumner
    numeric_cols = ['B_raw', 'Adj', 'e_base', 'y2024_excel', 'y2025_excel', 
                   'y2026_excel', 'y2027_excel', 'total_excel', 'mu_factor']
    
    for col in numeric_cols:
        if col in df_out.columns:
            df_out[col] = pd.to_numeric(df_out[col], errors='coerce')

    if 'Adj' not in df_out.columns:
        df_out['Adj'] = 0.0
    else:
        df_out['Adj'] = df_out['Adj'].fillna(0.0)

    # Filtrera till giltiga REId
    df_out = df_out.dropna(subset=['REId'])
    df_out = df_out[df_out['REId'].astype(str).str.startswith('REL')].reset_index(drop=True)

    # Varning för saknade kritiska värden
    critical_missing = df_out[['B_raw', 'e_base']].isna().any(axis=1).sum()
    if critical_missing > 0:
        warnings.warn(
            f"{critical_missing} REId saknar kritiska baseline-värden (B_raw eller e_base)",
            UserWarning
        )
    
    return df_out


def calculate_ir_paverkbara_export(
    dea_result: pd.DataFrame, 
    ir_baseline: pd.DataFrame
) -> Tuple[pd.DataFrame, dict]:
    """
    Beräknar påverkbara kostnader med Excel-exakt precision.
    
    Implementerar Ei:s metod:
    1. Behåller fullständig precision genom hela beräkningen
    2. Avrundar endast slutresultatet för varje år
    3. Använder exakta värden från Excel, inte föravrundade
    
    Args:
        dea_result: DataFrame med DEA-resultat, måste innehålla:
            - DMU
            - REId
            - Effkrav_proc (årligt effektiviseringskrav som decimal)
            - Företag (optional, för metadata)
        ir_baseline: DataFrame från load_ir_paverkbara_baseline()
        
    Returns:
        Tuple med:
        - export_data: DataFrame med beräknade påverkbara kostnader
        - metadata: Dict med sammanfattning och diagnostik
        
    Raises:
        ValueError: Om obligatoriska kolumner saknas
    """
    # Robust kolumnhantering för DEA-resultat
    available_cols = list(dea_result.columns)
    
    # Leta efter företagskolumn
    foretag_col = None
    for col in available_cols:
        if any(variant in col.lower() for variant in ['företag', 'foretag', 'företag', 'fö¶retag']):
            foretag_col = col
            break
    
    required_cols = ['DMU', 'REId', 'Effkrav_proc']
    if foretag_col:
        required_cols.append(foretag_col)
    
    # Kontrollera kolumner
    missing_cols = [col for col in required_cols if col not in available_cols]
    if missing_cols:
        raise ValueError(f"DEA-resultat saknar kolumner: {missing_cols}")
    
    # Skapa export-data
    export_data = dea_result[required_cols].copy()
    if foretag_col and foretag_col != 'Företag':
        export_data = export_data.rename(columns={foretag_col: 'Företag'})
    
    # Merge med IR baseline
    export_data = export_data.merge(ir_baseline, on='REId', how='left')
    
    # Filtrera till kompletta data
    required_baseline_cols = ['B_raw', 'e_base']
    complete_mask = export_data[required_baseline_cols].notna().all(axis=1)
    
    n_incomplete = (~complete_mask).sum()
    if n_incomplete > 0:
        warnings.warn(f"{n_incomplete} REId saknar baseline-data och exkluderas")
    
    export_data = export_data[complete_mask].copy()
    if export_data.empty:
        raise ValueError("Ingen REId har komplett baseline-data")
    
    # Konvertera till float64 för maximal precision
    DT = export_data['B_raw'].astype(np.float64)
    DU = export_data.get('Adj', 0).astype(np.float64).fillna(0.0)
    e_base = export_data['e_base'].astype(np.float64)
    e_scn = export_data['Effkrav_proc'].astype(np.float64)
    
    # Årlig fördelning av NeonAndringar med full precision
    Delta = DU / 4.0
    
    # Bas för procentberäkning med full precision
    B = DT + Delta
    
    def calculate_exact_yearly_values(DT_series, DU_series, e_series):
        """Beräknar årsvärden med Excel-exakt precision och avrundning"""
        results = []
        
        for dt_val, du_val, e_val in zip(DT_series, DU_series, e_series):
            # Konvertera till float64 för maximal precision
            dt = np.float64(dt_val)
            du = np.float64(du_val)
            e = np.float64(e_val)
            delta = du / 4.0
            B_val = dt + delta
            
            # Beräkna årliga inkrement med FULLSTÄNDIG precision
            inc_exact_vals = []
            inc_rounded_vals = []
            avdrag_vals = []

            for t in range(1, 5):  # t = 1,2,3,4 för åren 2024-2027
                # Beräkna inkrement med full precision
                growth_factor = (1.0 + e) ** (t - 1)
                inc_exact = e * B_val * growth_factor
                
                # Spara exakt värde för kumulativ summa
                inc_exact_vals.append(inc_exact)
                
                # Avrunda för kompatibilitet (används vid rapportering)
                inc_rounded = excel_half_up_round(inc_exact)
                inc_rounded_vals.append(inc_rounded)
                
                # KRITISK FIX: Kumulativt avdrag baserat på EXAKTA värden
                avdrag_kum = sum(inc_exact_vals)
                avdrag_vals.append(avdrag_kum)
            
            # Beräkna årsvärden: Y_t = DT - Avdrag_t + Δ
            year_vals = []
            for avdrag in avdrag_vals:
                y_exact = dt - avdrag + delta
                year_vals.append(y_exact)  # Behåll decimaler!
            
            results.append({
                'inc': inc_rounded_vals,      # Avrundade för visning
                'inc_exact': inc_exact_vals,  # Exakta för beräkning
                'avdrag': avdrag_vals,        # Baserat på exakta värden
                'years': year_vals,
                'B': B_val,
                'total': sum(year_vals)
            })
        
        return results
    
    # SCENARIO-BERÄKNING
    scn_results = calculate_exact_yearly_values(DT, DU, e_scn)
    
    # BASELINE-BERÄKNING
    base_results = calculate_exact_yearly_values(DT, DU, e_base)
    
    # EXTRAHERA RESULTAT
    # Scenario-värden
    y2024_scn = np.array([r['years'][0] for r in scn_results])
    y2025_scn = np.array([r['years'][1] for r in scn_results])
    y2026_scn = np.array([r['years'][2] for r in scn_results])
    y2027_scn = np.array([r['years'][3] for r in scn_results])
    total_4yr_scn = np.array([r['total'] for r in scn_results])
    
    # Baseline-värden
    y2024_base = np.array([r['years'][0] for r in base_results])
    y2025_base = np.array([r['years'][1] for r in base_results])
    y2026_base = np.array([r['years'][2] for r in base_results])
    y2027_base = np.array([r['years'][3] for r in base_results])
    total_4yr_base = np.array([r['total'] for r in base_results])
    
    # SKAPA EXPORT-DATAFRAME
    export_data['Paverkbara_Baseline_4yr'] = total_4yr_base
    export_data['Paverkbara_Target'] = total_4yr_scn
    export_data['Total_Reduction_tkr'] = total_4yr_base - total_4yr_scn
    export_data['Effektiviseringskrav'] = e_scn
    
    # Lägg till årsvisa värden
    export_data['Y2024_scenario'] = y2024_scn
    export_data['Y2025_scenario'] = y2025_scn
    export_data['Y2026_scenario'] = y2026_scn
    export_data['Y2027_scenario'] = y2027_scn
    
    export_data['Y2024_baseline'] = y2024_base
    export_data['Y2025_baseline'] = y2025_base
    export_data['Y2026_baseline'] = y2026_base
    export_data['Y2027_baseline'] = y2027_base
    
    # Debug-information med full precision
    export_data['DT_exact'] = DT
    export_data['DU_exact'] = DU
    export_data['Delta_exact'] = Delta
    export_data['B_exact'] = B
    export_data['e_base_exact'] = e_base
    export_data['e_scn_exact'] = e_scn
    
    # Lägg till inkrement för transparens
    for i, year in enumerate([2024, 2025, 2026, 2027]):
        export_data[f'Inc_{year}_scn'] = [r['inc'][i] for r in scn_results]
        export_data[f'Avdrag_{year}_scn'] = [r['avdrag'][i] for r in scn_results]
        export_data[f'Inc_{year}_base'] = [r['inc'][i] for r in base_results]
        export_data[f'Avdrag_{year}_base'] = [r['avdrag'][i] for r in base_results]
    
    export_data['Analysis_Method'] = 'Excel_exact_precision_fixed'
    
    # Metadata för diagnostik
    metadata = {
        'n_dea_input': len(dea_result),
        'n_with_baseline': len(export_data),
        'n_excluded': n_incomplete,
        'total_baseline_tkr': float(export_data['Paverkbara_Baseline_4yr'].sum()),
        'total_target_tkr': float(export_data['Paverkbara_Target'].sum()),
        'total_reduction_tkr': float(export_data['Total_Reduction_tkr'].sum()),
        'mean_effkrav_pct': float(export_data['Effektiviseringskrav'].mean() * 100),
        'analysis_method': 'Excel_exact_precision_fixed'
    }
    
    return export_data, metadata


def calculate_ir_paverkbara_from_file(
    dea_result: pd.DataFrame,
    ir_baseline_file: str
) -> Tuple[pd.DataFrame, dict]:
    """
    Convenience-funktion som laddar baseline OCH beräknar.
    
    Args:
        dea_result: DataFrame med DEA-resultat
        ir_baseline_file: Sökväg till Excel-fil med baseline
        
    Returns:
        Samma som calculate_ir_paverkbara_export()
    """
    ir_baseline = load_ir_paverkbara_baseline(ir_baseline_file)
    return calculate_ir_paverkbara_export(dea_result, ir_baseline)