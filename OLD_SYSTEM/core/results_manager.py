"""
Results Manager - Hantera resultat från beräkningar

Ansvarar för:
- Lagra resultat från beräkningar
- Jämföra resultat mellan scenarios
- Metadata tracking (timestamp, case_name, etc.)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class ResultMetadata:
    """Metadata för ett resultat"""
    case_name: str
    variable_name: str
    producer_id: str
    timestamp: str
    execution_time_ms: Optional[float] = None


@dataclass
class Result:
    """Ett resultat med metadata"""
    value: Any
    metadata: ResultMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertera till dict"""
        return {
            'value': self.value,
            'metadata': asdict(self.metadata)
        }


class ResultsManager:
    """
    Manager för att lagra och jämföra resultat.
    
    Lagrar resultat per case med metadata för tracking.
    """
    
    def __init__(self):
        """Initialisera results manager"""
        # Storage: {case_name: {variable_name: Result}}
        self._results: Dict[str, Dict[str, Result]] = {}
    
    def store_result(
        self,
        case_name: str,
        variable_name: str,
        value: Any,
        producer_id: str,
        execution_time_ms: Optional[float] = None
    ) -> None:
        """
        Lagra ett resultat.
        
        Args:
            case_name: Namnet på caset
            variable_name: Namnet på variabeln
            value: Värdet
            producer_id: ID för producer som producerade värdet
            execution_time_ms: Execution time i millisekunder
        """
        # Create metadata
        metadata = ResultMetadata(
            case_name=case_name,
            variable_name=variable_name,
            producer_id=producer_id,
            timestamp=datetime.now().isoformat(),
            execution_time_ms=execution_time_ms
        )
        
        # Create result
        result = Result(value=value, metadata=metadata)
        
        # Store
        if case_name not in self._results:
            self._results[case_name] = {}
        
        self._results[case_name][variable_name] = result
    
    def get_result(
        self,
        case_name: str,
        variable_name: str
    ) -> Optional[Result]:
        """
        Hämta ett lagrat resultat.
        
        Args:
            case_name: Namnet på caset
            variable_name: Namnet på variabeln
            
        Returns:
            Result eller None om inte finns
        """
        if case_name not in self._results:
            return None
        
        return self._results[case_name].get(variable_name)
    
    def get_value(
        self,
        case_name: str,
        variable_name: str
    ) -> Optional[Any]:
        """
        Hämta endast värdet (utan metadata).
        
        Args:
            case_name: Namnet på caset
            variable_name: Namnet på variabeln
            
        Returns:
            Värdet eller None om inte finns
        """
        result = self.get_result(case_name, variable_name)
        return result.value if result else None
    
    def get_all_results(self, case_name: str) -> Dict[str, Result]:
        """
        Hämta alla resultat för ett case.
        
        Args:
            case_name: Namnet på caset
            
        Returns:
            Dict med variable_name -> Result
        """
        return self._results.get(case_name, {}).copy()
    
    def get_all_values(self, case_name: str) -> Dict[str, Any]:
        """
        Hämta alla värden för ett case (utan metadata).
        
        Args:
            case_name: Namnet på caset
            
        Returns:
            Dict med variable_name -> value
        """
        results = self.get_all_results(case_name)
        return {
            var_name: result.value
            for var_name, result in results.items()
        }
    
    def list_cases(self) -> List[str]:
        """
        Lista alla case names som har resultat.
        
        Returns:
            Lista med case names
        """
        return list(self._results.keys())
    
    def case_exists(self, case_name: str) -> bool:
        """
        Kolla om ett case har resultat.
        
        Args:
            case_name: Namnet på caset
            
        Returns:
            True om caset finns
        """
        return case_name in self._results
    
    def delete_case(self, case_name: str) -> bool:
        """
        Radera alla resultat för ett case.
        
        Args:
            case_name: Namnet på caset
            
        Returns:
            True om caset fanns och raderades
        """
        if case_name in self._results:
            del self._results[case_name]
            return True
        return False
    
    def delete_result(
        self,
        case_name: str,
        variable_name: str
    ) -> bool:
        """
        Radera ett specifikt resultat.
        
        Args:
            case_name: Namnet på caset
            variable_name: Namnet på variabeln
            
        Returns:
            True om resultatet fanns och raderades
        """
        if case_name in self._results:
            if variable_name in self._results[case_name]:
                del self._results[case_name][variable_name]
                return True
        return False
    
    def clear_all(self) -> None:
        """Radera alla resultat"""
        self._results.clear()
    
    def compare_results(
        self,
        case1_name: str,
        case2_name: str,
        variables: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Jämför resultat mellan två cases.
        
        Args:
            case1_name: Namnet på första caset
            case2_name: Namnet på andra caset
            variables: Lista med variabler att jämföra (None = alla)
            
        Returns:
            Dict med comparisons: {
                variable_name: {
                    'case1': value1,
                    'case2': value2,
                    'difference': value2 - value1,
                    'percent_change': percent
                }
            }
        """
        case1_results = self.get_all_values(case1_name)
        case2_results = self.get_all_values(case2_name)
        
        # Determine which variables to compare
        if variables is None:
            variables = list(set(case1_results.keys()) | set(case2_results.keys()))
        
        comparison = {}
        
        for var_name in variables:
            val1 = case1_results.get(var_name)
            val2 = case2_results.get(var_name)
            
            comp = {
                'case1': val1,
                'case2': val2
            }
            
            # Calculate difference for numeric values
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                comp['difference'] = val2 - val1
                
                # Calculate percent change (avoid division by zero)
                if val1 != 0:
                    comp['percent_change'] = ((val2 - val1) / abs(val1)) * 100
                else:
                    comp['percent_change'] = None
            
            comparison[var_name] = comp
        
        return comparison
    
    def get_execution_summary(self, case_name: str) -> Dict[str, Any]:
        """
        Hämta execution summary för ett case.
        
        Args:
            case_name: Namnet på caset
            
        Returns:
            Summary med timing och metadata
        """
        results = self.get_all_results(case_name)
        
        if not results:
            return {
                'total_variables': 0,
                'total_execution_time_ms': 0,
                'variables': []
            }
        
        total_time = 0
        variables = []
        
        for var_name, result in results.items():
            exec_time = result.metadata.execution_time_ms or 0
            total_time += exec_time
            
            variables.append({
                'name': var_name,
                'producer': result.metadata.producer_id,
                'timestamp': result.metadata.timestamp,
                'execution_time_ms': exec_time
            })
        
        return {
            'total_variables': len(results),
            'total_execution_time_ms': total_time,
            'variables': variables
        }
    
    def export_results(
        self,
        case_name: str,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Exportera resultat för ett case.
        
        Args:
            case_name: Namnet på caset
            include_metadata: Om metadata ska inkluderas
            
        Returns:
            Dict med exporterade resultat
        """
        results = self.get_all_results(case_name)
        
        if include_metadata:
            return {
                var_name: result.to_dict()
                for var_name, result in results.items()
            }
        else:
            return {
                var_name: result.value
                for var_name, result in results.items()
            }
    
    def to_json(
        self,
        case_name: str,
        include_metadata: bool = True
    ) -> str:
        """
        Serialisera resultat till JSON.
        
        Args:
            case_name: Namnet på caset
            include_metadata: Om metadata ska inkluderas
            
        Returns:
            JSON string
        """
        data = self.export_results(case_name, include_metadata)
        return json.dumps(data, indent=2, default=str)