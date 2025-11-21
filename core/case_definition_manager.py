"""
Case Definition Manager - Hantera case definitions

Ansvarar för:
- Skapa nya cases
- Uppdatera parameters och modules
- Validera case definitions
- Serialisera/deserialisera till/från JSON
"""

from typing import Dict, Any, Optional
import json
from datetime import datetime
from core.producer_registry import ProducerRegistry
from core.validation_framework import validate_case_definition


class CaseDefinitionManager:
    """
    Manager för case definitions.
    
    Case definition är central datastruktur som definierar:
    - Vilka producers som ska användas för varje variabel
    - Värden för parameters
    - Konfiguration för modules
    """
    
    def __init__(self, registry: ProducerRegistry):
        """
        Initialisera manager.
        
        Args:
            registry: ProducerRegistry för validation
        """
        self.registry = registry
    
    def create_case(
        self,
        name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Skapa ny case definition med defaults.
        
        Args:
            name: Namnet på caset
            description: Beskrivning av caset
            
        Returns:
            Ny case definition
        """
        return {
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'parameters': {},
            'modules': {},
            'module_configs': {}
        }
    
    def update_parameter(
        self,
        case_def: Dict[str, Any],
        param_name: str,
        value: Any
    ) -> Dict[str, Any]:
        """
        Uppdatera parameter i case definition.
        
        Args:
            case_def: Case definition att uppdatera
            param_name: Namnet på parametern
            value: Nytt värde
            
        Returns:
            Uppdaterad case definition (ny dict)
        """
        case_def = case_def.copy()
        case_def['parameters'] = case_def.get('parameters', {}).copy()
        case_def['parameters'][param_name] = value
        case_def['updated_at'] = datetime.now().isoformat()
        return case_def
    
    def set_module(
        self,
        case_def: Dict[str, Any],
        variable_name: str,
        producer_id: str
    ) -> Dict[str, Any]:
        """
        Välj vilken producer som ska användas för en variabel.
        
        Args:
            case_def: Case definition att uppdatera
            variable_name: Namnet på variabeln
            producer_id: ID för producern att använda
            
        Returns:
            Uppdaterad case definition (ny dict)
            
        Raises:
            ValueError: Om variable/producer inte finns i registry
        """
        # Validera att variable och producer finns
        if variable_name not in self.registry.list_variables():
            raise ValueError(f"Unknown variable: {variable_name}")
        
        if producer_id not in self.registry.list_producers(variable_name):
            raise ValueError(
                f"Unknown producer '{producer_id}' for variable '{variable_name}'"
            )
        
        # Uppdatera case definition
        case_def = case_def.copy()
        case_def['modules'] = case_def.get('modules', {}).copy()
        case_def['modules'][variable_name] = producer_id
        case_def['updated_at'] = datetime.now().isoformat()
        return case_def
    
    def set_module_config(
        self,
        case_def: Dict[str, Any],
        variable_name: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sätt konfiguration för ett module.
        
        Args:
            case_def: Case definition att uppdatera
            variable_name: Namnet på variabeln
            config: Konfiguration för modulet
            
        Returns:
            Uppdaterad case definition (ny dict)
        """
        case_def = case_def.copy()
        case_def['module_configs'] = case_def.get('module_configs', {}).copy()
        case_def['module_configs'][variable_name] = config
        case_def['updated_at'] = datetime.now().isoformat()
        return case_def
    
    def remove_module(
        self,
        case_def: Dict[str, Any],
        variable_name: str
    ) -> Dict[str, Any]:
        """
        Ta bort module selection (kommer använda default).
        
        Args:
            case_def: Case definition att uppdatera
            variable_name: Namnet på variabeln
            
        Returns:
            Uppdaterad case definition (ny dict)
        """
        case_def = case_def.copy()
        case_def['modules'] = case_def.get('modules', {}).copy()
        case_def['module_configs'] = case_def.get('module_configs', {}).copy()
        
        # Remove module selection
        case_def['modules'].pop(variable_name, None)
        
        # Remove config
        case_def['module_configs'].pop(variable_name, None)
        
        case_def['updated_at'] = datetime.now().isoformat()
        return case_def
    
    def validate(self, case_def: Dict[str, Any]) -> None:
        """
        Validera att case definition är korrekt.
        
        Args:
            case_def: Case definition att validera
            
        Raises:
            ValidationError: Om case definition är invalid
        """
        validate_case_definition(case_def, self.registry)
    
    def to_json(self, case_def: Dict[str, Any]) -> str:
        """
        Serialisera case definition till JSON.
        
        Args:
            case_def: Case definition att serialisera
            
        Returns:
            JSON string
        """
        return json.dumps(case_def, indent=2)
    
    def from_json(self, json_str: str) -> Dict[str, Any]:
        """
        Deserialisera case definition från JSON.
        
        Args:
            json_str: JSON string
            
        Returns:
            Case definition
            
        Raises:
            json.JSONDecodeError: Om JSON är invalid
            ValidationError: Om case definition är invalid
        """
        case_def = json.loads(json_str)
        
        # Validera
        self.validate(case_def)
        
        return case_def
    
    def clone_case(
        self,
        case_def: Dict[str, Any],
        new_name: str
    ) -> Dict[str, Any]:
        """
        Skapa en kopia av ett case.
        
        Args:
            case_def: Case definition att kopiera
            new_name: Namn för nya caset
            
        Returns:
            Ny case definition
        """
        new_case = case_def.copy()
        new_case['name'] = new_name
        new_case['created_at'] = datetime.now().isoformat()
        new_case['updated_at'] = datetime.now().isoformat()
        
        # Deep copy nested dicts
        new_case['parameters'] = case_def.get('parameters', {}).copy()
        new_case['modules'] = case_def.get('modules', {}).copy()
        new_case['module_configs'] = case_def.get('module_configs', {}).copy()
        
        return new_case
    
    def get_active_producers(self, case_def: Dict[str, Any]) -> Dict[str, str]:
        """
        Hämta alla aktiva producers för ett case.
        
        Returns dict med variable_name -> producer_id för alla variabler
        som antingen är explicit satta eller har default producers.
        
        Args:
            case_def: Case definition
            
        Returns:
            Dict med variable_name -> producer_id
        """
        active = {}
        
        # Get all explicitly set modules
        if 'modules' in case_def:
            active.update(case_def['modules'])
        
        # Add default producers for unset variables
        for var_name in self.registry.list_variables():
            if var_name not in active:
                default = self.registry.get_default_producer(var_name)
                if default:
                    active[var_name] = default
        
        return active
    
    def compare_cases(
        self,
        case_def1: Dict[str, Any],
        case_def2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Jämför två cases och hitta skillnader.
        
        Args:
            case_def1: Första caset
            case_def2: Andra caset
            
        Returns:
            Dict med differences
        """
        differences = {
            'parameters': {},
            'modules': {},
            'module_configs': {}
        }
        
        # Compare parameters
        params1 = case_def1.get('parameters', {})
        params2 = case_def2.get('parameters', {})
        
        all_param_keys = set(params1.keys()) | set(params2.keys())
        for key in all_param_keys:
            val1 = params1.get(key)
            val2 = params2.get(key)
            if val1 != val2:
                differences['parameters'][key] = {
                    'case1': val1,
                    'case2': val2
                }
        
        # Compare modules
        modules1 = case_def1.get('modules', {})
        modules2 = case_def2.get('modules', {})
        
        all_module_keys = set(modules1.keys()) | set(modules2.keys())
        for key in all_module_keys:
            val1 = modules1.get(key)
            val2 = modules2.get(key)
            if val1 != val2:
                differences['modules'][key] = {
                    'case1': val1,
                    'case2': val2
                }
        
        # Compare module configs
        configs1 = case_def1.get('module_configs', {})
        configs2 = case_def2.get('module_configs', {})
        
        all_config_keys = set(configs1.keys()) | set(configs2.keys())
        for key in all_config_keys:
            val1 = configs1.get(key)
            val2 = configs2.get(key)
            if val1 != val2:
                differences['module_configs'][key] = {
                    'case1': val1,
                    'case2': val2
                }
        
        return differences