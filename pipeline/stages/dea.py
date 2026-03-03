"""
pipeline/stages/dea.py

Stage 3: Efficiency estimation
Runs DEA or loads pre-computed StoNED results.

Supports 3 methods:
1. baseline - Use Ei's baseline DEA results
2. dea - Run new DEA model with custom inputs/outputs
3. stoned - Load pre-computed StoNED efficiency scores

DEA always uses baseline (historical) OPEX/CAPEX/TOTEX values. User changes
to cost levels via pre_dea (scaling, overrides, WACC changes) do NOT affect
DEA inputs — they only affect the revenue frame in post_dea. The rationale
is that DEA inputs are based on historical data that has already occurred.

StoNED results are pre-computed offline and stored in data/stoned/. The
outputs use the same column structure as DEA so downstream stages work
unchanged.

No print statements - logging handled by PipelineDebugLogger.
"""

from typing import Optional

from config import DeaConfig, EfficiencyMethod
from pipeline.stages.stage_outputs import PreDeaStageOutput, DeaStageOutput, BaselineStageOutput
from calculations import run_dea_analysis
from calculations.frontier.dea_calculations import BASELINE_DEA_SPEC


def stage_dea(
    pre_dea: Optional[PreDeaStageOutput] = None,
    *,
    config: DeaConfig,
    baseline: BaselineStageOutput = None
) -> DeaStageOutput:
    """
    Stage 3: Run DEA analysis.

    DEA always uses baseline cost data (OPEX/CAPEX/TOTEX), regardless of
    user modifications in pre_dea. Only the model specification (inputs,
    outputs, RTS, outlier params) can be changed by the user.

    Args:
        pre_dea: Output from Pre-DEA stage (used for metadata only)
        config: DeaConfig with method and parameters
        baseline: BaselineStageOutput (required — provides baseline cost data)

    Returns:
        DeaStageOutput with:
        - dea_results: 148 rows with efficiency, potential, is_outlier
        - dea_method: Method used
        - dea_executed: True if new DEA was run

    Raises:
        ValueError: If invalid method or missing baseline
    """

    if baseline is None:
        raise ValueError("Baseline required for DEA stage")

    # =========================================================================
    # SCENARIO 1: Baseline DEA — return Ei's published results
    # =========================================================================
    if config.method == EfficiencyMethod.BASELINE:

        return DeaStageOutput(
            dea_results=baseline.dea_baseline.copy(),
            dea_method="baseline",
            dea_executed=False
        )

    # =========================================================================
    # SCENARIO 2: Custom DEA — run with baseline cost data
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

        # Always use baseline data for DEA (historical values)
        dea_results = run_dea_analysis(
            df=baseline.df_all_companies,
            model_spec=model_spec
        )

        return DeaStageOutput(
            dea_results=dea_results,
            dea_method="dea",
            dea_executed=True
        )

    # =========================================================================
    # SCENARIO 3: Pre-computed StoNED — load stored results
    # =========================================================================
    elif config.method == EfficiencyMethod.STONED:

        if not config.stoned_model_id:
            raise ValueError("StoNED method requires stoned_model_id in DeaConfig")

        from data_loaders.stoned_data import load_stoned_results

        return DeaStageOutput(
            dea_results=load_stoned_results(config.stoned_model_id),
            dea_method="stoned",
            dea_executed=False,
        )

    else:
        raise ValueError(f"Unknown DEA method: {config.method}")
