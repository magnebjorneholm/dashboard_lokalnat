"""
pipeline/stages/extraction.py

Stage 4: Extraction
Extracts results for user's specific REId.

No print statements - logging handled by PipelineDebugLogger.
"""

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
    
    Combines data from Pre-DEA (Kapitalkostnad_2024/OPEXp) and DEA (efficiency)
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
        foretag=str(row['Företag']),
        
        # From Pre-DEA
        capex=float(row['Kapitalkostnad_2024']),
        opex=float(row['OPEXp']),
        totex=float(row['TOTEX']),
        
        # Volumes
        cu=float(row['CU']),
        mw=float(row['MW']),
        ns=float(row['NS']),
        
        # From DEA
        efficiency=float(dea_row['Effektivitet']) if dea_row['Effektivitet'] is not None else None,
        potential=float(dea_row['potential']),
        is_outlier=bool(dea_row['is_outlier'])
    )