"""
Producer Registry - Central registry för alla variable producers

Registry håller reda på:
- Alla variabler som kan produceras
- Vilka producers som finns för varje variabel
- Dependencies mellan variabler
- Validation specs för varje variabel
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class ProducerSpec:
    """Specification för en producer"""
    method: Callable
    requires: List[str]
    provides: str
    description: str
    optional: Optional[List[str]] = None
    ui_component: Optional[str] = None
    module: Optional[str] = None
    default: bool = False


@dataclass
class VariableSpec:
    """Specification för en variabel"""
    dtype: type
    description: str
    unit: Optional[str] = None
    range: Optional[tuple] = None
    producers: Optional[Dict[str, ProducerSpec]] = None
    consumers: Optional[List[str]] = None


class ProducerRegistry:
    """
    Central registry för alla producers.
    
    Registry håller reda på vilka producers som finns för varje variabel,
    deras dependencies, och validation specs.
    """
    
    def __init__(self):
        self._registry: Dict[str, VariableSpec] = {}
    
    def register_variable(
        self, 
        variable_name: str, 
        dtype: type,
        description: str,
        unit: Optional[str] = None,
        range: Optional[tuple] = None,
        producers: Optional[Dict[str, dict]] = None,
        consumers: Optional[List[str]] = None
    ):
        """
        Registrera en variabel med dess producers.
        
        Args:
            variable_name: Namnet på variabeln
            dtype: Datatyp för variabeln
            description: Beskrivning av variabeln
            unit: Enhet (t.ex. 'TSEK', 'decimal')
            range: Tillåtet värdeintervall (min, max)
            producers: Dict med producer_id -> producer spec
            consumers: Lista med variabler som använder denna variabel
        """
        # Konvertera producer dicts till ProducerSpec objekt
        producer_specs = {}
        if producers:
            for producer_id, spec in producers.items():
                producer_specs[producer_id] = ProducerSpec(
                    method=spec.get('method'),
                    requires=spec.get('requires', []),
                    provides=variable_name,
                    description=spec.get('description', ''),
                    optional=spec.get('optional', []),
                    ui_component=spec.get('ui_component'),
                    module=spec.get('module'),
                    default=spec.get('default', False)
                )
        
        # Skapa VariableSpec
        var_spec = VariableSpec(
            dtype=dtype,
            description=description,
            unit=unit,
            range=range,
            producers=producer_specs,
            consumers=consumers or []
        )
        
        self._registry[variable_name] = var_spec
    
    def get_variable_spec(self, variable_name: str) -> VariableSpec:
        """
        Hämta complete spec för en variabel.
        
        Args:
            variable_name: Namnet på variabeln
            
        Returns:
            VariableSpec för variabeln
            
        Raises:
            KeyError: Om variabeln inte finns i registry
        """
        if variable_name not in self._registry:
            raise KeyError(f"Variable '{variable_name}' not found in registry")
        return self._registry[variable_name]
    
    def get_producer_spec(self, variable_name: str, producer_id: str) -> ProducerSpec:
        """
        Hämta spec för en specifik producer.
        
        Args:
            variable_name: Namnet på variabeln
            producer_id: ID för producern
            
        Returns:
            ProducerSpec för producern
            
        Raises:
            KeyError: Om variabel eller producer inte finns
        """
        var_spec = self.get_variable_spec(variable_name)
        
        if not var_spec.producers or producer_id not in var_spec.producers:
            raise KeyError(
                f"Producer '{producer_id}' not found for variable '{variable_name}'"
            )
        
        return var_spec.producers[producer_id]
    
    def list_variables(self) -> List[str]:
        """
        Lista alla registrerade variabler.
        
        Returns:
            Lista med variabelnamn
        """
        return list(self._registry.keys())
    
    def list_producers(self, variable_name: str) -> List[str]:
        """
        Lista alla producers för en variabel.
        
        Args:
            variable_name: Namnet på variabeln
            
        Returns:
            Lista med producer IDs
            
        Raises:
            KeyError: Om variabeln inte finns
        """
        var_spec = self.get_variable_spec(variable_name)
        
        if not var_spec.producers:
            return []
        
        return list(var_spec.producers.keys())
    
    def get_default_producer(self, variable_name: str) -> Optional[str]:
        """
        Hämta default producer för en variabel.
        
        Args:
            variable_name: Namnet på variabeln
            
        Returns:
            Producer ID för default producer, eller None
        """
        var_spec = self.get_variable_spec(variable_name)
        
        if not var_spec.producers:
            return None
        
        for producer_id, producer_spec in var_spec.producers.items():
            if producer_spec.default:
                return producer_id
        
        return None
    
    def validate_registry(self) -> List[str]:
        """
        Validera att registry är komplett och konsistent.
        
        Kontrollerar:
        - Att alla dependencies finns som variabler
        - Att alla variabler har minst en producer
        - Att consumers är korrekta
        
        Returns:
            Lista med valideringsfel (tom lista = OK)
        """
        errors = []
        
        # Kontrollera varje variabel
        for var_name, var_spec in self._registry.items():
            
            # Kontrollera att variabeln har producers
            if not var_spec.producers or len(var_spec.producers) == 0:
                errors.append(f"Variable '{var_name}' has no producers")
                continue
            
            # Kontrollera varje producer
            for producer_id, producer_spec in var_spec.producers.items():
                
                # Kontrollera att method är satt (kan vara None för placeholder)
                if producer_spec.method is None:
                    errors.append(
                        f"Producer '{producer_id}' for '{var_name}' has no method"
                    )
                
                # Kontrollera att alla dependencies finns
                for dep in producer_spec.requires:
                    if dep not in self._registry:
                        errors.append(
                            f"Producer '{producer_id}' for '{var_name}' "
                            f"requires unknown variable '{dep}'"
                        )
        
        return errors
    
    def get_dependency_chain(self, variable_name: str, producer_id: str) -> List[str]:
        """
        Hämta full dependency chain för en variabel.
        
        Args:
            variable_name: Namnet på variabeln
            producer_id: ID för producern
            
        Returns:
            Lista med alla variabler som behövs (i dependency order)
        """
        chain = []
        visited = set()
        
        def _collect_deps(var_name: str, prod_id: str):
            if var_name in visited:
                return
            
            visited.add(var_name)
            
            try:
                producer_spec = self.get_producer_spec(var_name, prod_id)
                
                # Rekursivt samla dependencies
                for dep in producer_spec.requires:
                    # Använd default producer för dependencies
                    default_prod = self.get_default_producer(dep)
                    if default_prod:
                        _collect_deps(dep, default_prod)
                
                chain.append(var_name)
            
            except KeyError:
                pass
        
        _collect_deps(variable_name, producer_id)
        return chain


def build_default_registry() -> ProducerRegistry:
    """
    Bygg registry med alla standard-producers för första implementation.
    
    Innehåller:
    - WACC (baseline, capm)
    - CAPEX (baseline, wacc_scaling, kent_full, kent_upload)
    - OPEX (baseline)
    - Volumes (baseline)
    - Efficiency (baseline, dea)
    - Effektiviseringskrav (calculation)
    - Intäktsram (assembly)
    
    Returns:
        ProducerRegistry med alla producers registrerade
    """
    registry = ProducerRegistry()
    
    # ========================================
    # WACC
    # ========================================
    registry.register_variable(
        variable_name='wacc',
        dtype=float,
        description='Weighted Average Cost of Capital',
        unit='decimal',
        range=(0.01, 0.15),
        producers={
            'baseline': {
                'method': None,  # Sätts senare när producer-funktioner finns
                'requires': [],
                'description': "Ei's baseline WACC (4.53%)",
                'default': True
            },
            'capm': {
                'method': None,
                'requires': ['wacc_components'],
                'description': 'Beräknad från CAPM-komponenter',
                'ui_component': 'render_wacc_ui',
                'default': False
            }
        },
        consumers=['capex']
    )
    
    # WACC Components (för CAPM-beräkning)
    registry.register_variable(
        variable_name='wacc_components',
        dtype=dict,
        description='CAPM komponenter för WACC-beräkning',
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': "Ei's standardvärden",
                'default': True
            },
            'user_input': {
                'method': None,
                'requires': [],
                'description': 'Användarangivna värden',
                'ui_component': 'render_wacc_components_ui',
                'default': False
            }
        },
        consumers=['wacc']
    )
    
    # ========================================
    # CAPEX
    # ========================================
    registry.register_variable(
        variable_name='capex',
        dtype=float,
        description='Årlig kapitalkostnad',
        unit='TSEK',
        range=(0, None),
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': 'Från Data_modeller.xlsx',
                'default': True
            },
            'wacc_scaling': {
                'method': None,
                'requires': ['wacc', 'capex_baseline'],
                'description': 'Snabb skalning vid WACC-ändring',
                'default': False
            },
            'kent_full': {
                'method': None,
                'requires': ['wacc', 'kent_parameters'],
                'description': 'Full KENT-pipeline med justeringar',
                'ui_component': 'render_kent_full_ui',
                'default': False
            },
            'kent_upload': {
                'method': None,
                'requires': ['kent_file'],
                'description': 'Från uppladdad KENT-fil',
                'ui_component': 'render_kent_upload_ui',
                'default': False
            }
        },
        consumers=['efficiency', 'intaktsram']
    )
    
    # ========================================
    # OPEX
    # ========================================
    registry.register_variable(
        variable_name='opex_paverkbara',
        dtype=float,
        description='Påverkbara driftskostnader',
        unit='TSEK',
        range=(0, None),
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': 'Från Data_modeller.xlsx',
                'default': True
            }
        },
        consumers=['efficiency', 'intaktsram']
    )
    
    registry.register_variable(
        variable_name='opex_opaverkbara',
        dtype=float,
        description='Opåverkbara driftskostnader',
        unit='TSEK',
        range=(0, None),
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': 'Från Data_modeller.xlsx',
                'default': True
            }
        },
        consumers=['intaktsram']
    )
    
    # ========================================
    # Volumes
    # ========================================
    registry.register_variable(
        variable_name='volumes',
        dtype=dict,
        description='Volymer (CU, MW, NS, MWhl, MWhh)',
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': 'Från Data_modeller.xlsx',
                'default': True
            }
        },
        consumers=['efficiency']
    )
    
    # ========================================
    # Efficiency
    # ========================================
    registry.register_variable(
        variable_name='efficiency',
        dtype=float,
        description='Technical efficiency score',
        range=(0, 1),
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': "Ei's reference DEA från 2024",
                'default': True
            },
            'dea': {
                'method': None,
                'requires': ['capex', 'opex_paverkbara', 'volumes', 'dea_config'],
                'description': 'User-konfigurerad DEA-analys',
                'ui_component': 'render_dea_config_ui',
                'module': 'DEA',
                'default': False
            }
        },
        consumers=['effektiviseringskrav']
    )
    
    # DEA Configuration
    registry.register_variable(
        variable_name='dea_config',
        dtype=dict,
        description='Konfiguration för DEA-analys',
        producers={
            'user_input': {
                'method': None,
                'requires': [],
                'description': 'Användarval för DEA',
                'ui_component': 'render_dea_config_ui',
                'default': True
            }
        },
        consumers=['efficiency']
    )
    
    # ========================================
    # Effektiviseringskrav
    # ========================================
    registry.register_variable(
        variable_name='effektiviseringskrav',
        dtype=float,
        description='Effektiviseringskrav',
        unit='TSEK',
        producers={
            'calculation': {
                'method': None,
                'requires': ['efficiency', 'opex_paverkbara', 'trunkering_params'],
                'description': 'Beräknat från efficiency score',
                'default': True
            }
        },
        consumers=['intaktsram']
    )
    
    # Trunkering parameters
    registry.register_variable(
        variable_name='trunkering_params',
        dtype=dict,
        description='Parametrar för trunkering',
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': "Ei's standardvärden",
                'default': True
            },
            'user_input': {
                'method': None,
                'requires': [],
                'description': 'Användarangivna värden',
                'default': False
            }
        },
        consumers=['effektiviseringskrav']
    )
    
    # ========================================
    # Intäktsram
    # ========================================
    registry.register_variable(
        variable_name='intaktsram',
        dtype=dict,
        description='Total intäktsram med breakdown',
        unit='TSEK',
        producers={
            'assembly': {
                'method': None,
                'requires': [
                    'capex',
                    'opex_opaverkbara',
                    'opex_paverkbara',
                    'effektiviseringskrav'
                ],
                'description': 'Sammansättning av komponenter',
                'default': True
            }
        },
        consumers=[]
    )
    
    # ========================================
    # Hjälpvariabler
    # ========================================
    
    # Baseline CAPEX (för wacc_scaling)
    registry.register_variable(
        variable_name='capex_baseline',
        dtype=float,
        description='Baseline CAPEX från Data_modeller.xlsx',
        unit='TSEK',
        producers={
            'baseline': {
                'method': None,
                'requires': [],
                'description': 'Från Data_modeller.xlsx',
                'default': True
            }
        },
        consumers=['capex']
    )
    
    # KENT parameters (för kent_full)
    registry.register_variable(
        variable_name='kent_parameters',
        dtype=dict,
        description='Justerade parametrar för KENT-pipeline',
        producers={
            'user_input': {
                'method': None,
                'requires': [],
                'description': 'Användarangivna justeringar',
                'ui_component': 'render_kent_parameters_ui',
                'default': True
            }
        },
        consumers=['capex']
    )
    
    # KENT file (för kent_upload)
    registry.register_variable(
        variable_name='kent_file',
        dtype=bytes,
        description='Uppladdad KENT-fil',
        producers={
            'user_upload': {
                'method': None,
                'requires': [],
                'description': 'Uppladdad Excel-fil',
                'ui_component': 'render_kent_upload_ui',
                'default': True
            }
        },
        consumers=['capex']
    )
    
    return registry