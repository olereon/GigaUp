#!/usr/bin/env python3
"""
Interactive test for setting custom scale factor in Topaz Gigapixel AI.
This script will try each input field and ask for confirmation.
"""

import sys
from pathlib import Path
from loguru import logger
from pywinauto import Application
from pywinauto.keyboard import send_keys
import time

def test_scale_input_interactive(exe_path: str, scale_value: str):
    """Test scale input with user confirmation for each field"""
    try:
        # Launch Gigapixel
        print("Launching Topaz Gigapixel AI...")
        app = Application(backend='uia').start(exe_path)
        time.sleep(5)  # Wait for app to fully load
        
        # Get the main window
        main_window = app.window(title_re=".*Topaz Gigapixel AI.*")
        main_window.wait('ready', timeout=10)
        print("✓ Gigapixel AI is ready")
        
        # Find all Edit controls
        print("\nSearching for all input fields...")
        all_edits = main_window.descendants(control_type="Edit")
        print(f"Found {len(all_edits)} input fields")
        
        # Test each edit control
        for i, edit in enumerate(all_edits):
            try:
                print(f"\n{'='*60}")
                print(f"Testing input field {i+1} of {len(all_edits)}")
                print(f"{'='*60}")
                
                # Get info about this edit control
                rect = edit.rectangle()
                current_value = ""
                try:
                    current_value = edit.get_value()
                except:
                    pass
                
                print(f"Position: ({rect.left}, {rect.top})")
                print(f"Current value: '{current_value}'")
                
                # Click the field
                print("\nClicking this input field...")
                edit.click_input()
                time.sleep(0.5)
                
                # Clear and set the scale value
                print(f"Setting value to {scale_value}...")
                send_keys('^a')  # Select all
                time.sleep(0.2)
                send_keys(scale_value)
                time.sleep(0.5)
                
                # Show the new value
                try:
                    new_value = edit.get_value()
                    print(f"New value: '{new_value}'")
                except:
                    print("Could not read new value")
                
                # Ask for confirmation
                print("\n*** Is this the Scale factor input field? (y/n) ***")
                response = input("Your answer: ").strip().lower()
                
                if response == 'y':
                    print("\n✓ SUCCESS! Scale factor input field identified!")
                    print(f"Field #{i+1} is the correct one")
                    
                    # Press Enter to confirm the value
                    send_keys('{ENTER}')
                    print(f"✓ Scale set to {scale_value}")
                    
                    # Save this information
                    print("\nField identification info:")
                    print(f"- Field index: {i}")
                    print(f"- Position: ({rect.left}, {rect.top})")
                    print(f"- Initial value: '{current_value}'")
                    
                    return True
                else:
                    print("Moving to next field...")
                    # Reset the field
                    try:
                        send_keys('^a')
                        send_keys(current_value if current_value else '1')
                    except:
                        pass
                    
            except Exception as e:
                print(f"Error with this field: {e}")
                continue
        
        print("\n✗ No more fields to test. Scale factor input not found.")
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        print("\nPress Enter to close Gigapixel...")
        input()
        try:
            app.kill()
        except:
            pass

def main():
    if len(sys.argv) < 3:
        print("Usage: python interactive_scale_test.py <gigapixel_exe_path> <scale_value>")
        print("Example: python interactive_scale_test.py \"C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe\" 1.5")
        sys.exit(1)
    
    exe_path = sys.argv[1]
    scale_value = sys.argv[2]
    
    print(f"Interactive Scale Factor Test")
    print(f"Scale value to set: {scale_value}")
    print(f"Executable: {exe_path}")
    print()
    
    test_scale_input_interactive(exe_path, scale_value)

if __name__ == "__main__":
    main()