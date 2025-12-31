"""
post_dea.py

Stage 5: Post-DEA
Beräknar effektiviseringskrav, incitamentjusteringar, påverkbara kostnader,
och assemblerar intäktsram.
"""

import pandas as pd
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
        capex_for_paverkbara = _prepare_capex_for_intaktsram(pre_dea, baseline)
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
    
    capex_for_intaktsram = _prepare_capex_for_intaktsram(
        pre_dea=pre_dea,
        baseline=baseline
    )
    
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
        user_reid=user_reid  # Skicka med user_reid för variable_overrides
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


def _log_incentive_params(incentive_config) -> None:
    """Loggar incitament-parametrar som avviker från baseline."""
    # Baseline-värden för jämförelse
    BASELINE = {
        'adj_max_agg': 1/3,
        'adj_max_cemi4': 0.25,
        'sharing_netloss': 0.75,
        'kpi': {2024: 1.1546, 2025: 1.1546, 2026: 1.1546, 2027: 1.1546},
        'k_nf': {2024: 753.44, 2025: 753.44, 2026: 753.44, 2027: 753.44},
    }
    
    changes = []
    
    # Enkla parametrar
    if hasattr(incentive_config, 'adj_max_agg') and incentive_config.adj_max_agg != BASELINE['adj_max_agg']:
        changes.append(f"adj_max_agg={incentive_config.adj_max_agg:.3f}")
    if hasattr(incentive_config, 'adj_max_cemi4') and incentive_config.adj_max_cemi4 != BASELINE['adj_max_cemi4']:
        changes.append(f"adj_max_cemi4={incentive_config.adj_max_cemi4:.3f}")
    if hasattr(incentive_config, 'sharing_netloss') and incentive_config.sharing_netloss != BASELINE['sharing_netloss']:
        changes.append(f"sharing_netloss={incentive_config.sharing_netloss:.2f}")
    
    # Dict-parametrar (kpi, k_nf)
    if hasattr(incentive_config, 'kpi') and incentive_config.kpi is not None:
        if incentive_config.kpi != BASELINE['kpi']:
            changes.append("kpi=ändrad")
    if hasattr(incentive_config, 'k_nf') and incentive_config.k_nf is not None:
        if incentive_config.k_nf != BASELINE['k_nf']:
            changes.append("k_nf=ändrad")
    
    # AIT/AIF-kostnader
    if hasattr(incentive_config, 'ait_costs') and incentive_config.ait_costs is not None:
        changes.append("ait_costs=ändrad")
    if hasattr(incentive_config, 'aif_costs') and incentive_config.aif_costs is not None:
        changes.append("aif_costs=ändrad")
    
    # On/off
    if hasattr(incentive_config, 'enable_quality') and not incentive_config.enable_quality:
        changes.append("enable_quality=False")
    if hasattr(incentive_config, 'enable_netloss') and not incentive_config.enable_netloss:
        changes.append("enable_netloss=False")
    if hasattr(incentive_config, 'enable_load') and not incentive_config.enable_load:
        changes.append("enable_load=False")
    
    # Variable overrides (NYA)
    if hasattr(incentive_config, 'variable_overrides') and incentive_config.variable_overrides:
        n = len(incentive_config.variable_overrides)
        changes.append(f"variable_overrides={n} st")
    
    if changes:
        print(f"    Parametrar: {', '.join(changes)}")


def _calculate_incentive_adjustments(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput,
    config: PostDeaConfig = None,
    user_reid: str = None
) -> pd.DataFrame:
    """
    Beräknar incitamentjusteringar för alla företag.
    
    Tre typer av incitament:
    1. Kvalitetsincitamentet (AIT/AIF)
    2. Nätförlustincitamentet
    3. Belastningsincitamentet
    
    Varje incitament begränsas till +/-1/3 av avkastningen per år (konfigurerbart).
    
    Args:
        pre_dea: Output från Pre-DEA stage
        baseline: Output från Baseline stage
        config: PostDeaConfig med incentive-parametrar (None = baseline)
        user_reid: REId för användarens företag (för variable_overrides)
    
    Returns:
        DataFrame med periodsummor per REId (tkr):
        - Kvalitetsjustering_Total
        - Natforlustjustering_Total
        - Belastningsjustering_Total
        - Incitamentjustering_Total
        - Missing_Incentive_Data (bool)
        
        Returnerar None om incitamentdata saknas.
    """
    try:
        # Ladda incitamentdata
        incentive_data = load_incentive_data()
        
        # Hämta avkastning per år
        return_per_year = get_return_per_year(pre_dea, baseline)
        
        # Förbered input med faktisk avkastning
        df_input = prepare_incentive_input(incentive_data, return_per_year)
        
        # Applicera variable_overrides om de finns
        if config and hasattr(config, 'incentive') and config.incentive:
            variable_overrides = getattr(config.incentive, 'variable_overrides', None)
            if variable_overrides and user_reid:
                df_input = apply_variable_overrides(df_input, user_reid, variable_overrides)
        
        # Extrahera incitament-parametrar från config
        incentive_params = _extract_incentive_params(config)
        
        # Kör beräkning med parametrar
        df_calc = calculate_all_incentives(df_input, ret_period_col='ret_period', **incentive_params)
        
        # Aggregera till periodsummor per REId
        df_summary = get_incentive_summary_by_reid(df_calc)
        
        return df_summary
        
    except FileNotFoundError as e:
        print(f"    [VARNING] Incitamentdata saknas: {e}")
        return None
    except Exception as e:
        print(f"    [FEL] Kunde inte beräkna incitament: {e}")
        return None


def _extract_incentive_params(config: PostDeaConfig) -> dict:
    """
    Extraherar incitament-parametrar från PostDeaConfig.
    
    Args:
        config: PostDeaConfig (kan vara None eller sakna incentive-attribut)
        
    Returns:
        Dict med parametrar för calculate_all_incentives
    """
    params = {}
    
    # Om ingen config eller ingen incentive-attribut, returnera tom dict (använd baseline)
    if config is None:
        return params
    
    incentive = getattr(config, 'incentive', None)
    if incentive is None:
        return params
    
    # Extrahera parametrar om de finns
    if hasattr(incentive, 'adj_max_agg') and incentive.adj_max_agg is not None:
        params['adj_max_agg'] = incentive.adj_max_agg
    
    if hasattr(incentive, 'adj_max_cemi4') and incentive.adj_max_cemi4 is not None:
        params['adj_max_cemi4'] = incentive.adj_max_cemi4
    
    if hasattr(incentive, 'sharing_netloss') and incentive.sharing_netloss is not None:
        params['sharing_netloss'] = incentive.sharing_netloss
    
    if hasattr(incentive, 'kpi') and incentive.kpi is not None:
        # KPI är en dict per år - om användaren anger ett värde, använd samma för alla år
        if isinstance(incentive.kpi, (int, float)):
            params['kpi'] = {year: incentive.kpi for year in [2024, 2025, 2026, 2027]}
        else:
            params['kpi'] = incentive.kpi
    
    if hasattr(incentive, 'k_nf') and incentive.k_nf is not None:
        # k_nf är en dict per år - om användaren anger ett värde, använd samma för alla år
        if isinstance(incentive.k_nf, (int, float)):
            params['k_nf'] = {year: incentive.k_nf for year in [2024, 2025, 2026, 2027]}
        else:
            params['k_nf'] = incentive.k_nf
    
    if hasattr(incentive, 'ait_costs') and incentive.ait_costs is not None:
        params['ait_costs'] = incentive.ait_costs
    
    if hasattr(incentive, 'aif_costs') and incentive.aif_costs is not None:
        params['aif_costs'] = incentive.aif_costs
    
    # Aktivera/inaktivera
    if hasattr(incentive, 'enable_quality'):
        params['enable_quality'] = incentive.enable_quality
    
    if hasattr(incentive, 'enable_netloss'):
        params['enable_netloss'] = incentive.enable_netloss
    
    if hasattr(incentive, 'enable_load'):
        params['enable_load'] = incentive.enable_load
    
    return params


def _prepare_capex_for_intaktsram(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Förbereder kapitalkostnad-data för intäktsram assembly.
    
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
        # Direkt från SDF - redan periodsumma
        return _get_capex_from_sdf(baseline)
    
    elif method == 'wacc_scaling':
        # Skala periodsummor (inte årsvärde × 4)
        return _calculate_wacc_scaled_period_capex(pre_dea, baseline)
    
    elif method in ['kent_upload', 'parameter_change']:
        # KENT-output - verifiera att det är periodsumma
        df_kent = pre_dea.df_all_companies
        
        if 'Kapitalkostnad_Period' in df_kent.columns:
            return df_kent[['REId', 'Kapitalkostnad_Period']].rename(
                columns={'Kapitalkostnad_Period': 'Kapitalkostnad_Total'}
            )
        elif 'Kapitalkostnad_Total' in df_kent.columns:
            return df_kent[['REId', 'Kapitalkostnad_Total']]
        else:
            raise ValueError(
                f"KENT-output saknar periodsumma för kapitalkostnad. "
                f"Förväntade kolumner: 'Kapitalkostnad_Period' eller 'Kapitalkostnad_Total'. "
                "Kontrollera KENT-output och kör om pre-dea-steget."
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
    
    Varför detta är korrekt:
    - Kapitalförslitning (avskrivning) beror på NUAV och livslängd, inte på WACC
    - Kapitalbindning (avkastning) = kapitalbas x WACC, proportionell mot WACC
    - Att ta årsvärde x 4 är FEL eftersom kapitalbindningen avtar varje halvår
      när tillgångarna åldras
    
    Args:
        pre_dea: Output från Pre-DEA stage (innehåller wacc_used)
        baseline: Output från Baseline stage (innehåller SDF IR med periodsummor)
    
    Returns:
        DataFrame med: REId, Kapitalkostnad_Total (korrekt skalad periodsumma)
    """
    
    # Validera att vi har WACC
    if pre_dea.wacc_used is None:
        raise ValueError(
            "wacc_used saknas i PreDeaStageOutput för wacc_scaling metod. "
            "Kontrollera att pre_dea.py sätter wacc_used korrekt."
        )
    
    new_wacc = pre_dea.wacc_used
    baseline_wacc = baseline.wacc
    
    # Validera SDF-kolumner
    sdf = baseline.sdf_ir.copy()
    
    if SDF_COL_KAPITALFORSLITNING not in sdf.columns:
        raise ValueError(
            f"Kolumn '{SDF_COL_KAPITALFORSLITNING}' saknas i SDF IR. "
            f"Tillgängliga kolumner: {list(sdf.columns)}"
        )
    
    if SDF_COL_KAPITALBINDNING not in sdf.columns:
        raise ValueError(
            f"Kolumn '{SDF_COL_KAPITALBINDNING}' saknas i SDF IR. "
            f"Tillgängliga kolumner: {list(sdf.columns)}"
        )
    
    # Extrahera periodsummor
    df = sdf[['REId', SDF_COL_KAPITALFORSLITNING, SDF_COL_KAPITALBINDNING]].copy()
    df.columns = ['REId', 'Kapitalforslitning_Period', 'Kapitalbindning_Period']
    
    # Konvertera till numeriska värden
    df['Kapitalforslitning_Period'] = pd.to_numeric(
        df['Kapitalforslitning_Period'], errors='coerce'
    ).fillna(0)
    df['Kapitalbindning_Period'] = pd.to_numeric(
        df['Kapitalbindning_Period'], errors='coerce'
    ).fillna(0)
    
    # Beräkna skalningsfaktor
    scaling_factor = new_wacc / baseline_wacc
    
    print(f"    WACC-skalning av periodsummor:")
    print(f"      Baseline WACC: {baseline_wacc:.4f} ({baseline_wacc*100:.2f}%)")
    print(f"      Ny WACC: {new_wacc:.4f} ({new_wacc*100:.2f}%)")
    print(f"      Skalningsfaktor: {scaling_factor:.4f}")
    
    # Skala endast kapitalbindningen
    df['Kapitalbindning_Skalad'] = df['Kapitalbindning_Period'] * scaling_factor
    
    # Ny periodsumma = Kapitalförslitning (oförändrad) + Kapitalbindning (skalad)
    df['Kapitalkostnad_Total'] = df['Kapitalforslitning_Period'] + df['Kapitalbindning_Skalad']
    
    # Logga förändring för verifiering
    total_baseline = df['Kapitalforslitning_Period'].sum() + df['Kapitalbindning_Period'].sum()
    total_scaled = df['Kapitalkostnad_Total'].sum()
    delta_pct = (total_scaled / total_baseline - 1) * 100
    
    print(f"      Baseline periodsumma (alla): {total_baseline:,.0f} tkr")
    print(f"      Skalad periodsumma (alla): {total_scaled:,.0f} tkr")
    print(f"      Förändring: {delta_pct:+.2f}%")
    
    return df[['REId', 'Kapitalkostnad_Total']]


def get_return_per_year(
    pre_dea: PreDeaStageOutput,
    baseline: BaselineStageOutput
) -> pd.DataFrame:
    """
    Hämtar avkastning per år för alla företag, baserat på capex_method.
    
    Används för incitamentjusteringens 1/3-cap som appliceras per år.
    
    Källor beroende på capex_method:
    - 'baseline': SDF "varav Kapital-bindning" / 4
    - 'wacc_scaling': SDF "varav Kapital-bindning" x (ny_WACC / baseline_WACC) / 4
    - 'kent_upload': KENT-output Avkastning_{year}
    - 'parameter_change': KENT-output Avkastning_{year}
    
    Args:
        pre_dea: Output från Pre-DEA stage
        baseline: Output från Baseline stage
    
    Returns:
        DataFrame med: REId, Avkastning_2024, Avkastning_2025, 
                       Avkastning_2026, Avkastning_2027 (alla i tkr)
    """
    
    method = pre_dea.capex_method
    years = [2024, 2025, 2026, 2027]
    
    if method == 'baseline':
        # Hämta periodsumma från SDF och dela med 4
        return _get_return_from_sdf(baseline, scaling_factor=1.0)
    
    elif method == 'wacc_scaling':
        # Skala periodsumma med WACC-kvot och dela med 4
        if pre_dea.wacc_used is None:
            raise ValueError(
                "wacc_used saknas i PreDeaStageOutput för wacc_scaling metod."
            )
        scaling_factor = pre_dea.wacc_used / baseline.wacc
        return _get_return_from_sdf(baseline, scaling_factor=scaling_factor)
    
    elif method in ['kent_upload', 'parameter_change']:
        # Hämta per-år avkastning från KENT-output
        return _get_return_from_kent(pre_dea, years)
    
    else:
        raise ValueError(
            f"Okänd capex_method: '{method}'. "
            f"Förväntade: 'baseline', 'wacc_scaling', 'parameter_change', 'kent_upload'"
        )


def _get_return_from_sdf(
    baseline: BaselineStageOutput,
    scaling_factor: float = 1.0
) -> pd.DataFrame:
    """
    Hämtar avkastning per år från SDF (för baseline och wacc_scaling).
    
    Approximerar per-år genom att ta periodsumma / 4.
    """
    sdf = baseline.sdf_ir.copy()
    
    if SDF_COL_KAPITALBINDNING not in sdf.columns:
        raise ValueError(
            f"Kolumn '{SDF_COL_KAPITALBINDNING}' saknas i SDF IR."
        )
    
    df = sdf[['REId']].copy()
    
    # Hämta periodsumma och skala
    kapitalbindning_period = pd.to_numeric(
        sdf[SDF_COL_KAPITALBINDNING], errors='coerce'
    ).fillna(0)
    
    kapitalbindning_skalad = kapitalbindning_period * scaling_factor
    
    # Approximera per år (periodsumma / 4)
    avkastning_per_year = kapitalbindning_skalad / 4
    
    # Sätt samma värde för alla år (approximation)
    for year in [2024, 2025, 2026, 2027]:
        df[f'Avkastning_{year}'] = avkastning_per_year
    
    return df


def _get_return_from_kent(
    pre_dea: PreDeaStageOutput,
    years: list
) -> pd.DataFrame:
    """
    Hämtar avkastning per år från KENT-output (för kent_upload och parameter_change).
    """
    df_kent = pre_dea.df_all_companies
    
    # Verifiera att per-år kolumner finns
    missing_years = []
    for year in years:
        col = f'Avkastning_{year}'
        if col not in df_kent.columns:
            missing_years.append(year)
    
    if missing_years:
        raise ValueError(
            f"Avkastning per år saknas i KENT-output för år: {missing_years}. "
            "Förväntade kolumner: Avkastning_2024, Avkastning_2025, etc. "
            "Kontrollera att kent_calculations.py genererar dessa kolumner."
        )
    
    # Extrahera relevanta kolumner
    cols = ['REId'] + [f'Avkastning_{year}' for year in years]
    return df_kent[cols].copy()