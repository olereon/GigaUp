from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass


class ModelClass(Enum):
    """AI Model Classes"""
    STANDARD = "Standard"
    GENERATIVE = "Generative"


class ModelCategory(Enum):
    """Model Categories"""
    ENHANCE = "Enhance"
    SHARPEN = "Sharpen"
    DENOISE = "Denoise"
    RESTORE = "Restore"
    LIGHTING = "Lighting"


@dataclass
class ModelParameter:
    """Definition of a model parameter"""
    name: str
    param_type: str  # 'decimal', 'integer', 'boolean', 'text'
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    default_value: Optional[Union[int, float, bool, str]] = None
    description: str = ""
    max_length: Optional[int] = None  # For text parameters


@dataclass
class AIModel:
    """Definition of an AI model with its parameters"""
    name: str
    display_name: str
    category: ModelCategory
    model_class: ModelClass
    description: str
    parameters: Dict[str, ModelParameter]
    ui_element_name: Optional[str] = None  # For GUI automation
    
    def __hash__(self):
        """Make AIModel hashable for use in sets"""
        return hash(self.name)
    
    def __eq__(self, other):
        """Define equality based on model name"""
        if not isinstance(other, AIModel):
            return False
        return self.name == other.name


# Enhanced Standard Models
class EnhanceStandardModel(Enum):
    """Standard Enhance Models"""
    STANDARD_V2 = AIModel(
        name="standard_v2",
        display_name="Standard V2",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.STANDARD,
        description="General-purpose model balancing detail, sharpness, and noise reduction for various images.",
        parameters={
            "sharpen": ModelParameter("sharpen", "integer", 1, 100, 1, "Slightly sharpens the image"),
            "denoise": ModelParameter("denoise", "integer", 1, 100, 1, "Reduces noise in the image"),
            "fix_compression": ModelParameter("fix_compression", "integer", 1, 100, 1, "Reduces compression artifacts to improve details")
        }
    )
    
    LOW_RESOLUTION_V2 = AIModel(
        name="low_resolution_v2",
        display_name="Low Resolution V2",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.STANDARD,
        description="Enhances clarity and detail in low-resolution images like web graphics and screenshots.",
        parameters={
            "sharpen": ModelParameter("sharpen", "integer", 1, 100, 1, "Slightly sharpens the image"),
            "denoise": ModelParameter("denoise", "integer", 1, 100, 1, "Reduces noise in the image"),
            "fix_compression": ModelParameter("fix_compression", "integer", 1, 100, 1, "Reduces compression artifacts to improve details")
        }
    )
    
    CGI = AIModel(
        name="cgi",
        display_name="CGI",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.STANDARD,
        description="Optimized for CGI and digital illustrations, enhancing texture and detail in computer-generated images.",
        parameters={
            "sharpen": ModelParameter("sharpen", "integer", 1, 100, 1, "Slightly sharpens the image"),
            "denoise": ModelParameter("denoise", "integer", 1, 100, 1, "Reduces noise in the image")
        }
    )
    
    HIGH_FIDELITY_V2 = AIModel(
        name="high_fidelity_v2",
        display_name="High Fidelity V2",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.STANDARD,
        description="Ideal for high-quality images, preserving intricate details in professional photography.",
        parameters={
            "sharpen": ModelParameter("sharpen", "integer", 1, 100, 1, "Slightly sharpens the image"),
            "denoise": ModelParameter("denoise", "integer", 1, 100, 1, "Reduces noise in the image"),
            "fix_compression": ModelParameter("fix_compression", "integer", 1, 100, 1, "Reduces compression artifacts to improve details"),
            "face_recovery": ModelParameter("face_recovery", "boolean", default_value=False, description="Enable face recovery processing")
        }
    )
    
    TEXT_REFINE = AIModel(
        name="text_refine",
        display_name="Text Refine",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.STANDARD,
        description="Designed for images with text and shapes, enhancing clarity and sharpness of elements.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Controls model strength. Too high can make results look unrealistic"),
            "sharpen": ModelParameter("sharpen", "decimal", 0.0, 1.0, 0.0, "Slightly sharpens the image"),
            "denoise": ModelParameter("denoise", "decimal", 0.0, 1.0, 0.0, "Reduces noise in the image"),
            "fix_compression": ModelParameter("fix_compression", "decimal", 0.0, 1.0, 0.0, "Reduces compression artifacts to improve details")
        }
    )


class EnhanceGenerativeModel(Enum):
    """Generative Enhance Models"""
    RECOVER = AIModel(
        name="recover",
        display_name="Recover",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.GENERATIVE,
        description="Delivers high fidelity upscaling for extremely low-resolution images, preserving natural detail and sharpness.",
        parameters={
            "version": ModelParameter("version", "text", default_value="v2", description="Version v1 or v2 (New)"),
            "detail": ModelParameter("detail", "integer", 0, 100, 50, "Adjusts the level of added detail after rendering"),
            "face_recovery": ModelParameter("face_recovery", "boolean", default_value=False, "Enable face recovery processing")
        }
    )
    
    REDEFINE_REALISTIC = AIModel(
        name="redefine_realistic",
        display_name="Redefine Realistic",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.GENERATIVE,
        description="Realistic upscaling with subtle enhancement options.",
        parameters={
            "enhancement": ModelParameter("enhancement", "text", default_value="None", description="Enhancement level: None or Subtle"),
            "face_recovery": ModelParameter("face_recovery", "boolean", default_value=False, "Enable face recovery processing")
        }
    )
    
    REDEFINE_CREATIVE = AIModel(
        name="redefine_creative",
        display_name="Redefine Creative",
        category=ModelCategory.ENHANCE,
        model_class=ModelClass.GENERATIVE,
        description="Creative upscaling with customizable creativity levels and texture control.",
        parameters={
            "creativity": ModelParameter("creativity", "text", default_value="Medium", description="Creativity level: Low, Medium, High, or Max"),
            "image_description": ModelParameter("image_description", "text", max_length=1024, default_value="", description="Guiding prompt for image description"),
            "texture": ModelParameter("texture", "integer", 1, 5, 1, "Texture level from 1 to 5"),
            "face_recovery": ModelParameter("face_recovery", "boolean", default_value=False, "Enable face recovery processing")
        }
    )


class SharpenStandardModel(Enum):
    """Standard Sharpen Models"""
    STANDARD = AIModel(
        name="sharpen_standard",
        display_name="Standard",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.STANDARD,
        description="All-purpose sharpening, intended for images with slight amounts of lens and motion blur.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "minor_denoise": ModelParameter("minor_denoise", "decimal", 0.01, 1.0, 0.0, "Removes noisy pixels to increase clarity")
        }
    )
    
    STRONG = AIModel(
        name="sharpen_strong",
        display_name="Strong",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.STANDARD,
        description="For very blurry and out-of-focus images. Try Standard model first to avoid over-sharpening.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Increases details. Too much can create unrealistic results")
        }
    )
    
    LENS_BLUR = AIModel(
        name="lens_blur",
        display_name="Lens Blur",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.STANDARD,
        description="Ideal for images affected by imperfections caused when camera lens fails to focus correctly.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "minor_denoise": ModelParameter("minor_denoise", "decimal", 0.01, 1.0, 0.0, "Removes noisy pixels to increase clarity")
        }
    )
    
    LENS_BLUR_V2 = AIModel(
        name="lens_blur_v2",
        display_name="Lens Blur V2",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.STANDARD,
        description="Generation 2 of the Lens Blur model, producing more consistent and stronger sharpening results.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "minor_denoise": ModelParameter("minor_denoise", "decimal", 0.01, 1.0, 0.0, "Removes noisy pixels to increase clarity")
        }
    )
    
    MOTION_BLUR = AIModel(
        name="motion_blur",
        display_name="Motion Blur",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.STANDARD,
        description="Optimized to correct streaked or smeared effect caused by movement during exposure.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "minor_denoise": ModelParameter("minor_denoise", "decimal", 0.01, 1.0, 0.0, "Removes noisy pixels to increase clarity")
        }
    )
    
    NATURAL = AIModel(
        name="natural",
        display_name="Natural",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.STANDARD,
        description="Designed to sharpen objects and keep textures looking natural.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "minor_denoise": ModelParameter("minor_denoise", "decimal", 0.01, 1.0, 0.0, "Removes noisy pixels to increase clarity")
        }
    )
    
    REFOCUS = AIModel(
        name="refocus",
        display_name="Refocus",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.STANDARD,
        description="Emphasize details and bring out finer lines or texture.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "minor_denoise": ModelParameter("minor_denoise", "decimal", 0.01, 1.0, 0.0, "Removes noisy pixels to increase clarity")
        }
    )


class SharpenGenerativeModel(Enum):
    """Generative Sharpen Models"""
    SUPER_FOCUS = AIModel(
        name="super_focus",
        display_name="Super Focus",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.GENERATIVE,
        description="Fix blur and extract detail on the most stubborn images that cannot be enhanced through other models.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.0, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "focus_boost": ModelParameter("focus_boost", "decimal", 0.25, 1.0, 0.5, "Use on very blurry images! Corrects missing detail by downscaling then upscaling"),
            "seed": ModelParameter("seed", "integer", -2147483648, 2147483647, 0, "Generation seed for reproducible results")
        }
    )
    
    SUPER_FOCUS_V2 = AIModel(
        name="super_focus_v2",
        display_name="Super Focus V2",
        category=ModelCategory.SHARPEN,
        model_class=ModelClass.GENERATIVE,
        description="Newest model that fixes blur and extracts detail on the most stubborn images.",
        parameters={
            "detail": ModelParameter("detail", "decimal", 0.0, 1.0, 0.5, "Increases details. Too much can create unrealistic results"),
            "focus_boost": ModelParameter("focus_boost", "decimal", 0.25, 1.0, 0.5, "Use on very blurry images! Corrects missing detail by downscaling then upscaling")
        }
    )


class DenoiseModel(Enum):
    """Denoise Models"""
    NORMAL = AIModel(
        name="denoise_normal",
        display_name="Normal",
        category=ModelCategory.DENOISE,
        model_class=ModelClass.STANDARD,
        description="Ideal to remove low-medium noise from low-light conditions or compression artifacts.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Reduces noise. Too high can remove detail and blur image"),
            "minor_deblur": ModelParameter("minor_deblur", "decimal", 0.01, 1.0, 0.0, "Slightly sharpens image. Counteracts softness from noise reduction"),
            "original_detail": ModelParameter("original_detail", "decimal", 0.0, 1.0, 0.0, "Return texture and details lost during noise reduction")
        }
    )
    
    STRONG = AIModel(
        name="denoise_strong",
        display_name="Strong",
        category=ModelCategory.DENOISE,
        model_class=ModelClass.STANDARD,
        description="Designed to strongly emphasize retaining image detail for medium-high noise images.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Reduces noise. Too high can remove detail and blur image"),
            "minor_deblur": ModelParameter("minor_deblur", "decimal", 0.01, 1.0, 0.0, "Slightly sharpens image. Counteracts softness from noise reduction"),
            "original_detail": ModelParameter("original_detail", "decimal", 0.0, 1.0, 0.0, "Return texture and details lost during noise reduction")
        }
    )
    
    EXTREME = AIModel(
        name="denoise_extreme",
        display_name="Extreme",
        category=ModelCategory.DENOISE,
        model_class=ModelClass.STANDARD,
        description="Prioritizes removing as much noise as possible rather than preserving detail.",
        parameters={
            "strength": ModelParameter("strength", "decimal", 0.01, 1.0, 0.5, "Reduces noise. Too high can remove detail and blur image"),
            "minor_deblur": ModelParameter("minor_deblur", "decimal", 0.01, 1.0, 0.0, "Slightly sharpens image. Counteracts softness from noise reduction"),
            "original_detail": ModelParameter("original_detail", "decimal", 0.0, 1.0, 0.0, "Return texture and details lost during noise reduction")
        }
    )


class RestoreModel(Enum):
    """Restore Models"""
    DUST_SCRATCH = AIModel(
        name="dust_scratch",
        display_name="Dust-Scratch",
        category=ModelCategory.RESTORE,
        model_class=ModelClass.GENERATIVE,
        description="Heal major dust, scratches, and surface damage while preserving the original photo look.",
        parameters={}  # No parameters - automatically configured
    )


class LightingModel(Enum):
    """Lighting Models"""
    ADJUST = AIModel(
        name="lighting_adjust",
        display_name="Adjust",
        category=ModelCategory.LIGHTING,
        model_class=ModelClass.STANDARD,
        description="Modifies exposure and contrast to produce a well-lit and vibrant image.",
        parameters={
            "color_correction": ModelParameter("color_correction", "boolean", default_value=True, description="Enable color correction"),
            "exposure": ModelParameter("exposure", "decimal", 0.0, 2.0, 1.0, "Exposure adjustment"),
            "highlight": ModelParameter("highlight", "decimal", 0.0, 2.0, 1.0, "Highlight adjustment"),
            "shadow": ModelParameter("shadow", "decimal", 0.0, 2.0, 1.0, "Shadow adjustment")
        }
    )
    
    WHITE_BALANCE = AIModel(
        name="white_balance",
        display_name="White Balance",
        category=ModelCategory.LIGHTING,
        model_class=ModelClass.STANDARD,
        description="Neutralizes unwanted color casts and allows creative tone adjustments.",
        parameters={
            "temperature": ModelParameter("temperature", "decimal", 0.01, 1.0, 0.5, "Color temperature adjustment"),
            "opacity": ModelParameter("opacity", "decimal", 0.01, 1.0, 1.0, "Effect opacity")
        }
    )


# Scale options (unchanged from original)
class Scale(Enum):
    X1 = "1x"
    X2 = "2x"
    X4 = "4x"
    X6 = "6x"


# Backward compatibility - mapping old modes to new models
class LegacyMode(Enum):
    """Legacy mode mapping for backward compatibility"""
    STANDARD = EnhanceStandardModel.STANDARD_V2
    HIGH_FIDELITY = EnhanceStandardModel.HIGH_FIDELITY_V2
    LOW_RESOLUTION = EnhanceStandardModel.LOW_RESOLUTION_V2
    TEXT_AND_SHAPES = EnhanceStandardModel.TEXT_REFINE
    ART_AND_CG = EnhanceStandardModel.CGI
    RECOVERY = EnhanceGenerativeModel.RECOVERY


# Utility functions for model management
def get_all_models() -> List[AIModel]:
    """Get all available AI models"""
    models = []
    for category in [EnhanceStandardModel, EnhanceGenerativeModel, SharpenStandardModel, 
                    SharpenGenerativeModel, DenoiseModel, RestoreModel, LightingModel]:
        for model_enum in category:
            models.append(model_enum.value)
    return models


def get_models_by_category(category: ModelCategory) -> List[AIModel]:
    """Get all models in a specific category"""
    return [model for model in get_all_models() if model.category == category]


def get_models_by_class(model_class: ModelClass) -> List[AIModel]:
    """Get all models of a specific class (Standard or Generative)"""
    return [model for model in get_all_models() if model.model_class == model_class]


def find_model_by_name(name: str) -> Optional[AIModel]:
    """Find a model by its name"""
    for model in get_all_models():
        if model.name == name:
            return model
    return None