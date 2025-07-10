from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
import json
from pathlib import Path

from .models import AIModel, ModelParameter
from .exceptions import GigapixelException


class ParameterValidationError(GigapixelException):
    """Exception raised when parameter validation fails"""
    pass


class ParameterConversionError(GigapixelException):
    """Exception raised when parameter conversion fails"""
    pass


@dataclass
class ProcessingParameters:
    """Container for processing parameters"""
    model: AIModel
    parameters: Dict[str, Any] = field(default_factory=dict)
    scale: Optional[str] = None
    
    def __post_init__(self):
        """Validate parameters after initialization"""
        self.validate_parameters()
    
    def validate_parameters(self):
        """Validate all parameters against model requirements"""
        for param_name, param_value in self.parameters.items():
            if param_name not in self.model.parameters:
                raise ParameterValidationError(f"Parameter '{param_name}' is not valid for model '{self.model.name}'")
            
            param_def = self.model.parameters[param_name]
            validated_value = ParameterValidator.validate_parameter(param_def, param_value)
            self.parameters[param_name] = validated_value
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get a parameter value with optional default"""
        return self.parameters.get(name, default)
    
    def set_parameter(self, name: str, value: Any):
        """Set a parameter value with validation"""
        if name not in self.model.parameters:
            raise ParameterValidationError(f"Parameter '{name}' is not valid for model '{self.model.name}'")
        
        param_def = self.model.parameters[name]
        validated_value = ParameterValidator.validate_parameter(param_def, value)
        self.parameters[name] = validated_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'model_name': self.model.name,
            'parameters': self.parameters,
            'scale': self.scale
        }


class ParameterValidator:
    """Utility class for parameter validation"""
    
    @staticmethod
    def validate_parameter(param_def: ModelParameter, value: Any) -> Any:
        """Validate a parameter value against its definition"""
        if value is None:
            return param_def.default_value
        
        if param_def.param_type == "decimal":
            return ParameterValidator._validate_decimal(param_def, value)
        elif param_def.param_type == "integer":
            return ParameterValidator._validate_integer(param_def, value)
        elif param_def.param_type == "boolean":
            return ParameterValidator._validate_boolean(param_def, value)
        elif param_def.param_type == "text":
            return ParameterValidator._validate_text(param_def, value)
        else:
            raise ParameterValidationError(f"Unknown parameter type: {param_def.param_type}")
    
    @staticmethod
    def _validate_decimal(param_def: ModelParameter, value: Any) -> float:
        """Validate decimal parameter"""
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ParameterConversionError(f"Cannot convert '{value}' to decimal for parameter '{param_def.name}'")
        
        if param_def.min_value is not None and float_value < param_def.min_value:
            raise ParameterValidationError(f"Parameter '{param_def.name}' value {float_value} is below minimum {param_def.min_value}")
        
        if param_def.max_value is not None and float_value > param_def.max_value:
            raise ParameterValidationError(f"Parameter '{param_def.name}' value {float_value} is above maximum {param_def.max_value}")
        
        return float_value
    
    @staticmethod
    def _validate_integer(param_def: ModelParameter, value: Any) -> int:
        """Validate integer parameter"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ParameterConversionError(f"Cannot convert '{value}' to integer for parameter '{param_def.name}'")
        
        if param_def.min_value is not None and int_value < param_def.min_value:
            raise ParameterValidationError(f"Parameter '{param_def.name}' value {int_value} is below minimum {param_def.min_value}")
        
        if param_def.max_value is not None and int_value > param_def.max_value:
            raise ParameterValidationError(f"Parameter '{param_def.name}' value {int_value} is above maximum {param_def.max_value}")
        
        return int_value
    
    @staticmethod
    def _validate_boolean(param_def: ModelParameter, value: Any) -> bool:
        """Validate boolean parameter"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ParameterConversionError(f"Cannot convert '{value}' to boolean for parameter '{param_def.name}'")
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        raise ParameterConversionError(f"Cannot convert '{value}' to boolean for parameter '{param_def.name}'")
    
    @staticmethod
    def _validate_text(param_def: ModelParameter, value: Any) -> str:
        """Validate text parameter"""
        str_value = str(value)
        
        if param_def.max_length is not None and len(str_value) > param_def.max_length:
            raise ParameterValidationError(f"Parameter '{param_def.name}' text length {len(str_value)} exceeds maximum {param_def.max_length}")
        
        return str_value


class ParameterManager:
    """Manager for handling parameter persistence and presets"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize parameter manager"""
        if config_dir is None:
            config_dir = Path.home() / ".gigapixel"
        
        self.config_dir = config_dir
        self.presets_file = config_dir / "presets.json"
        self.last_used_file = config_dir / "last_used.json"
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
        
        self._presets: Dict[str, Dict[str, Any]] = {}
        self._load_presets()
    
    def _load_presets(self):
        """Load presets from file"""
        try:
            if self.presets_file.exists():
                with open(self.presets_file, 'r') as f:
                    self._presets = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # If presets file is corrupted, start with empty presets
            self._presets = {}
    
    def _save_presets(self):
        """Save presets to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self._presets, f, indent=2)
        except IOError as e:
            raise GigapixelException(f"Could not save presets: {e}")
    
    def save_preset(self, name: str, parameters: ProcessingParameters):
        """Save a parameter preset"""
        self._presets[name] = parameters.to_dict()
        self._save_presets()
    
    def load_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a parameter preset"""
        return self._presets.get(name)
    
    def delete_preset(self, name: str) -> bool:
        """Delete a parameter preset"""
        if name in self._presets:
            del self._presets[name]
            self._save_presets()
            return True
        return False
    
    def list_presets(self) -> List[str]:
        """List all preset names"""
        return list(self._presets.keys())
    
    def save_last_used(self, parameters: ProcessingParameters):
        """Save the last used parameters"""
        try:
            with open(self.last_used_file, 'w') as f:
                json.dump(parameters.to_dict(), f, indent=2)
        except IOError as e:
            # Not critical if we can't save last used parameters
            pass
    
    def load_last_used(self) -> Optional[Dict[str, Any]]:
        """Load the last used parameters"""
        try:
            if self.last_used_file.exists():
                with open(self.last_used_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return None
    
    def get_default_parameters(self, model: AIModel) -> ProcessingParameters:
        """Get default parameters for a model"""
        default_params = {}
        for param_name, param_def in model.parameters.items():
            if param_def.default_value is not None:
                default_params[param_name] = param_def.default_value
        
        return ProcessingParameters(model=model, parameters=default_params)


class ParameterBuilder:
    """Builder pattern for creating ProcessingParameters"""
    
    def __init__(self, model: AIModel):
        self.model = model
        self.parameters = {}
        self.scale = None
    
    def with_parameter(self, name: str, value: Any) -> 'ParameterBuilder':
        """Add a parameter to the builder"""
        self.parameters[name] = value
        return self
    
    def with_scale(self, scale: str) -> 'ParameterBuilder':
        """Add scale to the builder"""
        self.scale = scale
        return self
    
    def build(self) -> ProcessingParameters:
        """Build the ProcessingParameters object"""
        return ProcessingParameters(
            model=self.model,
            parameters=self.parameters,
            scale=self.scale
        )


# Utility functions for parameter conversion
def convert_legacy_parameters(scale: Optional[str] = None, mode: Optional[str] = None) -> Optional[ProcessingParameters]:
    """Convert legacy scale/mode parameters to new parameter system"""
    from .models import LegacyMode, Scale
    
    if mode is None:
        return None
    
    # Map legacy mode to new model
    try:
        legacy_mode = LegacyMode[mode.upper().replace(" ", "_").replace("&", "AND")]
        model = legacy_mode.value.value
        
        # Create parameters with defaults
        param_manager = ParameterManager()
        parameters = param_manager.get_default_parameters(model)
        
        if scale:
            parameters.scale = scale
        
        return parameters
    except KeyError:
        return None


def create_parameters_from_dict(model: AIModel, params_dict: Dict[str, Any]) -> ProcessingParameters:
    """Create ProcessingParameters from a dictionary"""
    builder = ParameterBuilder(model)
    
    for param_name, param_value in params_dict.items():
        if param_name == "scale":
            builder.with_scale(param_value)
        else:
            builder.with_parameter(param_name, param_value)
    
    return builder.build()