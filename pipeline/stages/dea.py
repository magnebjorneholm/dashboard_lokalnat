"""
pipeline/stages/dea.py

Stage 3: DEA
Runs Data Envelopment Analysis for efficiency measurement.

Supports 2 methods:
1. baseline - Use Ei's baseline DEA results
2. dea - Run new DEA model with custom inputs/outputs

NOTE: If CAPEX modified in Pre-DEA, new DEA always runs for methodological
consistency, even if user selected "baseline". This is because baseline-DEA
was calculated with original CAPEX and is not valid for modified data.

No print statements - logging handled by PipelineDebugLogger.
"""

from config import DeaConfig, EfficiencyMethod
from pipeline.stages.stage_outputs import PreDeaStageOutput, DeaStageOutput, BaselineStageOutput
from calculations import run_dea_analysis
from calculations.dea_calculations import BASELINE_DEA_SPEC


def stage_dea(
    pre_dea: PreDeaStageOutput,
    config: DeaConfig,
    baseline: BaselineStageOutput = None
) -> DeaStageOutput:
    """
    Stage 3: Run DEA analysis.

    Args:
        pre_dea: Output from Pre-DEA stage
        config: DeaConfig with method and parameters
        baseline: BaselineStageOutput (required for baseline method)

    Returns:
        DeaStageOutput with:
        - dea_results: 148 rows with efficiency, potential, is_outlier
        - dea_method: Method used
        - dea_executed: True if new DEA was run

    Raises:
        ValueError: If invalid method or missing baseline
    """

    capex_modified = pre_dea.capex_modified
    opex_modified = getattr(pre_dea, 'opex_modified', False)
    data_modified = capex_modified or opex_modified

    # =========================================================================
    # SCENARIO 1: Baseline DEA (no data modification)
    # =========================================================================
    if config.method == EfficiencyMethod.BASELINE and not data_modified:

        if baseline is None:
            raise ValueError("Baseline required for baseline DEA method")

        return DeaStageOutput(
            dea_results=baseline.dea_baseline.copy(),
            dea_method="baseline",
            dea_executed=False
        )

    # =========================================================================
    # SCENARIO 2: Baseline spec with modified data (run new DEA)
    # =========================================================================
    elif config.method == EfficiencyMethod.BASELINE and data_modified:

        dea_results = run_dea_analysis(
            df=pre_dea.df_all_companies,
            model_spec=BASELINE_DEA_SPEC
        )

        return DeaStageOutput(
            dea_results=dea_results,
            dea_method="baseline_recalculated",
            dea_executed=True
        )

    # =========================================================================
    # SCENARIO 3: Custom DEA
    # =========================================================================
    elif config.method == EfficiencyMethod.DEA:

        # Extract model specification from config
        model_spec = {
            'inputs': config.inputs,
            'outputs': config.outputs,
            'rts': config.rts,
            'orientation': config.orientation,
            'outlier_params': {
                'q_lower': config.q_lower,
                'q_upper': config.q_upper,
                'multiplier': config.multiplier
            }
        }

        dea_results = run_dea_analysis(
            df=pre_dea.df_all_companies,
            model_spec=model_spec
        )

        return DeaStageOutput(
            dea_results=dea_results,
            dea_method="dea",
            dea_executed=True
        )

    else:
        raise ValueError(f"Unknown DEA method: {config.method}")
