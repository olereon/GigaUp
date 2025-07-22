# GigaUp Models and Parameters Reference

This document provides a comprehensive list of all AI models available in GigaUp and their respective parameters for use in JSON configuration files.

## Table of Contents
- [Model Categories](#model-categories)
- [Enhance Models](#enhance-models)
- [Sharpen Models](#sharpen-models)
- [Denoise Models](#denoise-models)
- [Restore Models](#restore-models)
- [Lighting Models](#lighting-models)
- [Common Parameters](#common-parameters)
- [JSON Configuration Examples](#json-configuration-examples)

## Model Categories

GigaUp supports five main categories of AI models:

1. **Enhance** - General image enhancement and upscaling
2. **Sharpen** - Blur correction and sharpening
3. **Denoise** - Noise reduction for low-light images
4. **Restore** - Damage repair for old/damaged photos
5. **Lighting** - Exposure and color correction

## Enhance Models

### Standard Models

#### `standard_v2`
Standard AI model for general image enhancement.

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

#### `high_fidelity_v2`
High fidelity model for maximum detail preservation.

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

#### `low_resolution_v2`
Optimized for low resolution source images.

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

#### `text_refine`
Specialized for images containing text and shapes.

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

#### `cgi`
Optimized for art and computer-generated imagery.

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

### Generative Models

#### `recover`
Advanced recovery model with version selection.

**Parameters:**
- `version` (string): "v1" or "v2", default: "v2"
- `detail` (int): 0-100, default: 50
- `face_recovery` (bool): true/false, default: false

#### `redefine_realistic`
Realistic enhancement with subtle improvements.

**Parameters:**
- `enhancement` (string): "None" or "Subtle", default: "None"
- `face_recovery` (bool): true/false, default: false

#### `redefine_creative`
Creative enhancement with AI-generated details.

**Parameters:**
- `creativity` (string): "Low", "Medium", "High", or "Max", default: "Medium"
- `prompt` (string): Text description to guide enhancement (optional)
- `texture` (int): 1-5, default: 1
- `face_recovery` (bool): true/false, default: false (NOT AVAILABLE FOR THIS MODEL)

## Sharpen Models

All sharpen models share the same parameters:

**Models:**
- `sharpen_standard`
- `sharpen_strong`
- `lens_blur`
- `lens_blur_v2`
- `motion_blur`
- `natural`
- `refocus`
- `super_focus`
- `super_focus_v2`

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

## Denoise Models

**Models:**
- `denoise_normal`
- `denoise_strong`
- `denoise_extreme`

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

## Restore Models

#### `dust_scratch`
Removes dust and scratches from old photos.

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

## Lighting Models

**Models:**
- `lighting_adjust`
- `white_balance`

**Parameters:**
- `sharpen` (int): 0-100, default: 1
- `denoise` (int): 0-100, default: 1
- `fix_compression` (int): 0-100, default: 1
- `face_recovery` (bool): true/false, default: false

## Common Parameters

### Scale Options
The `scale` parameter can be:
- Standard scales: `"1x"`, `"2x"`, `"4x"`, `"6x"`
- Custom scales: `"1.5"`, `"3.5"`, etc. (as string)
- Width-based: Use `width` parameter instead (e.g., `"width": 2560`)
- Height-based: Use `height` parameter instead (e.g., `"height": 1440`)

### Export Parameters
- `quality` (int): JPEG quality, 1-100, default: 95
- `prefix` (string): Filename prefix, default: ""
- `suffix` (string): 
  - `"0"` - Disable suffix
  - `"1"` - Enable suffix with empty value
  - `"auto"` - Auto-generate suffix from parameters
  - `"custom_text"` - Use custom suffix text

## JSON Configuration Examples

### Example 1: Standard Enhancement
```json
{
  "executable": "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe",
  "input": ["image1.jpg", "image2.jpg"],
  "output": "enhanced_images",
  "model": "standard_v2",
  "scale": "4x",
  "parameters": {
    "sharpen": 25,
    "denoise": 15,
    "face_recovery": true
  },
  "quality": 95,
  "suffix": "auto"
}
```

### Example 2: Creative Enhancement with Prompt
```json
{
  "executable": "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe",
  "input": ["portrait.jpg"],
  "model": "redefine_creative",
  "scale": "2x",
  "parameters": {
    "creativity": "High",
    "prompt": "A professional portrait with enhanced details and vibrant colors",
    "texture": 3,
    "face_recovery": true
  },
  "quality": 98,
  "prefix": "enhanced_",
  "suffix": "auto"
}
```

### Example 3: Photo Restoration
```json
{
  "executable": "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe",
  "input": ["old_photo.jpg"],
  "model": "recover",
  "width": 2560,
  "parameters": {
    "version": "v2",
    "detail": 75,
    "face_recovery": true
  },
  "quality": 90,
  "suffix": "restored"
}
```

### Example 4: Batch Processing with Different Models
```json
{
  "executable": "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe",
  "input": ["blurry1.jpg", "blurry2.jpg", "blurry3.jpg"],
  "output": "sharpened",
  "model": "lens_blur_v2",
  "scale": "2x",
  "parameters": {
    "sharpen": 50,
    "denoise": 20,
    "fix_compression": 30
  },
  "quality": 95,
  "suffix": "auto",
  "continue_on_error": true
}
```

### Example 5: High Fidelity Enhancement
```json
{
  "executable": "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe",
  "input": ["landscape.jpg"],
  "model": "high_fidelity_v2",
  "scale": "6x",
  "parameters": {
    "sharpen": 35,
    "denoise": 10,
    "fix_compression": 15,
    "face_recovery": false
  },
  "quality": 100,
  "suffix": "auto"
}
```

## Auto Suffix Generation

When `suffix` is set to `"auto"`, the following format is used:
- `{scale}-{model}-{parameters}`

Examples:
- `2x-sd-sp25-fr` (2x scale, standard model, sharpen 25, face recovery)
- `h2560-rc-hi3` (height 2560, redefine creative, high creativity, texture 3)
- `4x-hf-sp35-dn10` (4x scale, high fidelity, sharpen 35, denoise 10)

**Note**: The prompt parameter is NOT included in the auto-generated suffix.

## Model Abbreviations in Auto Suffix

- `sd` - standard_v2
- `hf` - high_fidelity_v2
- `lr` - low_resolution_v2
- `ts` - text_refine
- `ac` - cgi (art & CG)
- `rv` - recover
- `rr` - redefine_realistic
- `rc` - redefine_creative
- `sp` - sharpen (various)
- `lb` - lens_blur
- `mb` - motion_blur
- `nt` - natural
- `rf` - refocus
- `sf` - super_focus
- `dn` - denoise_normal
- `dns` - denoise_strong
- `dne` - denoise_extreme
- `ds` - dust_scratch
- `la` - lighting_adjust
- `wb` - white_balance

## Parameter Abbreviations in Auto Suffix

- `sp{n}` - sharpen value (e.g., sp25)
- `dn{n}` - denoise value (e.g., dn15)
- `fc{n}` - fix_compression value (e.g., fc20)
- `fr` - face_recovery enabled
- `lo` - Low creativity
- `md` - Medium creativity
- `hi` - High creativity
- `mx` - Max creativity
- `nn` - None enhancement
- `st` - Subtle enhancement
- `v1`/`v2` - version selection
- `d{n}` - detail value (e.g., d75)
- `q{n}` - quality (if not 95)