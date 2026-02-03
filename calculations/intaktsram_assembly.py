"""
intaktsram_assembly.py

Assemblering av intäktsram från alla komponenter.
Summerar kapitalkostnad, påverkbara, opåverkbara, incitament, och övriga komponenter.

Vid TOTEX-metod: CAPEX reduceras separat med sin andel av effektiviseringskravet.
"""

import pandas as pd
from typing import Optional


def assemble_intaktsram(
    capex_result: pd.DataFrame,
    paverkbara_result: pd.DataFrame,
    sdf_baseline: pd.DataFrame,
    incentive_result: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Assemblerar komplett intäktsram för alla företag.
    
    Formel (OPEX-metod):
    Intäktsram_Total = Kapitalkostnad_Total
                     + Påverkbara_Periodsumma (efter OPEX-effektivisering)
                     + Opåverkbara_Kostnader
                     + Flexibilitetstjänster
                     + Avbrottsersättning_12_24h
                     - Avdrag_Statligt_Stöd
                     + Incitamentjustering_Total
    
    Formel (TOTEX-metod):
    Intäktsram_Total = Kapitalkostnad_Efter_Effektivisering (CAPEX - CAPEX_Effektivisering)
                     + OPEX_Efter (OPEX-andel av påverkbara efter effektivisering)
                     + Opåverkbara_Kostnader
                     + Flexibilitetstjänster
                     + Avbrottsersättning_12_24h
                     - Avdrag_Statligt_Stöd
                     + Incitamentjustering_Total
    
    Args:
        capex_result: DataFrame med REId, Kapitalkostnad_Total
        paverkbara_result: DataFrame med REId, Paverkbara_Periodsumma, OPEX/CAPEX-fält
        sdf_baseline: DataFrame från SDF Excel med opåverkbara och övriga komponenter
        incentive_result: Optional DataFrame med incitamentjusteringar per REId
        
    Returns:
        DataFrame med alla komponenter och Intaktsram_Total
    """
    # Start med CAPEX
    df = capex_result[['REId', 'Kapitalkostnad_Total']].copy()
    
    # Merge påverkbara - inkludera alla relevanta fält
    paverkbara_cols = ['REId', 'Paverkbara_Periodsumma', 'Method_used']
    
    # Legacy efficiency fields
    for col in ['Paverkbara_Fore_Periodsumma', 'Effektivisering_Total']:
        if col in paverkbara_result.columns:
            paverkbara_cols.append(col)
    
    # New separated OPEX/CAPEX fields
    for col in ['OPEX_Fore', 'OPEX_Efter', 'OPEX_Effektivisering',
                'CAPEX_Fore', 'CAPEX_Efter', 'CAPEX_Effektivisering',
                'OPEX_Andel', 'CAPEX_Andel']:
        if col in paverkbara_result.columns:
            paverkbara_cols.append(col)
    
    df = df.merge(
        paverkbara_result[paverkbara_cols],
        on='REId',
        how='left'
    )
    
    # Apply CAPEX efficiency reduction for TOTEX method
    # Kapitalkostnad_Efter_Effektivisering = Kapitalkostnad_Total - CAPEX_Effektivisering
    if 'CAPEX_Effektivisering' in df.columns:
        df['CAPEX_Effektivisering'] = df['CAPEX_Effektivisering'].fillna(0)
        df['Kapitalkostnad_Efter_Effektivisering'] = (
            df['Kapitalkostnad_Total'] - df['CAPEX_Effektivisering']
        )
    else:
        df['CAPEX_Effektivisering'] = 0
        df['Kapitalkostnad_Efter_Effektivisering'] = df['Kapitalkostnad_Total']
    
    # Merge SDF baseline komponenter
    sdf_cols = [
        'REId',
        'Opåverkbara kostnader',
        'Kostnader för flexibilitetstjänster',
        'Avbrottsersättning 12-24 timmar',
        'Avdrag av kapitalkostnader pga anläggningar med statligt stöd'
    ]
    
    # Validera att kolumner finns i SDF
    available_cols = ['REId']
    col_mapping = {
        'Opåverkbara kostnader': 'Opaverkbara_Kostnader',
        'Kostnader för flexibilitetstjänster': 'Flexibilitetstjanster',
        'Avbrottsersättning 12-24 timmar': 'Avbrottsersattning_12_24h',
        'Avdrag av kapitalkostnader pga anläggningar med statligt stöd': 'Avdrag_Statligt_Stod'
    }
    
    for col in sdf_cols[1:]:  # Skip REId
        if col in sdf_baseline.columns:
            available_cols.append(col)
    
    sdf_subset = sdf_baseline[available_cols].copy()
    
    # Rename kolumner
    rename_dict = {k: v for k, v in col_mapping.items() if k in sdf_subset.columns}
    sdf_subset = sdf_subset.rename(columns=rename_dict)
    
    # Merge med main dataframe
    df = df.merge(sdf_subset, on='REId', how='left')
    
    # Fyll NaN med 0 för komponenter som saknas
    for col in col_mapping.values():
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0
    
    # Merge incitamentjusteringar om tillgängliga
    if incentive_result is not None and not incentive_result.empty:
        incentive_cols = [
            'REId',
            'Kvalitetsjustering_Total',
            'Natforlustjustering_Total',
            'Belastningsjustering_Total',
            'Incitamentjustering_Total',
            'Missing_Incentive_Data'
        ]
        # Välj endast kolumner som finns
        available_inc_cols = [c for c in incentive_cols if c in incentive_result.columns]
        
        df = df.merge(
            incentive_result[available_inc_cols],
            on='REId',
            how='left'
        )
        
        # Fyll NaN med 0 för incitamentkomponenter
        for col in ['Kvalitetsjustering_Total', 'Natforlustjustering_Total',
                    'Belastningsjustering_Total', 'Incitamentjustering_Total']:
            if col in df.columns:
                df[col] = df[col].fillna(0)
            else:
                df[col] = 0
        
        # Sätt Missing_Incentive_Data till False om saknas
        if 'Missing_Incentive_Data' not in df.columns:
            df['Missing_Incentive_Data'] = False
    else:
        # Ingen incitamentdata - sätt allt till 0
        df['Kvalitetsjustering_Total'] = 0
        df['Natforlustjustering_Total'] = 0
        df['Belastningsjustering_Total'] = 0
        df['Incitamentjustering_Total'] = 0
        df['Missing_Incentive_Data'] = True
    
    # Determine which CAPEX value to use based on method
    # For TOTEX: use Kapitalkostnad_Efter_Effektivisering
    # For OPEX: use Kapitalkostnad_Total (no reduction)
    method_is_totex = df['Method_used'] == 'TOTEX'
    
    df['Kapitalkostnad_I_Intaktsram'] = df.apply(
        lambda row: row['Kapitalkostnad_Efter_Effektivisering'] 
                    if row['Method_used'] == 'TOTEX' 
                    else row['Kapitalkostnad_Total'],
        axis=1
    )
    
    # For TOTEX, use OPEX_Efter; for OPEX, use Paverkbara_Periodsumma
    # (These should be the same value, but OPEX_Efter is more explicit)
    if 'OPEX_Efter' in df.columns:
        df['Paverkbara_I_Intaktsram'] = df.apply(
            lambda row: row.get('OPEX_Efter', row['Paverkbara_Periodsumma'])
                        if pd.notna(row.get('OPEX_Efter'))
                        else row['Paverkbara_Periodsumma'],
            axis=1
        )
    else:
        df['Paverkbara_I_Intaktsram'] = df['Paverkbara_Periodsumma']
    
    # Beräkna total intäktsram inkl. incitament
    # Uses the method-appropriate values for CAPEX and OPEX
    df['Intaktsram_Total'] = (
        df['Kapitalkostnad_I_Intaktsram']
        + df['Paverkbara_I_Intaktsram']
        + df['Opaverkbara_Kostnader']
        + df['Flexibilitetstjanster']
        + df['Avbrottsersattning_12_24h']
        - df['Avdrag_Statligt_Stod']
        + df['Incitamentjustering_Total']
    )
    
    return df


def extract_user_intaktsram(
    intaktsram_df: pd.DataFrame,
    user_reid: str
) -> pd.Series:
    """
    Extraherar intäktsram för ett specifikt företag.
    
    Args:
        intaktsram_df: DataFrame med alla företags intäktsramar
        user_reid: REId för användarens företag
        
    Returns:
        Series med alla komponenter för detta företag
        
    Raises:
        ValueError: Om REId inte finns i data
    """
    result = intaktsram_df[intaktsram_df['REId'] == user_reid]
    
    if result.empty:
        raise ValueError(f"REId '{user_reid}' finns inte i intäktsram-data")
    
    return result.iloc[0]


def create_intaktsram_breakdown(
    user_intaktsram: pd.Series
) -> pd.DataFrame:
    """
    Skapar breakdown-tabell för visualisering.
    
    Args:
        user_intaktsram: Series med alla komponenter
        
    Returns:
        DataFrame med kolumner: Komponent, Värde (tkr)
    """
    method = user_intaktsram.get('Method_used', 'OPEX')
    
    # Use method-appropriate values
    capex_value = user_intaktsram.get('Kapitalkostnad_I_Intaktsram', 
                                       user_intaktsram.get('Kapitalkostnad_Total', 0))
    paverkbara_value = user_intaktsram.get('Paverkbara_I_Intaktsram',
                                            user_intaktsram.get('Paverkbara_Periodsumma', 0))
    
    breakdown = [
        ('Kapitalkostnad', capex_value),
        ('Påverkbara kostnader', paverkbara_value),
        ('Opåverkbara kostnader', user_intaktsram.get('Opaverkbara_Kostnader', 0)),
        ('Flexibilitetstjänster', user_intaktsram.get('Flexibilitetstjanster', 0)),
        ('Avbrottsersättning 12-24h', user_intaktsram.get('Avbrottsersattning_12_24h', 0)),
        ('Avdrag statligt stöd', -user_intaktsram.get('Avdrag_Statligt_Stod', 0)),
    ]
    
    # Show efficiency breakdown for TOTEX
    if method == 'TOTEX':
        capex_eff = user_intaktsram.get('CAPEX_Effektivisering', 0)
        opex_eff = user_intaktsram.get('OPEX_Effektivisering', 0)
        if capex_eff != 0 or opex_eff != 0:
            breakdown.append(('', ''))
            breakdown.append(('Effektivisering (TOTEX):', ''))
            if opex_eff != 0:
                breakdown.append(('  - OPEX-reduktion', -opex_eff))
            if capex_eff != 0:
                breakdown.append(('  - CAPEX-reduktion', -capex_eff))
    
    # Lägg till incitamentjusteringar om de finns
    if 'Incitamentjustering_Total' in user_intaktsram.index:
        inc_total = user_intaktsram.get('Incitamentjustering_Total', 0)
        if inc_total != 0:
            breakdown.append(('', ''))
            breakdown.append(('Incitamentjusteringar:', ''))
            
            qual = user_intaktsram.get('Kvalitetsjustering_Total', 0)
            loss = user_intaktsram.get('Natforlustjustering_Total', 0)
            util = user_intaktsram.get('Belastningsjustering_Total', 0)
            
            if qual != 0:
                breakdown.append(('  - Kvalitetsincitament', qual))
            if loss != 0:
                breakdown.append(('  - Nätförlustincitament', loss))
            if util != 0:
                breakdown.append(('  - Belastningsincitament', util))
            
            breakdown.append(('Incitamentjustering totalt', inc_total))
    
    breakdown.append(('', ''))
    breakdown.append(('TOTAL INTÄKTSRAM', user_intaktsram.get('Intaktsram_Total', 0)))
    
    df = pd.DataFrame(breakdown, columns=['Komponent', 'Värde (tkr)'])
    
    return df


def create_detailed_breakdown(
    user_intaktsram: pd.Series,
    show_incitament_details: bool = True
) -> pd.DataFrame:
    """
    Skapar detaljerad breakdown med alla incitamentkomponenter.
    
    Args:
        user_intaktsram: Series med alla komponenter
        show_incitament_details: Om True, visa kvalitet/nätförlust/belastning separat
        
    Returns:
        DataFrame med kolumner: Komponent, Värde (tkr), Andel (%)
    """
    total = user_intaktsram.get('Intaktsram_Total', 0)
    method = user_intaktsram.get('Method_used', 'OPEX')
    
    components = []
    
    # Use method-appropriate values
    capex_value = user_intaktsram.get('Kapitalkostnad_I_Intaktsram', 
                                       user_intaktsram.get('Kapitalkostnad_Total', 0))
    paverkbara_value = user_intaktsram.get('Paverkbara_I_Intaktsram',
                                            user_intaktsram.get('Paverkbara_Periodsumma', 0))
    
    # Huvudkomponenter
    main = [
        ('Kapitalkostnad', capex_value),
        ('Påverkbara kostnader', paverkbara_value),
        ('Opåverkbara kostnader', user_intaktsram.get('Opaverkbara_Kostnader', 0)),
        ('Flexibilitetstjänster', user_intaktsram.get('Flexibilitetstjanster', 0)),
        ('Avbrottsersättning 12-24h', user_intaktsram.get('Avbrottsersattning_12_24h', 0)),
    ]
    
    for label, val in main:
        pct = (val / total * 100) if total != 0 else 0
        components.append((label, val, pct))
    
    # Avdrag (negativt)
    avdrag = user_intaktsram.get('Avdrag_Statligt_Stod', 0)
    if avdrag != 0:
        pct = (-avdrag / total * 100) if total != 0 else 0
        components.append(('Avdrag statligt stöd', -avdrag, pct))
    
    # Incitamentjusteringar
    inc_total = user_intaktsram.get('Incitamentjustering_Total', 0)
    
    if show_incitament_details and inc_total != 0:
        qual = user_intaktsram.get('Kvalitetsjustering_Total', 0)
        loss = user_intaktsram.get('Natforlustjustering_Total', 0)
        util = user_intaktsram.get('Belastningsjustering_Total', 0)
        
        if qual != 0:
            pct = (qual / total * 100) if total != 0 else 0
            components.append(('Kvalitetsincitament', qual, pct))
        if loss != 0:
            pct = (loss / total * 100) if total != 0 else 0
            components.append(('Nätförlustincitament', loss, pct))
        if util != 0:
            pct = (util / total * 100) if total != 0 else 0
            components.append(('Belastningsincitament', util, pct))
    elif inc_total != 0:
        pct = (inc_total / total * 100) if total != 0 else 0
        components.append(('Incitamentjustering', inc_total, pct))
    
    df = pd.DataFrame(components, columns=['Komponent', 'Värde (tkr)', 'Andel (%)'])
    
    return df