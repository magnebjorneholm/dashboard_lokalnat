"""
intaktsram_assembly.py

Assemblering av intäktsram från alla komponenter.
Summerar kapitalkostnad, påverkbara, opåverkbara, incitament, och övriga komponenter.
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
    
    Formel:
    Intäktsram_Total = Kapitalkostnad_Total
                     + Påverkbara_Periodsumma
                     + Opåverkbara_Kostnader
                     + Flexibilitetstjänster
                     + Avbrottsersättning_12_24h
                     - Avdrag_Statligt_Stöd
                     + Incitamentjustering_Total    <- NY POST
    
    Args:
        capex_result: DataFrame med REId, Kapitalkostnad_Total
        paverkbara_result: DataFrame med REId, Paverkbara_Periodsumma
        sdf_baseline: DataFrame från SDF Excel med opåverkbara och övriga komponenter
        incentive_result: Optional DataFrame med incitamentjusteringar per REId
        
    Returns:
        DataFrame med alla komponenter och Intaktsram_Total
    """
    # Start med CAPEX
    df = capex_result[['REId', 'Kapitalkostnad_Total']].copy()
    
    # Merge påverkbara
    paverkbara_cols = ['REId', 'Paverkbara_Periodsumma', 'Method_used']
    # Include new efficiency fields if present
    if 'Paverkbara_Fore_Periodsumma' in paverkbara_result.columns:
        paverkbara_cols.append('Paverkbara_Fore_Periodsumma')
    if 'Effektivisering_Total' in paverkbara_result.columns:
        paverkbara_cols.append('Effektivisering_Total')
    
    df = df.merge(
        paverkbara_result[paverkbara_cols],
        on='REId',
        how='left'
    )
    
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
    
    # Beräkna total intäktsram inkl. incitament
    df['Intaktsram_Total'] = (
        df['Kapitalkostnad_Total']
        + df['Paverkbara_Periodsumma']
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
    breakdown = [
        ('Kapitalkostnad', user_intaktsram['Kapitalkostnad_Total']),
        ('Påverkbara kostnader', user_intaktsram['Paverkbara_Periodsumma']),
        ('Opåverkbara kostnader', user_intaktsram['Opaverkbara_Kostnader']),
        ('Flexibilitetstjänster', user_intaktsram['Flexibilitetstjanster']),
        ('Avbrottsersättning 12-24h', user_intaktsram['Avbrottsersattning_12_24h']),
        ('Avdrag statligt stöd', -user_intaktsram['Avdrag_Statligt_Stod']),
    ]
    
    # Lägg till incitamentjusteringar om de finns
    if 'Incitamentjustering_Total' in user_intaktsram.index:
        inc_total = user_intaktsram.get('Incitamentjustering_Total', 0)
        if inc_total != 0:
            # Visa dekomposition
            breakdown.append(('', ''))  # Blank rad
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
    
    breakdown.append(('', ''))  # Blank rad
    breakdown.append(('TOTAL INTÄKTSRAM', user_intaktsram['Intaktsram_Total']))
    
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
    total = user_intaktsram['Intaktsram_Total']
    
    components = []
    
    # Huvudkomponenter
    main = [
        ('Kapitalkostnad', 'Kapitalkostnad_Total'),
        ('Påverkbara kostnader', 'Paverkbara_Periodsumma'),
        ('Opåverkbara kostnader', 'Opaverkbara_Kostnader'),
        ('Flexibilitetstjänster', 'Flexibilitetstjanster'),
        ('Avbrottsersättning 12-24h', 'Avbrottsersattning_12_24h'),
    ]
    
    for label, col in main:
        val = user_intaktsram.get(col, 0)
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