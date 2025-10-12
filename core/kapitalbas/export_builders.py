"""
export_builders.py - Byggare för DEA och IR exporttabeller
==========================================================

Innehåller logik för att bygga exporttabeller från beräkningsdata.
Hanterar både DEA-export (CAPEX baseline vs scenario) och IR-export
(detaljerad kapitalkostnad med koncessionsjusteringar).

Inga UI-beroenden - ren databearbetning som kan användas av både Streamlit och Dash.
"""

from typing import Tuple, Dict, Optional
from pathlib import Path
import pandas as pd
import numpy as np
import warnings

# Import från andra core-moduler
try:
    from .calculations import R_OLD, YEAR_TO_CODES, apply_interest_scenario, get_period_df
    from .dmu_aggregation import aggregate_to_dmu, check_year_completeness
    from .export_writers import format_wacc_tag
except ImportError:
    from calculations import R_OLD, YEAR_TO_CODES, apply_interest_scenario, get_period_df
    from dmu_aggregation import aggregate_to_dmu, check_year_completeness
    from export_writers import format_wacc_tag


# ============================================================================
# DEA-BAS LÄSNING
# ============================================================================

def read_dmu_from_dea_base(path_xlsx: str) -> Optional[pd.DataFrame]:
    """
    Läser DMU-lista från DEA-basfil för att identifiera vilka DMU som ska inkluderas.
    
    DEA-analysen använder en specifik uppsättning DMU. Denna funktion läser
    listan från Excel-filen för att säkerställa att endast relevanta DMU exporteras.
    
    Args:
        path_xlsx: Sökväg till DEA Excel-fil (t.ex. "Data_modeller.xlsx")
        
    Returns:
        DataFrame med kolumner [DMU, Företag], eller None om filen inte kan läsas
    """
    if not Path(path_xlsx).exists():
        warnings.warn(f"DEA-basfil hittades inte: {path_xlsx}")
        return None
    
    try:
        df = pd.read_excel(path_xlsx, sheet_name="Körning")
        
        if 'DMU' not in df.columns:
            warnings.warn("DEA-basfil saknar 'DMU'-kolumn")
            return None
        
        # Behåll endast DMU och Företag (om den finns)
        cols = ['DMU']
        if 'Företag' in df.columns:
            cols.append('Företag')
        
        return df[cols].drop_duplicates()
        
    except Exception as e:
        warnings.warn(f"Kunde inte läsa DEA-basfil: {e}")
        return None


# ============================================================================
# DEA-EXPORT BUILDER
# ============================================================================

def build_dea_export_table(
    df_year: pd.DataFrame,
    r_new: float,
    dea_base_path: Optional[str] = None,
    exclude_missing_dmus: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    Bygger DEA-exporttabell med CAPEX baseline vs scenario.
    
    KRITISK FIX: Aggregerar till årsnivå FÖRE scenario-beräkning och avrundning
    för att undvika avrundningsfel per halvår som ger inkonsistenta resultat.
    
    Processen:
    1. Aggregerar halvår (H1+H2) till årsnivå för varje DMU
    2. Applicerar scenario-beräkning EN GÅNG per DMU (inte per halvår)
    3. Avrundning sker på årsnivå
    4. Exkluderar DMU som saknas i DEA-basfil (optional)
    
    Args:
        df_year: DataFrame för specifikt år (bör innehålla båda halvår)
                 Måste innehålla: DMU, Företag, time, capcost_sum, 
                                 dep_ord, dep_tail, return_ord, return_tail
        r_new: Ny kalkylränta (real, före skatt) för scenario
        dea_base_path: Sökväg till DEA Excel-fil för DMU-validering (optional)
        exclude_missing_dmus: Om True, exkludera DMU som saknas i DEA-bas
        
    Returns:
        Tuple med:
        - export_df: DataFrame med CAPEX baseline och scenario per DMU
        - excluded_df: DataFrame med DMU som exkluderades (tom om exclude_missing_dmus=False)
        - tag: WACC-tag för kolumnnamn (t.ex. "0p0475")
        
    Raises:
        ValueError: Om obligatoriska kolumner saknas eller r_new är ogiltig
    """
    # Validera input
    required_cols = ['DMU', 'Företag', 'capcost_sum', 'dep_ord', 'dep_tail', 
                     'return_ord', 'return_tail']
    missing_cols = [col for col in required_cols if col not in df_year.columns]
    if missing_cols:
        raise ValueError(f"DataFrame saknar obligatoriska kolumner: {missing_cols}")
    
    if not (isinstance(r_new, (float, int)) and np.isfinite(r_new)):
        raise ValueError(f"r_new måste vara ändligt tal, fick {r_new}")
    
    # Steg 1: Aggregera till årsnivå (H1+H2) FÖRE scenario-beräkning
    df_year_agg = df_year.groupby(["DMU", "Företag"], as_index=False).agg({
        'capcost_sum': 'sum',
        'dep_ord': 'sum', 
        'dep_tail': 'sum',
        'return_ord': 'sum',
        'return_tail': 'sum'
    })
    
    # Steg 2: Scenario-beräkning på årsnivå (EN GÅNG per DMU)
    scale = float(r_new) / R_OLD
    
    # Exakt hantering när r_new == R_OLD
    if abs(float(r_new) - R_OLD) < 1e-10:
        df_year_agg["return_ord_new"] = df_year_agg["return_ord"]
        df_year_agg["return_tail_new"] = df_year_agg["return_tail"]
    else:
        # Avrunda EFTER summering av halvår
        df_year_agg["return_ord_new"] = (df_year_agg["return_ord"] * scale).round()
        df_year_agg["return_tail_new"] = (df_year_agg["return_tail"] * scale).round()
    
    # Beräkna ny total kapitalkostnad
    df_year_agg["capcost_sum_new"] = (
        df_year_agg["dep_ord"] + 
        df_year_agg["dep_tail"] + 
        df_year_agg["return_ord_new"] + 
        df_year_agg["return_tail_new"]
    )
    
    # Steg 3: Bygg export-tabell
    out = df_year_agg.rename(columns={
        'capcost_sum': 'CAPEX_2024_tkr',
        'capcost_sum_new': 'CAPEX_2024_wacc_tkr'
    })[["DMU", "Företag", "CAPEX_2024_tkr", "CAPEX_2024_wacc_tkr"]].copy()
    
    # Beräkna delta med tolerans
    out["delta_tkr"] = out["CAPEX_2024_wacc_tkr"] - out["CAPEX_2024_tkr"]
    tolerance = 1e-6 
    mask = abs(out["delta_tkr"]) < tolerance
    out.loc[mask, "delta_tkr"] = 0.0
    out["delta_tkr"] = out["delta_tkr"].round(3)
    
    # Lägg till metadata-kolumner
    out["r_old"] = R_OLD
    out["r_new"] = round(float(r_new), 4)
    out["price_year"] = 2022
    
    # Steg 4: Exkludera DMU som saknas i DEA-bas (optional)
    excluded = pd.DataFrame()
    
    if exclude_missing_dmus and dea_base_path:
        dmu_base = read_dmu_from_dea_base(dea_base_path)
        
        if dmu_base is not None:
            out = out.merge(dmu_base[["DMU"]].assign(in_dea=1), on="DMU", how="left")
            excluded = out[out["in_dea"].isna()][["DMU", "Företag"]].copy()
            out = out[out["in_dea"].eq(1)].drop(columns=["in_dea"])
            
            if not excluded.empty:
                warnings.warn(
                    f"{len(excluded)} DMU exkluderades (saknas i DEA-bas): "
                    f"{excluded['DMU'].tolist()}"
                )
    
    # Döp scenariokolumnen med wacc-tagg
    tag = format_wacc_tag(out["r_new"].iloc[0] if len(out) else r_new)
    out = out.rename(columns={"CAPEX_2024_wacc_tkr": f"CAPEX_2024_wacc_{tag}_tkr"})
    
    return out, excluded, tag


# ============================================================================
# IR-EXPORT BUILDER
# ============================================================================

def build_ir_export_table_period(
    df_all: pd.DataFrame,
    r_new: float,
    years: Tuple[int, ...] = (2024, 2025, 2026, 2027),
    apply_concessions: bool = True
) -> Tuple[pd.DataFrame, str]:
    """
    Bygger IR-exporttabell som SUMMA över hela regleringsperioden.
    
    Processen:
    1. Filtrerar till specificerade år
    2. Applicerar scenarioberäkning (skalar return_* med r_new/R_OLD per halvår)
    3. Aggregerar alla halvår till periodsumma per DMU
    4. Applicerar koncessionsjusteringar (optional)
    
    Args:
        df_all: DataFrame med alla tidsperioder
                Måste innehålla: DMU, Företag, time, dep_ord, dep_tail,
                                return_ord, return_tail, capcost_sum
        r_new: Ny kalkylränta (real, före skatt) för scenario
        years: Tuple med år att inkludera (default: 2024-2027)
        apply_concessions: Om True, applicera koncessionsjusteringar
        
    Returns:
        Tuple med:
        - export_df: DataFrame med detaljerad kapitalkostnad per DMU
        - tag: WACC-tag (t.ex. "0p0475")
        
    Raises:
        ValueError: Om obligatoriska kolumner saknas eller ingen data för period
    """
    # Validera input
    required_cols = ['DMU', 'Företag', 'time', 'dep_ord', 'dep_tail', 
                     'return_ord', 'return_tail', 'capcost_sum']
    missing_cols = [col for col in required_cols if col not in df_all.columns]
    if missing_cols:
        raise ValueError(f"DataFrame saknar obligatoriska kolumner: {missing_cols}")
    
    # Steg 1: Filtrera till specificerad period
    df_period = get_period_df(df_all, years=years)
    
    if df_period.empty:
        raise ValueError(f"Ingen data hittades för åren {years}")
    
    # Steg 2: Applicera scenario (skalar return_* per halvår)
    scen = apply_interest_scenario(df_period, r_new)
    
    # Steg 3: Aggregera över alla halvår till periodsumma per DMU
    ir = scen.groupby(["DMU", "Företag"], as_index=False).agg({
        'dep_ord': 'sum',
        'dep_tail': 'sum',
        'return_ord': 'sum',
        'return_tail': 'sum',
        'return_ord_new': 'sum',
        'return_tail_new': 'sum',
        'capcost_sum': 'sum',
        'capcost_sum_new': 'sum'
    })
    
    # Steg 4: Skapa export-kolumner
    ir["Kapitalkostnad_Baseline"] = ir["capcost_sum"]
    ir["Kapitalkostnad_Ny"] = ir["capcost_sum_new"]
    ir["Avskrivningar_Ny"] = ir["dep_ord"] + ir["dep_tail"]  # WACC påverkar ej
    ir["Avkastning_Baseline"] = ir["return_ord"] + ir["return_tail"]
    ir["Avkastning_Ny"] = ir["return_ord_new"] + ir["return_tail_new"]
    
    # Detaljerade ord/tail-delar (för framtida analys)
    ir["dep_ord_Ny"] = ir["dep_ord"]
    ir["dep_tail_Ny"] = ir["dep_tail"]
    ir["return_ord_Ny"] = ir["return_ord_new"]
    ir["return_tail_Ny"] = ir["return_tail_new"]
    
    # Steg 5: Applicera koncessionsjusteringar
    if apply_concessions:
        ir = apply_concession_adjustments(ir)
    
    # Metadata
    tag = format_wacc_tag(r_new)
    ir["r_old"] = R_OLD
    ir["r_new"] = round(float(r_new), 4)
    ir["price_year"] = 2022
    ir["scenario_tag"] = tag
    
    # Välj kolumner för export
    cols = [
        'DMU', 'Företag',
        'Kapitalkostnad_Baseline', 'Kapitalkostnad_Ny',
        'Avskrivningar_Ny', 'Avkastning_Baseline', 'Avkastning_Ny',
        'dep_ord_Ny', 'dep_tail_Ny', 'return_ord_Ny', 'return_tail_Ny',
        'r_old', 'r_new', 'price_year', 'scenario_tag'
    ]
    
    return ir[cols], tag


# ============================================================================
# KONCESSIONSJUSTERINGAR
# ============================================================================

def get_concession_adjustments() -> Dict[str, Dict[int, float]]:
    """
    Returnerar manuella tilläggsdata för koncessionskostnader per DMU.
    
    Dessa kostnader saknas i originaldata men finns i intäktsramen.
    Data baserad på delta-värden mellan beräknad kapitalkostnad och
    faktisk intäktsram för specificerade DMU.
    
    Värden är i tkr och representerar periodsumma 2024-2027.
    
    Returns:
        Dict med två nycklar:
        - 'dep_adjustments': Dict[DMU, avskrivning_tkr]
        - 'return_adjustments': Dict[DMU, avkastning_tkr]
    """
    # Avskrivningsjusteringar (från analys av delta-värden)
    dep_adjustments = {
        115: 1032,  # Umeå Energi Elnät AB
        121: 1013,  # Kraftringen Nät AB  
        41: 355,    # Jönköping Energinät AB
        30: 1047,   # Göteborg Energi Nät AB
        24: 59,     # Eskilstuna Energi och Miljö Elnät AB
    }
    
    # Avkastningsjusteringar
    return_adjustments = {
        115: 941,   # Umeå Energi Elnät AB
        30: 947,    # Göteborg Energi Nät AB
        41: 265,    # Jönköping Energinät AB
        121: 318,   # Kraftringen Nät AB
        24: 68,     # Eskilstuna Energi och Miljö Elnät AB
    }
    
    return {
        'dep_adjustments': dep_adjustments,
        'return_adjustments': return_adjustments
    }


def apply_concession_adjustments(df_ir_export: pd.DataFrame) -> pd.DataFrame:
    """
    Applicerar manuella koncessionskostnader på IR-export.
    
    Koncessionskostnader påverkas INTE av WACC-ändringar eftersom de
    är administrativa avgifter, inte kapitalkostnader.
    
    Funktionen:
    1. Hämtar justeringsdata från get_concession_adjustments()
    2. Adderar till relevanta DMU:s avskrivningar och avkastning
    3. Uppdaterar total kapitalkostnad
    4. Loggar vilka justeringar som applicerades
    
    Args:
        df_ir_export: DataFrame med IR-export
                      Måste innehålla: DMU, Avskrivningar_Ny, Avkastning_Ny,
                                      Kapitalkostnad_Ny, dep_ord_Ny, return_ord_Ny
        
    Returns:
        DataFrame med applicerade koncessionsjusteringar
        
    Raises:
        ValueError: Om obligatoriska kolumner saknas
    """
    # Validera input
    required_cols = ['DMU', 'Avskrivningar_Ny', 'Avkastning_Ny', 'Kapitalkostnad_Ny']
    missing_cols = [col for col in required_cols if col not in df_ir_export.columns]
    if missing_cols:
        raise ValueError(f"DataFrame saknar obligatoriska kolumner: {missing_cols}")
    
    adjustments = get_concession_adjustments()
    df_adjusted = df_ir_export.copy()
    
    applied_adjustments = []
    
    # Applicera avskrivningsjusteringar
    for dmu, dep_adj in adjustments['dep_adjustments'].items():
        if dmu in df_adjusted['DMU'].values:
            mask = df_adjusted['DMU'] == dmu
            df_adjusted.loc[mask, 'Avskrivningar_Ny'] += dep_adj
            df_adjusted.loc[mask, 'Kapitalkostnad_Ny'] += dep_adj
            
            # Uppdatera detaljerad kolumn om den finns
            if 'dep_ord_Ny' in df_adjusted.columns:
                df_adjusted.loc[mask, 'dep_ord_Ny'] += dep_adj
            
            applied_adjustments.append(f"DMU {dmu}: +{dep_adj} tkr avskrivning")
    
    # Applicera avkastningsjusteringar
    for dmu, ret_adj in adjustments['return_adjustments'].items():
        if dmu in df_adjusted['DMU'].values:
            mask = df_adjusted['DMU'] == dmu
            df_adjusted.loc[mask, 'Avkastning_Ny'] += ret_adj
            df_adjusted.loc[mask, 'Kapitalkostnad_Ny'] += ret_adj
            
            # Uppdatera detaljerad kolumn om den finns
            if 'return_ord_Ny' in df_adjusted.columns:
                df_adjusted.loc[mask, 'return_ord_Ny'] += ret_adj
            
            applied_adjustments.append(f"DMU {dmu}: +{ret_adj} tkr avkastning")
    
    # Logga applicerade justeringar
    if applied_adjustments:
        unique_dmus = len(set(
            list(adjustments['dep_adjustments'].keys()) + 
            list(adjustments['return_adjustments'].keys())
        ))
        warnings.warn(
            f"Applicerade koncessionsjusteringar för {unique_dmus} DMU:er "
            f"för att matcha intäktsramen. Detaljer: {applied_adjustments}"
        )
    
    return df_adjusted


# ============================================================================
# TESTER
# ============================================================================

if __name__ == "__main__":
    """
    Tester för export-builders.
    """
    print("Testing export_builders.py...")
    print("=" * 60)
    
    # Test 1: DEA-export builder
    print("\nTest 1: DEA-export builder")
    
    # Skapa test-data med halvårsdata som ska aggregeras
    test_df_dea = pd.DataFrame({
        'DMU': [1, 1, 2, 2],
        'Företag': ['Test AB', 'Test AB', 'Demo AB', 'Demo AB'],
        'time': [229, 230, 229, 230],  # 2024 H1 och H2
        'capcost_sum': [500, 520, 1000, 1050],
        'dep_ord': [300, 310, 600, 620],
        'dep_tail': [50, 55, 100, 105],
        'return_ord': [130, 135, 250, 270],
        'return_tail': [20, 20, 50, 55]
    })
    
    r_scenario = 0.05  # 5% WACC scenario
    
    try:
        df_export, df_excluded, tag = build_dea_export_table(
            test_df_dea,
            r_scenario,
            exclude_missing_dmus=False
        )
        
        print(f"Export skapad: {len(df_export)} DMU")
        print(f"WACC-tag: '{tag}' (förväntat: '0p0500')")
        print(f"Har baseline-kolumn: {'' if 'CAPEX_2024_tkr' in df_export.columns else ''}")
        print(f"Har scenario-kolumn: {'' if f'CAPEX_2024_wacc_{tag}_tkr' in df_export.columns else ''}")
        
        # Verifiera att aggregering skedde (2 halvår → 1 rad per DMU)
        print(f"Aggregering korrekt: {'' if len(df_export) == 2 else ''}")
        
        # Verifiera att DMU 1 har summan av halvåren
        if 1 in df_export['DMU'].values:
            dmu1_baseline = df_export[df_export['DMU'] == 1]['CAPEX_2024_tkr'].iloc[0]
            expected_baseline = 500 + 520  # H1 + H2
            print(f"DMU 1 baseline korrekt: {'' if abs(dmu1_baseline - expected_baseline) < 1 else ''}")
        
    except Exception as e:
        print(f" Fel: {e}")
    
    # Test 2: IR-export builder
    print("\nTest 2: IR-export builder")
    
    # Skapa test-data för hela perioden
    test_df_ir = pd.DataFrame({
        'DMU': [1] * 8,
        'Företag': ['Test AB'] * 8,
        'time': [229, 230, 231, 232, 233, 234, 235, 236],  # 2024-2027
        'dep_ord': [100] * 8,
        'dep_tail': [20] * 8,
        'return_ord': [50] * 8,
        'return_tail': [10] * 8,
        'capcost_sum': [180] * 8
    })
    
    try:
        df_export, tag = build_ir_export_table_period(
            test_df_ir,
            r_scenario,
            apply_concessions=False  # Skippa för test
        )
        
        print(f"Export skapad: {len(df_export)} DMU")
        print(f"Har Kapitalkostnad_Ny: {'' if 'Kapitalkostnad_Ny' in df_export.columns else ''}")
        print(f"Har Avskrivningar_Ny: {'' if 'Avskrivningar_Ny' in df_export.columns else ''}")
        print(f"Har Avkastning_Ny: {'' if 'Avkastning_Ny' in df_export.columns else ''}")
        
        # Verifiera periodsummering (8 halvår → 1 rad)
        if len(df_export) == 1:
            total_avskr = df_export['Avskrivningar_Ny'].iloc[0]
            expected_avskr = (100 + 20) * 8  # 8 halvår
            print(f"Periodsummering korrekt: {'' if abs(total_avskr - expected_avskr) < 1 else ''}")
        
    except Exception as e:
        print(f" Fel: {e}")
    
    # Test 3: Koncessionsjusteringar
    print("\nTest 3: Koncessionsjusteringar")
    
    adjustments = get_concession_adjustments()
    print(f"Avskrivningsjusteringar: {len(adjustments['dep_adjustments'])} DMU")
    print(f"Avkastningsjusteringar: {len(adjustments['return_adjustments'])} DMU")
    
    # Test applicering
    test_df_conc = pd.DataFrame({
        'DMU': [115, 999],  # 115 har justeringar, 999 har inte
        'Företag': ['Test', 'Other'],
        'Avskrivningar_Ny': [1000.0, 2000.0],
        'Avkastning_Ny': [500.0, 1000.0],
        'Kapitalkostnad_Ny': [1500.0, 3000.0]
    })
    
    try:
        df_adjusted = apply_concession_adjustments(test_df_conc)
        
        # Verifiera att DMU 115 fick justeringar
        dmu115_avskr = df_adjusted[df_adjusted['DMU'] == 115]['Avskrivningar_Ny'].iloc[0]
        expected_avskr = 1000.0 + adjustments['dep_adjustments'][115]
        adjustment_applied = abs(dmu115_avskr - expected_avskr) < 0.1
        print(f"Justeringar applicerade på DMU 115: {'' if adjustment_applied else ''}")
        
        # Verifiera att DMU 999 inte påverkades
        dmu999_avskr = df_adjusted[df_adjusted['DMU'] == 999]['Avskrivningar_Ny'].iloc[0]
        no_adjustment = abs(dmu999_avskr - 2000.0) < 0.1
        print(f"DMU 999 opåverkad: {'' if no_adjustment else ''}")
        
    except Exception as e:
        print(f" Fel: {e}")
    
    print("\n" + "=" * 60)
    print("Alla tester slutförda.")