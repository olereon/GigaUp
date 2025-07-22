<h1 align="center">
  <br>
  <img src="logo.png" alt="Gigapixel" height="260">
  <br>
  Gigapixel
  <br>
</h1>

<h4 align="center">Advanced Topaz Gigapixel AI automation tool with GUI and CLI interfaces</h4>

<p align="center">
    <img src="https://img.shields.io/pypi/v/gigapixel?style=for-the-badge" alt="PyPI">
    <img src="https://img.shields.io/pypi/pyversions/gigapixel?style=for-the-badge" alt="Python 3">
    <img src="https://img.shields.io/github/actions/workflow/status/TimNekk/Gigapixel/tests.yml?branch=main&label=TESTS&style=for-the-badge" alt="Tests">
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#requirements">Requirements</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

## Features

### Core Functionality
🎨 **Comprehensive Model Support**: All AI model categories (Enhance, Sharpen, Denoise, Restore, Lighting)  
🖥️ **Desktop GUI**: Intuitive interface with collapsible sections and tooltips  
⚡ **Command Line Interface**: Full-featured CLI for automation and scripting  
📦 **Intelligent Batch Processing**: Smart completion detection with auto-close functionality  
🎛️ **Advanced Parameters**: Fine-tune all model parameters with validation  
💾 **Preset Management**: Save and load processing configurations  
🔄 **Legacy Compatible**: Backward compatibility with v1.x API  
📊 **Progress Tracking**: Real-time progress with detailed logging  
🔔 **Notifications**: Audio and visual completion alerts

### Latest Improvements ✨
⚡ **Value Verification System**: Skips unchanged parameters for 40-60% faster processing  
🎯 **Smart Window Detection**: Robust UI automation with multi-monitor support  
🤖 **Auto-Completion**: Automatically closes processing windows when batch completes  
📁 **Guaranteed File Naming**: Suffix format ensures proper file delineation (e.g., `image-3x-rc-hi2.jpg`)  
🛡️ **Production Ready**: Clean, optimized codebase with comprehensive error handling  
🔧 **Enhanced Reliability**: Advanced fallback strategies for all UI operations

## Requirements

- **Windows 10/11** (required for Topaz Gigapixel AI automation)
- **Python 3.6+**
- [Topaz Gigapixel AI](https://www.topazlabs.com/gigapixel-ai) **v7.2.3+** installed

## Installation

### Option 1: PyPI Installation (Recommended)
```bash
# Basic installation
pip install gigapixel

# With GUI support (recommended)
pip install "gigapixel[gui]"
```

### Option 2: Development Installation
```bash
git clone https://github.com/olereon/GigaUp.git
cd GigaUp
pip install pywinauto clipboard loguru the-retry plyer

# Run without installation
python run_gui.py          # GUI application
python run_cli.py --help   # CLI interface
```

## Usage

### Desktop GUI Application
```bash
# Launch the GUI
gigapixel

# Features:
# - Visual model selection with tooltips
# - Batch processing with progress tracking
# - Parameter fine-tuning with validation
# - Preset management
# - Real-time logging with collapsible viewer
```

### Command Line Interface
```bash
# Basic usage
gigapixel-cli input.jpg -e "C:\Program Files\Topaz Labs LLC\Topaz Gigapixel AI\Topaz Gigapixel AI.exe" -m standard_v2 -s 4x

# Advanced usage with parameters
gigapixel-cli input.jpg -e path/to/exe -m redefine -p '{"creativity": 3, "texture": 2}' -s 6x

# Batch processing
gigapixel-cli folder/ -e path/to/exe -m high_fidelity_v2 -o output_folder/

# Using presets
gigapixel-cli input.jpg -e path/to/exe --preset "my_favorite_settings"

# List available models
gigapixel-cli --list-models
```

### Python API

#### Legacy API (v1.x Compatible)
```python
from gigapixel import Gigapixel, Scale, Mode

gp = Gigapixel(r"C:\Program Files\Topaz Labs LLC\Topaz Gigapixel AI\Topaz Gigapixel AI.exe")
gp.process(r"path\to\image.jpg", scale=Scale.X2, mode=Mode.HIGH_FIDELITY)
```

#### Advanced API (v2.x)
```python
from gigapixel import Gigapixel, get_model_factory

# Initialize
gp = Gigapixel(exe_path)
factory = get_model_factory()

# Create processing parameters
params = factory.create_processing_parameters(
    "redefine", 
    {"creativity": 4, "texture": 2}, 
    "4x"
)

# Process single image
gp.process_with_model("image.jpg", params)

# Batch processing
from gigapixel import ProcessingJob
from pathlib import Path

jobs = [
    ProcessingJob(Path("img1.jpg"), Path("output/enhanced_img1.jpg"), params),
    ProcessingJob(Path("img2.jpg"), Path("output/enhanced_img2.jpg"), params)
]
gp.process_batch(jobs)
```

### Available AI Models
- **Enhance**: Standard V2, Low Resolution V2, CGI, High Fidelity V2, Text Refine, Redefine, Recovery, Recovery V2
- **Sharpen**: Standard, Strong, Lens Blur, Lens Blur V2, Motion Blur, Natural, Refocus, Super Focus, Super Focus V2  
- **Denoise**: Normal, Strong, Extreme
- **Restore**: Dust-Scratch
- **Lighting**: Adjust, White Balance


## Contributing

Bug reports and/or pull requests are welcome


## License

The module is available as open source under the terms of the [Apache License, Version 2.0](https://opensource.org/licenses/Apache-2.0)
