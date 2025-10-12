"""
dmu_aggregation.py - DMU-aggregering och reconciliation
=======================================================

Hanterar mappning mellan id_network och DMU samt aggregering av data
från nätverksnivå till DMU-nivå. Filtrerar bort regionnät (RER/RET)
och behåller endast lokalnät (REL).

Inga UI-beroenden - ren databearbetning som kan användas av både Streamlit och Dash.
"""

from typing import Optional, List, Tuple
from pathlib import Path
import pandas as pd
import warnings

# Import från calculations för konstanter
try:
    from .calculations import YEAR_TO_CODES
except ImportError:
    # När filen körs direkt (inte som modul)
    from calculations import YEAR_TO_CODES


# ============================================================================
# RECONCILIATION - MAPPNING ID_NETWORK ↔ DMU
# ============================================================================

def read_reconciliation(
    path_csv: str,
    required_columns: Optional[List[str]] = None
) -> Optional[pd.DataFrame]:
    """
    Läser reconciliation-fil med standardisering av kolumnnamn.
    
    Reconciliation-filen mappar mellan:
    - id_network (nätverksidentifierare)
    - DMU (Decision Making Unit - företagsidentifierare)
    - Företag (företagsnamn)
    - REId (nätverks-ID sträng för filtrering)
    
    Funktionen hanterar olika varianter av kolumnnamn (case-insensitive)
    och standardiserar till: id_network, DMU, Företag, REId.
    
    Args:
        path_csv: Sökväg till reconciliation CSV-fil
        required_columns: Lista med kolumner som måste finnas (default: None = alla)
        
    Returns:
        DataFrame med standardiserade kolumner, eller None om filen inte kan läsas
        
    Raises:
        FileNotFoundError: Om filen inte existerar
        ValueError: Om required_columns saknas efter standardisering
    """
    # Kontrollera att filen finns
    if not Path(path_csv).exists():
        raise FileNotFoundError(f"Reconciliation-fil hittades inte: {path_csv}")
    
    try:
        rec = pd.read_csv(path_csv)
    except Exception as e:
        warnings.warn(f"Kunde inte läsa reconciliation-fil: {e}")
        return None
    
    # Skapa case-insensitive mappning av kolumnnamn
    cols = {c.lower(): c for c in rec.columns}
    
    # Definiera mappning från olika varianter till standardnamn
    mapping = {}
    
    # id_network: kan heta id_network, idnetwork, network_id
    id_variants = ["id_network", "idnetwork", "network_id"]
    for variant in id_variants:
        if variant in cols:
            mapping['id_network'] = cols[variant]
            break
    
    # DMU: kan heta dmu, DMU, dmu_id
    dmu_variants = ["dmu", "dmu_id"]
    for variant in dmu_variants:
        if variant in cols:
            mapping['DMU'] = cols[variant]
            break
    
    # Företag: kan heta företag, foretag, id_firm, firm, company
    firm_variants = ["företag", "foretag", "id_firm", "firm", "company"]
    for variant in firm_variants:
        if variant in cols:
            mapping['Företag'] = cols[variant]
            break
    
    # REId: kan heta reid, REId, id_network_string, network_string
    reid_variants = ["reid", "id_network_string", "network_string"]
    for variant in reid_variants:
        if variant in cols:
            mapping['REId'] = cols[variant]
            break
    
    # Applicera mappning
    if mapping:
        rec = rec.rename(columns={v: k for k, v in mapping.items()})
    
    # Behåll endast relevanta kolumner som hittades
    keep_cols = [c for c in ["id_network", "DMU", "Företag", "REId"] if c in rec.columns]
    rec = rec[keep_cols].drop_duplicates()
    
    # Validera required_columns om specificerat
    if required_columns:
        missing = [col for col in required_columns if col not in rec.columns]
        if missing:
            raise ValueError(
                f"Reconciliation-fil saknar obligatoriska kolumner: {missing}. "
                f"Tillgängliga: {list(rec.columns)}"
            )
    
    # Konvertera datatyper
    if "DMU" in rec.columns:
        rec["DMU"] = rec["DMU"].astype("Int64")
    
    if "id_network" in rec.columns:
        rec["id_network"] = rec["id_network"].astype("Int64")
    
    if "REId" in rec.columns:
        rec["REId"] = rec["REId"].astype("string").str.strip()
    
    return rec


# ============================================================================
# DMU-AGGREGERING
# ============================================================================

def aggregate_to_dmu(
    df_facit: pd.DataFrame,
    recon_path: str = "effektiviseringskrav/data/reconciliation_id_network_firm_dmu.csv",
    filter_regional: bool = True,
    group_cols: Optional[List[str]] = None,
    agg_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Aggregerar data från id_network-nivå till DMU-nivå.
    
    Processen:
    1. Läser reconciliation-fil för mappning id_network → DMU
    2. Mergar facit-data med DMU-information
    3. Filtrerar bort regionnät om filter_regional=True (behåller REL-nät)
    4. Aggregerar numeriska kolumner per DMU och tidsperiod
    
    Args:
        df_facit: DataFrame med data på id_network-nivå
                  Måste innehålla kolumn 'id_network'
        recon_path: Sökväg till reconciliation CSV-fil
        filter_regional: Om True, filtrera bort regionnät (RER/RET)
        group_cols: Kolumner att gruppera på (default: ["DMU", "Företag", "time"])
        agg_cols: Kolumner att aggregera (default: automatisk från df_facit)
        
    Returns:
        DataFrame aggregerad till DMU-nivå
        
    Raises:
        ValueError: Om id_network-kolumn saknas eller reconciliation misslyckas
    """
    # Validera input
    if 'id_network' not in df_facit.columns:
        raise ValueError("DataFrame måste innehålla kolumn 'id_network'")
    
    # Läs reconciliation
    rec = read_reconciliation(recon_path, required_columns=['id_network', 'DMU'])
    if rec is None:
        raise ValueError(f"Kunde inte läsa reconciliation-fil: {recon_path}")
    
    # Merge med DMU-information
    df_with_dmu = df_facit.merge(rec, on="id_network", how="left")
    
    # Filtrering av regionnät
    if filter_regional and "REId" in df_with_dmu.columns:
        before_count = len(df_with_dmu)
        
        # Behåll endast lokalnät (REId börjar med REL men inte RER)
        df_with_dmu = df_with_dmu[
            df_with_dmu["REId"].astype("string").str.startswith("REL", na=False)
        ]
        
        filtered_count = before_count - len(df_with_dmu)
        if filtered_count > 0:
            warnings.warn(
                f"Filtrerade bort {filtered_count} regionnät (RER/RET). "
                f"Behåller {len(df_with_dmu)} lokalnät (REL)."
            )
    
    # Debug: Kontrollera missing DMU
    missing_dmu = df_with_dmu['DMU'].isna()
    if missing_dmu.any():
        unmapped_networks = df_with_dmu[missing_dmu]['id_network'].unique()
        warnings.warn(
            f"{len(unmapped_networks)} id_network saknar DMU-mappning och exkluderas. "
            f"Exempel: {list(unmapped_networks[:5])}"
        )
        df_with_dmu = df_with_dmu.dropna(subset=['DMU'])
    
    if df_with_dmu.empty:
        raise ValueError("Ingen data kvar efter DMU-mappning och filtrering")
    
    # Default gruppering och aggregering
    if group_cols is None:
        group_cols = ["DMU", "Företag", "time"] if "time" in df_with_dmu.columns else ["DMU", "Företag"]
        # Filtrera till endast kolumner som faktiskt finns
        group_cols = [col for col in group_cols if col in df_with_dmu.columns]
    
    if agg_cols is None:
        # Automatisk detektion av numeriska kolumner att aggregera
        numeric_cols = df_with_dmu.select_dtypes(include=['number']).columns
        # Exkludera grupperings-kolumner och id-kolumner
        exclude = set(group_cols) | {'id_network', 'id_component'}
        agg_cols = [col for col in numeric_cols if col not in exclude]
    
    # Aggregera
    df_aggregated = (df_with_dmu
        .groupby(group_cols, dropna=False)
        .agg({col: 'sum' for col in agg_cols})
        .reset_index()
    )
    
    return df_aggregated


# ============================================================================
# DATAKVALITET - KOMPLETTHETS-KONTROLL
# ============================================================================

def check_year_completeness(
    df_year: pd.DataFrame,
    year: int,
    dmu_col: str = "DMU",
    time_col: str = "time"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Kontrollerar att varje DMU har kompletta data för både H1 och H2.
    
    För ett givet år förväntas varje DMU ha exakt 2 rader (H1 + H2).
    Funktionen identifierar DMU som saknar antingen H1 eller H2.
    
    Args:
        df_year: DataFrame filtrerad till specifikt år
        year: År att kontrollera (t.ex. 2024)
        dmu_col: Namn på DMU-kolumn (default: "DMU")
        time_col: Namn på tidskolumn (default: "time")
        
    Returns:
        Tuple med:
        - DataFrame med kompletta DMU (har både H1 och H2)
        - DataFrame med inkompletta DMU (saknar H1 eller H2)
        
    Raises:
        ValueError: Om obligatoriska kolumner saknas eller år är ogiltigt
    """
    # Validera input
    if dmu_col not in df_year.columns:
        raise ValueError(f"DataFrame saknar kolumn: {dmu_col}")
    
    if time_col not in df_year.columns:
        raise ValueError(f"DataFrame saknar kolumn: {time_col}")
    
    if year not in YEAR_TO_CODES:
        raise ValueError(
            f"Ogiltigt år: {year}. Giltiga år: {list(YEAR_TO_CODES.keys())}"
        )
    
    # Räkna antal halvår per DMU
    counts = df_year.groupby(dmu_col)[time_col].nunique().reset_index(name="n_halvår")
    
    # Identifiera kompletta och inkompletta DMU
    complete_dmus = counts[counts["n_halvår"] == 2][dmu_col]
    incomplete_dmus = counts[counts["n_halvår"] < 2]
    
    # Filtrera original-data
    df_complete = df_year[df_year[dmu_col].isin(complete_dmus)]
    df_incomplete_data = df_year[df_year[dmu_col].isin(incomplete_dmus[dmu_col])]
    
    # Lägg till diagnostisk information i incomplete DataFrame
    if not incomplete_dmus.empty:
        # För varje inkomplett DMU, visa vilka tidskoder som finns
        expected_codes = set(YEAR_TO_CODES[year])
        
        diagnostics = []
        for dmu in incomplete_dmus[dmu_col]:
            dmu_data = df_year[df_year[dmu_col] == dmu]
            present_codes = set(dmu_data[time_col].unique())
            missing_codes = expected_codes - present_codes
            
            diagnostics.append({
                dmu_col: dmu,
                'n_halvår': len(present_codes),
                'present_codes': sorted(present_codes),
                'missing_codes': sorted(missing_codes)
            })
        
        incomplete_dmus = pd.DataFrame(diagnostics)
    
    return df_complete, incomplete_dmus


def get_complete_dmus_for_year(
    df: pd.DataFrame,
    year: int,
    warn: bool = True
) -> pd.DataFrame:
    """
    Hjälpfunktion som returnerar endast kompletta DMU för ett år.
    
    Convenience wrapper runt check_year_completeness som direkt returnerar
    kompletta data och varnar om inkompletta DMU hittas.
    
    Args:
        df: DataFrame med data
        year: År att filtrera (t.ex. 2024)
        warn: Om True, visa varning för inkompletta DMU
        
    Returns:
        DataFrame med endast kompletta DMU
    """
    # Filtrera till rätt år först
    if year not in YEAR_TO_CODES:
        raise ValueError(f"Ogiltigt år: {year}")
    
    df_year = df[df["time"].isin(YEAR_TO_CODES[year])]
    
    # Kontrollera komplethet
    df_complete, df_incomplete = check_year_completeness(df_year, year)
    
    # Varna om inkompletta DMU
    if warn and not df_incomplete.empty:
        warnings.warn(
            f"{len(df_incomplete)} DMU saknar H1 eller H2 för {year} och exkluderas:\n"
            f"{df_incomplete.to_string()}"
        )
    
    return df_complete


# ============================================================================
# TESTER
# ============================================================================

if __name__ == "__main__":
    """
    Tester för DMU-aggregering och reconciliation.
    """
    print("Testing dmu_aggregation.py...")
    print("=" * 60)
    
    # Test 1: Reconciliation-läsning (simulerad data)
    print("\nTest 1: Reconciliation-läsning")
    import tempfile
    import os
    
    # Skapa test-CSV
    test_csv_content = """id_network,DMU,Företag,REId
1,100,Test AB,REL001
2,100,Test AB,REL002
3,200,Demo AB,REL003
4,200,Demo AB,RER001
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(test_csv_content)
        test_csv_path = f.name
    
    try:
        rec = read_reconciliation(test_csv_path)
        print(f"Läste {len(rec)} rader: {'' if len(rec) == 4 else ''}")
        print(f"Har kolumn 'DMU': {'' if 'DMU' in rec.columns else ''}")
        print(f"Har kolumn 'REId': {'' if 'REId' in rec.columns else ''}")
    finally:
        os.unlink(test_csv_path)
    
    # Test 2: DMU-aggregering (simulerad data)
    print("\nTest 2: DMU-aggregering")
    
    # Skapa test-facit data
    test_facit = pd.DataFrame({
        'id_network': [1, 1, 2, 2, 3, 3, 4, 4],
        'time': [229, 230, 229, 230, 229, 230, 229, 230],
        'capcost_sum': [100, 110, 200, 220, 300, 330, 400, 440]
    })
    
    # Skapa test-reconciliation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(test_csv_content)
        test_csv_path = f.name
    
    try:
        # Aggregera med filtrering (ska ta bort id_network=4 som är RER)
        df_agg = aggregate_to_dmu(
            test_facit,
            recon_path=test_csv_path,
            filter_regional=True
        )
        
        print(f"Original id_networks: 4, Efter filtrering: {df_agg['DMU'].nunique()} DMU")
        print(f"Regionnät (RER) filtrerat: {'' if len(df_agg) < len(test_facit) else ''}")
        print(f"Data aggregerad: {'' if 'capcost_sum' in df_agg.columns else ''}")
        
        # Kontrollera att DMU 100 har summan av id_network 1 och 2
        if 100 in df_agg['DMU'].values:
            dmu100_sum = df_agg[df_agg['DMU'] == 100]['capcost_sum'].sum()
            expected = 100 + 110 + 200 + 220  # Summa för id_network 1 och 2
            print(f"DMU 100 totalsumma korrekt: {'' if abs(dmu100_sum - expected) < 0.1 else ''}")
        
    finally:
        os.unlink(test_csv_path)
    
    # Test 3: Kompletthets-kontroll
    print("\nTest 3: Kompletthets-kontroll")
    
    # Skapa test-data med både kompletta och inkompletta DMU
    test_df = pd.DataFrame({
        'DMU': [1, 1, 2, 3, 3],  # DMU 1 och 3 kompletta, DMU 2 inkomplett
        'time': [229, 230, 229, 229, 230],
        'value': [10, 20, 30, 40, 50]
    })
    
    df_complete, df_incomplete = check_year_completeness(test_df, 2024)
    
    print(f"Kompletta DMU: {len(df_complete['DMU'].unique())} (förväntat: 2)")
    print(f"Inkompletta DMU: {len(df_incomplete)} (förväntat: 1)")
    print(f"Inkomplett DMU är 2: {'' if 2 in df_incomplete['DMU'].values else ''}")
    
    print("\n" + "=" * 60)
    print("Alla tester slutförda.")