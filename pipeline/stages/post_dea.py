"""
pipeline/stages/post_dea.py

Stage 5: Post-DEA
Beräknar effektiviseringskrav, incitamentjusteringar, påverkbara kostnader,
och assemblerar intäktsram.

UPPDATERAD med förenklad get_return_per_year():
- Baseline har nu Avkastning_2024-2027 direkt i df_all_companies
- Eliminerar approximationen "periodsumma / 4" för baseline och wacc_scaling
- Korrekt per-år variation bevaras för incitamentjusteringens 1/3-cap
"""

import pandas as pd
from typing import Optional

from config import PostDeaConfig
from config.case_definition import PaverkbaraMethod
from pipeline.stages.stage_outputs import (
    DeaStageOutput,
    PreDeaStageOutput,
    BaselineStageOutput,
    PostDeaStageOutput,
)
from calculations.effektiviseringskrav import calculate_effkrav_for_dataframe
from calculations.paverkbara_calculations import calculate_paverkbara_with_effkrav, get_paverkbara_from_sdf
from calculations.intaktsram_assembly import assemble_intaktsram, extract_user_intaktsram
from calculations.incentive_calculations import calculate_all_incentives
from data_loaders.incentive_data import (
    load_incentive_data,
    prepare_incentive_input,
    get_incentive_summary_by_reid,
    apply_variable_overrides,
)


# Kolumnnamn i SDF IR-sheet för periodsummor
SDF_COL_KAPITALFORSLITNING = '-varav Kapital-förslitning'
SDF_COL_KAPITALBINDNING = 'varav Kapital-bindning'
SDF_COL_KAPITALKOSTNAD = 'Kapitalkostnad'


# =============================================================================
# HUVUDFUNKTION: stage_post_dea
# =============================================================================

def stage_post_dea(
    dea: DeaStageOutput,
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig,
    user_reid: str
) -> PostDeaStageOutput:
    """
    Stage 5: Beräkna effektiviseringskrav, incitament, påverkbara, och intäktsram.
    
    Process:
    1. Beräkna effektiviseringskrav för alla 148 företag
    2. Beräkna påverkbara kostnader (OPEX eller TOTEX)
    3. Förbered kapitalkostnad baserat på Pre-DEA metod
    4. Beräkna incitamentjusteringar (kvalitet, nätförlust, belastning)
    5. Assemblera intäktsram med alla komponenter inkl. incitament
    6. Extrahera användarens specifika intäktsram
    
    Args:
        dea: Output från DEA stage (effektivitet, potential för alla 148)
        pre_dea: Output från Pre-DEA stage (CAPEX-data + metadata)
        baseline: Output från Baseline stage (SDF-data)
        config: PostDeaConfig med trunkering, kunddelning, realiseringstid, incentive, etc.
        user_reid: REId för användarens företag
        
    Returns:
        PostDeaStageOutput med alla beräknade komponenter
    """
    
    print("\n" + "="*60)
    print("STAGE 5: POST-DEA")
    print("="*60)
    
    # STEG 1: Beräkna effektiviseringskrav för alla 148 företag
    print("\n  Steg 1/6: Beräknar effektiviseringskrav...")
    print(f"    Parametrar: trunkering=[{config.trunkering_min:.1%}, {config.trunkering_max:.1%}], "
          f"kunddelning={config.kunddelning:.0%}, realiseringstid={config.realiseringstid} år")
    
    all_effkrav = calculate_effkrav_for_dataframe(
        df=dea.dea_results,
        potential_col='potential',
        outlier_col='is_outlier',
        trunkering_min=config.trunkering_min,
        trunkering_max=config.trunkering_max,
        outlier_krav=config.outlier_krav,
        kunddelning=config.kunddelning,
        realiseringstid=config.realiseringstid,
        tillsynsperiod=config.tillsynsperiod
    )
    
    print(f"    [OK] Effektiviseringskrav beräknat för {len(all_effkrav)} företag")
    
    # STEG 2: Förbered påverkbara baseline-data från SDF
    print("\n  Steg 2/6: Laddar påverkbara baseline från SDF...")
    
    sdf_paverkbara = get_paverkbara_from_sdf(
        sdf_ir=baseline.sdf_ir,
        sdf_paverkbara=baseline.sdf_paverkbara
    )
    
    print(f"    [OK] Påverkbara baseline laddad för {len(sdf_paverkbara)} företag")
    
    # STEG 3: Beräkna påverkbara kostnader med effektiviseringskrav
    print(f"\n  Steg 3/6: Beräknar påverkbara kostnader ({config.paverkbara_method})...")
    
    # För TOTEX behövs kapitalkostnad
    if config.paverkbara_method == PaverkbaraMethod.TOTEX:
        capex_for_paverkbara = get_period_capex(pre_dea, baseline)
    else:
        # För OPEX behövs ingen CAPEX-data
        capex_for_paverkbara = pd.DataFrame({'REId': pre_dea.df_all_companies['REId']})
    
    all_paverkbara = calculate_paverkbara_with_effkrav(
        effkrav_data=all_effkrav,
        sdf_baseline=sdf_paverkbara,
        capex_data=capex_for_paverkbara,
        method=config.paverkbara_method.value
    )
    
    print(f"    [OK] Påverkbara beräknat för {len(all_paverkbara)} företag")
    
    # STEG 4: Förbered kapitalkostnad för intäktsram (baserat på Pre-DEA metod)
    print(f"\n  Steg 4/6: Förbereder kapitalkostnad (källa: {pre_dea.capex_method})...")
    
    capex_for_intaktsram = get_period_capex(pre_dea, baseline)
    
    print(f"    [OK] Kapitalkostnad förberedd för {len(capex_for_intaktsram)} företag")
    
    # STEG 5: Beräkna incitamentjusteringar
    print("\n  Steg 5/6: Beräknar incitamentjusteringar...")
    
    # Logga incitament-parametrar om de avviker från baseline
    incentive_config = getattr(config, 'incentive', None)
    if incentive_config:
        _log_incentive_params(incentive_config)
    
    all_incentives = _calculate_incentive_adjustments(
        pre_dea=pre_dea,
        baseline=baseline,
        config=config,
        user_reid=user_reid
    )
    
    if all_incentives is not None:
        n_valid = (~all_incentives['Missing_Incentive_Data']).sum()
        n_missing = all_incentives['Missing_Incentive_Data'].sum()
        print(f"    [OK] Incitament beräknat för {n_valid} företag ({n_missing} saknar data)")
        
        # Visa statistik
        total_inc = all_incentives['Incitamentjustering_Total'].sum()
        print(f"    Total incitamentjustering (alla): {total_inc:,.0f} tkr")
    else:
        print("    [VARNING] Incitamentdata saknas - sätter till 0")
    
    # STEG 6: Assemblera intäktsram
    print("\n  Steg 6/6: Assemblerar intäktsram...")
    
    all_intaktsram = assemble_intaktsram(
        capex_result=capex_for_intaktsram,
        paverkbara_result=all_paverkbara,
        sdf_baseline=baseline.sdf_ir,
        incentive_result=all_incentives
    )
    
    print(f"    [OK] Intäktsram assemblerad för {len(all_intaktsram)} företag")
    
    # Extrahera användarens specifika data
    print(f"\n  Extraherar data för användare ({user_reid})...")
    
    user_intaktsram = extract_user_intaktsram(all_intaktsram, user_reid)
    user_effkrav_proc = all_effkrav[all_effkrav['REId'] == user_reid]['Effkrav_proc'].iloc[0]
    
    # Hämta användarens incitamentjustering
    user_incentive = 0.0
    if all_incentives is not None:
        user_inc_row = all_incentives[all_incentives['REId'] == user_reid]
        if not user_inc_row.empty:
            user_incentive = user_inc_row['Incitamentjustering_Total'].iloc[0]
    
    print(f"    [OK] Intäktsram: {user_intaktsram['Intaktsram_Total']:,.0f} tkr")
    print(f"    [OK] Effektiviseringskrav: {user_effkrav_proc*100:.2f}% per år")
    print(f"    [OK] Incitamentjustering: {user_incentive:,.0f} tkr")
    
    print("="*60 + "\n")
    
    # Returnera output
    return PostDeaStageOutput(
        user_reid=user_reid,
        user_intaktsram=user_intaktsram,
        user_effkrav_proc=user_effkrav_proc,
        all_intaktsram=all_intaktsram,
        all_effkrav=all_effkrav,
        all_incentives=all_incentives
    )


# =============================================================================
# KAPITALKOSTNAD PERIODSUMMA
# =============================================================================

def get_period_capex(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Hämtar kapitalkostnad periodsumma för alla företag.
    
    KRITISKT: Returnerar PERIODSUMMA (4 år), INTE årsvärde!
    
    Källa beror på Pre-DEA metod:
    - 'baseline': Använd SDF "Kapitalkostnad" (periodsumma)
    - 'wacc_scaling': Skala SDF kapitalbindning med WACC-kvot
    - 'kent_upload' / 'parameter_change': Använd KENT-output periodsumma
    
    Args:
        pre_dea: Output från Pre-DEA stage
        baseline: Output från Baseline stage
    
    Returns:
        DataFrame med: REId, Kapitalkostnad_Total (periodsumma i tkr)
    """
    
    method = pre_dea.capex_method
    
    if method == 'baseline':
        return _get_capex_from_sdf(baseline)
    
    elif method == 'wacc_scaling':
        return _calculate_wacc_scaled_period_capex(pre_dea, baseline)
    
    elif method in ['kent_upload', 'parameter_change']:
        df_kent = pre_dea.df_all_companies
        
        if 'Kapitalkostnad_Period' in df_kent.columns:
            return df_kent[['REId', 'Kapitalkostnad_Period']].rename(
                columns={'Kapitalkostnad_Period': 'Kapitalkostnad_Total'}
            )
        elif 'Kapitalkostnad_Total' in df_kent.columns:
            return df_kent[['REId', 'Kapitalkostnad_Total']]
        else:
            # Fallback: summera per-år om de finns
            yearly_cols = ['Kapitalkostnad_2024', 'Kapitalkostnad_2025',
                          'Kapitalkostnad_2026', 'Kapitalkostnad_2027']
            if all(col in df_kent.columns for col in yearly_cols):
                df = df_kent[['REId']].copy()
                df['Kapitalkostnad_Total'] = (
                    df_kent['Kapitalkostnad_2024'] + df_kent['Kapitalkostnad_2025'] +
                    df_kent['Kapitalkostnad_2026'] + df_kent['Kapitalkostnad_2027']
                )
                return df
            else:
                raise ValueError(
                    f"KENT-output saknar periodsumma för kapitalkostnad. "
                    f"Tillgängliga kolumner: {list(df_kent.columns)}"
                )
    
    else:
        raise ValueError(
            f"Okänd capex_method: '{method}'. "
            f"Förväntade värden: 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'"
        )


def _get_capex_from_sdf(baseline: BaselineStageOutput) -> pd.DataFrame:
    """Hämtar kapitalkostnad periodsumma direkt från SDF."""
    sdf = baseline.sdf_ir.copy()
    
    if SDF_COL_KAPITALKOSTNAD not in sdf.columns:
        raise ValueError(
            f"Kolumn '{SDF_COL_KAPITALKOSTNAD}' saknas i SDF IR."
        )
    
    df = sdf[['REId', SDF_COL_KAPITALKOSTNAD]].copy()
    df.columns = ['REId', 'Kapitalkostnad_Total']
    df['Kapitalkostnad_Total'] = pd.to_numeric(
        df['Kapitalkostnad_Total'], errors='coerce'
    ).fillna(0)
    
    return df


def _calculate_wacc_scaled_period_capex(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Beräknar korrekt WACC-skalad periodsumma för kapitalkostnad.
    
    Metod:
    1. Hämta periodsummor för kapitalförslitning och kapitalbindning från SDF
    2. Beräkna skalningsfaktor: ny_WACC / baseline_WACC
    3. Skala ENDAST kapitalbindningen (avkastning ändras med WACC)
    4. Ny periodsumma = Kapitalförslitning + Skalad Kapitalbindning
    """
    
    if pre_dea.wacc_used is None:
        raise ValueError(
            "wacc_used saknas i PreDeaStageOutput för wacc_scaling metod."
        )
    
    new_wacc = pre_dea.wacc_used
    baseline_wacc = baseline.wacc
    
    sdf = baseline.sdf_ir.copy()
    
    for col in [SDF_COL_KAPITALFORSLITNING, SDF_COL_KAPITALBINDNING]:
        if col not in sdf.columns:
            raise ValueError(
                f"Kolumn '{col}' saknas i SDF IR. "
                f"Tillgängliga kolumner: {list(sdf.columns)}"
            )
    
    df = sdf[['REId', SDF_COL_KAPITALFORSLITNING, SDF_COL_KAPITALBINDNING]].copy()
    df.columns = ['REId', 'Kapitalforslitning_Period', 'Kapitalbindning_Period']
    
    df['Kapitalforslitning_Period'] = pd.to_numeric(
        df['Kapitalforslitning_Period'], errors='coerce'
    ).fillna(0)
    df['Kapitalbindning_Period'] = pd.to_numeric(
        df['Kapitalbindning_Period'], errors='coerce'
    ).fillna(0)
    
    scaling_factor = new_wacc / baseline_wacc
    
    print(f"    WACC-skalning av periodsummor:")
    print(f"      Baseline WACC: {baseline_wacc:.4f} ({baseline_wacc*100:.2f}%)")
    print(f"      Ny WACC: {new_wacc:.4f} ({new_wacc*100:.2f}%)")
    print(f"      Skalningsfaktor: {scaling_factor:.4f}")
    
    df['Kapitalbindning_Skalad'] = df['Kapitalbindning_Period'] * scaling_factor
    df['Kapitalkostnad_Total'] = df['Kapitalforslitning_Period'] + df['Kapitalbindning_Skalad']
    
    return df[['REId', 'Kapitalkostnad_Total']]


# =============================================================================
# AVKASTNING PER ÅR (FÖRBÄTTRAD - använder baseline per-år kolumner)
# =============================================================================

def get_return_per_year(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Hämtar avkastning per år för alla företag, baserat på capex_method.
    
    Används för incitamentjusteringens 1/3-cap som appliceras per år.
    
    FÖRBÄTTRAD VERSION:
    - Baseline har nu Avkastning_2024-2027 direkt i df_all_companies
    - Eliminerar approximationen "periodsumma / 4"
    - Korrekt per-år variation bevaras
    
    Källor beroende på capex_method:
    - 'baseline': Direkt från baseline.df_all_companies
    - 'wacc_scaling': Skala baseline per-år avkastning med WACC-kvot
    - 'kent_upload' / 'parameter_change': Från KENT-output (har redan per-år)
    
    Args:
        pre_dea: Output från Pre-DEA stage
        baseline: Output från Baseline stage
    
    Returns:
        DataFrame med: REId, Avkastning_2024, Avkastning_2025, 
                       Avkastning_2026, Avkastning_2027 (alla i tkr)
    """
    
    method = pre_dea.capex_method
    years = [2024, 2025, 2026, 2027]
    yearly_cols = [f'Avkastning_{year}' for year in years]
    
    if method == 'baseline':
        return _get_return_from_baseline(baseline, yearly_cols)
    
    elif method == 'wacc_scaling':
        return _get_return_wacc_scaled(pre_dea, baseline, yearly_cols)
    
    elif method in ['kent_upload', 'parameter_change']:
        return _get_return_from_kent(pre_dea, yearly_cols)
    
    else:
        raise ValueError(
            f"Okänd capex_method: '{method}'. "
            f"Förväntade: 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'"
        )


def _get_return_from_baseline(
    baseline: BaselineStageOutput,
    yearly_cols: list
) -> pd.DataFrame:
    """
    Hämtar avkastning per år direkt från baseline df_all_companies.
    
    FÖRBÄTTRING: Använder faktiska per-år värden istället för periodsumma/4.
    """
    df = baseline.df_all_companies
    
    missing_cols = [col for col in yearly_cols if col not in df.columns]
    
    if missing_cols:
        print(f"    [VARNING] Per-år avkastning saknas: {missing_cols}")
        print(f"    -> Använder fallback (Avkastning för alla år)")
        
        # Fallback till aggregerad avkastning
        result = df[['REId']].copy()
        for col in yearly_cols:
            if 'Avkastning' in df.columns:
                result[col] = df['Avkastning']
            else:
                result[col] = 0
        return result
    
    return df[['REId'] + yearly_cols].copy()


def _get_return_wacc_scaled(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    yearly_cols: list
) -> pd.DataFrame:
    """
    Skalar baseline per-år avkastning med WACC-kvot.
    
    FÖRBÄTTRING: Skalar varje års avkastning individuellt istället för 
    att approximera med periodsumma/4.
    """
    if pre_dea.wacc_used is None:
        raise ValueError(
            "wacc_used saknas i PreDeaStageOutput för wacc_scaling metod."
        )
    
    scaling_factor = pre_dea.wacc_used / baseline.wacc
    
    df_baseline = _get_return_from_baseline(baseline, yearly_cols)
    
    df_result = df_baseline[['REId']].copy()
    for col in yearly_cols:
        df_result[col] = df_baseline[col] * scaling_factor
    
    print(f"    Skalade per-år avkastning med faktor {scaling_factor:.4f}")
    
    return df_result


def _get_return_from_kent(
    pre_dea: PreDeaStageOutput,
    yearly_cols: list
) -> pd.DataFrame:
    """
    Hämtar avkastning per år från KENT-output (för kent_upload och parameter_change).
    """
    df_kent = pre_dea.df_all_companies
    
    missing_cols = [col for col in yearly_cols if col not in df_kent.columns]
    
    if missing_cols:
        raise ValueError(
            f"Avkastning per år saknas i KENT-output: {missing_cols}. "
            "Kontrollera att kent_calculations.py genererar dessa kolumner."
        )
    
    return df_kent[['REId'] + yearly_cols].copy()


# =============================================================================
# INCITAMENTJUSTERINGAR
# =============================================================================

def _calculate_incentive_adjustments(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig,
    user_reid: str
) -> Optional[pd.DataFrame]:
    """
    Beräknar incitamentjusteringar för alla företag.
    
    Tre typer av incitament:
    1. Kvalitetsincitamentet (AIT/AIF)
    2. Nätförlustincitamentet
    3. Belastningsincitamentet
    
    Varje incitament begränsas till +/-1/3 av avkastningen per år (konfigurerbart).
    """
    try:
        incentive_data = load_incentive_data()
        
        # Hämta avkastning per år (nu med korrekt per-år värden!)
        return_per_year = get_return_per_year(pre_dea, baseline)
        
        df_input = prepare_incentive_input(incentive_data, return_per_year)
        
        # Applicera variable_overrides om de finns
        incentive_config = getattr(config, 'incentive', None)
        if incentive_config:
            variable_overrides = getattr(incentive_config, 'variable_overrides', None)
            if variable_overrides and user_reid:
                df_input = apply_variable_overrides(df_input, user_reid, variable_overrides)
        
        incentive_params = _extract_incentive_params(config)
        
        df_calc = calculate_all_incentives(
            df_input, 
            ret_period_col='ret_period', 
            **incentive_params
        )
        
        df_summary = get_incentive_summary_by_reid(df_calc)
        
        return df_summary
        
    except FileNotFoundError as e:
        print(f"    [VARNING] Incitamentdata saknas: {e}")
        return None
    except Exception as e:
        print(f"    [FEL] Kunde inte beräkna incitament: {e}")
        return None


def _extract_incentive_params(config: Optional[PostDeaConfig]) -> dict:
    """
    Extraherar incitament-parametrar från PostDeaConfig.
    """
    params = {}
    
    if config is None:
        return params
    
    incentive_config = getattr(config, 'incentive', None)
    if incentive_config is None:
        return params
    
    param_mapping = {
        'kpi': 'kpi',
        'k_nf': 'k_nf',
        'sharing_netloss': 'sharing_netloss',
        'adj_max_agg': 'adj_max_agg',
        'adj_max_cemi4': 'adj_max_cemi4',
        'ait_costs': 'ait_costs',
        'aif_costs': 'aif_costs',
        'enable_quality': 'enable_quality',
        'enable_netloss': 'enable_netloss',
        'enable_load': 'enable_load',
    }
    
    for config_attr, param_name in param_mapping.items():
        if hasattr(incentive_config, config_attr):
            value = getattr(incentive_config, config_attr)
            if value is not None:
                params[param_name] = value
    
    return params


def _log_incentive_params(incentive_config) -> None:
    """Loggar incitament-parametrar som avviker från baseline."""
    BASELINE = {
        'adj_max_agg': 1/3,
        'adj_max_cemi4': 0.25,
        'sharing_netloss': 0.75,
        'kpi': {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546},
        'k_nf': {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44},
    }
    
    changes = []
    
    # Enkla parametrar - kolla is not None FÖRE jämförelse
    if (hasattr(incentive_config, 'adj_max_agg') 
        and incentive_config.adj_max_agg is not None 
        and incentive_config.adj_max_agg != BASELINE['adj_max_agg']):
        changes.append(f"adj_max_agg={incentive_config.adj_max_agg:.3f}")
    
    if (hasattr(incentive_config, 'adj_max_cemi4') 
        and incentive_config.adj_max_cemi4 is not None 
        and incentive_config.adj_max_cemi4 != BASELINE['adj_max_cemi4']):
        changes.append(f"adj_max_cemi4={incentive_config.adj_max_cemi4:.3f}")
    
    if (hasattr(incentive_config, 'sharing_netloss') 
        and incentive_config.sharing_netloss is not None 
        and incentive_config.sharing_netloss != BASELINE['sharing_netloss']):
        changes.append(f"sharing_netloss={incentive_config.sharing_netloss:.2f}")
    
    # Dict-parametrar (kpi, k_nf)
    if hasattr(incentive_config, 'kpi') and incentive_config.kpi is not None:
        if incentive_config.kpi != BASELINE['kpi']:
            changes.append("kpi=modified")
    
    if hasattr(incentive_config, 'k_nf') and incentive_config.k_nf is not None:
        if incentive_config.k_nf != BASELINE['k_nf']:
            changes.append("k_nf=modified")
    
    if changes:
        print(f"    Incitament-parametrar: {', '.join(changes)}")