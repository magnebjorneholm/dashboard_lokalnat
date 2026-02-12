"""
data_loaders/baseline_data.py

Baseline data loader.
Loads all data needed for baseline calculations.

Column names are renamed from Swedish to English at the load boundary.
After loading, all DataFrames use canonical English names from config.column_names.
"""

from dataclasses import dataclass
import pandas as pd
from typing import Dict, Optional
from pathlib import Path

from config.column_names import (
    COL_REID, COL_DMU, COL_COMPANY_NAME,
    COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG, COL_DEPRECIATION_2024,
    COL_RETURN_2024, COL_RETURN_2025, COL_RETURN_2026, COL_RETURN_2027,
    COL_RETURN_PERIOD, COL_TOTEX,
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL,
    COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL,
    DATA_MODELLER_RENAME, EIS_DEA_RENAME, SDF_IR_RENAME,
    SDF_IR_REVENUE_FRAME_PATTERNS, COL_REVENUE_FRAME,
    COL_CAPITAL_COST_PERIOD, COL_DEPRECIATION_PERIOD, COL_RETURN_PERIOD,
)


def _find_data_file(filename: str, data_path: Optional[str] = None) -> Path:
    """Search for a data file in standard locations and return the first match.

    Search order: data_path/ (if given), cwd, data/, /mnt/project/.
    """
    search_paths = []
    if data_path:
        search_paths.append(Path(data_path) / filename)
    search_paths.extend([
        Path(filename),
        Path("data") / filename,
        Path("/mnt/project") / filename,
    ])
    for path in search_paths:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Could not find {filename}. "
        f"Tried: {[str(p) for p in search_paths]}"
    )


@dataclass(frozen=True)
class BaselineData:
    """
    Immutable baseline data container.
    Frozen = read-only, cannot be modified after creation.
    """
    # Main data
    df_all_companies: pd.DataFrame  # 148 rows with CAPEX, OPEX, volumes, return per year
    dea_results: pd.DataFrame       # 148 rows from EIs_DEA.xlsx
    sdf_ir: pd.DataFrame
    sdf_controllable: pd.DataFrame
    sdf_non_controllable: pd.DataFrame
    reconciliation: pd.DataFrame    # Mapping REId <-> id_network (also has DMU for compatibility)
    
    # Parameters
    wacc: float = 0.0453  # Real WACC before tax (= BASELINE_WACC from wacc_calculations)


def _load_data_modeller(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load Data_modeller.xlsx with DEA data and per-year return.

    Args:
        data_path: Path to data folder. If None, use default paths.

    Returns:
        DataFrame with columns:
        ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'Avskrivning', 'Avkastning',
         'CU', 'MW', 'NS', 'MWhl', 'MWhh', 'TOTEX', 'Kapitalkostnad_2024',
         'Avkastning_2024', 'Avkastning_2025', 'Avkastning_2026', 'Avkastning_2027',
         'Avkastning_Period']
    """
    data_file = _find_data_file("Data_modeller.xlsx", data_path)

    # Try reading from different sheet names (backwards compatibility)
    df = None
    sheet_names_to_try = ["Körning", "Sheet1", 0]

    for sheet_name in sheet_names_to_try:
        try:
            df = pd.read_excel(data_file, sheet_name=sheet_name, engine="openpyxl")
            break
        except Exception:
            continue

    if df is None:
        raise RuntimeError(
            f"Could not read Data_modeller.xlsx. "
            f"Tried sheets: {sheet_names_to_try}"
        )

    # Validate required columns
    required_cols = ['DMU', 'REId', 'Företag', 'OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in Data_modeller.xlsx: {missing}")

    # Convert numeric columns
    numeric_cols = ['OPEXp', 'CAPEX', 'CU', 'MW', 'NS', 'MWhl', 'MWhh']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Handle Avskrivning and Avkastning (aggregate)
    if 'Avskrivning' in df.columns:
        df['Avskrivning'] = pd.to_numeric(df['Avskrivning'], errors="coerce")
    else:
        df['Avskrivning'] = df['CAPEX'] * 0.5
        print("  WARNING: Avskrivning missing, using approximation (CAPEX * 0.5)")

    if 'Avkastning' in df.columns:
        df['Avkastning'] = pd.to_numeric(df['Avkastning'], errors="coerce")
    else:
        df['Avkastning'] = df['CAPEX'] * 0.5
        print("  WARNING: Avkastning missing, using approximation (CAPEX * 0.5)")

    # Handle per-year return columns
    yearly_return_cols = ['Avkastning_2024', 'Avkastning_2025',
                          'Avkastning_2026', 'Avkastning_2027']

    for col in yearly_return_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = df['Avkastning']
            print(f"  WARNING: {col} missing, using Avkastning as approximation")

    # Handle Avkastning_Period (period sum)
    if 'Avkastning_Period' in df.columns:
        df['Avkastning_Period'] = pd.to_numeric(df['Avkastning_Period'], errors="coerce")
    else:
        df['Avkastning_Period'] = (
            df['Avkastning_2024'] + df['Avkastning_2025'] +
            df['Avkastning_2026'] + df['Avkastning_2027']
        )
        print("  WARNING: Avkastning_Period missing, calculated from per-year values")

    # Calculate TOTEX (before rename, using original column names)
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]

    # Drop legacy aggregate columns that conflict with per-year columns
    # Avkastning (aggregate) conflicts with Avkastning_2024; per-year is more accurate
    if 'Avkastning' in df.columns and 'Avkastning_2024' in df.columns:
        df = df.drop(columns=['Avkastning'])

    # Rename Swedish → English at the load boundary
    df = df.rename(columns=DATA_MODELLER_RENAME)

    return df


def _load_eis_dea(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load Ei's reference DEA results from Excel.

    Args:
        data_path: Path to data folder. If None, use default paths.

    Returns:
        DataFrame with columns:
        - REId: Network operator ID (primary key)
        - DMU: Company DMU (also present for compatibility)
        - Företag: Company name
        - Effektivitet: Efficiency value (or None for outliers)
        - Supereffektivitet: Super-efficiency value (or None for outliers)
        - potential: Improvement potential
        - Effkrav_proc: Annual efficiency requirement
        - is_outlier: Boolean flag
    """
    data_file = _find_data_file("EIs_DEA.xlsx", data_path)

    try:
        df = pd.read_excel(data_file, sheet_name='Körning', engine='openpyxl')
    except Exception as e:
        raise RuntimeError(f"Error reading EIs_DEA.xlsx: {e}")

    # Handle outliers
    df['is_outlier'] = df['Effektivitet'].astype(str).str.upper() == 'OUTLIER'

    # Convert Effektivitet to float (None for outliers)
    def parse_efficiency(val):
        if str(val).upper() == 'OUTLIER':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    df['Effektivitet'] = df['Effektivitet'].apply(parse_efficiency)

    if 'Supereffektivitet' in df.columns:
        df['Supereffektivitet'] = df['Supereffektivitet'].apply(parse_efficiency)
    else:
        df['Supereffektivitet'] = None

    # Handle potential
    if 'potential' in df.columns:
        df['potential'] = pd.to_numeric(df['potential'], errors='coerce').fillna(0.0)
    else:
        df['potential'] = 0.0

    # Convert Effkrav_proc to float
    if 'Effkrav_proc' in df.columns:
        df['Effkrav_proc'] = pd.to_numeric(df['Effkrav_proc'], errors='coerce').fillna(0.0)
    else:
        df['Effkrav_proc'] = 0.0

    # Rename Swedish → English at the load boundary
    df = df.rename(columns=EIS_DEA_RENAME)

    return df


def _load_sdf_data(data_path: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Load SDF data from "Löpande kostnader från SDF" Excel file.

    Args:
        data_path: Path to data folder

    Returns:
        Dict with three DataFrames: 'ir', 'controllable', 'non_controllable'
    """
    data_file = _find_data_file("Löpande kostnader från SDF 2024-27.xlsx", data_path)

    result = {}

    # Sheet names to try for each type
    sheet_mappings = {
        'ir': ['IR 2024-2027', 'IR 2024-27', 'IR'],
        'controllable': ['Påverkbara', 'Paverkbara'],
        'non_controllable': ['Opåverkbara', 'Opaverkbara'],
    }

    for key, sheet_names in sheet_mappings.items():
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(data_file, sheet_name=sheet_name, engine="openpyxl")
                result[key] = df
                break
            except Exception:
                continue

        if key not in result:
            print(f"  WARNING: Could not read SDF sheet '{key}'")
            result[key] = pd.DataFrame()

    # Rename IR sheet columns: Swedish → English at the load boundary
    if 'ir' in result and not result['ir'].empty:
        ir_df = result['ir']
        ir_df = ir_df.rename(columns=SDF_IR_RENAME)
        # Rename revenue frame total column (varies by file version)
        for pattern in SDF_IR_REVENUE_FRAME_PATTERNS:
            for col in ir_df.columns:
                if pattern.lower() in col.lower():
                    ir_df = ir_df.rename(columns={col: COL_REVENUE_FRAME})
                    break
        # Normalize REId column name
        if 'REid' in ir_df.columns and 'REId' not in ir_df.columns:
            ir_df = ir_df.rename(columns={'REid': 'REId'})
        result['ir'] = ir_df

    return result


def _load_reconciliation(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load reconciliation mapping between REId, id_network and DMU.

    Args:
        data_path: Path to data folder

    Returns:
        DataFrame with mappings
    """
    data_file = _find_data_file("reconciliation_id_network_firm_dmu.csv", data_path)

    df = pd.read_csv(data_file)

    # Handle different column names (REId vs id_network_string)
    if 'id_network_string' in df.columns and 'REId' not in df.columns:
        df['REId'] = df['id_network_string']

    return df


def load_baseline_data(data_path: Optional[str] = None) -> BaselineData:
    """
    Main function to load all baseline data.

    Args:
        data_path: Path to data folder. If None, use default paths.

    Returns:
        BaselineData object with all data

    Raises:
        FileNotFoundError: If critical files are missing
        RuntimeError: If loading fails
    """

    # 1. Load Data_modeller.xlsx
    print("Loading Data_modeller.xlsx...")
    df_all_companies = _load_data_modeller(data_path)
    print(f"  Loaded {len(df_all_companies)} companies")

    # Verify per-year return
    yearly_cols = [COL_RETURN_2024, COL_RETURN_2025,
                   COL_RETURN_2026, COL_RETURN_2027]
    has_yearly = all(col in df_all_companies.columns for col in yearly_cols)
    if has_yearly:
        print(f"  Per-year return available (2024-2027)")
    else:
        print(f"  Per-year return missing or approximated")

    # 2. Load EIs_DEA.xlsx
    print("Loading EIs_DEA.xlsx...")
    dea_results = _load_eis_dea(data_path)
    print(f"  Loaded DEA results for {len(dea_results)} companies")

    # 3. Load SDF data
    print("Loading SDF running costs...")
    sdf_data = _load_sdf_data(data_path)
    n_ir = len(sdf_data.get('ir', pd.DataFrame()))
    n_non_ctrl = len(sdf_data.get('non_controllable', pd.DataFrame()))
    n_ctrl = len(sdf_data.get('controllable', pd.DataFrame()))
    print(f"  Loaded SDF data (IR: {n_ir}, Non-controllable: {n_non_ctrl}, Controllable: {n_ctrl} rows)")

    # 4. Load reconciliation mapping
    print("Loading reconciliation...")
    reconciliation = _load_reconciliation(data_path)
    print(f"  Loaded reconciliation ({len(reconciliation)} mappings)")

    # 5. Validate that all datasets have the same number of companies
    n_companies = len(df_all_companies)
    n_dea = len(dea_results)

    if n_companies != n_dea:
        print(f"WARNING: Data_modeller has {n_companies} companies but EIs_DEA has {n_dea}")

    return BaselineData(
        df_all_companies=df_all_companies,
        dea_results=dea_results,
        sdf_ir=sdf_data['ir'],
        sdf_controllable=sdf_data['controllable'],
        sdf_non_controllable=sdf_data['non_controllable'],
        reconciliation=reconciliation,
        wacc=0.0453,  # = BASELINE_WACC from wacc_calculations
    )