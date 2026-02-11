"""
pipeline/debug_logger.py

Debug logging for pipeline execution.
Logs config, stage outputs, timing, and validates results.
"""

import time
from typing import Any, Dict, List, Optional

import pandas as pd

from config.column_names import (
    COL_COMPANY_NAME, COL_CAPITAL_COST_2024, COL_CONTROLLABLE_AVG,
    COL_DEA_EFFICIENCY, COL_DEA_POTENTIAL, COL_IS_OUTLIER,
    COL_CONTROLLABLE_PERIOD, COL_NON_CONTROLLABLE,
    COL_CAPITAL_COST_PERIOD, COL_REVENUE_FRAME,
    COL_QUALITY_INCENTIVE, COL_NETLOSS_INCENTIVE,
    COL_LOAD_INCENTIVE, COL_INCENTIVE_TOTAL, COL_MISSING_INCENTIVE,
)

EXPECTED_COMPANY_COUNT = 148
BASELINE_WACC = 0.0453


class PipelineDebugLogger:
    """
    Collects and reports debug information from pipeline execution.

    Usage:
        logger = PipelineDebugLogger(case_config, user_reid)
        logger.log_config()
        logger.log_baseline(baseline_output)
        logger.log_pre_dea(pre_dea_output, baseline_output)
        logger.log_dea(dea_output)
        logger.log_extraction(extraction_output)
        logger.log_post_dea(post_dea_output)
        logger.print_report()
        logger.validate()
    """

    def __init__(self, case_config: Any, user_reid: str, baseline_wacc: float = BASELINE_WACC):
        self.case_config = case_config
        self.user_reid = user_reid
        self.baseline_wacc = baseline_wacc

        self.start_time = time.time()
        self.stages: List[Dict[str, Any]] = []
        self.validation_errors: List[str] = []

        # User spotlight — key values tracked through the pipeline
        self.user: Dict[str, Any] = {"reid": user_reid}

    # =========================================================================
    # CONFIG LOGGING
    # =========================================================================

    def log_config(self) -> None:
        """Log complete case configuration."""
        cfg = self.case_config
        self._header("CASE CONFIGURATION")

        print(f"  Case Name: {cfg.name}")
        print(f"  User REId: {cfg.user_reid}")

        pre = cfg.pre_dea
        print(f"\n  [Pre-DEA]  source={pre.capbase_source}  method={pre.method}  wacc={pre.wacc or 'baseline'}")
        if pre.normvalue_adjustments:
            print(f"    normvalue_adjustments: {pre.normvalue_adjustments}")
        if pre.lifetime_adjustments:
            print(f"    lifetime_adjustments: {pre.lifetime_adjustments}")
        if hasattr(pre, 'user_capbase_scaled') and pre.user_capbase_scaled is not None:
            print(f"    user_capbase_scaled: {pre.user_capbase_scaled.shape}")
        if hasattr(pre, 'kent_file_bytes') and pre.kent_file_bytes:
            print(f"    kent_file: {len(pre.kent_file_bytes):,} bytes")

        dea = cfg.dea
        print(f"\n  [DEA]  method={dea.method}")
        if hasattr(dea, 'inputs'):
            print(f"    inputs={dea.inputs}  outputs={dea.outputs}  rts={dea.rts}")
        if hasattr(dea, 'q_lower'):
            print(f"    outlier: q=[{dea.q_lower}, {dea.q_upper}], k={dea.multiplier}")

        post = cfg.post_dea
        print(f"\n  [Post-DEA]  truncation=[{post.truncation_min:.2%}, {post.truncation_max:.2%}]"
              f"  customer_sharing={post.customer_sharing:.0%}  realization_time={post.realization_time}yr")

        if hasattr(post, 'incentive'):
            inc = post.incentive
            print(f"    incentive: quality={inc.enable_quality}  netloss={inc.enable_netloss}  load={inc.enable_load}")
        print()

    # =========================================================================
    # STAGE LOGGING
    # =========================================================================

    def log_baseline(self, output: Any) -> None:
        """Log baseline stage output."""
        t0 = time.time()
        self._header("STAGE: BASELINE")

        df = output.df_all_companies
        errors = self._validate_companies(df, "baseline")

        print(f"  Output: {df.shape[0]} rows x {df.shape[1]} cols")
        print(f"  WACC: {output.wacc}  DEA baseline: {len(output.dea_baseline)} rows")

        # User spotlight
        user_row = df[df['REId'] == self.user_reid]
        if not user_row.empty:
            row = user_row.iloc[0]
            self.user['company_name'] = str(row.get(COL_COMPANY_NAME, ''))
            self.user['capex_baseline'] = float(row[COL_CAPITAL_COST_2024])
            self.user['opex_baseline'] = float(row[COL_CONTROLLABLE_AVG])

        dea_row = output.dea_baseline[output.dea_baseline['REId'] == self.user_reid]
        if not dea_row.empty:
            row = dea_row.iloc[0]
            self.user['efficiency_baseline'] = float(row[COL_DEA_EFFICIENCY])
            self.user['potential_baseline'] = float(row[COL_DEA_POTENTIAL])

        self._record_stage("baseline", t0, errors)

    def log_pre_dea(self, output: Any, baseline: Any) -> None:
        """Log pre-DEA stage output."""
        t0 = time.time()
        self._header("STAGE: PRE-DEA")

        df = output.df_all_companies
        errors = self._validate_companies(df, "pre_dea")

        print(f"  Output: {df.shape[0]} rows x {df.shape[1]} cols")
        print(f"  source={output.capbase_source}  method={output.capex_method}"
              f"  modified={output.capex_modified}  wacc={output.wacc_used}")

        # Track whether CAPEX actually changed
        bl_capex = baseline.df_all_companies[COL_CAPITAL_COST_2024].sum()
        case_capex = df[COL_CAPITAL_COST_2024].sum()
        capex_changed = abs(case_capex - bl_capex) > 1
        if capex_changed != output.capex_modified:
            msg = f"capex_modified={output.capex_modified} but actual change={capex_changed}"
            print(f"  WARN: {msg}")
            errors.append(msg)

        # User spotlight
        user_row = df[df['REId'] == self.user_reid]
        if not user_row.empty:
            row = user_row.iloc[0]
            self.user['capex_case'] = float(row[COL_CAPITAL_COST_2024])
            self.user['opex_case'] = float(row[COL_CONTROLLABLE_AVG])

        self._record_stage("pre_dea", t0, errors)

    def log_dea(self, output: Any, baseline: Any = None) -> None:
        """Log DEA stage output."""
        t0 = time.time()
        self._header("STAGE: DEA")

        df = output.dea_results
        errors = self._validate_companies(df, "dea")

        eff = df[COL_DEA_EFFICIENCY]
        print(f"  Output: {df.shape[0]} rows x {df.shape[1]} cols")
        print(f"  method={output.dea_method}  executed={output.dea_executed}")
        print(f"  Efficiency: mean={eff.mean():.4f}  std={eff.std():.4f}"
              f"  min={eff.min():.4f}  max={eff.max():.4f}")
        print(f"  Efficient (>=1): {(eff >= 1.0).sum()}"
              f"  Outliers: {df[COL_IS_OUTLIER].sum() if COL_IS_OUTLIER in df.columns else 0}")

        # User spotlight
        user_row = df[df['REId'] == self.user_reid]
        if not user_row.empty:
            row = user_row.iloc[0]
            self.user['efficiency_case'] = float(row[COL_DEA_EFFICIENCY])
            self.user['potential_case'] = float(row[COL_DEA_POTENTIAL])
            self.user['is_outlier'] = bool(row[COL_IS_OUTLIER])

        self._record_stage("dea", t0, errors)

    def log_extraction(self, output: Any) -> None:
        """Log extraction stage output."""
        t0 = time.time()
        self._header("STAGE: EXTRACTION")

        errors = []
        if output.user_reid != self.user_reid:
            errors.append(f"REId mismatch: expected {self.user_reid}, got {output.user_reid}")

        print(f"  REId={output.user_reid}  Company={output.company_name}")
        print(f"  CAPEX={output.capex:,.0f}  OPEX={output.opex:,.0f}  TOTEX={output.totex:,.0f}")
        print(f"  Efficiency={output.efficiency:.4f}  Potential={output.potential:.4f}"
              f"  Outlier={output.is_outlier}")

        # TOTEX consistency
        expected_totex = output.capex + output.opex
        if abs(output.totex - expected_totex) > 1:
            print(f"  WARN: TOTEX={output.totex:.0f} != CAPEX+OPEX={expected_totex:.0f}")

        self._record_stage("extraction", t0, errors)

    def log_post_dea(self, output: Any) -> None:
        """Log post-DEA stage output."""
        t0 = time.time()
        self._header("STAGE: POST-DEA")

        errors = []
        if output.user_reid != self.user_reid:
            errors.append(f"REId mismatch: expected {self.user_reid}, got {output.user_reid}")

        if output.all_revenue_frames is not None:
            print(f"  all_revenue_frames: {output.all_revenue_frames.shape}")

        ir = output.user_revenue_frame
        ir_dict = ir.to_dict() if hasattr(ir, 'to_dict') else dict(ir)

        print(f"  Eff req (annual): {output.user_eff_req_pct:.2%}")
        for key in [COL_CONTROLLABLE_PERIOD, COL_NON_CONTROLLABLE,
                     COL_CAPITAL_COST_PERIOD, COL_REVENUE_FRAME]:
            if key in ir_dict:
                print(f"  {key}: {ir_dict[key]:,.0f} tkr")

        # User spotlight
        self.user['eff_req_annual'] = output.user_eff_req_pct
        if COL_REVENUE_FRAME in ir_dict:
            self.user['revenue_frame_total'] = ir_dict[COL_REVENUE_FRAME]
        if COL_CONTROLLABLE_PERIOD in ir_dict:
            self.user['controllable_total'] = ir_dict[COL_CONTROLLABLE_PERIOD]
        if COL_NON_CONTROLLABLE in ir_dict:
            self.user['non_controllable_total'] = ir_dict[COL_NON_CONTROLLABLE]
        if COL_CAPITAL_COST_PERIOD in ir_dict:
            self.user['capital_cost_total'] = ir_dict[COL_CAPITAL_COST_PERIOD]

        # Incentive breakdown
        if output.all_incentives is not None:
            user_inc = output.all_incentives[output.all_incentives['REId'] == self.user_reid]
            if not user_inc.empty:
                row = user_inc.iloc[0]
                for col, key in [
                    (COL_QUALITY_INCENTIVE, 'incentive_quality'),
                    (COL_NETLOSS_INCENTIVE, 'incentive_netloss'),
                    (COL_LOAD_INCENTIVE, 'incentive_load'),
                    (COL_INCENTIVE_TOTAL, 'incentive_total'),
                ]:
                    if col in row:
                        self.user[key] = float(row[col])
                        print(f"  {col}: {float(row[col]):,.0f} tkr")
                if COL_MISSING_INCENTIVE in row:
                    self.user['incentive_missing_data'] = bool(row[COL_MISSING_INCENTIVE])

        self._record_stage("post_dea", t0, errors)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def validate(self) -> bool:
        """
        Run validation checks. Raises ValueError if critical errors found.
        Returns True if all checks pass.
        """
        errors = []
        for stage in self.stages:
            errors.extend(stage['errors'])

        # Cross-stage: if CAPEX flagged as modified, user value should differ
        pre_dea = next((s for s in self.stages if s['name'] == 'pre_dea'), None)
        if pre_dea:
            capex_bl = self.user.get('capex_baseline')
            capex_cs = self.user.get('capex_case')
            if capex_bl and capex_cs:
                capex_changed = abs(capex_cs - capex_bl) > 1
                # Already warned in log_pre_dea, just collect

        self.validation_errors = errors

        if errors:
            self._header("VALIDATION ERRORS")
            for err in errors:
                print(f"  ERROR: {err}")
            raise ValueError(f"Pipeline validation failed with {len(errors)} errors")

        return True

    # =========================================================================
    # REPORTING
    # =========================================================================

    def print_report(self) -> None:
        """Print final summary report."""
        total_ms = (time.time() - self.start_time) * 1000

        self._header("PIPELINE SUMMARY")

        # Timing
        print("  [Timing]")
        for stage in self.stages:
            print(f"    {stage['name']:12s}: {stage['duration_ms']:8.1f} ms")
        print(f"    {'TOTAL':12s}: {total_ms:8.1f} ms")

        # Warnings
        all_warnings = [w for s in self.stages for w in s.get('warnings', [])]
        if all_warnings:
            print("\n  [Warnings]")
            for w in all_warnings:
                print(f"    WARN: {w}")

        # User spotlight
        u = self.user
        print(f"\n  [User: {u['reid']}]")
        if u.get('company_name'):
            print(f"    {u['company_name']}")

        if u.get('capex_baseline') is not None:
            delta = (u.get('capex_case', 0) or 0) - u['capex_baseline']
            print(f"    CAPEX: {u['capex_baseline']:>12,.0f} → {u.get('capex_case', 0):>12,.0f}  ({delta:+,.0f})")
        if u.get('opex_baseline') is not None:
            delta = (u.get('opex_case', 0) or 0) - u['opex_baseline']
            print(f"    OPEX:  {u['opex_baseline']:>12,.0f} → {u.get('opex_case', 0):>12,.0f}  ({delta:+,.0f})")
        if u.get('efficiency_baseline') is not None:
            delta = (u.get('efficiency_case', 0) or 0) - u['efficiency_baseline']
            print(f"    Eff:   {u['efficiency_baseline']:.4f} → {u.get('efficiency_case', 0):.4f}  ({delta:+.4f})")
        if u.get('eff_req_annual') is not None:
            print(f"    Eff req: {u['eff_req_annual']:.2%}")
        if u.get('revenue_frame_total') is not None:
            print(f"    Revenue frame: {u['revenue_frame_total']:,.0f} tkr")
        print()

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _header(self, title: str) -> None:
        print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}")

    def _validate_companies(self, df: pd.DataFrame, stage_name: str) -> List[str]:
        """Check company count and return errors list."""
        errors = []
        if len(df) != EXPECTED_COMPANY_COUNT:
            errors.append(f"[{stage_name}] Expected {EXPECTED_COMPANY_COUNT} companies, got {len(df)}")
        return errors

    def _record_stage(self, name: str, t0: float, errors: List[str]) -> None:
        self.stages.append({
            'name': name,
            'duration_ms': (time.time() - t0) * 1000,
            'errors': errors,
            'warnings': [],
        })


def create_logger(case_config: Any, user_reid: str) -> PipelineDebugLogger:
    """Create and initialize a pipeline debug logger."""
    return PipelineDebugLogger(case_config, user_reid)
