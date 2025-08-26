# ir_model.py
# Beräkningslogik för intäktsram-dekomposition och scenario-hantering

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class IntaktsramModel:
    """
    Huvudklass för intäktsram-beräkningar och scenario-hantering.
    Hanterar baseline-data och applicering av scenarier från andra sektioner.
    """
    
    def __init__(self, baseline_df: pd.DataFrame):
        """
        Initialiserar modellen med baseline-data.
        
        Args:
            baseline_df: DataFrame med baseline intäktsram-data
        """
        self.baseline_df = baseline_df.copy()
        self.scenarios = {}
        self.current_scenario = None
        
        # Definiera komponent-mappning
        self.components = {
            'paverkbara': 'Paverkbara_Kostnader',
            'opaverkbara': 'Opaverkbara_Kostnader', 
            'flexibilitetstjanster': 'Flexibilitetstjanster',
            'avbrottsersattning': 'Avbrottsersattning_12_24h',
            'kapitalkostnad': 'Kapitalkostnad_Total'
        }
    
    
    def create_scenario(self, name: str, description: str = "") -> Dict:
        """
        Skapar ett nytt scenario baserat på baseline.
        
        Args:
            name: Scenario-namn
            description: Beskrivning av scenariot
            
        Returns:
            Dict med scenario-metadata
        """
        if name in self.scenarios:
            raise ValueError(f"Scenario '{name}' existerar redan")
        
        scenario = {
            'name': name,
            'description': description,
            'created': datetime.now(),
            'baseline_snapshot': self.baseline_df.copy(),
            'modifications': {},
            'component_sources': {comp: 'baseline' for comp in self.components.keys()},
            'metadata': {}
        }
        
        self.scenarios[name] = scenario
        self.current_scenario = name
        
        return scenario
    
    
    def apply_scenario_modification(
        self, 
        component: str, 
        modifications: Dict[str, float], 
        source: str = "manual",
        metadata: Optional[Dict] = None
    ):
        """
        Applicerar modifikationer på en komponent i aktuellt scenario.
        
        Args:
            component: Komponent att modifiera ('paverkbara', 'kapitalkostnad', etc.)
            modifications: Dict med REId -> nytt värde
            source: Källa för modifikationen ('manual', 'effektiviseringskrav', 'kapitalbas')
            metadata: Extra metadata för spårbarhet
        """
        if not self.current_scenario:
            raise ValueError("Inget aktivt scenario - skapa ett scenario först")
        
        if component not in self.components:
            raise ValueError(f"Okänd komponent: {component}")
        
        scenario = self.scenarios[self.current_scenario]
        
        scenario['modifications'][component] = {
            'values': modifications,
            'source': source,
            'applied': datetime.now(),
            'metadata': metadata or {}
        }
        
        scenario['component_sources'][component] = source
    
    
    def get_working_dataframe(self, scenario_name: Optional[str] = None) -> pd.DataFrame:
        """
        Hämtar arbetsdataframe med applicerade scenario-modifikationer.
        
        Args:
            scenario_name: Scenario att använda (default: aktuellt scenario)
            
        Returns:
            DataFrame med applicerade modifikationer
        """
        if scenario_name is None:
            scenario_name = self.current_scenario
        
        if not scenario_name or scenario_name not in self.scenarios:
            return self.baseline_df.copy()
        
        scenario = self.scenarios[scenario_name]
        working_df = scenario['baseline_snapshot'].copy()
        
        # Applicera alla modifikationer
        for component, mod_data in scenario['modifications'].items():
            if component in self.components and 'values' in mod_data:
                self._apply_component_modifications(
                    working_df, 
                    component, 
                    mod_data['values'],
                    mod_data['source']
                )
        
        # Omberäkna total intäktsram
        working_df = self._recalculate_totals(working_df)
        
        return working_df
    
    
    def _apply_component_modifications(
        self, 
        df: pd.DataFrame, 
        component: str, 
        modifications: Dict[str, float],
        source: str
    ):
        """Applicerar modifikationer på en specifik komponent."""
        col_name = self.components[component]
        
        for reid, new_value in modifications.items():
            mask = df['REId'] == reid
            if mask.any():
                df.loc[mask, col_name] = new_value
                df.loc[mask, f'Källa_{component.title()}'] = f"Scenario ({source})"
                df.loc[mask, f'Uppdaterad_{component.title()}'] = True
    
    
    def _recalculate_totals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Omberäknar total intäktsram baserat på komponenter."""
        component_cols = [
            self.components['paverkbara'],
            self.components['opaverkbara'],
            self.components['flexibilitetstjanster'], 
            self.components['avbrottsersattning'],
            self.components['kapitalkostnad']
        ]
        
        # Beräkna ny total
        df['Intaktsram_Beraknad'] = df[component_cols].sum(axis=1, skipna=False)
        
        # Beräkna delta mot baseline
        if 'Intaktsram_Total' in df.columns:
            df['Delta_Intaktsram'] = df['Intaktsram_Beraknad'] - df['Intaktsram_Total']
            df['Delta_Procent'] = (df['Delta_Intaktsram'] / df['Intaktsram_Total'] * 100).round(2)
        
        return df
    
    
    def calculate_scenario_impact(self, scenario_name: Optional[str] = None) -> Dict:
        """
        Beräknar påverkan av ett scenario jämfört med baseline.
        
        Returns:
            Dict med aggregerad påverkan och statistik
        """
        working_df = self.get_working_dataframe(scenario_name)
        
        if 'Delta_Intaktsram' not in working_df.columns:
            return {'total_impact': 0, 'affected_companies': 0}
        
        delta_series = working_df['Delta_Intaktsram'].fillna(0)
        
        impact = {
            'total_impact_tkr': delta_series.sum(),
            'average_impact_tkr': delta_series.mean(),
            'affected_companies': (abs(delta_series) > 0).sum(),
            'positive_impact_companies': (delta_series > 0).sum(),
            'negative_impact_companies': (delta_series < 0).sum(),
            'max_increase_tkr': delta_series.max(),
            'max_decrease_tkr': delta_series.min(),
            'median_impact_tkr': delta_series.median()
        }
        
        return impact
    
    
    def get_component_breakdown(
        self, 
        reid: str, 
        scenario_name: Optional[str] = None
    ) -> Dict:
        """
        Hämtar detaljerad breakdown för ett specifikt företag.
        
        Args:
            reid: Företags-ID
            scenario_name: Scenario att använda
            
        Returns:
            Dict med komponent-breakdown
        """
        working_df = self.get_working_dataframe(scenario_name)
        
        entity_data = working_df[working_df['REId'] == reid]
        if entity_data.empty:
            raise ValueError(f"REId {reid} hittades inte")
        
        row = entity_data.iloc[0]
        
        breakdown = {}
        for component, col_name in self.components.items():
            breakdown[component] = {
                'value': row.get(col_name, 0),
                'source': row.get(f'Källa_{component.title()}', 'Baseline'),
                'updated': row.get(f'Uppdaterad_{component.title()}', False)
            }
        
        # Lägg till totaler
        breakdown['total'] = {
            'baseline': row.get('Intaktsram_Total', 0),
            'calculated': row.get('Intaktsram_Beraknad', 0),
            'delta': row.get('Delta_Intaktsram', 0),
            'delta_percent': row.get('Delta_Procent', 0)
        }
        
        return breakdown
    
    
    def validate_scenario_data(self, scenario_name: str) -> List[str]:
        """
        Validerar scenario-data och returnerar lista med varningar.
        
        Returns:
            Lista med varningsmeddelanden
        """
        warnings = []
        
        if scenario_name not in self.scenarios:
            warnings.append(f"Scenario '{scenario_name}' existerar inte")
            return warnings
        
        working_df = self.get_working_dataframe(scenario_name)
        
        # Kontrollera för stora förändringar
        if 'Delta_Procent' in working_df.columns:
            large_changes = working_df[abs(working_df['Delta_Procent']) > 20]
            if not large_changes.empty:
                warnings.append(
                    f"{len(large_changes)} företag har förändringar över 20%: "
                    f"{', '.join(large_changes['REId'].astype(str))}"
                )
        
        # Kontrollera negativa värden
        for component, col_name in self.components.items():
            negative_values = working_df[working_df[col_name] < 0]
            if not negative_values.empty:
                warnings.append(
                    f"Negativa värden i {component}: "
                    f"{', '.join(negative_values['REId'].astype(str))}"
                )
        
        # Kontrollera saknade värden
        for component, col_name in self.components.items():
            missing_values = working_df[working_df[col_name].isna()]
            if not missing_values.empty:
                warnings.append(
                    f"Saknade värden i {component}: "
                    f"{', '.join(missing_values['REId'].astype(str))}"
                )
        
        return warnings
    
    
    def export_scenario(
        self, 
        scenario_name: str, 
        filepath: str, 
        format: str = 'parquet'
    ):
        """
        Exporterar scenario-data till fil.
        
        Args:
            scenario_name: Scenario att exportera
            filepath: Sökväg för export
            format: Filformat ('parquet', 'excel', 'csv')
        """
        working_df = self.get_working_dataframe(scenario_name)
        scenario = self.scenarios[scenario_name]
        
        # Lägg till scenario-metadata
        working_df.attrs['scenario_metadata'] = {
            'name': scenario['name'],
            'description': scenario['description'],
            'created': scenario['created'].isoformat(),
            'exported': datetime.now().isoformat(),
            'modifications': scenario['modifications'],
            'component_sources': scenario['component_sources']
        }
        
        if format.lower() == 'parquet':
            working_df.to_parquet(filepath)
        elif format.lower() == 'excel':
            working_df.to_excel(filepath, index=False)
        elif format.lower() == 'csv':
            working_df.to_csv(filepath, index=False)
        else:
            raise ValueError(f"Okänt format: {format}")
    
    
    def reset_component(self, component: str, scenario_name: Optional[str] = None):
        """Återställer en komponent till baseline i specificerat scenario."""
        if scenario_name is None:
            scenario_name = self.current_scenario
        
        if scenario_name and scenario_name in self.scenarios:
            scenario = self.scenarios[scenario_name]
            if component in scenario['modifications']:
                del scenario['modifications'][component]
            scenario['component_sources'][component] = 'baseline'
    
    
    def reset_all_components(self, scenario_name: Optional[str] = None):
        """Återställer alla komponenter till baseline."""
        if scenario_name is None:
            scenario_name = self.current_scenario
        
        if scenario_name and scenario_name in self.scenarios:
            scenario = self.scenarios[scenario_name]
            scenario['modifications'] = {}
            scenario['component_sources'] = {comp: 'baseline' for comp in self.components.keys()}


def create_waterfall_data(
    entity_data: pd.Series, 
    components: List[Tuple[str, str]]
) -> Dict:
    """
    Förbereder data för waterfall-chart visualization.
    
    Args:
        entity_data: Data för ett specifikt företag
        components: Lista med (display_name, column_name) tupler
        
    Returns:
        Dict med data formaterad för Plotly waterfall
    """
    waterfall_data = {
        'labels': [],
        'values': [],
        'measures': [],
        'text': []
    }
    
    running_total = 0
    
    for display_name, col_name in components:
        value = entity_data.get(col_name, 0)
        waterfall_data['labels'].append(display_name)
        waterfall_data['values'].append(value)
        waterfall_data['measures'].append('relative')
        waterfall_data['text'].append(f"{value:,.0f}")
        running_total += value
    
    # Lägg till total
    waterfall_data['labels'].append('Total Intäktsram')
    waterfall_data['values'].append(0)  # Plotly beräknar total automatiskt
    waterfall_data['measures'].append('total')
    waterfall_data['text'].append(f"{running_total:,.0f}")
    
    return waterfall_data