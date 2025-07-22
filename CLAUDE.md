# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Guidelines

### Git Commit Guidelines
- Make new git commits only when prompted by the user or after major code changes, such as, added new feature or verified fix of a serious bug.

### UI Automation Guidelines
- Always consider types of the controls and their relative position against other UI controls
- Many interactive controls do not have a TITLE or their TITLE is matching their current value
- When designing search methods for controls, use position-based detection when titles are unreliable
- Verify current values before setting new ones to avoid unnecessary operations

## Project Overview

GigaUp (published as "gigapixel" on PyPI) is a comprehensive Python automation library and desktop application for Topaz Gigapixel AI. Version 2.0 provides both programmatic control and a user-friendly GUI for automating image upscaling tasks with support for all the latest AI models and advanced features.

### Recent Major Improvements (v2.0+)

#### Performance Optimizations
- **Value Verification System**: Comprehensive parameter checking to skip unchanged values across all UI controls
- **Processing Completion Detection**: Intelligent window monitoring for last file in batch with auto-completion
- **Reduced Processing Overhead**: Wait times optimized from 1-4 seconds to 0.1-0.3 seconds
- **Batch Export Optimization**: Single batch operation instead of individual file processing
- **Code Cleanup**: Removed over 1,100 lines of debug code for improved performance

#### Enhanced UI Automation
- **Robust Window Detection**: Image file extension-based window search with file sequence tracking
- **Position-based Control Detection**: Reliable field identification using spatial relationships
- **Export Dialog Detection**: Uses "Export settings" text for reliable dialog identification
- **Smart Parameter Discovery**: Button-reference alignment for multi-monitor compatibility
- **Comprehensive Value Verification**: All controls (scale, dimensions, parameters, text fields) check current values
- **Error Recovery**: Graceful fallback strategies for UI element detection failures

#### Advanced Batch Processing
- **Intelligent Completion Tracking**: Waits for last file in batch before checking completion buttons
- **Batch Export Detection**: Prevents redundant individual processing after batch completion
- **Window State Management**: Robust handling of changing window titles during processing
- **Auto-Close Functionality**: Automatically clicks "Close window" when processing completes

#### Enhanced Features
- **Auto Suffix Generation**: Guaranteed "-" prefix for proper file delineation (e.g., `image-3x-rc-hi2.jpg`)
- **JSON Configuration Support**: Full parameter control with empty path handling
- **Processing Completion Automation**: Automatic "Close window" clicking after batch completion
- **Comprehensive Error Handling**: Improved exception handling with proper error recovery

#### Model Support
- Comprehensive support for all Topaz Gigapixel AI models:
  - Enhance models (Standard, High Fidelity, Low Resolution, Text & Shapes, Art & CG)
  - Generative models (Recover, Redefine Realistic, Redefine Creative)
  - Sharpen models (9 variants including Lens Blur, Motion Blur, Super Focus)
  - Denoise models (Normal, Strong, Extreme)
  - Restore models (Dust & Scratch)
  - Lighting models (Lighting Adjust, White Balance)

See MODELS_REFERENCE.md for complete model documentation.

## Key Implementation Details

### Advanced Control Detection Strategy
The application uses a sophisticated multi-layered detection strategy for UI controls:

1. **Export Dialog Fields** (left panel, x < 3000):
   - Position 0: Prefix field
   - Position 1: Suffix field  
   - Position 2: Quality field
   - **Value verification**: Checks current values before setting to avoid redundant operations

2. **Main Window Parameters**:
   - **Scale factors**: Multiple detection methods with value verification
   - **Dimensions**: Width/height settings with fallback strategies
   - **Model parameters**: Sharpen, denoise, texture, creativity with current value checking
   - **Text fields**: Prompt fields with content verification

3. **Generative Model Parameters**:
   - Prompt field: Large Edit control (400px+) aligned with "Low" button
   - Texture field: Edit control aligned with "Max" button
   - **Smart positioning**: Button-reference alignment for reliable detection

### Enhanced Export Dialog Workflow
1. Opens export dialog with Ctrl+S
2. Detects dialog by finding "Export settings" text
3. **Value-verified parameter setting**: Quality, prefix, suffix with current value checking
4. Sets output path using clipboard paste with error handling
5. Clicks Save button with multiple fallback strategies
6. **Processing completion detection**: Monitors for last file in batch
7. **Auto-completion**: Automatically clicks "Close window" when done

### Batch Processing Intelligence
- **Window monitoring**: Tracks changing window titles during processing
- **Last file detection**: Waits for final file before checking completion
- **Completion button detection**: Finds "Close window" and "Export again" buttons
- **Auto-close functionality**: Clicks appropriate completion button
- **Error recovery**: Handles window detection failures gracefully

### Auto Suffix Generation
- Format: `-{scale}-{model}-{parameters}`
- Example: `-3x-rc-hi2` = 3x scale, redefine creative, high creativity, texture 2
- **Guaranteed dash prefix**: Always starts with "-" for proper file delineation
- **Smart exclusions**: Prompts excluded from auto-generated suffixes

### Value Verification System
- **Universal coverage**: All UI controls check current values before setting
- **Performance optimization**: Skips operations when values already match
- **Comprehensive logging**: Clear indication when values are skipped vs changed
- **Error resilience**: Fallback to setting values if verification fails

### Production-Ready Code Quality
- **Clean codebase**: Removed all debug methods and interactive debugging
- **Streamlined logging**: Essential automation logs without verbose debug output
- **Exception handling**: Robust error recovery with proper error propagation
- **Memory efficiency**: Eliminated debug overhead and unused code paths

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

### UI Automation Best Practices
- **Value Verification First**: Always check current values before setting UI controls
- **Position-based Detection**: Use spatial relationships rather than brittle text matching
- **Graceful Fallbacks**: Implement multiple detection strategies for robustness
- **Window State Awareness**: Handle dynamic window titles and changing UI states
- **Error Recovery**: Provide fallback mechanisms for all UI operations

### Working with AI Models
- All models are defined in `models.py` with comprehensive parameter definitions
- Use the ModelFactory for model instantiation and management
- Validate parameters using the ParameterValidator class
- Support both legacy Mode enum and new model system for backward compatibility
- Implement value verification for all model parameter setting

### Batch Processing Architecture
- **ProcessingJob Management**: Use dataclass for structured job handling
- **Completion Detection**: Monitor window changes to detect processing completion
- **Auto-close Integration**: Implement automatic UI cleanup after processing
- **Error Continuity**: Support continue-on-error semantics for robust operations
- **Progress Tracking**: Comprehensive logging and user feedback systems

### GUI Development Standards
- Use custom widgets from `gui/widgets.py` for consistency
- Implement tooltips for all user-facing controls with 1-2 second delay
- Follow collapsible section pattern for tool organization
- Use threading for background processing to maintain UI responsiveness
- Implement proper progress tracking and user feedback

### Code Quality Standards
- **Production-Ready Code**: Remove all debug methods and interactive debugging
- **Clean Logging**: Use essential automation logs without verbose debug output
- **Exception Handling**: Implement robust error recovery with proper propagation
- **Performance Optimization**: Eliminate unnecessary operations through value verification
- **Memory Efficiency**: Remove debug overhead and unused code paths

### Parameter Management
- Use ProcessingParameters for type-safe parameter handling
- Implement comprehensive value verification before setting
- Support preset save/load functionality with validation
- Maintain backward compatibility with legacy Scale/Mode enums
- Handle empty configurations with intelligent defaults

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

# JSON configuration
gigapixel-cli --json config.json
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

### Code Quality Standards
- **Static Analysis**: Comprehensive flake8 and mypy checking with zero errors
- **Type Safety**: Full type hints throughout codebase for IDE support and validation
- **Clean Architecture**: Production-ready code with all debug artifacts removed
- **Exception Handling**: Robust error recovery with custom exception hierarchy
- **Performance Optimization**: Value verification system reduces unnecessary operations

### Automation Reliability
- **UI Automation Testing**: Comprehensive testing of control detection strategies
- **Batch Processing Validation**: End-to-end testing of completion detection
- **Error Recovery Testing**: Validation of fallback mechanisms and error handling
- **Parameter Validation**: Prevents invalid configurations with comprehensive validation
- **Cross-monitor Compatibility**: Testing on different screen configurations

### Logging and Debugging
- **Production Logging**: Essential automation logs without debug verbosity
- **Error Tracking**: Comprehensive error reporting with actionable information
- **Performance Monitoring**: Value verification skip/change tracking
- **UI State Logging**: Window detection and control interaction logging

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

## Recent Major Updates (Latest)

### Performance & Reliability Improvements
- **Value Verification System**: Added comprehensive current value checking across all UI controls
- **Processing Completion Automation**: Intelligent last-file detection with automatic window closing
- **Batch Processing Optimization**: Enhanced to prevent redundant operations and handle dynamic window states
- **Code Quality Cleanup**: Removed 1,100+ lines of debug code for production-ready performance

### Enhanced Automation Features
- **Intelligent Window Detection**: Image extension-based window search with file sequence tracking
- **Auto-Close Functionality**: Automatic "Close window" clicking when batch processing completes
- **Robust Error Recovery**: Comprehensive fallback strategies for all UI automation operations
- **Cross-Monitor Compatibility**: Improved control detection for multi-monitor setups

### File Naming & Configuration
- **Guaranteed Suffix Format**: All auto-generated suffixes start with "-" for proper file delineation
- **Empty Path Handling**: Intelligent defaults when output directories are not specified
- **JSON Configuration**: Enhanced support with validation and error handling

These improvements make GigaUp significantly more reliable, faster, and production-ready while maintaining full backward compatibility with existing workflows.