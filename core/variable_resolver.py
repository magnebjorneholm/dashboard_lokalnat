"""
Variable Resolver - Huvudkomponent för variabel-resolution

Hanterar:
- Val av producer för variabler
- Dependency resolution
- Caching av resultat
- Producer execution
"""

from typing import Any, Dict, Optional
from core.producer_registry import ProducerRegistry
from core.validation_framework import validate_producer_result


class VariableResolver:
    """
    Resolves variables by selecting appropriate producer and managing dependencies.
    
    Denna klass är hjärtat i systemet och hanterar hela flödet från
    case definition till färdiga värden.
    """
    
    def __init__(
        self,
        producer_registry: ProducerRegistry,
        case_definition: Dict[str, Any],
        baseline_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialisera Variable Resolver.
        
        Args:
            producer_registry: Registry med alla producers
            case_definition: Case definition med användarval
            baseline_data: Baseline data (för baseline producers)
        """
        self.registry = producer_registry
        self.case_def = case_definition
        self.baseline = baseline_data or {}
        self.cache: Dict[str, Any] = {}
        self._resolution_stack: list = []  # För att hitta cirkulära dependencies
    
    def get_variable(self, variable_name: str) -> Any:
        """
        Hämta värde för en variabel.
        
        Flow:
        1. Check cache
        2. Determine producer
        3. Resolve dependencies (rekursivt)
        4. Run producer
        5. Validate result
        6. Cache result
        7. Return
        
        Args:
            variable_name: Namnet på variabeln att hämta
            
        Returns:
            Värdet för variabeln
            
        Raises:
            KeyError: Om variabel inte finns i registry
            RecursionError: Om cirkulär dependency upptäcks
            ValidationError: Om producer-resultat är invalid
        """
        # Check cache
        if variable_name in self.cache:
            return self.cache[variable_name]
        
        # Check for circular dependencies
        if variable_name in self._resolution_stack:
            cycle = ' -> '.join(self._resolution_stack + [variable_name])
            raise RecursionError(
                f"Circular dependency detected: {cycle}"
            )
        
        # Add to resolution stack
        self._resolution_stack.append(variable_name)
        
        try:
            # Determine producer
            producer_id = self._determine_producer(variable_name)
            producer_spec = self.registry.get_producer_spec(variable_name, producer_id)
            
            # Resolve dependencies
            deps = self._resolve_dependencies(producer_spec)
            
            # Run producer
            result = self._run_producer(variable_name, producer_spec, deps)
            
            # Validate result
            self._validate_result(variable_name, result)
            
            # Cache result
            self.cache[variable_name] = result
            
            return result
        
        finally:
            # Remove from resolution stack
            self._resolution_stack.pop()
    
    def _determine_producer(self, variable_name: str) -> str:
        """
        Bestäm vilken producer som ska användas för en variabel.
        
        Logik:
        1. Kolla case_definition['modules'][variable_name]
        2. Om inte specificerad, använd default producer
        3. Om ingen default, använd första tillgängliga producer
        
        Args:
            variable_name: Namnet på variabeln
            
        Returns:
            Producer ID att använda
            
        Raises:
            ValueError: Om ingen producer kan bestämmas
        """
        # Check case definition
        if 'modules' in self.case_def:
            modules = self.case_def['modules']
            if variable_name in modules:
                return modules[variable_name]
        
        # Use default producer
        default = self.registry.get_default_producer(variable_name)
        if default:
            return default
        
        # Use first available producer
        producers = self.registry.list_producers(variable_name)
        if producers:
            return producers[0]
        
        raise ValueError(
            f"No producer found for variable '{variable_name}'"
        )
    
    def _resolve_dependencies(self, producer_spec) -> Dict[str, Any]:
        """
        Rekursivt hämta alla dependencies för en producer.
        
        Args:
            producer_spec: ProducerSpec med requires-lista
            
        Returns:
            Dict med dependency_name -> dependency_value
        """
        deps = {}
        
        for dep_name in producer_spec.requires:
            # Rekursiv call till get_variable
            deps[dep_name] = self.get_variable(dep_name)
        
        return deps
    
    def _run_producer(
        self,
        variable_name: str,
        producer_spec,
        deps: Dict[str, Any]
    ) -> Any:
        """
        Kör producer method med dependencies.
        
        Args:
            variable_name: Namnet på variabeln
            producer_spec: ProducerSpec med method
            deps: Dict med resolved dependencies
            
        Returns:
            Värde från producer
            
        Raises:
            RuntimeError: Om producer method är None och baseline saknas
        """
        method = producer_spec.method
        
        # Check baseline data first (för baseline producers utan requires)
        if not producer_spec.requires and variable_name in self.baseline:
            return self.baseline[variable_name]
        
        # If no method and no baseline, raise error
        if method is None:
            raise RuntimeError(
                f"Producer method not set for '{variable_name}' "
                f"(producer: {producer_spec.provides})"
            )
        
        # Get module config if needed
        config = self._get_module_config(variable_name)
        if config is not None:
            deps['config'] = config
        
        # Run producer method
        try:
            result = method(**deps)
            return result
        except Exception as e:
            raise RuntimeError(
                f"Error running producer for '{variable_name}': {str(e)}"
            ) from e
    
    def _get_module_config(self, variable_name: str) -> Optional[Dict]:
        """
        Hämta module config från case definition.
        
        Args:
            variable_name: Namnet på variabeln
            
        Returns:
            Config dict eller None
        """
        if 'module_configs' not in self.case_def:
            return None
        
        configs = self.case_def['module_configs']
        return configs.get(variable_name)
    
    def _validate_result(self, variable_name: str, result: Any):
        """
        Validera att producer-resultat följer kontrakt.
        
        Args:
            variable_name: Namnet på variabeln
            result: Värdet från producer
            
        Raises:
            ValidationError: Om resultat är invalid
        """
        validate_producer_result(result, variable_name, self.registry)
    
    def clear_cache(self, variable_name: Optional[str] = None):
        """
        Rensa cache.
        
        Args:
            variable_name: Om angiven, rensa bara denna variabel.
                          Om None, rensa hela cachen.
        """
        if variable_name:
            self.cache.pop(variable_name, None)
        else:
            self.cache.clear()
    
    def invalidate_downstream(self, variable_name: str):
        """
        Invalidera cache för alla downstream variabler.
        
        När en variabel ändras måste alla variabler som beror på den
        räknas om.
        
        Args:
            variable_name: Namnet på variabeln som ändrats
        """
        # Rensa denna variabel först
        self.clear_cache(variable_name)
        
        # Hitta alla variabler som beror på denna
        try:
            var_spec = self.registry.get_variable_spec(variable_name)
            
            # Rensa alla consumers rekursivt
            if var_spec.consumers:
                for consumer in var_spec.consumers:
                    self.invalidate_downstream(consumer)
        except KeyError:
            # Variable not in registry, just clear cache
            pass
    
    def get_cache_state(self) -> Dict[str, Any]:
        """
        Hämta current cache state för debugging.
        
        Returns:
            Dict med cached values
        """
        return self.cache.copy()
    
    def update_case_definition(self, new_case_def: Dict[str, Any]):
        """
        Uppdatera case definition och invalidera cache.
        
        Args:
            new_case_def: Ny case definition
        """
        self.case_def = new_case_def
        self.clear_cache()
    
    def get_execution_plan(self, variable_name: str) -> list:
        """
        Hämta execution plan för en variabel (vilka steg som behövs).
        
        Args:
            variable_name: Namnet på variabeln
            
        Returns:
            Lista med (variable_name, producer_id) tuples i execution order
        """
        plan = []
        visited = set()
        
        def _build_plan(var_name: str):
            if var_name in visited:
                return
            
            visited.add(var_name)
            
            # Determine producer for this variable
            producer_id = self._determine_producer(var_name)
            producer_spec = self.registry.get_producer_spec(var_name, producer_id)
            
            # First resolve dependencies
            for dep in producer_spec.requires:
                _build_plan(dep)
            
            # Then add this variable
            plan.append((var_name, producer_id))
        
        _build_plan(variable_name)
        return plan
    
    def execute_plan(self, variable_name: str) -> Any:
        """
        Exekvera en variabel genom att följa execution plan.
        
        Samma som get_variable men returnerar även execution plan.
        
        Args:
            variable_name: Namnet på variabeln
            
        Returns:
            (result, execution_plan)
        """
        plan = self.get_execution_plan(variable_name)
        result = self.get_variable(variable_name)
        return result, plan