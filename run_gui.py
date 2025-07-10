#!/usr/bin/env python3
"""
Development launcher for GigaUp GUI
This script allows running the GUI without installation issues
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Try to import and run the GUI
    from gigapixel.gui.main_window import main
    print("Starting GigaUp GUI...")
    main()
except ImportError as e:
    print(f"Import Error: {e}")
    print("\nThis appears to be a Linux/non-Windows environment.")
    print("GigaUp is designed for Windows and requires Windows-specific modules.")
    print("\nTo run on Windows:")
    print("1. Install Python 3.6+ on Windows")
    print("2. Install dependencies: pip install pywinauto clipboard loguru the-retry plyer")
    print("3. Run: python run_gui.py")
    print("\nFor development/testing on Linux, you could:")
    print("1. Use a Windows VM")
    print("2. Use Wine with Windows Python")
    print("3. Mock the Windows modules for GUI development")
    sys.exit(1)
except Exception as e:
    print(f"Error starting GUI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)