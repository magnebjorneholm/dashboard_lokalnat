# data_loader.py
# Laddar baseline-data från "Löpande kostnader från SDF 202427.xlsx"
# och hanterar framtida scenario-integration

from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List


def load_baseline_data(filepath: str) -> pd.DataFrame:
    """
    Laddar baseline-data från Excel-filen med löpande kostnader.
    Robust inläsning som hanterar olika kolumnformat och -namn.
    
    Returnerar DataFrame med standardiserade kolumnnamn.
    """
    try:
        # Försök läsa från första sheet först
        df = pd.read_excel(filepath, engine="openpyxl")
    except Exception as e:
        # Om första sheet misslyckas, försök hitta rätt sheet
        try:
            xl = pd.ExcelFile(filepath)
            # Leta efter sheet som kan innehålla intäktsram-data
            for sheet_name in xl.sheet_names:
                if any(keyword in sheet_name.lower() for keyword in ['intäkt', 'kostn', 'data']):
                    df = pd.read_excel(filepath, sheet_name=sheet_name, engine="openpyxl")
                    break
            else:
                # Om inget passande sheet hittas, använd första
                df = pd.read_excel(filepath, sheet_name=0, engine="openpyxl")
        except Exception:
            raise RuntimeError(f"Fel vid inläsning av fil: {e}")
    
    # Debug: Visa tillgängliga kolumner
    print(f"Tillgängliga kolumner i Excel-filen:")
    for i, col in enumerate(df.columns):
        print(f"  {i}: '{col}'")
    
    # Rensa kolumnnamn
    df.columns = df.columns.str.strip()
    
    # Definiera söktermer för varje komponent
    column_searches = {
        'REId': ['reid'],
        'Intaktsram_Total': ['intäktsram', 'intaktsram', 'beräknad'],
        'Paverkbara_Kostnader': ['påverkbara kostnader', 'paverkbara kostnader'],
        'Opaverkbara_Kostnader': ['opåverkbara kostnader', 'opaverkbara kostnader'],
        'Flexibilitetstjanster': ['flexibilitetstjänster', 'flexibilitetstjanster'],
        'Avbrottsersattning_12_24h': ['avbrottsersättning 12-24', 'avbrottsersattning 12-24'],
        'Kapitalkostnad_Total': ['kapitalkostnad'],
        'Avskrivningar': ['kapital-förslitning', 'kapital-forslitning', '-varav kapital-förslitning', 'varav kapital-förslitning'],
        'Avkastning': ['kapital-bindning', 'varav kapital-bindning']
    }
    
    # Hitta matchande kolumner (exakt match först för att undvika dubbletter)
    column_mapping = {}
    available_cols = df.columns.tolist()
    used_cols = set()  # Håll koll på använda kolumner
    
    for std_name, keywords in column_searches.items():
        found_col = None
        
        # Försök exakt match först
        for keyword in keywords:
            for col in available_cols:
                if col not in used_cols and col.lower().strip() == keyword.lower().strip():
                    found_col = col
                    break
            if found_col:
                break
        
        # Om ingen exakt match, försök partiell match
        if not found_col:
            for keyword in keywords:
                for col in available_cols:
                    if col not in used_cols and keyword.lower() in col.lower():
                        found_col = col
                        break
                if found_col:
                    break
        
        if found_col:
            column_mapping[found_col] = std_name
            used_cols.add(found_col)
            print(f"Mappar '{found_col}' -> '{std_name}'")
        else:
            print(f"Varning: Ingen kolumn hittad för {std_name} (söktermer: {keywords})")
    
    # Applicera mapping
    df_mapped = df.rename(columns=column_mapping)
    
    # Kontrollera kritiska kolumner
    if 'REId' not in df_mapped.columns:
        # Försök hitta första kolumn som kan vara REId
        potential_id_cols = [col for col in df_mapped.columns 
                           if any(term in col.lower() for term in ['id', 'företag', 'foretag', 'name'])]
        if potential_id_cols:
            df_mapped = df_mapped.rename(columns={potential_id_cols[0]: 'REId'})
            print(f"Använder '{potential_id_cols[0]}' som REId")
        else:
            raise ValueError("Kunde inte hitta kolumn för företags-ID. Tillgängliga kolumner: " + str(df.columns.tolist()))
    
    # Konvertera numeriska kolumner
    numeric_cols = [col for col in df_mapped.columns if col != 'REId']
    for col in numeric_cols:
        if col in df_mapped.columns:
            df_mapped[col] = pd.to_numeric(df_mapped[col], errors="coerce")
    
    # Ta bort helt tomma rader och rader utan REId
    df_mapped = df_mapped.dropna(how='all')
    df_mapped = df_mapped.dropna(subset=['REId']).reset_index(drop=True)
    
    # Säkerställ att vi har både Avskrivningar och Avkastning, eller beräkna från total
    if 'Avskrivningar' in df_mapped.columns and 'Avkastning' in df_mapped.columns:
        # Vi har separata komponenter - beräkna total om den saknas
        if 'Kapitalkostnad_Total' not in df_mapped.columns:
            df_mapped['Kapitalkostnad_Total'] = df_mapped['Avskrivningar'] + df_mapped['Avkastning']
    elif 'Kapitalkostnad_Total' in df_mapped.columns:
        # Vi har bara total - för nu lämna som den är
        # I framtiden kan vi försöka uppskatta uppdelningen
        pass
    
    # Om vi inte har Intaktsram_Total, försök beräkna den från komponenter
    if 'Intaktsram_Total' not in df_mapped.columns:
        # Försök med uppdelade komponenter först
        if 'Avskrivningar' in df_mapped.columns and 'Avkastning' in df_mapped.columns:
            component_cols = ['Paverkbara_Kostnader', 'Opaverkbara_Kostnader', 
                             'Flexibilitetstjanster', 'Avbrottsersattning_12_24h', 
                             'Avskrivningar', 'Avkastning']
        else:
            component_cols = ['Paverkbara_Kostnader', 'Opaverkbara_Kostnader', 
                             'Flexibilitetstjanster', 'Avbrottsersattning_12_24h', 
                             'Kapitalkostnad_Total']
        
        available_components = [col for col in component_cols if col in df_mapped.columns]
        
        if available_components:
            df_mapped['Intaktsram_Total'] = df_mapped[available_components].sum(axis=1, skipna=True)
            print(f"Beräknade Intaktsram_Total från komponenter: {available_components}")
    
    # Lägg till metadata-kolumner
    df_mapped['Källa_Paverkbara'] = 'Baseline'
    df_mapped['Källa_Kapitalkostnad'] = 'Baseline'
    df_mapped['Uppdaterad_Paverkbara'] = False
    df_mapped['Uppdaterad_Kapitalkostnad'] = False
    
    print(f"Slutlig dataframe: {len(df_mapped)} rader, {len(df_mapped.columns)} kolumner")
    return df_mapped


def load_dmu_mapping(filepath: str = "intaktsram/data/reconciliation_id_network_firm_dmu.csv") -> pd.DataFrame:
    """
    Laddar mappning mellan REId och DMU för att kunna växla mellan vyerna.
    """
    try:
        df = pd.read_csv(filepath)
        # Normalisera kolumnnamn
        if 'id_firm' in df.columns and 'DMU' in df.columns:
            return df[['id_firm', 'DMU']].rename(columns={'id_firm': 'REId'}).dropna()
        else:
            print("Varning: DMU-mapping-fil saknar förväntade kolumner")
            return pd.DataFrame(columns=['REId', 'DMU'])
    except Exception as e:
        print(f"Kunde inte ladda DMU-mapping: {e}")
        return pd.DataFrame(columns=['REId', 'DMU'])


def detect_scenario_updates() -> Dict[str, Optional[str]]:
    """
    Letar efter scenario-filer från andra sektioner i 'scenario/' mappen.
    
    Returns:
        Dict med information om tillgängliga scenarier:
        {
            'effektiviseringskrav': 'scenario/effkrav_2024_v1.parquet' eller None,
            'kapitalbas': 'dea_exports/capex_wacc_0p0475_y2024_tkr.parquet' eller None
        }
    """
    updates = {
        'effektiviseringskrav': None,
        'kapitalbas': None
    }
    
    # Leta efter effektiviseringskrav-filer i scenario/
    scenario_dir = Path("scenario")
    if scenario_dir.exists():
        for file in scenario_dir.glob("effkrav_*.parquet"):
            updates['effektiviseringskrav'] = str(file)
            break
    
    # Leta efter kapitalbas-filer i dea_exports/ (enligt översikt.py)
    dea_dir = Path("dea_exports")
    if dea_dir.exists():
        # Hitta senaste WACC-scenario från kapitalbas
        capex_files = list(dea_dir.glob("capex_wacc_*_y2024_tkr.parquet"))
        if capex_files:
            # Välj senaste fil baserat på modifierad tid
            latest_capex = max(capex_files, key=lambda f: f.stat().st_mtime)
            updates['kapitalbas'] = str(latest_capex)
    
    return updates


def load_scenario_data(scenario_type: str, scenario_file: str, baseline_df: pd.DataFrame) -> pd.DataFrame:
    """
    Laddar och integrerar scenario-data från andra sektioner.
    
    Args:
        scenario_type: 'effektiviseringskrav' eller 'kapitalbas'
        scenario_file: Sökväg till scenario-fil
        baseline_df: Baseline-data för merge
        
    Returns:
        DataFrame med uppdaterade värden från scenariot
    """
    try:
        scenario_df = pd.read_parquet(scenario_file)
        result_df = baseline_df.copy()
        
        if scenario_type == 'effektiviseringskrav':
            # Förvänta kolumner som REId/DMU och nya påverkbara kostnader
            if 'REId' in scenario_df.columns and 'Paverkbara_Nya' in scenario_df.columns:
                merge_df = scenario_df[['REId', 'Paverkbara_Nya']]
                result_df = result_df.merge(merge_df, on='REId', how='left')
                
                # Uppdatera där scenario-data finns
                mask = result_df['Paverkbara_Nya'].notna()
                result_df.loc[mask, 'Paverkbara_Kostnader'] = result_df.loc[mask, 'Paverkbara_Nya']
                result_df.loc[mask, 'Källa_Paverkbara'] = 'Scenario'
                result_df.loc[mask, 'Uppdaterad_Paverkbara'] = True
                
                result_df = result_df.drop('Paverkbara_Nya', axis=1)
        
        elif scenario_type == 'kapitalbas':
            # Läs kapitalbas-export enligt översikt.py format
            # Kolumner: id_network, CAPEX_2024_wacc_0pXXXX_tkr, DMU, Företag
            
            # Hitta scenario-kolumn (CAPEX_2024_wacc_*)
            capex_cols = [col for col in scenario_df.columns 
                         if col.startswith('CAPEX_2024_wacc_') and col.endswith('_tkr')]
            
            if capex_cols:
                capex_col = capex_cols[0]  # Ta första matchande kolumn
                
                # Ladda DMU-mapping för att konvertera id_network -> REId
                dmu_mapping = load_dmu_mapping()
                if not dmu_mapping.empty and 'DMU' in scenario_df.columns:
                    # Mappa DMU -> REId
                    scenario_with_reid = scenario_df.merge(
                        dmu_mapping, 
                        on='DMU', 
                        how='left'
                    )
                    
                    if 'REId' in scenario_with_reid.columns:
                        merge_df = scenario_with_reid[['REId', capex_col]].dropna()
                        merge_df = merge_df.rename(columns={capex_col: 'Kapitalkostnad_Ny'})
                        
                        result_df = result_df.merge(merge_df, on='REId', how='left')
                        
                        # Uppdatera där scenario-data finns
                        mask = result_df['Kapitalkostnad_Ny'].notna()
                        
                        # Om vi har separerade komponenter, uppdatera bara avkastning
                        if 'Avkastning' in result_df.columns and 'Avskrivningar' in result_df.columns:
                            # Beräkna ny avkastning (total - avskrivning)
                            result_df.loc[mask, 'Avkastning'] = (
                                result_df.loc[mask, 'Kapitalkostnad_Ny'] - 
                                result_df.loc[mask, 'Avskrivningar']
                            )
                            # Uppdatera också total
                            result_df.loc[mask, 'Kapitalkostnad_Total'] = result_df.loc[mask, 'Kapitalkostnad_Ny']
                        else:
                            # Enkel uppdatering av total kapitalkostnad
                            result_df.loc[mask, 'Kapitalkostnad_Total'] = result_df.loc[mask, 'Kapitalkostnad_Ny']
                        
                        result_df.loc[mask, 'Källa_Kapitalkostnad'] = f'Scenario ({capex_col})'  
                        result_df.loc[mask, 'Uppdaterad_Kapitalkostnad'] = True
                        
                        result_df = result_df.drop('Kapitalkostnad_Ny', axis=1)
        
        return result_df
        
    except Exception as e:
        print(f"Fel vid laddning av scenario {scenario_type}: {e}")
        return baseline_df


def calculate_intaktsram(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar total intäktsram baserat på komponenter.
    Används när komponenter har uppdaterats via scenarier.
    """
    result_df = df.copy()
    
    # Komponenter som ingår i intäktsram
    components = [
        'Paverkbara_Kostnader',
        'Opaverkbara_Kostnader', 
        'Flexibilitetstjanster',
        'Avbrottsersattning_12_24h'
    ]
    
    # Lägg till kapitalkostnad (antingen uppdelad eller total)
    if 'Avskrivningar' in result_df.columns and 'Avkastning' in result_df.columns:
        # Använd uppdelade komponenter
        components.extend(['Avskrivningar', 'Avkastning'])
    else:
        # Fallback till total kapitalkostnad
        components.append('Kapitalkostnad_Total')
    
    # Beräkna ny total (endast för rader där alla komponenter finns)
    component_sum = result_df[components].sum(axis=1, skipna=False)
    
    # Uppdatera total intäktsram där vi har kompletta data
    mask = component_sum.notna()
    result_df.loc[mask, 'Intaktsram_Beraknad'] = component_sum[mask]
    
    # Beräkna delta mot baseline
    if 'Intaktsram_Total' in result_df.columns:
        result_df['Delta_Intaktsram'] = result_df['Intaktsram_Beraknad'] - result_df['Intaktsram_Total']
        result_df['Delta_Procent'] = (result_df['Delta_Intaktsram'] / result_df['Intaktsram_Total'] * 100).round(2)
    
    return result_df