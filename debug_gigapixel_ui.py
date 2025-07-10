#!/usr/bin/env python3
"""
Debug tool for inspecting Gigapixel AI UI elements
This helps identify the exact names of buttons and controls
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gigapixel import Gigapixel

def debug_ui_elements(exe_path):
    """Debug UI elements in Gigapixel AI"""
    
    try:
        print("Connecting to Gigapixel AI...")
        gp = Gigapixel(exe_path)
        
        print("\nPrinting all UI control identifiers...")
        print("=" * 60)
        
        # This will print all available UI elements
        gp._app._print_elements()
        
        print("=" * 60)
        print("Debug completed. Check the output above to see available UI elements.")
        print("Look for buttons that might correspond to modes and scales.")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Topaz Gigapixel AI is installed")
        print("2. The executable path is correct")
        print("3. The application can be launched")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_gigapixel_ui.py <path_to_gigapixel_exe>")
        print('Example: python debug_gigapixel_ui.py "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe"')
        sys.exit(1)
    
    exe_path = sys.argv[1]
    debug_ui_elements(exe_path)