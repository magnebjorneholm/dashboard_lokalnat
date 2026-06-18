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

from config.data_paths import require_dataset, dataset_path
from data_loaders._cache import cached
from data_loaders.schemas import require_columns


def _load_snapshot(snap_name: str):
    """Return the frozen parquet snapshot if present (and no explicit override)."""
    snap = dataset_path(snap_name)
    return pd.read_parquet(snap) if snap.exists() else None
from config.column_names import (
    COL_REID, COL_DMU, COL_COMPANY_NAME, COL_COMPANY_NAME_SHORT, COL_DISPLAY_NAME,
    COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
    COL_RETURN_2024, COL_RETURN_2025, COL_RETURN_2026, COL_RETURN_2027,
    COL_RETURN_PERIOD, COL_TOTEX,
    COL_DEA_EFFICIENCY, COL_DEA_SUPER_EFF, COL_DEA_POTENTIAL,
    COL_IS_OUTLIER, COL_EFF_REQ_ANNUAL,
    DATA_MODELLER_RENAME, EIS_DEA_RENAME, SDF_IR_RENAME,
    SDF_IR_REVENUE_FRAME_PATTERNS, COL_REVENUE_FRAME,
    COL_CAPITAL_COST_PERIOD, COL_DEPRECIATION_PERIOD,
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

    # Grunddata (detailed cost data from parquet files)
    controllable_detail: pd.DataFrame     # From controllable_a.parquet
    controllable_meta: pd.DataFrame       # From controllable_meta.parquet
    non_controllable_detail: pd.DataFrame # From non_controllable_a.parquet

    # Parameters
    wacc: float = 0.0453  # Real WACC before tax (= BASELINE_WACC from wacc_calculations)


def _load_data_modeller(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load Data_modeller (frozen snapshot if available, else parse the Excel)."""
    if data_path is None:
        snap = _load_snapshot("snap_data_modeller")
        if snap is not None:
            return require_columns(snap, "data_modeller")
    return require_columns(_parse_data_modeller(data_path), "data_modeller")


def _parse_data_modeller(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load Data_modeller.xlsx with company identifiers, volumes, and OPEXp/CAPEX.

    Capital cost data (return, depreciation) is sourced from capcost_a.parquet,
    not from this file. Avkastning columns have been removed from the Excel.

    Args:
        data_path: Path to data folder. If None, use default paths.

    Returns:
        DataFrame with columns (after rename):
        ['DMU', 'REId', 'company_name', 'controllable_cost_average',
         'capital_cost_2024', 'CU', 'MW', 'NS', 'MWhl', 'MWhh', 'totex_first_year']
    """
    data_file = require_dataset("data_modeller", data_path)

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

    # Calculate TOTEX (before rename, using original column names)
    df["TOTEX"] = df["OPEXp"] + df["CAPEX"]

    # Rename Swedish → English at the load boundary
    df = df.rename(columns=DATA_MODELLER_RENAME)

    return df


def _aggregate_return_from_capcost(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Aggregate return on assets per company per year from capcost_a.parquet.

    Returns:
        DataFrame with REId, return_on_assets_2024-2027, return_on_assets_period
    """
    from data_loaders.rab_data import load_capcost_a
    from config.time_codes import YEAR_TO_TIMECODES

    df = load_capcost_a(data_path)
    df = df.copy()
    df['return_total'] = df['return_ord'] + df['return_tail']

    # Map timecodes to years
    tc_to_year = {}
    for year, tcs in YEAR_TO_TIMECODES.items():
        for tc in tcs:
            tc_to_year[tc] = year
    df['year'] = df['time'].map(tc_to_year)

    # Aggregate per company per year
    yearly = df.groupby(['id_network', 'year'])['return_total'].sum().reset_index()
    pivot = yearly.pivot(index='id_network', columns='year', values='return_total').reset_index()

    # Map id_network → REId
    pivot['REId'] = pivot['id_network'].apply(lambda x: f"REL{x:05d}")

    # Rename to canonical column names
    year_col_map = {
        2024: COL_RETURN_2024,
        2025: COL_RETURN_2025,
        2026: COL_RETURN_2026,
        2027: COL_RETURN_2027,
    }
    pivot = pivot.rename(columns=year_col_map)

    return_cols = [COL_RETURN_2024, COL_RETURN_2025, COL_RETURN_2026, COL_RETURN_2027]
    pivot[COL_RETURN_PERIOD] = pivot[return_cols].sum(axis=1)

    return pivot[['REId'] + return_cols + [COL_RETURN_PERIOD]]


def _load_eis_dea(data_path: Optional[str] = None) -> pd.DataFrame:
    """Load Ei DEA results (frozen snapshot if available, else parse the Excel)."""
    if data_path is None:
        snap = _load_snapshot("snap_eis_dea")
        if snap is not None:
            return require_columns(snap, "eis_dea")
    return require_columns(_parse_eis_dea(data_path), "eis_dea")


def _parse_eis_dea(data_path: Optional[str] = None) -> pd.DataFrame:
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
    data_file = require_dataset("eis_dea", data_path)

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

    Not frozen to parquet: the controllable / non-controllable sheets contain
    heterogeneous Excel columns that do not round-trip through parquet safely.

    Args:
        data_path: Path to data folder

    Returns:
        Dict with three DataFrames: 'ir', 'controllable', 'non_controllable'
    """
    data_file = require_dataset("sdf_running_costs", data_path)

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
    data_file = require_dataset("reconciliation", data_path)

    df = pd.read_csv(data_file)

    # Handle different column names (REId vs id_network_string)
    if 'id_network_string' in df.columns and 'REId' not in df.columns:
        df['REId'] = df['id_network_string']

    return require_columns(df, "reconciliation")


def _load_company_names(data_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load curated company names (full + short) keyed on REId.

    Source: data/reference/company_names.csv (see scripts/generate_company_names.py).

    Returns:
        DataFrame with columns [REId, company_name, company_name_short].
    """
    data_file = require_dataset("company_names", data_path)
    df = require_columns(pd.read_csv(data_file), "company_names")
    return df.rename(columns={
        "name_full": COL_COMPANY_NAME,
        "name_short": COL_COMPANY_NAME_SHORT,
    })[["REId", COL_COMPANY_NAME, COL_COMPANY_NAME_SHORT]]


@cached(ttl=3600, show_spinner="Loading baseline data...")
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

    # 1b. Override names with the curated list (full + short), keyed on REId.
    #     Falls back to the Excel name where a REId is missing from the list.
    company_names = _load_company_names(data_path)
    excel_name = df_all_companies[COL_COMPANY_NAME]
    df_all_companies = df_all_companies.drop(columns=[COL_COMPANY_NAME])
    df_all_companies = df_all_companies.merge(company_names, on="REId", how="left")
    df_all_companies[COL_COMPANY_NAME] = df_all_companies[COL_COMPANY_NAME].fillna(excel_name)
    df_all_companies[COL_COMPANY_NAME_SHORT] = df_all_companies[COL_COMPANY_NAME_SHORT].fillna(
        df_all_companies[COL_COMPANY_NAME]
    )
    df_all_companies[COL_DISPLAY_NAME] = (
        df_all_companies[COL_COMPANY_NAME_SHORT] + " (" + df_all_companies["REId"] + ")"
    )

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

    # 5. Load grunddata (controllable/non-controllable detail parquets)
    print("Loading grunddata parquets...")
    from data_loaders.cost_data import (
        load_controllable_detail, load_controllable_meta, load_non_controllable_detail
    )
    controllable_detail = load_controllable_detail(data_path)
    controllable_meta = load_controllable_meta(data_path)
    non_controllable_detail = load_non_controllable_detail(data_path)
    print(f"  Loaded grunddata (ctrl: {len(controllable_detail)}, meta: {len(controllable_meta)}, "
          f"nonctrl: {len(non_controllable_detail)} rows)")

    # 6. Add return on assets from capcost_a.parquet
    print("Aggregating return on assets from capcost_a...")
    return_df = _aggregate_return_from_capcost(data_path)
    df_all_companies = df_all_companies.merge(return_df, on="REId", how="left")
    print(f"  Added per-year return (2024-2027) for {len(return_df)} companies")

    # 8. Replace OPEXp with SDF-derived controllable_cost_average.
    #    Preserve the raw Data_modeller OPEXp first: it is the exact cost input
    #    Ei ran the baseline DEA on (the SDF-derived value diverges for ~109
    #    firms — see eis_dea_metod.md). Keeping both lets an exact-replication
    #    profile feed raw OPEXp to the DEA while everything else uses the
    #    SDF-derived controllable_cost_average.
    from config.column_names import COL_OPEXP_RAW
    df_all_companies[COL_OPEXP_RAW] = df_all_companies[COL_CONTROLLABLE_AVG]

    from calculations.opex.cost_aggregation import aggregate_controllable
    sdf_derived = aggregate_controllable(controllable_detail, controllable_meta)
    # Compute opexp_equivalent = controllable_cost_average + neo_adjustments/4
    # This matches how OPEXp was used: as the DEA input (average + annualized neo)
    sdf_derived["opexp_equivalent"] = (
        sdf_derived[COL_CONTROLLABLE_AVG]
        + sdf_derived["neo_adjustments_period"] / 4
    )
    # Replace OPEXp-based controllable_cost_average in df_all_companies
    df_all_companies = df_all_companies.drop(columns=[COL_CONTROLLABLE_AVG], errors="ignore")
    df_all_companies = df_all_companies.merge(
        sdf_derived[["REId", "opexp_equivalent"]].rename(
            columns={"opexp_equivalent": COL_CONTROLLABLE_AVG}
        ),
        on="REId",
        how="left",
    )
    # Recalculate TOTEX with SDF-derived value
    df_all_companies[COL_TOTEX] = (
        df_all_companies[COL_CONTROLLABLE_AVG] + df_all_companies[COL_CAPITAL_COST_2024]
    )
    print(f"  Replaced OPEXp with SDF-derived controllable_cost_average")

    # 9. Validate
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
        controllable_detail=controllable_detail,
        controllable_meta=controllable_meta,
        non_controllable_detail=non_controllable_detail,
        wacc=0.0453,  # = BASELINE_WACC from wacc_calculations
    )