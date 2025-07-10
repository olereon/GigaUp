#!/usr/bin/env python3
"""
Development launcher for GigaUp CLI
This script allows running the CLI without installation issues
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Try to import and run the CLI
    from gigapixel.cli import main
    print("Starting GigaUp CLI...")
    main()
except ImportError as e:
    print(f"Import Error: {e}")
    print("\nThis appears to be a Linux/non-Windows environment.")
    print("GigaUp is designed for Windows and requires Windows-specific modules.")
    print("\nTo run on Windows:")
    print("1. Install Python 3.6+ on Windows")
    print("2. Install dependencies: pip install pywinauto clipboard loguru the-retry")
    print("3. Run: python run_cli.py [arguments]")
    print("\nFor CLI help: python run_cli.py --help")
    sys.exit(1)
except Exception as e:
    print(f"Error starting CLI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)