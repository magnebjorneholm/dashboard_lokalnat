"""
pipeline/stages/extraction.py

Stage 4: Extraction
Extraherar resultat för användarens specifik REId.
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
    Stage 4: Extrahera resultat för användarens företag.
    
    Kombinerar data från Pre-DEA (Kapitalkostnad_2024/OPEXp) och DEA (efficiency)
    för det specifika företaget.
    
    Args:
        pre_dea: Output från Pre-DEA stage
        dea: Output från DEA stage
        user_reid: Användarens REId (ex: "REL00001")
        
    Returns:
        ExtractionStageOutput med alla värden för användarens företag
        
    Raises:
        ValueError: Om REId inte finns i data
    """
    
    # Hitta företagets rad i Pre-DEA data
    df = pre_dea.df_all_companies
    company = df[df['REId'] == user_reid]
    
    if company.empty:
        raise ValueError(f"REId {user_reid} finns inte i Pre-DEA data")
    
    row = company.iloc[0]
    
    # Hitta företagets DEA-resultat
    dea_df = dea.dea_results
    dea_company = dea_df[dea_df['REId'] == user_reid]
    
    if dea_company.empty:
        raise ValueError(f"REId {user_reid} finns inte i DEA-resultat")
    
    dea_row = dea_company.iloc[0]
    
    # Extrahera alla värden
    return ExtractionStageOutput(
        user_reid=user_reid,
        foretag=str(row['Företag']),
        
        # Från Pre-DEA
        capex=float(row['Kapitalkostnad_2024']),
        opex=float(row['OPEXp']),
        totex=float(row['TOTEX']),
        
        # Volumes
        cu=float(row['CU']),
        mw=float(row['MW']),
        ns=float(row['NS']),
        
        # Från DEA
        efficiency=float(dea_row['Effektivitet']) if dea_row['Effektivitet'] is not None else None,
        potential=float(dea_row['potential']),
        is_outlier=bool(dea_row['is_outlier'])
    )