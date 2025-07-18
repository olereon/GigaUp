#!/usr/bin/env python3
"""
Debug script to inspect Gigapixel AI UI elements
Helps identify correct element names and control types
"""

import sys
import time
from pathlib import Path
from pywinauto import Application
from loguru import logger


def find_gigapixel_window(exe_path: str):
    """Find and connect to Gigapixel window"""
    try:
        # Try to connect to existing instance
        app = Application(backend="uia").connect(path=exe_path)
        logger.info("Connected to existing Gigapixel instance")
        return app
    except:
        # Start new instance
        logger.info("Starting new Gigapixel instance...")
        app = Application(backend="uia").start(exe_path)
        time.sleep(5)  # Wait for startup
        return app


def print_all_elements(window, indent=0):
    """Recursively print all UI elements"""
    prefix = "  " * indent
    try:
        info = window.element_info
        print(f"{prefix}Title: '{info.name}' | Type: {info.control_type} | Visible: {info.visible}")
        
        # Print children
        for child in window.children():
            print_all_elements(child, indent + 1)
    except Exception as e:
        print(f"{prefix}Error reading element: {e}")


def analyze_ui_state(app):
    """Analyze current UI state"""
    main_window = app.window(title_re=".*Gigapixel.*")
    
    print("\n" + "="*80)
    print("MAIN WINDOW ANALYSIS")
    print("="*80)
    
    # Window info
    print(f"Window Title: {main_window.element_info.name}")
    print(f"Window Class: {main_window.element_info.class_name}")
    print(f"Window Handle: {main_window.element_info.handle}")
    
    # Look for key elements
    print("\n" + "-"*40)
    print("KEY UI ELEMENTS")
    print("-"*40)
    
    # Browse Images button (initial state)
    try:
        browse_btn = main_window.child_window(title="Browse Images", control_type="Button")
        print("✓ Found 'Browse Images' button - App is in initial state (no image loaded)")
    except:
        print("✗ 'Browse Images' button not found - Image may be loaded")
    
    # Check for scale buttons
    scale_found = False
    for scale in ["1x", "2x", "4x", "6x"]:
        try:
            scale_btn = main_window.child_window(title=scale)
            print(f"✓ Found '{scale}' button")
            scale_found = True
        except:
            pass
    
    if not scale_found:
        print("✗ No scale buttons found")
    
    # Check for mode buttons
    print("\n" + "-"*40)
    print("MODE/MODEL BUTTONS")
    print("-"*40)
    
    modes_to_check = [
        "Standard", "High fidelity", "Low res", "Text & shapes", "Art & CG", "Recovery",
        "Standard v2", "High Fidelity", "Low resolution", "Text", "CGI", "Face Recovery"
    ]
    
    for mode in modes_to_check:
        for control_type in ["Button", "RadioButton", None]:
            try:
                if control_type:
                    btn = main_window.child_window(title=mode, control_type=control_type)
                else:
                    btn = main_window.child_window(title=mode)
                print(f"✓ Found '{mode}' as {control_type or 'Any'}")
                break
            except:
                pass
    
    # Print all controls
    print("\n" + "-"*40)
    print("ALL CONTROLS (simplified)")
    print("-"*40)
    
    try:
        main_window.print_control_identifiers(filename=None)
    except Exception as e:
        print(f"Error printing controls: {e}")
    
    # Try hierarchical view
    print("\n" + "-"*40)
    print("HIERARCHICAL VIEW (top 3 levels)")
    print("-"*40)
    
    try:
        print_all_elements(main_window, indent=0)
    except Exception as e:
        print(f"Error in hierarchical view: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_ui_elements.py <path_to_gigapixel.exe>")
        sys.exit(1)
    
    exe_path = sys.argv[1]
    
    if not Path(exe_path).exists():
        print(f"Error: Gigapixel executable not found at: {exe_path}")
        sys.exit(1)
    
    print(f"Debugging Gigapixel UI at: {exe_path}")
    
    try:
        app = find_gigapixel_window(exe_path)
        analyze_ui_state(app)
        
        print("\n" + "="*80)
        print("DEBUG COMPLETE")
        print("="*80)
        print("\nThis output shows the current UI elements available for automation.")
        print("Use these element names and control types in the main script.")
        
    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()