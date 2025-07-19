#!/usr/bin/env python3
"""
Auto suffix generation for GigaUp based on model parameters.
"""

from typing import Dict, Any, Optional
from .models import AIModel, ModelClass
from .parameters import ProcessingParameters


def generate_auto_suffix(parameters: ProcessingParameters, size_param: str, quality: Optional[int] = None) -> str:
    """
    Generate automatic suffix based on processing parameters.
    
    Format: "-{size}-{model}-{params}"
    Examples:
    - Scale 2x, High fidelity with Face recovery: "-2x-hf-fr"
    - Width 2560, Redefine creative with Low creativity and texture 1: "-w2560-rc-lo1"
    """
    suffix_parts = []
    
    # Add size parameter
    if size_param:
        suffix_parts.append(_format_size_param(size_param))
    
    # Add model abbreviation
    model_abbrev = _get_model_abbreviation(parameters.model)
    if model_abbrev:
        suffix_parts.append(model_abbrev)
    
    # Add model-specific parameters
    param_parts = _get_parameter_abbreviations(parameters)
    suffix_parts.extend(param_parts)
    
    # Add quality if specified and not default
    if quality and quality != 95:
        suffix_parts.append(f"q{quality}")
    
    # Join with dashes
    if suffix_parts:
        return "-" + "-".join(suffix_parts)
    else:
        return ""


def _format_size_param(size_param: str) -> str:
    """Format size parameter for suffix"""
    if size_param.startswith('w') or size_param.startswith('h'):
        # Width or height
        return size_param
    elif size_param.endswith('x'):
        # Standard scale
        return size_param
    else:
        # Custom scale - format decimal values
        try:
            scale_val = float(size_param)
            if scale_val == int(scale_val):
                # Whole number
                scale_int = int(scale_val)
                if scale_int <= 6:
                    return f"{scale_int}x"
                else:
                    return f"{scale_int}x"  # Cap display at actual value
            else:
                # Decimal - replace dot with underscore
                return f"{size_param.replace('.', '_')}x"
        except ValueError:
            return size_param


def _get_model_abbreviation(model: AIModel) -> str:
    """Get model abbreviation for suffix"""
    model_abbreviations = {
        # Standard models
        "standard_v2": "sd",
        "high_fidelity_v2": "hf", 
        "low_resolution_v2": "lr",
        "text_refine": "ts",
        "cgi": "ac",
        
        # Generative models
        "recover": "rv",
        "redefine_realistic": "rr",
        "redefine_creative": "rc",
        
        # Sharpen models
        "sharpen_standard": "sp",
        "sharpen_strong": "sps",
        "lens_blur": "lb",
        "lens_blur_v2": "lb2",
        "motion_blur": "mb",
        "natural": "nt",
        "refocus": "rf",
        "super_focus": "sf",
        "super_focus_v2": "sf2",
        
        # Denoise models
        "denoise_normal": "dn",
        "denoise_strong": "dns",
        "denoise_extreme": "dne",
        
        # Restore models
        "dust_scratch": "ds",
        
        # Lighting models
        "lighting_adjust": "la",
        "white_balance": "wb",
    }
    
    return model_abbreviations.get(model.name, model.name[:3])


def _get_parameter_abbreviations(parameters: ProcessingParameters) -> list:
    """Get parameter abbreviations for suffix"""
    parts = []
    model = parameters.model
    params = parameters.parameters
    
    # Handle model-specific parameters
    if model.model_class == ModelClass.GENERATIVE:
        if model.name == "recover":
            # Recover parameters
            if params.get("version") == "v1":
                parts.append("v1")
            elif params.get("version") == "v2":
                parts.append("v2")
            
            detail = params.get("detail")
            if detail and detail != 50:  # Non-default detail
                parts.append(f"d{detail}")
                
        elif model.name == "redefine_realistic":
            # Redefine realistic parameters
            enhancement = params.get("enhancement", "None")
            if enhancement == "Subtle":
                parts.append("st")
            else:
                parts.append("nn")  # None
                
        elif model.name == "redefine_creative":
            # Redefine creative parameters
            creativity = params.get("creativity", "Medium")
            texture = params.get("texture", 1)
            
            creativity_map = {
                "Low": "lo",
                "Medium": "md", 
                "High": "hi",
                "Max": "mx"
            }
            
            creativity_abbrev = creativity_map.get(creativity, "md")
            parts.append(f"{creativity_abbrev}{texture}")
    
    # Handle standard parameters (for all models)
    sharpen = params.get("sharpen")
    if sharpen and sharpen != 1:  # Non-default sharpen
        parts.append(f"sp{sharpen}")
    
    denoise = params.get("denoise") 
    if denoise and denoise != 1:  # Non-default denoise
        parts.append(f"ds{denoise}")
        
    fix_compression = params.get("fix_compression")
    if fix_compression and fix_compression != 1:  # Non-default fix_compression
        parts.append(f"fc{fix_compression}")
    
    # Face recovery (global parameter)
    if params.get("face_recovery"):
        parts.append("fr")
    
    return parts


def parse_suffix_mode(suffix_arg: str) -> Dict[str, Any]:
    """
    Parse suffix argument and return configuration.
    
    Returns:
        dict with keys: 'mode', 'value', 'toggle_on'
    """
    if suffix_arg == "0":
        return {"mode": "empty", "value": "", "toggle_on": False}
    elif suffix_arg == "1":
        return {"mode": "empty", "value": "", "toggle_on": True}
    elif suffix_arg == "auto":
        return {"mode": "auto", "value": "", "toggle_on": True}
    else:
        # Custom string
        return {"mode": "custom", "value": suffix_arg, "toggle_on": False}


# Example usage and testing
if __name__ == "__main__":
    from .models import EnhanceStandardModel, EnhanceGenerativeModel
    from .factory import get_model_factory
    
    # Test cases
    factory = get_model_factory()
    
    # Test 1: Standard model with scale
    params1 = factory.create_processing_parameters(
        "standard_v2", 
        {"sharpen": 25, "face_recovery": True}, 
        "2x"
    )
    suffix1 = generate_auto_suffix(params1, "2x", 95)
    print(f"Test 1: {suffix1}")  # Expected: -2x-sd-sp25-fr
    
    # Test 2: Generative model with width
    params2 = factory.create_processing_parameters(
        "redefine_creative",
        {"creativity": "Low", "texture": 2, "face_recovery": True},
        "w2560"
    )
    suffix2 = generate_auto_suffix(params2, "w2560", 80)
    print(f"Test 2: {suffix2}")  # Expected: -w2560-rc-lo2-fr-q80