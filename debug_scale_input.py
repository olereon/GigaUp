#!/usr/bin/env python3
"""
Debug tool to find the Scale factor input field in Topaz Gigapixel AI.
"""

import sys
from pathlib import Path
from loguru import logger
from pywinauto import Application
from pywinauto.timings import TimeoutError
import time

def find_scale_input_field(exe_path: str):
    """Find and test the scale factor input field"""
    try:
        # Launch Gigapixel
        app = Application(backend='uia').start(exe_path)
        time.sleep(5)  # Wait for app to fully load
        
        # Get the main window
        main_window = app.window(title_re=".*Topaz Gigapixel AI.*")
        main_window.wait('ready', timeout=10)
        
        print("\n" + "="*80)
        print("SEARCHING FOR SCALE FACTOR INPUT FIELD")
        print("="*80)
        
        # Method 1: Look for all Edit controls
        print("\n1. Looking for all Edit controls...")
        try:
            all_edits = main_window.descendants(control_type="Edit")
            print(f"Found {len(all_edits)} Edit controls:")
            
            for i, edit in enumerate(all_edits):
                try:
                    rect = edit.rectangle()
                    value = ""
                    try:
                        value = edit.get_value()
                    except:
                        pass
                    
                    print(f"\n  [{i+1}] Edit Control:")
                    print(f"      Position: ({rect.left}, {rect.top})")
                    print(f"      Size: {rect.width()}x{rect.height()}")
                    print(f"      Value: '{value}'")
                    print(f"      Visible: {edit.is_visible()}")
                    print(f"      Enabled: {edit.is_enabled()}")
                except Exception as e:
                    print(f"      Error reading edit control: {e}")
        except Exception as e:
            print(f"Error finding Edit controls: {e}")
        
        # Method 2: Look for Text elements with "Scale factor"
        print("\n2. Looking for 'Scale factor' text element...")
        try:
            all_texts = main_window.descendants(control_type="Text")
            scale_text = None
            
            for text in all_texts:
                try:
                    name = text.element_info.name
                    if name and "Scale factor" in name:
                        scale_text = text
                        rect = text.rectangle()
                        print(f"\nFound 'Scale factor' text at: ({rect.left}, {rect.top})")
                        break
                except:
                    continue
            
            if scale_text:
                # Look for nearby Edit controls
                print("\n3. Looking for Edit controls near 'Scale factor' text...")
                scale_rect = scale_text.rectangle()
                
                for i, edit in enumerate(all_edits):
                    try:
                        edit_rect = edit.rectangle()
                        # Check if edit is to the right of the text (within 200 pixels)
                        if (edit_rect.left > scale_rect.left and 
                            edit_rect.left < scale_rect.left + 200 and
                            abs(edit_rect.top - scale_rect.top) < 50):
                            
                            print(f"\nFound potential scale input field!")
                            print(f"  Position: ({edit_rect.left}, {edit_rect.top})")
                            print(f"  Distance from text: {edit_rect.left - scale_rect.left}px")
                            
                            # Try to interact with it
                            print("\nTesting interaction...")
                            edit.click_input()
                            time.sleep(0.5)
                            
                            # Try to set a value
                            edit.type_keys('^a')  # Select all
                            time.sleep(0.2)
                            edit.type_keys('1.5')
                            time.sleep(0.5)
                            
                            print("✓ Successfully set value to 1.5!")
                            
                            # Show current value
                            try:
                                current = edit.get_value()
                                print(f"Current value: '{current}'")
                            except:
                                print("Could not read current value")
                            
                            return True
                            
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"Error in scale factor search: {e}")
        
        # Method 3: Interactive selection
        print("\n4. Interactive mode - Select the scale input field manually")
        print("-" * 80)
        
        all_elements = []
        try:
            # Get all potentially interactable elements
            descendants = main_window.descendants()
            for elem in descendants:
                try:
                    elem_info = elem.element_info
                    if elem_info.control_type in ["Edit", "Text", "Button"]:
                        rect = elem.rectangle()
                        all_elements.append({
                            'element': elem,
                            'type': elem_info.control_type,
                            'name': elem_info.name or "<no name>",
                            'rect': rect,
                            'value': elem.get_value() if elem_info.control_type == "Edit" else ""
                        })
                except:
                    continue
            
            # Sort by position (top to bottom, left to right)
            all_elements.sort(key=lambda e: (e['rect'].top, e['rect'].left))
            
            print(f"\nFound {len(all_elements)} elements. Showing Edit controls and nearby elements:")
            
            for i, elem_data in enumerate(all_elements):
                if elem_data['type'] == "Edit" or "scale" in elem_data['name'].lower():
                    print(f"\n[{i+1}] {elem_data['type']:10} | '{elem_data['name'][:30]:<30}' | Pos: ({elem_data['rect'].left}, {elem_data['rect'].top})")
                    if elem_data['value']:
                        print(f"     Value: '{elem_data['value']}'")
            
            print("\nEnter the number of the scale factor input field (or 0 to exit):")
            
            while True:
                try:
                    choice = input("Number: ").strip()
                    if not choice:
                        continue
                    
                    num = int(choice)
                    if num == 0:
                        break
                    
                    if 1 <= num <= len(all_elements):
                        selected = all_elements[num-1]
                        print(f"\nTesting element: {selected['name']}")
                        
                        # Try to interact
                        selected['element'].click_input()
                        time.sleep(0.5)
                        
                        if selected['type'] == "Edit":
                            selected['element'].type_keys('^a1.75')
                            print("✓ Set value to 1.75")
                            
                            # Verify
                            try:
                                new_value = selected['element'].get_value()
                                print(f"New value: '{new_value}'")
                            except:
                                pass
                        
                        print("\nIs this the correct scale factor input? (y/n):")
                        if input().strip().lower() == 'y':
                            print("\n✓ Scale factor input field identified!")
                            return True
                        
                except ValueError:
                    print("Please enter a valid number")
                except Exception as e:
                    print(f"Error: {e}")
                    
        except Exception as e:
            print(f"Error in interactive mode: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        print("\nPress Enter to close Gigapixel...")
        input()
        try:
            app.kill()
        except:
            pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_scale_input.py <gigapixel_exe_path>")
        sys.exit(1)
    
    exe_path = sys.argv[1]
    find_scale_input_field(exe_path)

if __name__ == "__main__":
    main()