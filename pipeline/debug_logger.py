"""
pipeline/debug_logger.py

Comprehensive debug logging for pipeline execution.
Designed for technical debugging after refactoring.

Features:
- Full config dump with nested structures
- Data shape and column validation
- MD5 checksums for critical columns (detect unexpected mutations)
- Value range assertions (fail fast on invalid data)
- Timing per stage
- Stage-specific metrics
- User company spotlight (track values through pipeline)
- Consistency checks across stages
"""

import hashlib
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import pandas as pd
import numpy as np


# =============================================================================
# CONSTANTS
# =============================================================================

EXPECTED_COMPANY_COUNT = 148
BASELINE_WACC = 0.0453

# Valid ranges for assertions
VALID_RANGES = {
    'wacc': (0.0, 0.20),
    'efficiency': (0.0, 3.0),
    'potential': (-1.0, 1.0),
    'trunkering_min': (0.0, 1.0),
    'trunkering_max': (0.0, 1.0),
    'kunddelning': (0.0, 1.0),
    'capex': (0, 1e12),
    'opex': (0, 1e12),
}

# Critical columns to checksum
CHECKSUM_COLUMNS = [
    'Kapitalkostnad_2024',
    'OPEXp',
    'Effektivitet',
    'potential',
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StageMetrics:
    """Metrics collected for a single stage."""
    name: str
    duration_ms: float
    input_shape: Optional[Tuple[int, int]] = None
    output_shape: Optional[Tuple[int, int]] = None
    checksums: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class UserSpotlight:
    """Track user's company values through pipeline."""
    reid: str
    foretag: Optional[str] = None
    
    # Pre-DEA values
    capex_baseline: Optional[float] = None
    capex_case: Optional[float] = None
    opex_baseline: Optional[float] = None
    opex_case: Optional[float] = None
    
    # DEA values
    efficiency_baseline: Optional[float] = None
    efficiency_case: Optional[float] = None
    potential_baseline: Optional[float] = None
    potential_case: Optional[float] = None
    is_outlier: Optional[bool] = None
    
    # Post-DEA values
    effkrav_arligt: Optional[float] = None
    intaktsram_total: Optional[float] = None
    
    # Incentive breakdown
    incentive_quality: Optional[float] = None
    incentive_netloss: Optional[float] = None
    incentive_load: Optional[float] = None
    incentive_total: Optional[float] = None
    incentive_missing_data: Optional[bool] = None
    
    # Intaktsram components
    paverkbara_total: Optional[float] = None
    opaverkbara_total: Optional[float] = None
    kapitalkostnad_total: Optional[float] = None


# =============================================================================
# MAIN LOGGER CLASS
# =============================================================================

class PipelineDebugLogger:
    """
    Collects and reports debug information from pipeline execution.
    
    Usage:
        logger = PipelineDebugLogger(case_config, user_reid)
        logger.log_config()
        
        # After each stage:
        logger.log_baseline(baseline_output)
        logger.log_pre_dea(pre_dea_output, baseline_output)
        logger.log_dea(dea_output)
        logger.log_extraction(extraction_output)
        logger.log_post_dea(post_dea_output)
        
        # At end:
        logger.print_report()
        logger.validate()  # Raises if inconsistencies found
    """
    
    def __init__(self, case_config: Any, user_reid: str, baseline_wacc: float = BASELINE_WACC):
        self.case_config = case_config
        self.user_reid = user_reid
        self.baseline_wacc = baseline_wacc
        
        self.start_time = time.time()
        self.stage_metrics: List[StageMetrics] = []
        self.user_spotlight = UserSpotlight(reid=user_reid)
        self.validation_errors: List[str] = []
        
        self._current_stage_start: Optional[float] = None
    
    # =========================================================================
    # CONFIG LOGGING
    # =========================================================================
    
    def log_config(self) -> None:
        """Log complete case configuration with exact values."""
        self._print_header("CASE CONFIGURATION")
        
        cfg = self.case_config
        
        print(f"  Case Name: {cfg.name}")
        print(f"  User REId: {cfg.user_reid}")
        print()
        
        # Pre-DEA config
        print("  [Pre-DEA Config]")
        pre = cfg.pre_dea
        print(f"    capbase_source: {pre.capbase_source}")
        print(f"    method: {pre.method}")
        print(f"    wacc: {pre.wacc if pre.wacc else 'None (baseline 0.0453)'}")
        
        # Show exact normvalue adjustments
        if pre.normvalue_adjustments:
            print(f"    normvalue_adjustments: {pre.normvalue_adjustments}")
        
        # Show exact lifetime adjustments
        if pre.lifetime_adjustments:
            print(f"    lifetime_adjustments: {pre.lifetime_adjustments}")
        
        if hasattr(pre, 'user_capbase_scaled') and pre.user_capbase_scaled is not None:
            df = pre.user_capbase_scaled
            print(f"    user_capbase_scaled: DataFrame({df.shape[0]} rows, {df.shape[1]} cols)")
            if 'id_network' in df.columns:
                networks = df['id_network'].unique()
                print(f"      networks: {list(networks)}")
            if 'nuav' in df.columns:
                total_nuav = df['nuav'].sum() / 1e6
                print(f"      total NUAV: {total_nuav:,.1f} Mkr")
        
        if hasattr(pre, 'kent_file_bytes') and pre.kent_file_bytes:
            print(f"    kent_file_bytes: {len(pre.kent_file_bytes):,} bytes")
            if hasattr(pre, 'kent_user_id_network') and pre.kent_user_id_network:
                print(f"    kent_user_id_network: {pre.kent_user_id_network}")
        print()
        
        # DEA config
        print("  [DEA Config]")
        dea = cfg.dea
        print(f"    method: {dea.method}")
        if hasattr(dea, 'inputs'):
            print(f"    inputs: {dea.inputs}")
            print(f"    outputs: {dea.outputs}")
            print(f"    rts: {dea.rts}")
            print(f"    orientation: {dea.orientation}")
        if hasattr(dea, 'q_lower'):
            print(f"    outlier_params: q=[{dea.q_lower}, {dea.q_upper}], multiplier={dea.multiplier}")
        print()
        
        # Post-DEA config
        print("  [Post-DEA Config]")
        post = cfg.post_dea
        print(f"    trunkering_min: {post.trunkering_min:.4f} ({post.trunkering_min:.2%})")
        print(f"    trunkering_max: {post.trunkering_max:.4f} ({post.trunkering_max:.2%})")
        print(f"    outlier_krav: {post.outlier_krav:.4f} ({post.outlier_krav:.2%})")
        print(f"    kunddelning: {post.kunddelning:.2f} ({post.kunddelning:.0%})")
        print(f"    realiseringstid: {post.realiseringstid} years")
        print(f"    tillsynsperiod: {post.tillsynsperiod} years")
        print(f"    paverkbara_method: {post.paverkbara_method}")
        
        # Incentive config with full details
        if hasattr(post, 'incentive'):
            inc = post.incentive
            print()
            print("  [Incentive Config]")
            print(f"    enable_quality: {inc.enable_quality}")
            print(f"    enable_netloss: {inc.enable_netloss}")
            print(f"    enable_load: {inc.enable_load}")
            print(f"    adj_max_agg: {inc.adj_max_agg:.4f} ({inc.adj_max_agg:.2%})")
            print(f"    adj_max_cemi4: {inc.adj_max_cemi4:.4f} ({inc.adj_max_cemi4:.2%})")
            print(f"    sharing_netloss: {inc.sharing_netloss:.2f}")
            
            if inc.kpi:
                print(f"    kpi: {inc.kpi}")
            if inc.k_nf:
                print(f"    k_nf: {inc.k_nf}")
            if inc.variable_overrides:
                print(f"    variable_overrides: {inc.variable_overrides}")
        
        print()
    
    # =========================================================================
    # STAGE LOGGING
    # =========================================================================
    
    def start_stage(self, name: str) -> None:
        """Mark stage start for timing."""
        self._current_stage_start = time.time()
        self._print_header(f"STAGE: {name}")
    
    def end_stage(self, name: str, metrics: StageMetrics) -> None:
        """Mark stage end and record metrics."""
        if self._current_stage_start:
            metrics.duration_ms = (time.time() - self._current_stage_start) * 1000
        self.stage_metrics.append(metrics)
        self._current_stage_start = None
    
    def log_baseline(self, output: Any) -> None:
        """Log baseline stage output."""
        self.start_stage("BASELINE")
        
        metrics = StageMetrics(name="baseline", duration_ms=0)
        
        df = output.df_all_companies
        metrics.output_shape = df.shape
        
        # Validate company count
        if len(df) != EXPECTED_COMPANY_COUNT:
            metrics.errors.append(f"Expected {EXPECTED_COMPANY_COUNT} companies, got {len(df)}")
        
        # Check required columns
        required = ['REId', 'Företag', 'Kapitalkostnad_2024', 'OPEXp', 'CU', 'MW', 'NS']
        missing = [c for c in required if c not in df.columns]
        if missing:
            metrics.errors.append(f"Missing columns: {missing}")
        
        # Checksums
        metrics.checksums = self._compute_checksums(df, ['Kapitalkostnad_2024', 'OPEXp'])
        
        # Metrics
        metrics.metrics = {
            'n_companies': len(df),
            'wacc': output.wacc,
            'dea_baseline_rows': len(output.dea_baseline),
            'sdf_ir_rows': len(output.sdf_ir),
            'columns': list(df.columns),
        }
        
        # User spotlight - baseline values
        user_row = df[df['REId'] == self.user_reid]
        if not user_row.empty:
            row = user_row.iloc[0]
            self.user_spotlight.foretag = str(row.get('Företag', ''))
            self.user_spotlight.capex_baseline = float(row['Kapitalkostnad_2024'])
            self.user_spotlight.opex_baseline = float(row['OPEXp'])
        
        # Baseline DEA values
        dea_row = output.dea_baseline[output.dea_baseline['REId'] == self.user_reid]
        if not dea_row.empty:
            row = dea_row.iloc[0]
            self.user_spotlight.efficiency_baseline = float(row['Effektivitet'])
            self.user_spotlight.potential_baseline = float(row['potential'])
        
        self._print_metrics(metrics)
        self.end_stage("BASELINE", metrics)
    
    def log_pre_dea(self, output: Any, baseline: Any) -> None:
        """Log pre-DEA stage output."""
        self.start_stage("PRE-DEA")
        
        metrics = StageMetrics(name="pre_dea", duration_ms=0)
        
        df = output.df_all_companies
        metrics.input_shape = (len(baseline.df_all_companies), len(baseline.df_all_companies.columns))
        metrics.output_shape = df.shape
        
        # Validate
        if len(df) != EXPECTED_COMPANY_COUNT:
            metrics.errors.append(f"Expected {EXPECTED_COMPANY_COUNT} companies, got {len(df)}")
        
        # Checksums
        metrics.checksums = self._compute_checksums(df, ['Kapitalkostnad_2024', 'OPEXp'])
        
        # Check if checksums changed (CAPEX modification)
        baseline_checksums = self._compute_checksums(baseline.df_all_companies, ['Kapitalkostnad_2024'])
        capex_changed = metrics.checksums.get('Kapitalkostnad_2024') != baseline_checksums.get('Kapitalkostnad_2024')
        
        # Metrics
        metrics.metrics = {
            'capbase_source': output.capbase_source,
            'capex_method': output.capex_method,
            'capex_modified': output.capex_modified,
            'wacc_used': output.wacc_used,
            'user_id_network': output.user_id_network,
            'capex_checksum_changed': capex_changed,
        }
        
        # KENT coverage analysis (if KENT was used)
        if output.capex_method in ['parameter_change', 'baseline'] and output.capbase_source != 'baseline':
            # Check for KENT-specific columns that indicate coverage
            if 'Kapitalkostnad_Period' in df.columns:
                # Count companies with KENT data vs SDF fallback
                # This is approximate - assumes KENT values differ from SDF
                baseline_sdf = baseline.sdf_ir
                if 'Kapitalkostnad' in baseline_sdf.columns:
                    # Merge to compare
                    sdf_capex = baseline_sdf[['REId', 'Kapitalkostnad']].copy()
                    sdf_capex.columns = ['REId', 'SDF_Kapitalkostnad']
                    merged = df[['REId', 'Kapitalkostnad_Period']].merge(sdf_capex, on='REId', how='left')
                    
                    # Companies where KENT differs from SDF (likely KENT-calculated)
                    merged['is_kent'] = (merged['Kapitalkostnad_Period'] != merged['SDF_Kapitalkostnad'])
                    n_kent = merged['is_kent'].sum()
                    n_sdf_fallback = len(merged) - n_kent
                    
                    metrics.metrics['kent_coverage'] = {
                        'n_kent': int(n_kent),
                        'n_sdf_fallback': int(n_sdf_fallback),
                        'kent_pct': f"{n_kent/len(merged)*100:.1f}%"
                    }
        
        # Column diff: what new columns were added?
        baseline_cols = set(baseline.df_all_companies.columns)
        output_cols = set(df.columns)
        new_cols = output_cols - baseline_cols
        if new_cols:
            metrics.metrics['new_columns'] = sorted(list(new_cols))
        
        # Consistency check
        if capex_changed != output.capex_modified:
            metrics.warnings.append(
                f"capex_modified={output.capex_modified} but checksum changed={capex_changed}"
            )
        
        # User spotlight
        user_row = df[df['REId'] == self.user_reid]
        if not user_row.empty:
            row = user_row.iloc[0]
            self.user_spotlight.capex_case = float(row['Kapitalkostnad_2024'])
            self.user_spotlight.opex_case = float(row['OPEXp'])
        
        self._print_metrics(metrics)
        self.end_stage("PRE-DEA", metrics)
    
    def log_dea(self, output: Any, baseline: Any = None) -> None:
        """Log DEA stage output."""
        self.start_stage("DEA")
        
        metrics = StageMetrics(name="dea", duration_ms=0)
        
        df = output.dea_results
        metrics.output_shape = df.shape
        
        # Validate
        if len(df) != EXPECTED_COMPANY_COUNT:
            metrics.errors.append(f"Expected {EXPECTED_COMPANY_COUNT} companies, got {len(df)}")
        
        # Required columns
        required = ['REId', 'Effektivitet', 'potential', 'is_outlier']
        missing = [c for c in required if c not in df.columns]
        if missing:
            metrics.errors.append(f"Missing DEA columns: {missing}")
        
        # Checksums
        metrics.checksums = self._compute_checksums(df, ['Effektivitet', 'potential'])
        
        # Statistics
        eff_col = df['Effektivitet']
        metrics.metrics = {
            'dea_method': output.dea_method,
            'dea_executed': output.dea_executed,
            'n_companies': len(df),
            'efficiency_mean': float(eff_col.mean()),
            'efficiency_std': float(eff_col.std()),
            'efficiency_min': float(eff_col.min()),
            'efficiency_max': float(eff_col.max()),
            'n_efficient': int((eff_col >= 1.0).sum()),
            'n_outliers': int(df['is_outlier'].sum()) if 'is_outlier' in df.columns else 0,
        }
        
        # Store DEA spec if custom DEA was run
        if output.dea_executed and hasattr(self.case_config, 'dea'):
            dea_cfg = self.case_config.dea
            if hasattr(dea_cfg, 'inputs'):
                metrics.metrics['dea_spec'] = {
                    'inputs': dea_cfg.inputs,
                    'outputs': dea_cfg.outputs,
                    'rts': dea_cfg.rts,
                    'orientation': dea_cfg.orientation,
                }
                if hasattr(dea_cfg, 'q_lower'):
                    metrics.metrics['dea_spec']['outlier_params'] = {
                        'q_lower': dea_cfg.q_lower,
                        'q_upper': dea_cfg.q_upper,
                        'multiplier': dea_cfg.multiplier
                    }
        
        # Value range check
        if eff_col.min() < VALID_RANGES['efficiency'][0]:
            metrics.errors.append(f"Efficiency below valid range: {eff_col.min():.4f}")
        if eff_col.max() > VALID_RANGES['efficiency'][1]:
            metrics.warnings.append(f"Efficiency above expected max: {eff_col.max():.4f}")
        
        # User spotlight
        user_row = df[df['REId'] == self.user_reid]
        if not user_row.empty:
            row = user_row.iloc[0]
            self.user_spotlight.efficiency_case = float(row['Effektivitet'])
            self.user_spotlight.potential_case = float(row['potential'])
            self.user_spotlight.is_outlier = bool(row['is_outlier'])
        
        self._print_metrics(metrics)
        self.end_stage("DEA", metrics)
    
    def log_extraction(self, output: Any) -> None:
        """Log extraction stage output."""
        self.start_stage("EXTRACTION")
        
        metrics = StageMetrics(name="extraction", duration_ms=0)
        
        # Validate REId consistency
        if output.user_reid != self.user_reid:
            metrics.errors.append(f"REId mismatch: expected {self.user_reid}, got {output.user_reid}")
        
        # Metrics from extraction
        metrics.metrics = {
            'user_reid': output.user_reid,
            'foretag': output.foretag,
            'capex': output.capex,
            'opex': output.opex,
            'totex': output.totex,
            'cu': output.cu,
            'mw': output.mw,
            'ns': output.ns,
            'efficiency': output.efficiency,
            'potential': output.potential,
            'is_outlier': output.is_outlier,
        }
        
        # TOTEX consistency check
        expected_totex = output.capex + output.opex
        if abs(output.totex - expected_totex) > 1:  # Allow 1 tkr rounding
            metrics.warnings.append(
                f"TOTEX inconsistency: {output.totex:.0f} != CAPEX({output.capex:.0f}) + OPEX({output.opex:.0f})"
            )
        
        # Value range checks
        if output.capex < 0:
            metrics.errors.append(f"Negative CAPEX: {output.capex}")
        if output.opex < 0:
            metrics.errors.append(f"Negative OPEX: {output.opex}")
        if output.efficiency is not None and output.efficiency < 0:
            metrics.errors.append(f"Negative efficiency: {output.efficiency}")
        
        self._print_metrics(metrics)
        self.end_stage("EXTRACTION", metrics)
    
    def log_post_dea(self, output: Any) -> None:
        """Log post-DEA stage output."""
        self.start_stage("POST-DEA")
        
        metrics = StageMetrics(name="post_dea", duration_ms=0)
        
        # Validate
        if output.user_reid != self.user_reid:
            metrics.errors.append(f"REId mismatch: expected {self.user_reid}, got {output.user_reid}")
        
        # Check all_intaktsram
        if output.all_intaktsram is not None:
            metrics.output_shape = output.all_intaktsram.shape
            n_rows = len(output.all_intaktsram)
            if n_rows != EXPECTED_COMPANY_COUNT:
                # Count regional vs local networks
                n_regional = output.all_intaktsram['REId'].str.startswith('RER').sum()
                n_local = n_rows - n_regional
                if n_local == EXPECTED_COMPANY_COUNT:
                    metrics.metrics['network_breakdown'] = f"{n_local} local + {n_regional} regional"
                else:
                    metrics.warnings.append(
                        f"all_intaktsram has {n_rows} rows ({n_local} local, {n_regional} regional), expected {EXPECTED_COMPANY_COUNT} local"
                    )
        
        # User intaktsram components
        ir = output.user_intaktsram
        ir_dict = ir.to_dict() if hasattr(ir, 'to_dict') else dict(ir)
        
        metrics.metrics = {
            'user_reid': output.user_reid,
            'user_effkrav_proc': output.user_effkrav_proc,
            'all_effkrav_rows': len(output.all_effkrav) if output.all_effkrav is not None else 0,
            'all_intaktsram_rows': len(output.all_intaktsram) if output.all_intaktsram is not None else 0,
            'incentives_available': output.all_incentives is not None,
        }
        
        # Add key intaktsram components
        key_components = [
            'Paverkbara_Periodsumma', 'Opaverkbara_Kostnader', 'Effektiviseringskrav',
            'Kapitalkostnad_Total', 'Intaktsram_Total'
        ]
        for comp in key_components:
            if comp in ir_dict:
                metrics.metrics[f'ir_{comp}'] = ir_dict[comp]
        
        # User spotlight - basic values
        self.user_spotlight.effkrav_arligt = output.user_effkrav_proc
        if 'Intaktsram_Total' in ir_dict:
            self.user_spotlight.intaktsram_total = ir_dict['Intaktsram_Total']
        if 'Paverkbara_Periodsumma' in ir_dict:
            self.user_spotlight.paverkbara_total = ir_dict['Paverkbara_Periodsumma']
        if 'Opaverkbara_Kostnader' in ir_dict:
            self.user_spotlight.opaverkbara_total = ir_dict['Opaverkbara_Kostnader']
        if 'Kapitalkostnad_Total' in ir_dict:
            self.user_spotlight.kapitalkostnad_total = ir_dict['Kapitalkostnad_Total']
        
        # User spotlight - incentive breakdown
        if output.all_incentives is not None:
            user_inc = output.all_incentives[output.all_incentives['REId'] == self.user_reid]
            if not user_inc.empty:
                row = user_inc.iloc[0]
                
                # Extract incentive components
                if 'Kvalitetsjustering_Total' in row:
                    self.user_spotlight.incentive_quality = float(row['Kvalitetsjustering_Total'])
                    metrics.metrics['incentive_quality'] = float(row['Kvalitetsjustering_Total'])
                
                if 'Natforlustjustering_Total' in row:
                    self.user_spotlight.incentive_netloss = float(row['Natforlustjustering_Total'])
                    metrics.metrics['incentive_netloss'] = float(row['Natforlustjustering_Total'])
                
                if 'Belastningsjustering_Total' in row:
                    self.user_spotlight.incentive_load = float(row['Belastningsjustering_Total'])
                    metrics.metrics['incentive_load'] = float(row['Belastningsjustering_Total'])
                
                if 'Incitamentjustering_Total' in row:
                    self.user_spotlight.incentive_total = float(row['Incitamentjustering_Total'])
                    metrics.metrics['incentive_total'] = float(row['Incitamentjustering_Total'])
                
                if 'Missing_Incentive_Data' in row:
                    self.user_spotlight.incentive_missing_data = bool(row['Missing_Incentive_Data'])
                    metrics.metrics['incentive_missing_data'] = bool(row['Missing_Incentive_Data'])
        
        self._print_metrics(metrics)
        self.end_stage("POST-DEA", metrics)
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def validate(self) -> bool:
        """
        Run all validation checks. Raises ValueError if critical errors found.
        Returns True if all checks pass.
        """
        errors = []
        
        # Collect all errors from stages
        for stage in self.stage_metrics:
            for err in stage.errors:
                errors.append(f"[{stage.name}] {err}")
        
        # Cross-stage consistency checks
        errors.extend(self._validate_consistency())
        
        self.validation_errors = errors
        
        if errors:
            self._print_header("VALIDATION ERRORS")
            for err in errors:
                print(f"  ERROR: {err}")
            print()
            raise ValueError(f"Pipeline validation failed with {len(errors)} errors")
        
        return True
    
    def _validate_consistency(self) -> List[str]:
        """Cross-stage consistency checks."""
        errors = []
        
        # Check user spotlight consistency
        spot = self.user_spotlight
        
        # If CAPEX was modified, case value should differ from baseline
        pre_dea_metrics = next((s for s in self.stage_metrics if s.name == 'pre_dea'), None)
        if pre_dea_metrics:
            capex_modified = pre_dea_metrics.metrics.get('capex_modified', False)
            if spot.capex_baseline and spot.capex_case:
                capex_changed = abs(spot.capex_case - spot.capex_baseline) > 1
                if capex_modified and not capex_changed:
                    errors.append(
                        f"capex_modified=True but user CAPEX unchanged: "
                        f"baseline={spot.capex_baseline:.0f}, case={spot.capex_case:.0f}"
                    )
        
        return errors
    
    # =========================================================================
    # REPORTING
    # =========================================================================
    
    def print_report(self) -> None:
        """Print final summary report."""
        total_time = (time.time() - self.start_time) * 1000
        
        self._print_header("PIPELINE SUMMARY")
        
        # Timing breakdown
        print("  [Timing]")
        for stage in self.stage_metrics:
            print(f"    {stage.name:12s}: {stage.duration_ms:8.1f} ms")
        print(f"    {'TOTAL':12s}: {total_time:8.1f} ms")
        print()
        
        # Warnings summary
        all_warnings = []
        for stage in self.stage_metrics:
            for warn in stage.warnings:
                all_warnings.append(f"[{stage.name}] {warn}")
        
        if all_warnings:
            print("  [Warnings]")
            for warn in all_warnings:
                print(f"    WARN: {warn}")
            print()
        
        # User spotlight
        self._print_user_spotlight()
        
        # Checksums
        self._print_checksums()
    
    def _print_user_spotlight(self) -> None:
        """Print user company values through pipeline."""
        spot = self.user_spotlight
        
        print("  [User Spotlight]")
        print(f"    REId: {spot.reid}")
        if spot.foretag:
            print(f"    Foretag: {spot.foretag}")
        print()
        
        # CAPEX/OPEX comparison
        if spot.capex_baseline is not None:
            capex_delta = (spot.capex_case or 0) - spot.capex_baseline
            print(f"    CAPEX baseline: {spot.capex_baseline:>12,.0f} tkr")
            print(f"    CAPEX case:     {spot.capex_case:>12,.0f} tkr  (delta: {capex_delta:+,.0f})")
        
        if spot.opex_baseline is not None:
            opex_delta = (spot.opex_case or 0) - spot.opex_baseline
            print(f"    OPEX baseline:  {spot.opex_baseline:>12,.0f} tkr")
            print(f"    OPEX case:      {spot.opex_case:>12,.0f} tkr  (delta: {opex_delta:+,.0f})")
        print()
        
        # DEA comparison
        if spot.efficiency_baseline is not None:
            eff_delta = (spot.efficiency_case or 0) - spot.efficiency_baseline
            print(f"    Efficiency baseline: {spot.efficiency_baseline:>8.4f}")
            print(f"    Efficiency case:     {spot.efficiency_case:>8.4f}  (delta: {eff_delta:+.4f})")
            print(f"    Potential case:      {spot.potential_case:>8.4f}")
            print(f"    Is outlier:          {spot.is_outlier}")
        print()
        
        # Efficiency requirement
        if spot.effkrav_arligt is not None:
            print(f"    Effkrav (annual):    {spot.effkrav_arligt:>8.2%}")
        print()
        
        # Intaktsram components
        print("  [Intaktsram Components]")
        if spot.paverkbara_total is not None:
            print(f"    Paverkbara:          {spot.paverkbara_total:>12,.0f} tkr")
        if spot.opaverkbara_total is not None:
            print(f"    Opaverkbara:         {spot.opaverkbara_total:>12,.0f} tkr")
        if spot.kapitalkostnad_total is not None:
            print(f"    Kapitalkostnad:      {spot.kapitalkostnad_total:>12,.0f} tkr")
        print()
        
        # Incentive breakdown
        print("  [Incentive Breakdown]")
        if spot.incentive_missing_data:
            print("    WARNING: Missing incentive data for this company")
        
        if spot.incentive_quality is not None:
            print(f"    Kvalitetsjustering:  {spot.incentive_quality:>12,.0f} tkr")
        if spot.incentive_netloss is not None:
            print(f"    Natforlustjustering: {spot.incentive_netloss:>12,.0f} tkr")
        if spot.incentive_load is not None:
            print(f"    Belastningsjustering:{spot.incentive_load:>12,.0f} tkr")
        if spot.incentive_total is not None:
            print(f"    TOTAL Incitament:    {spot.incentive_total:>12,.0f} tkr")
        print()
        
        # Final intaktsram
        if spot.intaktsram_total is not None:
            print(f"    === INTAKTSRAM TOTAL: {spot.intaktsram_total:>12,.0f} tkr ===")
        print()
    
    def _print_checksums(self) -> None:
        """Print checksums for data integrity verification."""
        print("  [Checksums]")
        for stage in self.stage_metrics:
            if stage.checksums:
                for col, checksum in stage.checksums.items():
                    print(f"    {stage.name}.{col}: {checksum[:12]}")
        print()
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _print_header(self, title: str) -> None:
        """Print section header."""
        print()
        print("=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def _print_metrics(self, metrics: StageMetrics) -> None:
        """Print stage metrics."""
        print()
        
        # Shapes
        if metrics.input_shape:
            print(f"  Input:  {metrics.input_shape[0]} rows x {metrics.input_shape[1]} cols")
        if metrics.output_shape:
            print(f"  Output: {metrics.output_shape[0]} rows x {metrics.output_shape[1]} cols")
        
        # Key metrics
        if metrics.metrics:
            print()
            print("  [Metrics]")
            for key, value in metrics.metrics.items():
                # Handle nested dictionaries (like dea_spec)
                if isinstance(value, dict):
                    print(f"    {key}:")
                    for k, v in value.items():
                        if isinstance(v, dict):
                            print(f"      {k}: {v}")
                        elif isinstance(v, list):
                            print(f"      {k}: {v}")
                        else:
                            print(f"      {k}: {v}")
                elif isinstance(value, float):
                    if 'efficiency' in key.lower() or 'potential' in key.lower() or 'proc' in key.lower():
                        print(f"    {key}: {value:.4f}")
                    elif value > 1000:
                        print(f"    {key}: {value:,.0f}")
                    else:
                        print(f"    {key}: {value:.4f}")
                elif isinstance(value, list) and len(value) > 10:
                    print(f"    {key}: [{len(value)} items]")
                else:
                    print(f"    {key}: {value}")
        
        # Warnings
        if metrics.warnings:
            print()
            for warn in metrics.warnings:
                print(f"  WARN: {warn}")
        
        # Errors
        if metrics.errors:
            print()
            for err in metrics.errors:
                print(f"  ERROR: {err}")
    
    def _compute_checksums(self, df: pd.DataFrame, columns: List[str]) -> Dict[str, str]:
        """Compute MD5 checksums for specified columns."""
        checksums = {}
        for col in columns:
            if col in df.columns:
                # Convert to bytes and hash
                data = df[col].fillna(0).values
                if data.dtype in [np.float64, np.float32]:
                    # Round to avoid floating point precision issues
                    data = np.round(data, 6)
                data_bytes = data.tobytes()
                checksums[col] = hashlib.md5(data_bytes).hexdigest()
        return checksums


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_logger(case_config: Any, user_reid: str) -> PipelineDebugLogger:
    """Create and initialize a pipeline debug logger."""
    return PipelineDebugLogger(case_config, user_reid)