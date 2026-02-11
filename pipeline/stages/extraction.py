"""
pipeline/stages/extraction.py

Stage 4: Extraction
Extracts results for user's specific REId.

No print statements - logging handled by PipelineDebugLogger.
"""

from config.column_names import (
    COL_COMPANY_NAME, COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
    COL_TOTEX, COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
)
from pipeline.stages.stage_outputs import (
    PreDeaStageOutput,
    DeaStageOutput,
    ExtractionStageOutput
)


def stage_extraction(
    pre_dea: PreDeaStageOutput,
    dea: DeaStageOutput,
    user_reid: str
) -> ExtractionStageOutput:
    """
    Stage 4: Extract results for user's company.

    Combines data from Pre-DEA (capital_cost_2024/controllable_cost_average) and DEA (efficiency)
    for the specific company.

    Args:
        pre_dea: Output from Pre-DEA stage
        dea: Output from DEA stage
        user_reid: User's REId (ex: "REL00001")

    Returns:
        ExtractionStageOutput with all values for user's company

    Raises:
        ValueError: If REId not found in data
    """

    # Find company row in Pre-DEA data
    df = pre_dea.df_all_companies
    company = df[df['REId'] == user_reid]

    if company.empty:
        raise ValueError(f"REId {user_reid} not found in Pre-DEA data")

    row = company.iloc[0]

    # Find company DEA result
    dea_df = dea.dea_results
    dea_company = dea_df[dea_df['REId'] == user_reid]

    if dea_company.empty:
        raise ValueError(f"REId {user_reid} not found in DEA results")

    dea_row = dea_company.iloc[0]

    # Extract all values
    return ExtractionStageOutput(
        user_reid=user_reid,
        company_name=str(row[COL_COMPANY_NAME]),

        # From Pre-DEA
        capex=float(row[COL_CAPITAL_COST_2024]),
        opex=float(row[COL_CONTROLLABLE_AVG]),
        totex=float(row[COL_TOTEX]),

        # Volumes
        cu=float(row['CU']),
        mw=float(row['MW']),
        ns=float(row['NS']),

        # From DEA
        efficiency=float(dea_row[COL_DEA_EFFICIENCY]) if dea_row[COL_DEA_EFFICIENCY] is not None else None,
        potential=float(dea_row[COL_DEA_POTENTIAL]),
        is_outlier=bool(dea_row[COL_IS_OUTLIER])
    )
