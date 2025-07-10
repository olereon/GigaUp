from typing import Dict, Any, Optional, List, Type, Union
from abc import ABC, abstractmethod
import re

from .models import (
    AIModel, ModelCategory, ModelClass, Scale,
    EnhanceStandardModel, EnhanceGenerativeModel, 
    SharpenStandardModel, SharpenGenerativeModel,
    DenoiseModel, RestoreModel, LightingModel,
    LegacyMode, get_all_models, find_model_by_name
)
from .parameters import ProcessingParameters, ParameterManager, ParameterBuilder
from .exceptions import GigapixelException


class ModelFactoryError(GigapixelException):
    """Exception raised by ModelFactory"""
    pass


class ModelNotFoundError(ModelFactoryError):
    """Exception raised when a requested model is not found"""
    pass


class InvalidModelConfigError(ModelFactoryError):
    """Exception raised when model configuration is invalid"""
    pass


class ModelFactory:
    """Factory for creating AI models and processing parameters"""
    
    def __init__(self):
        self._parameter_manager = ParameterManager()
        self._model_registry = self._build_model_registry()
    
    def _build_model_registry(self) -> Dict[str, AIModel]:
        """Build a registry of all available models"""
        registry = {}
        
        # Register all model types
        model_enums = [
            EnhanceStandardModel, EnhanceGenerativeModel,
            SharpenStandardModel, SharpenGenerativeModel,
            DenoiseModel, RestoreModel, LightingModel
        ]
        
        for model_enum in model_enums:
            for model_item in model_enum:
                model = model_item.value
                registry[model.name] = model
                # Also register by display name for user-friendly lookup
                registry[model.display_name.lower().replace(" ", "_")] = model
        
        return registry
    
    def get_model_by_name(self, name: str) -> AIModel:
        """Get a model by its name or display name"""
        # Try exact match first
        if name in self._model_registry:
            return self._model_registry[name]
        
        # Try case-insensitive match
        name_lower = name.lower()
        for model_name, model in self._model_registry.items():
            if model_name.lower() == name_lower:
                return model
        
        # Try fuzzy match (replace spaces/underscores)
        normalized_name = name_lower.replace(" ", "_").replace("-", "_")
        for model_name, model in self._model_registry.items():
            normalized_model_name = model_name.lower().replace(" ", "_").replace("-", "_")
            if normalized_model_name == normalized_name:
                return model
        
        raise ModelNotFoundError(f"Model '{name}' not found")
    
    def get_models_by_category(self, category: ModelCategory) -> List[AIModel]:
        """Get all models in a specific category"""
        return [model for model in self._model_registry.values() 
                if model.category == category]
    
    def get_models_by_class(self, model_class: ModelClass) -> List[AIModel]:
        """Get all models of a specific class"""
        return [model for model in self._model_registry.values() 
                if model.model_class == model_class]
    
    def get_all_models(self) -> List[AIModel]:
        """Get all available models"""
        return list(set(self._model_registry.values()))  # Remove duplicates
    
    def get_categories(self) -> List[ModelCategory]:
        """Get all available model categories"""
        return list(ModelCategory)
    
    def create_processing_parameters(self, 
                                   model_name: str, 
                                   parameters: Optional[Dict[str, Any]] = None,
                                   scale: Optional[str] = None) -> ProcessingParameters:
        """Create processing parameters for a model"""
        model = self.get_model_by_name(model_name)
        
        # Start with default parameters
        default_params = self._parameter_manager.get_default_parameters(model)
        
        # Override with provided parameters
        if parameters:
            for param_name, param_value in parameters.items():
                if param_name in model.parameters:
                    default_params.set_parameter(param_name, param_value)
                else:
                    raise InvalidModelConfigError(f"Parameter '{param_name}' not valid for model '{model_name}'")
        
        # Set scale if provided
        if scale:
            default_params.scale = scale
        
        return default_params
    
    def create_from_preset(self, preset_name: str) -> Optional[ProcessingParameters]:
        """Create processing parameters from a saved preset"""
        preset_data = self._parameter_manager.load_preset(preset_name)
        if not preset_data:
            return None
        
        model = self.get_model_by_name(preset_data['model_name'])
        return ProcessingParameters(
            model=model,
            parameters=preset_data.get('parameters', {}),
            scale=preset_data.get('scale')
        )
    
    def create_from_legacy(self, mode: str, scale: Optional[str] = None) -> ProcessingParameters:
        """Create processing parameters from legacy mode string"""
        try:
            # Convert legacy mode name to enum
            legacy_mode_name = mode.upper().replace(" ", "_").replace("&", "AND")
            legacy_mode = LegacyMode[legacy_mode_name]
            model = legacy_mode.value.value
            
            # Get default parameters
            default_params = self._parameter_manager.get_default_parameters(model)
            if scale:
                default_params.scale = scale
            
            return default_params
        except KeyError:
            raise ModelNotFoundError(f"Legacy mode '{mode}' not found")
    
    def save_preset(self, name: str, parameters: ProcessingParameters):
        """Save processing parameters as a preset"""
        self._parameter_manager.save_preset(name, parameters)
    
    def load_preset(self, name: str) -> Optional[ProcessingParameters]:
        """Load a preset by name"""
        return self.create_from_preset(name)
    
    def list_presets(self) -> List[str]:
        """List all available presets"""
        return self._parameter_manager.list_presets()
    
    def delete_preset(self, name: str) -> bool:
        """Delete a preset by name"""
        return self._parameter_manager.delete_preset(name)
    
    def validate_model_config(self, model_name: str, parameters: Dict[str, Any]) -> bool:
        """Validate a model configuration"""
        try:
            model = self.get_model_by_name(model_name)
            # Try to create parameters - this will validate them
            self.create_processing_parameters(model_name, parameters)
            return True
        except (ModelNotFoundError, InvalidModelConfigError):
            return False
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        model = self.get_model_by_name(model_name)
        return {
            'name': model.name,
            'display_name': model.display_name,
            'description': model.description,
            'category': model.category.value,
            'model_class': model.model_class.value,
            'parameters': {
                param_name: {
                    'type': param.param_type,
                    'min_value': param.min_value,
                    'max_value': param.max_value,
                    'default_value': param.default_value,
                    'description': param.description,
                    'max_length': param.max_length
                }
                for param_name, param in model.parameters.items()
            }
        }
    
    def suggest_models(self, query: str, limit: int = 5) -> List[AIModel]:
        """Suggest models based on a search query"""
        query_lower = query.lower()
        matches = []
        
        for model in self.get_all_models():
            score = 0
            
            # Exact name match gets highest score
            if query_lower == model.name.lower():
                score += 100
            elif query_lower in model.name.lower():
                score += 50
            
            # Display name match
            if query_lower == model.display_name.lower():
                score += 90
            elif query_lower in model.display_name.lower():
                score += 40
            
            # Description match
            if query_lower in model.description.lower():
                score += 20
            
            # Category match
            if query_lower in model.category.value.lower():
                score += 10
            
            if score > 0:
                matches.append((score, model))
        
        # Sort by score and return top matches
        matches.sort(key=lambda x: x[0], reverse=True)
        return [model for score, model in matches[:limit]]


class ModelBuilder:
    """Builder pattern for creating models with fluent interface"""
    
    def __init__(self, factory: ModelFactory):
        self._factory = factory
        self._model_name: Optional[str] = None
        self._parameters: Dict[str, Any] = {}
        self._scale: Optional[str] = None
    
    def model(self, name: str) -> 'ModelBuilder':
        """Set the model name"""
        self._model_name = name
        return self
    
    def parameter(self, name: str, value: Any) -> 'ModelBuilder':
        """Add a parameter"""
        self._parameters[name] = value
        return self
    
    def scale(self, scale: str) -> 'ModelBuilder':
        """Set the scale"""
        self._scale = scale
        return self
    
    def build(self) -> ProcessingParameters:
        """Build the processing parameters"""
        if not self._model_name:
            raise InvalidModelConfigError("Model name must be specified")
        
        return self._factory.create_processing_parameters(
            self._model_name, 
            self._parameters, 
            self._scale
        )


class ModelConfigValidator:
    """Validator for model configurations"""
    
    def __init__(self, factory: ModelFactory):
        self._factory = factory
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate a model configuration and return list of errors"""
        errors = []
        
        # Check required fields
        if 'model' not in config:
            errors.append("Model name is required")
            return errors
        
        try:
            model = self._factory.get_model_by_name(config['model'])
        except ModelNotFoundError as e:
            errors.append(str(e))
            return errors
        
        # Validate parameters
        parameters = config.get('parameters', {})
        for param_name, param_value in parameters.items():
            if param_name not in model.parameters:
                errors.append(f"Parameter '{param_name}' is not valid for model '{model.name}'")
                continue
            
            param_def = model.parameters[param_name]
            try:
                from .parameters import ParameterValidator
                ParameterValidator.validate_parameter(param_def, param_value)
            except Exception as e:
                errors.append(f"Parameter '{param_name}': {str(e)}")
        
        # Validate scale
        scale = config.get('scale')
        if scale:
            try:
                Scale(scale)
            except ValueError:
                errors.append(f"Invalid scale value: {scale}")
        
        return errors
    
    def is_valid_config(self, config: Dict[str, Any]) -> bool:
        """Check if a configuration is valid"""
        return len(self.validate_config(config)) == 0


# Global factory instance
_global_factory = None


def get_model_factory() -> ModelFactory:
    """Get the global ModelFactory instance"""
    global _global_factory
    if _global_factory is None:
        _global_factory = ModelFactory()
    return _global_factory


def create_model_builder() -> ModelBuilder:
    """Create a new ModelBuilder instance"""
    return ModelBuilder(get_model_factory())


def create_model_validator() -> ModelConfigValidator:
    """Create a new ModelConfigValidator instance"""
    return ModelConfigValidator(get_model_factory())


# Convenience functions
def create_parameters(model_name: str, 
                     parameters: Optional[Dict[str, Any]] = None,
                     scale: Optional[str] = None) -> ProcessingParameters:
    """Convenience function to create processing parameters"""
    return get_model_factory().create_processing_parameters(model_name, parameters, scale)


def get_model_by_name(name: str) -> AIModel:
    """Convenience function to get a model by name"""
    return get_model_factory().get_model_by_name(name)


def list_models() -> List[AIModel]:
    """Convenience function to list all models"""
    return get_model_factory().get_all_models()


def suggest_models(query: str, limit: int = 5) -> List[AIModel]:
    """Convenience function to suggest models"""
    return get_model_factory().suggest_models(query, limit)