# New Features in GigaUp v2

## Performance Optimizations

All wait times have been reduced from 1-4 seconds to 0.1-0.3 seconds for faster processing:
- Window focus wait: 0.2s (was 1.5s)
- Dialog opening: 0.3s (was 2.0s)
- File loading: 0.5s (was 4.0s)
- UI interactions: 0.1s (was 0.2-0.5s)

This results in significantly faster batch processing, especially when handling many files.

## JSON Configuration Support

You can now use a JSON configuration file to specify all parameters:

```bash
gigapixel-cli --json config.json
```

### Sample JSON Configuration

```json
{
  "executable": "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe",
  "input": ["image1.jpg", "image2.png"],
  "output": "output_folder",
  "model": "redefine_creative",
  "scale": "4x",
  "parameters": {
    "creativity": "High",
    "prompt": "A beautiful landscape with vivid colors",
    "texture": 3
  },
  "quality": 95,
  "prefix": "enhanced_",
  "suffix": "auto",
  "continue_on_error": true,
  "timeout": 900
}
```

### JSON Fields

- `executable`: Path to Topaz Gigapixel AI executable
- `input`: Single file path or array of file paths
- `output`: Output directory (optional)
- `model`: AI model name
- `scale`: Scale factor (e.g., "2x", "4x", "6x", or custom like "3.5")
- `width`: Target width in pixels (alternative to scale)
- `height`: Target height in pixels (alternative to scale)
- `parameters`: Model-specific parameters as an object
- `quality`: JPEG quality 1-100 (default: 95)
- `prefix`: Filename prefix
- `suffix`: Filename suffix ("0", "1", "auto", or custom string)
- `preset`: Use a saved preset name
- `continue_on_error`: Continue if a file fails (default: true)
- `timeout`: Processing timeout in seconds (default: 900)
- `preset_mode`: Enable preset mode (see below)

## Preset Mode

Preset mode allows minimal intervention processing using Gigapixel's saved settings:

```bash
# Command line
gigapixel-cli input.jpg -e "path/to/exe" --preset-mode

# With prompt for Redefine models
gigapixel-cli input.jpg -e "path/to/exe" --preset-mode --json preset_config.json
```

### Preset Mode JSON Configuration

```json
{
  "executable": "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe",
  "input": ["image1.jpg", "image2.png", "image3.jpg"],
  "preset_mode": true,
  "prompt": "Enhance the details and colors naturally"
}
```

In preset mode:
- The application uses whatever settings were last used in Gigapixel
- Only the file is opened and processed with existing settings
- If a prompt is provided, it will be set for Redefine models
- No other parameters are changed

## Export Parameters

You can now control export dialog parameters:

```python
# In Python
gigapixel.set_export_parameters(quality=90, prefix="IMG_", suffix="enhanced")

# In CLI via arguments
gigapixel-cli input.jpg -e exe_path -q 90 --prefix "IMG_" --suffix "enhanced"
```

### Export Parameters

- **Quality**: JPEG quality from 1-100
- **Prefix**: Text added before the filename
- **Suffix**: 
  - `"0"` - Turn off suffix checkbox
  - `"1"` - Turn on suffix checkbox
  - `"auto"` - Generate suffix from parameters
  - `"custom string"` - Use custom suffix with checkbox off

## Usage Examples

### Basic JSON Config
```bash
gigapixel-cli --json batch_config.json
```

### Preset Mode for Quick Processing
```bash
# Process single file with current Gigapixel settings
gigapixel-cli photo.jpg -e "C:\\Path\\To\\Gigapixel.exe" --preset-mode

# Process multiple files from JSON
gigapixel-cli --json preset_batch.json
```

### Mixed Mode (JSON + Command Line)
```bash
# JSON provides base config, command line overrides model
gigapixel-cli --json config.json -m standard_v2
```

### Batch Processing with Custom Export
```bash
gigapixel-cli *.jpg -e exe_path -m high_fidelity_v2 -s 4x -q 100 --prefix "HQ_" --suffix "auto"
```

## Benefits

1. **Faster Processing**: Reduced wait times mean batch processing completes much faster
2. **Automation-Friendly**: JSON configs can be generated programmatically
3. **Preset Mode**: Quick processing without parameter setup
4. **Export Control**: Full control over output naming and quality
5. **Flexible Integration**: Mix JSON configs with command-line arguments