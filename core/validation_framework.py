"""
Validation Framework - Validering av data mellan steg

Innehåller funktioner för att validera:
- Enkla värden mot specs
- DataFrames mot specs
- Case definitions
"""

from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np


class ValidationError(Exception):
    """Custom exception för validation errors"""
    pass


def validate(value: Any, spec: Dict[str, Any]) -> None:
    """
    Validera ett värde mot en specification.
    
    Args:
        value: Värdet att validera
        spec: Dict med validation rules:
            - dtype: Expected datatype
            - range: (min, max) för numeriska värden
            - constraints: Dict med extra constraints
            
    Raises:
        ValidationError: Om validering misslyckas
    """
    # Type check
    if 'dtype' in spec:
        expected_type = spec['dtype']
        
        # Hantera special cases
        if expected_type == float and isinstance(value, (int, float, np.number)):
            pass  # Allow int for float
        elif expected_type == dict and isinstance(value, dict):
            pass
        elif not isinstance(value, expected_type):
            raise ValidationError(
                f"Type mismatch: expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
    
    # Range check för numeriska värden
    if 'range' in spec and isinstance(value, (int, float, np.number)):
        min_val, max_val = spec['range']
        
        if min_val is not None and value < min_val:
            raise ValidationError(
                f"Value {value} below minimum {min_val}"
            )
        
        if max_val is not None and value > max_val:
            raise ValidationError(
                f"Value {value} above maximum {max_val}"
            )
    
    # Custom constraints
    if 'constraints' in spec:
        constraints = spec['constraints']
        
        # Check for NaN
        if 'allow_nan' in constraints and not constraints['allow_nan']:
            if pd.isna(value):
                raise ValidationError("NaN not allowed")
        
        # Check for None
        if 'allow_none' in constraints and not constraints['allow_none']:
            if value is None:
                raise ValidationError("None not allowed")
        
        # Check if value is positive
        if constraints.get('positive_only') and isinstance(value, (int, float)):
            if value <= 0:
                raise ValidationError(f"Value must be positive, got {value}")
        
        # Check if value is non-negative
        if constraints.get('non_negative') and isinstance(value, (int, float)):
            if value < 0:
                raise ValidationError(f"Value must be non-negative, got {value}")
        
        # Custom validator function
        if 'validator' in constraints:
            validator = constraints['validator']
            if not validator(value):
                raise ValidationError("Custom validation failed")


def validate_dataframe(
    df: pd.DataFrame, 
    spec: Dict[str, Any],
    raise_on_error: bool = True
) -> List[str]:
    """
    Validera en DataFrame mot specification.
    
    Args:
        df: DataFrame att validera
        spec: Dict med validation rules:
            - columns: Required columns
            - dtypes: Expected dtypes för columns
            - constraints: Dict med constraints
        raise_on_error: Om True, raise ValidationError. Om False, returnera lista med errors
        
    Returns:
        Lista med error messages (tom om allt OK)
        
    Raises:
        ValidationError: Om raise_on_error=True och validering misslyckas
    """
    errors = []
    
    # Check required columns
    if 'columns' in spec:
        required_cols = spec['columns']
        missing = set(required_cols) - set(df.columns)
        if missing:
            errors.append(f"Missing columns: {missing}")
    
    # Check dtypes
    if 'dtypes' in spec:
        dtypes_spec = spec['dtypes']
        for col, expected_dtype in dtypes_spec.items():
            if col not in df.columns:
                continue
            
            actual_dtype = df[col].dtype
            if not pd.api.types.is_dtype_equal(actual_dtype, expected_dtype):
                errors.append(
                    f"Column '{col}' has wrong dtype: "
                    f"expected {expected_dtype}, got {actual_dtype}"
                )
    
    # Check constraints
    if 'constraints' in spec:
        constraints = spec['constraints']
        
        # All positive values
        if constraints.get('all_positive'):
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if (df[col] <= 0).any():
                    errors.append(f"Column '{col}' contains non-positive values")
        
        # No negative values
        if constraints.get('non_negative'):
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if (df[col] < 0).any():
                    errors.append(f"Column '{col}' contains negative values")
        
        # No NaN values
        if constraints.get('no_nan'):
            nan_cols = df.columns[df.isna().any()].tolist()
            if nan_cols:
                errors.append(f"Columns with NaN values: {nan_cols}")
        
        # Minimum rows
        if 'min_rows' in constraints:
            min_rows = constraints['min_rows']
            if len(df) < min_rows:
                errors.append(
                    f"DataFrame has {len(df)} rows, minimum required: {min_rows}"
                )
        
        # Maximum rows
        if 'max_rows' in constraints:
            max_rows = constraints['max_rows']
            if len(df) > max_rows:
                errors.append(
                    f"DataFrame has {len(df)} rows, maximum allowed: {max_rows}"
                )
        
        # Unique columns
        if 'unique_columns' in constraints:
            unique_cols = constraints['unique_columns']
            for col in unique_cols:
                if col not in df.columns:
                    continue
                if df[col].duplicated().any():
                    errors.append(f"Column '{col}' contains duplicate values")
    
    # Raise or return errors
    if errors and raise_on_error:
        raise ValidationError("; ".join(errors))
    
    return errors


def validate_case_definition(
    case_def: Dict[str, Any],
    registry
) -> None:
    """
    Validera att en case_definition är korrekt formaterad.
    
    Args:
        case_def: Case definition att validera
        registry: ProducerRegistry för att validera mot
        
    Raises:
        ValidationError: Om case_definition är invalid
    """
    # Check structure
    required_keys = ['name', 'parameters', 'modules']
    for key in required_keys:
        if key not in case_def:
            raise ValidationError(f"Missing required key: '{key}'")
    
    # Validate name
    if not isinstance(case_def['name'], str):
        raise ValidationError("'name' must be a string")
    
    if not case_def['name'].strip():
        raise ValidationError("'name' cannot be empty")
    
    # Validate parameters
    if not isinstance(case_def['parameters'], dict):
        raise ValidationError("'parameters' must be a dict")
    
    # Validate modules
    if not isinstance(case_def['modules'], dict):
        raise ValidationError("'modules' must be a dict")
    
    # Validate each module
    for var_name, producer_id in case_def['modules'].items():
        # Check that variable exists in registry
        if var_name not in registry.list_variables():
            raise ValidationError(
                f"Unknown variable in modules: '{var_name}'"
            )
        
        # Check that producer exists for variable
        if producer_id not in registry.list_producers(var_name):
            raise ValidationError(
                f"Unknown producer '{producer_id}' for variable '{var_name}'"
            )
    
    # Validate module_configs if present
    if 'module_configs' in case_def:
        if not isinstance(case_def['module_configs'], dict):
            raise ValidationError("'module_configs' must be a dict")


def validate_producer_result(
    value: Any,
    variable_name: str,
    registry
) -> None:
    """
    Validera att ett producer-resultat är korrekt.
    
    Args:
        value: Värdet från producer
        variable_name: Namnet på variabeln
        registry: ProducerRegistry med variable specs
        
    Raises:
        ValidationError: Om resultat är invalid
    """
    var_spec = registry.get_variable_spec(variable_name)
    
    # Skapa validation spec från variable spec
    spec = {
        'dtype': var_spec.dtype
    }
    
    if var_spec.range is not None:
        spec['range'] = var_spec.range
    
    # Validera
    validate(value, spec)


def create_validation_spec(
    dtype: type,
    range: Optional[tuple] = None,
    allow_nan: bool = False,
    allow_none: bool = False,
    positive_only: bool = False,
    non_negative: bool = False
) -> Dict[str, Any]:
    """
    Helper function för att skapa validation specs.
    
    Args:
        dtype: Expected datatype
        range: (min, max) för numeriska värden
        allow_nan: Om NaN tillåts
        allow_none: Om None tillåts
        positive_only: Om endast positiva värden tillåts
        non_negative: Om endast icke-negativa värden tillåts
        
    Returns:
        Validation spec dict
    """
    spec = {'dtype': dtype}
    
    if range is not None:
        spec['range'] = range
    
    constraints = {}
    if not allow_nan:
        constraints['allow_nan'] = False
    if not allow_none:
        constraints['allow_none'] = False
    if positive_only:
        constraints['positive_only'] = True
    if non_negative:
        constraints['non_negative'] = True
    
    if constraints:
        spec['constraints'] = constraints
    
    return spec


def validate_dict_keys(
    data: dict,
    required_keys: List[str],
    optional_keys: List[str] = None
) -> None:
    """
    Validera att en dict har rätt keys.
    
    Args:
        data: Dict att validera
        required_keys: Keys som måste finnas
        optional_keys: Keys som får finnas (utöver required)
        
    Raises:
        ValidationError: Om required keys saknas eller unknown keys finns
    """
    if not isinstance(data, dict):
        raise ValidationError(f"Expected dict, got {type(data).__name__}")
    
    # Check required keys
    missing = set(required_keys) - set(data.keys())
    if missing:
        raise ValidationError(f"Missing required keys: {missing}")
    
    # Check for unknown keys if optional_keys specified
    if optional_keys is not None:
        allowed = set(required_keys) | set(optional_keys)
        unknown = set(data.keys()) - allowed
        if unknown:
            raise ValidationError(f"Unknown keys: {unknown}")