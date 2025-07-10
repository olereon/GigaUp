# GigaUp Installation Guide

## Platform Requirements

**GigaUp v2.0 is designed specifically for Windows** as it automates the Windows desktop application "Topaz Gigapixel AI" using Windows-specific GUI automation libraries.

## Windows Installation

### Prerequisites
1. **Windows 10/11** (required for Topaz Gigapixel AI)
2. **Python 3.6+** installed on Windows
3. **Topaz Gigapixel AI** application installed

### Installation Steps

#### Option 1: From PyPI (Recommended for Users)
```bash
# Basic installation
pip install gigapixel

# With GUI support (recommended)
pip install "gigapixel[gui]"
```

#### Option 2: Development Installation
```bash
# Clone the repository
git clone https://github.com/olereon/GigaUp.git
cd GigaUp

# Install dependencies
pip install pywinauto clipboard loguru the-retry plyer

# Run directly (no installation required)
python run_gui.py
# or
python run_cli.py --help
```

### Usage on Windows

#### GUI Application
```bash
# Launch GUI (default)
gigapixel

# Or explicitly
gigapixel-gui
```

#### Command Line Interface
```bash
# Basic usage
gigapixel-cli input.jpg -e "C:\Program Files\Topaz Labs LLC\Topaz Gigapixel AI\Topaz Gigapixel AI.exe" -m standard_v2 -s 4x

# With custom parameters
gigapixel-cli input.jpg -e path/to/exe -m redefine -p '{"creativity": 3, "texture": 2}'

# Using presets
gigapixel-cli input.jpg -e path/to/exe --preset "my_preset"

# Get help
gigapixel-cli --help
```

## Linux/WSL Development

If you're developing on Linux/WSL (like your current environment), you have several options:

### Option 1: Windows VM (Recommended for Full Testing)
1. Set up a Windows VM with VirtualBox/VMware
2. Install Topaz Gigapixel AI in the VM
3. Test the complete automation workflow

### Option 2: Wine (Limited Support)
```bash
# Install Wine
sudo apt update
sudo apt install wine

# Install Windows Python via Wine
# (This is complex and may not work perfectly)
```

### Option 3: Development with Mock Mode (UI Testing Only)
```bash
# Install GUI dependencies only
pip install tkinter plyer

# Run the mock version (GUI only, no actual processing)
python run_gui_mock.py
```

## Troubleshooting

### Permission Errors
If you get permission errors during installation:
```bash
# Use user installation
pip install --user "gigapixel[gui]"

# Or use virtual environment
python -m venv gigapixel_env
source gigapixel_env/bin/activate  # Linux/Mac
# or
gigapixel_env\Scripts\activate     # Windows
pip install "gigapixel[gui]"
```

### Module Not Found Errors
If you get "No module named 'win32api'" on Linux:
- This is expected - the module is Windows-only
- Use the development launchers or mock mode for GUI testing
- For full functionality, use Windows environment

### Topaz Gigapixel AI Not Found
1. Ensure Topaz Gigapixel AI is installed
2. Note the exact installation path
3. Use the full path in the executable parameter:
   ```
   -e "C:\Program Files\Topaz Labs LLC\Topaz Gigapixel AI\Topaz Gigapixel AI.exe"
   ```

## Architecture Notes

- **Core Logic**: Cross-platform (models, parameters, factory patterns)
- **GUI Interface**: Cross-platform (tkinter-based)
- **Automation Engine**: Windows-only (pywinauto + Windows API)
- **CLI Interface**: Cross-platform structure, Windows-only execution

## Development Environment Setup

For development on Linux/WSL while targeting Windows:

1. **Code Development**: Full development possible on Linux
2. **GUI Testing**: Use mock mode on Linux
3. **Automation Testing**: Requires Windows environment
4. **Integration Testing**: Windows VM or dual-boot recommended

## Support

- **GitHub Issues**: Report bugs and feature requests
- **Platform**: Windows 10/11 required for full functionality
- **Dependencies**: Automatically managed via pip
- **Documentation**: See CLAUDE.md for development guidelines