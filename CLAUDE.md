# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GigaUp (published as "gigapixel" on PyPI) is a comprehensive Python automation library and desktop application for Topaz Gigapixel AI. Version 2.0 provides both programmatic control and a user-friendly GUI for automating image upscaling tasks with support for all the latest AI models and advanced features.

## Development Commands

### Linting and Type Checking
```bash
# Run all checks via tox
tox

# Run specific checks
tox -e flake8  # Linting only
tox -e mypy    # Type checking only

# Direct commands
flake8 gigapixel
mypy gigapixel --install-types --non-interactive --ignore-missing-imports
```

### Installation and Usage

**Platform Note**: GigaUp requires Windows for full functionality as it automates the Windows-only Topaz Gigapixel AI application.

#### Windows Installation
```bash
# Install from PyPI with GUI support (recommended)
pip install "gigapixel[gui]"

# Launch GUI application
gigapixel
# or
gigapixel-gui

# Use CLI interface
gigapixel-cli --help
```

#### Development Installation (any platform)
```bash
# Clone and install dependencies
git clone https://github.com/olereon/GigaUp.git
cd GigaUp
pip install pywinauto clipboard loguru the-retry plyer

# Windows: Run normally
python run_gui.py

# Linux/WSL: Run mock mode for GUI testing
python run_gui_mock.py
```

## Enhanced Architecture (v2.0)

The codebase has been significantly extended with a modular architecture:

### Core Components
- **gigapixel/gigapixel.py**: Enhanced `Gigapixel` class with advanced model support, batch processing, and callback system
- **gigapixel/models.py**: Comprehensive AI model definitions for all Topaz Gigapixel AI categories (Enhance, Sharpen, Denoise, Restore, Lighting)
- **gigapixel/parameters.py**: Dynamic parameter system with validation, conversion, and persistence
- **gigapixel/factory.py**: Model factory pattern with builder and validator classes
- **gigapixel/exceptions.py**: Extended exception hierarchy for new functionality
- **gigapixel/cli.py**: Command-line interface with full feature support
- **gigapixel/gui/**: Complete desktop GUI implementation

### GUI Components
- **gui/main_window.py**: Main tkinter application with collapsible sections, tooltips, and batch processing
- **gui/widgets.py**: Custom widgets (CollapsibleFrame, ToolTip, ParameterWidget, ProgressFrame, LogViewer)
- **gui/utils.py**: Utility functions for GUI operations, notifications, and background tasks

### Key Architectural Patterns
- **Factory Pattern**: ModelFactory for creating and managing AI models
- **Builder Pattern**: ParameterBuilder and ModelBuilder for fluent configuration
- **Observer Pattern**: ProcessingCallback system for event handling
- **Facade Pattern**: Simplified API while hiding internal complexity
- **Strategy Pattern**: Different processing strategies for Standard vs Generative models

## AI Model System

### Model Categories
1. **Enhance** (Standard & Generative): General upscaling and enhancement
2. **Sharpen** (Standard & Generative): Blur correction and sharpening
3. **Denoise**: Noise reduction for low-light images
4. **Restore**: Damage repair for old/damaged photos
5. **Lighting**: Exposure and color correction

### Model Selection
```python
# Get model factory
factory = get_model_factory()

# List models by category
enhance_models = factory.get_models_by_category(ModelCategory.ENHANCE)

# Get specific model
model = factory.get_model_by_name("standard_v2")

# Create processing parameters
params = factory.create_processing_parameters(
    "standard_v2", 
    {"sharpen": 0.5, "denoise": 0.3}, 
    "4x"
)
```

## Development Guidelines

### Working with AI Models
- All models are defined in `models.py` with comprehensive parameter definitions
- Use the ModelFactory for model instantiation and management
- Validate parameters using the ParameterValidator class
- Support both legacy Mode enum and new model system for backward compatibility

### GUI Development
- Use custom widgets from `gui/widgets.py` for consistency
- Implement tooltips for all user-facing controls with 1-2 second delay
- Follow collapsible section pattern for tool organization
- Use threading for background processing to keep UI responsive
- Implement proper progress tracking and user feedback

### Batch Processing
- Use ProcessingJob dataclass for job management
- Implement ProcessingCallback for progress updates
- Support continue-on-error semantics for robust batch operations
- Provide comprehensive logging and error reporting

### Parameter Management
- Use ProcessingParameters for type-safe parameter handling
- Support preset save/load functionality
- Implement parameter validation and conversion
- Maintain backward compatibility with legacy Scale/Mode enums

## Entry Points and Compatibility

### Command Line Interface
```bash
# Basic usage
gigapixel-cli input.jpg -e "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe" -m standard_v2 -s 4x

# With parameters
gigapixel-cli input.jpg -e path/to/exe -m redefine -p '{"creativity": 3, "texture": 2}'

# Using presets
gigapixel-cli input.jpg -e path/to/exe --preset "my_preset"

# Legacy mode
gigapixel-cli input.jpg -e path/to/exe --legacy-mode "High fidelity" -s 2x
```

### Programmatic Usage
```python
# Legacy API (still supported)
from gigapixel import Gigapixel, Mode, Scale
gp = Gigapixel(exe_path)
gp.process("image.jpg", scale=Scale.X2, mode=Mode.HIGH_FIDELITY)

# New API with advanced models
from gigapixel import Gigapixel, get_model_factory
gp = Gigapixel(exe_path)
factory = get_model_factory()
params = factory.create_processing_parameters("redefine", {"creativity": 4})
gp.process_with_model("image.jpg", params)

# Batch processing
jobs = [ProcessingJob(input_path=Path(f), parameters=params) for f in files]
gp.process_batch(jobs)
```

## Important Constraints

1. **Windows-only**: Uses pywinauto for Windows GUI automation
2. **Python 3.6+**: Supports Python 3.6 through 3.13
3. **Flake8 config**: Max line length is 160 characters
4. **GUI Framework**: Uses tkinter for cross-platform compatibility
5. **Model Automation**: Simplified UI automation maps new models to existing Gigapixel UI elements
6. **Threading**: GUI uses background threads for processing to maintain responsiveness

## Testing and Quality Assurance

- Static analysis via flake8 and mypy
- Type hints throughout codebase for IDE support
- Comprehensive error handling with custom exceptions
- Extensive logging for debugging automation issues
- Parameter validation prevents invalid configurations

## Configuration and Persistence

- User preferences stored in `~/.gigapixel/`
- Preset management with JSON serialization
- GUI settings persistence (window geometry, executable path)
- Last-used parameters for convenience

## Common Development Tasks

### Adding New AI Models
1. Define model in appropriate enum in `models.py`
2. Add parameter definitions with validation rules
3. Update legacy mapping in `gigapixel.py` if needed
4. Test UI automation for model selection

### Extending Parameter Types
1. Add new parameter type to `ParameterWidget` in `gui/widgets.py`
2. Update validation in `ParameterValidator`
3. Add conversion logic in parameter system

### GUI Enhancements
- Use CollapsibleFrame for new tool sections
- Add tooltips with comprehensive descriptions
- Implement proper progress tracking for long operations
- Follow existing patterns for state management

### CLI Extensions
- Add new arguments to `cli.py` parser
- Implement corresponding functionality
- Update help text and documentation
- Maintain backward compatibility