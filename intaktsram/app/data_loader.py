# data_loader.py
# Laddar baseline-data från "Löpande kostnader från SDF 202427.xlsx"
# och hanterar framtida scenario-integration med ny DMU-mappning

from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List


def load_baseline_data(filepath: str) -> pd.DataFrame:
    """
    Laddar baseline-data från Excel-filen med löpande kostnader.
    Robust inläsning som hanterar olika kolumnformat och -namn.
    Lägger automatiskt till DMU-mappning från new_recon.csv.
    
    Returnerar DataFrame med standardiserade kolumnnamn inklusive DMU.
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
    
    # NYTT: Lägg automatiskt till DMU-mappning
    dmu_mapping = load_dmu_mapping()
    if not dmu_mapping.empty:
        original_count = len(df_mapped)
        df_mapped = df_mapped.merge(dmu_mapping[['REId', 'DMU']], on='REId', how='left')
        mapped_count = df_mapped['DMU'].notna().sum()
        
        # Filtrera bort omappade REId (regionnät) - behåll bara lokalnät
        unmapped_reids = df_mapped[df_mapped['DMU'].isna()]['REId'].tolist()
        df_mapped = df_mapped[df_mapped['DMU'].notna()].reset_index(drop=True)
        
        print(f"DMU-mappning tillagd: {mapped_count}/{original_count} REId mappade till DMU")
        print(f"Filtrerade bort {len(unmapped_reids)} regionnät (RER*): behåller bara lokalnät")
        
        if len(unmapped_reids) > 0:
            sample_unmapped = unmapped_reids[:3]  # Visa första 3
            print(f"Exempel på filtrerade regionnät: {sample_unmapped}")
    else:
        print("Varning: Kunde inte ladda DMU-mappning - scenario-integration kommer inte fungera")
    
    # Lägg till metadata-kolumner
    df_mapped['Källa_Paverkbara'] = 'Baseline'
    df_mapped['Källa_Kapitalkostnad'] = 'Baseline'
    df_mapped['Uppdaterad_Paverkbara'] = False
    df_mapped['Uppdaterad_Kapitalkostnad'] = False
    
    print(f"Slutlig dataframe: {len(df_mapped)} rader, {len(df_mapped.columns)} kolumner")
    return df_mapped


def load_dmu_mapping(filepath: str = "new_recon.csv") -> pd.DataFrame:
    """
    Laddar mappning mellan REId och DMU från nya reconciliation-filen.
    Används för scenario-integration med kapitalbas.
    """
    # Försök olika sökvägar för new_recon.csv
    possible_paths = [
        filepath,
        f"intaktsram/data/{filepath}",
        f"effektiviseringskrav/data/{filepath}",
        f"data/{filepath}",
        f"../intaktsram/data/{filepath}"
    ]
    
    print(f"DEBUG: Söker efter {filepath}")
    for path in possible_paths:
        print(f"DEBUG: Testar sökväg: {path}")
    
    for path in possible_paths:
        try:
            df = pd.read_csv(path)
            # Kontrollera att vi har förväntade kolumner
            if 'REId' in df.columns and 'DMU' in df.columns:
                # Rensa bort rader utan DMU eller REId
                df_clean = df.dropna(subset=['REId', 'DMU'])
                print(f"Laddade DMU-mappning från {path}: {len(df_clean)} mappningar")
                return df_clean[['REId', 'DMU', 'Företag']].drop_duplicates()
            else:
                print(f"Fil {path} saknar REId eller DMU kolumner: {df.columns.tolist()}")
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Fel vid läsning av {path}: {e}")
            continue
    
    print("Varning: Kunde inte hitta eller läsa DMU-mappning från new_recon.csv")
    return pd.DataFrame(columns=['REId', 'DMU', 'Företag'])


# Uppdatera detect_scenario_updates() i data_loader.py
def detect_scenario_updates() -> Dict[str, Optional[str]]:
    """
    Letar efter scenario-filer från andra sektioner i nya mappstrukturen.
    
    Returns:
        Dict med information om tillgängliga scenarier:
        {
            'effektiviseringskrav': 'scenario/effektiviseringskrav/exports_to_ir/ir_paverkbara_*.parquet' eller None,
            'kapitalbas': 'scenario/kapitalbas/exports_to_ir/ir_kapkost_wacc_*.parquet' eller None
        }
    """
    updates = {
        'effektiviseringskrav': None,
        'kapitalbas': None
    }
    
    # Debug: visa vilka kataloger som kollas
    print("DEBUG: Letar efter scenario-filer...")

    # Leta efter effektiviseringskrav-filer i scenario/effektiviseringskrav/exports_to_ir/
    effkrav_dir = Path("scenario/effektiviseringskrav/exports_to_ir/")
    print(f"DEBUG: Kollar {effkrav_dir}, exists: {effkrav_dir.exists()}")
    if effkrav_dir.exists():
        effkrav_files = list(effkrav_dir.glob("ir_paverkbara_*.parquet"))
        print(f"DEBUG: Hittade {len(effkrav_files)} effektiviseringskrav-filer")
        if effkrav_files:
            # Ta senaste fil baserat på modifierad tid
            latest_effkrav = max(effkrav_files, key=lambda f: f.stat().st_mtime)
            updates['effektiviseringskrav'] = str(latest_effkrav)
            print(f"DEBUG: Senaste effektiviseringskrav-fil: {latest_effkrav}")

    # Leta efter kapitalbas-filer i scenario/kapitalbas/exports_to_ir/
    kapital_dir = Path("scenario/kapitalbas/exports_to_ir/")
    print(f"DEBUG: Kollar {kapital_dir}, exists: {kapital_dir.exists()}")
    if kapital_dir.exists():
        kapital_files = list(kapital_dir.glob("ir_kapkost_wacc_*.parquet"))
        print(f"DEBUG: Hittade {len(kapital_files)} kapitalkostnad-filer")
        for f in kapital_files:
            print(f"DEBUG: Kapitalkostnad-fil: {f}")
        if kapital_files:
            # Ta senaste fil baserat på modifierad tid
            latest_kapital = max(kapital_files, key=lambda f: f.stat().st_mtime)
            updates['kapitalbas'] = str(latest_kapital)
            print(f"DEBUG: Senaste kapitalkostnad-fil: {latest_kapital}")
    else:
        print(f"DEBUG: Kapitalkostnad-katalog finns inte: {kapital_dir}")
    
    print(f"DEBUG: Slutresultat - updates: {updates}")
    return updates


def load_scenario_data(scenario_type: str, scenario_file: str, baseline_df: pd.DataFrame) -> pd.DataFrame:
    """
    Laddar och integrerar scenario-data från andra sektioner med ny DMU-baserad merge.
    
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
            # Stöd både äldre och nya kolumnnamn
            # Ny export från DEA: 'Paverkbara_Target' (periodsumma 2024–2027)
            # Äldre fallback: 'Paverkbara_Nya'
            candidate_cols = [c for c in ['Paverkbara_Target', 'Paverkbara_Nya'] if c in scenario_df.columns]
            if not candidate_cols:
                print("Effektiviseringskrav: Ingen av kolumnerna 'Paverkbara_Target'/'Paverkbara_Nya' hittades")
                return baseline_df

            value_col = candidate_cols[0]

            # Merge-nyckel: använd REId (exporten innehåller både DMU och REId)
            if 'REId' not in scenario_df.columns:
                print("Effektiviseringskrav: Scenario saknar REId -> kan inte merga")
                return baseline_df

            merge_df = scenario_df[['REId', value_col]].rename(columns={value_col: 'Paverkbara_Scenario'})
            result_df = result_df.merge(merge_df, on='REId', how='left')

            mask = result_df['Paverkbara_Scenario'].notna()
            if mask.any():
                result_df.loc[mask, 'Paverkbara_Kostnader'] = result_df.loc[mask, 'Paverkbara_Scenario']
                result_df.loc[mask, 'Källa_Paverkbara'] = 'Scenario (effektiviseringskrav)'
                result_df.loc[mask, 'Uppdaterad_Paverkbara'] = True
                print(f"Effektiviseringskrav: {mask.sum()} REId uppdaterade från {value_col}")

            result_df = result_df.drop(columns=['Paverkbara_Scenario'])

        
        elif scenario_type == 'kapitalbas':
            # Ny logik för kapitalbas med DMU-merge
            required_cols = ['DMU', 'Kapitalkostnad_Ny']
            missing_cols = [col for col in required_cols if col not in scenario_df.columns]
            if missing_cols:
                print(f"Saknade kolumner i kapitalbas-scenario: {missing_cols}")
                return baseline_df
            
            # Kontrollera att baseline har DMU-kolumn
            if 'DMU' not in baseline_df.columns:
                print("Varning: Baseline saknar DMU-kolumn - kan inte merga kapitalbas-scenario")
                return baseline_df
            
            # Förbered merge-data
            merge_cols = ['DMU', 'Kapitalkostnad_Ny']
            optional_cols = ['Avskrivningar_Ny', 'Avkastning_Ny', 'scenario_tag']
            
            # Lägg till tillgängliga optional kolumner
            for col in optional_cols:
                if col in scenario_df.columns:
                    merge_cols.append(col)
            
            merge_df = scenario_df[merge_cols].copy()
            result_df = baseline_df.merge(merge_df, on='DMU', how='left')
            
            # Uppdatera där scenario-data finns
            mask = result_df['Kapitalkostnad_Ny'].notna()
            updated_count = mask.sum()
            
            if updated_count > 0:
                # Uppdatera separerade komponenter om de finns
                if 'Avskrivningar_Ny' in result_df.columns and 'Avskrivningar' in result_df.columns:
                    result_df.loc[mask, 'Avskrivningar'] = result_df.loc[mask, 'Avskrivningar_Ny']
                
                if 'Avkastning_Ny' in result_df.columns and 'Avkastning' in result_df.columns:
                    result_df.loc[mask, 'Avkastning'] = result_df.loc[mask, 'Avkastning_Ny']
                
                # Uppdatera total kapitalkostnad
                result_df.loc[mask, 'Kapitalkostnad_Total'] = result_df.loc[mask, 'Kapitalkostnad_Ny']
                
                # Sätt metadata
                scenario_tag = scenario_df.get('scenario_tag', 'okänd') if 'scenario_tag' in scenario_df.columns else 'kapitalbas'
                result_df.loc[mask, 'Källa_Kapitalkostnad'] = f'Scenario ({scenario_tag})'
                result_df.loc[mask, 'Uppdaterad_Kapitalkostnad'] = True
                
                print(f"Kapitalbas: {updated_count} DMU uppdaterade med nya kapitalkostnader")
            else:
                print("Kapitalbas: Ingen DMU matchade för scenario-uppdatering")
            
            # Rensa temporära kolumner
            temp_cols = ['Kapitalkostnad_Ny', 'Avskrivningar_Ny', 'Avkastning_Ny', 'scenario_tag']
            result_df = result_df.drop(columns=[col for col in temp_cols if col in result_df.columns])
        
        return result_df
        
    except Exception as e:
        print(f"Fel vid laddning av scenario {scenario_type}: {e}")
        return baseline_df


def calculate_intaktsram(df: pd.DataFrame) -> pd.DataFrame:
    """
    Beräknar total intäktsram baserat på komponenter.
    Används när komponenter har uppdaterats via scenarier.
    Stödjer både uppdelad och total kapitalkostnad.
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