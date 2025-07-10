#!/usr/bin/env python3
"""
Mock version of GigaUp GUI for development/testing on non-Windows platforms
This allows testing the GUI interface without Windows dependencies
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock
import importlib.util

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Mock Windows-specific modules
class MockWin32:
    """Mock win32api module"""
    def LoadKeyboardLayout(self, layout, flag):
        print(f"[MOCK] LoadKeyboardLayout called with {layout}, {flag}")
        return True

class MockWin32Con:
    """Mock win32con module"""
    KLF_ACTIVATE = 1

class MockWinsound:
    """Mock winsound module"""
    MB_OK = 0
    
    @staticmethod
    def MessageBeep(sound_type):
        print(f"[MOCK] System beep: {sound_type}")

# Install mocks before importing gigapixel modules
sys.modules['win32api'] = MockWin32()
sys.modules['win32con'] = MockWin32Con()
sys.modules['winsound'] = MockWinsound()

# Mock pywinauto
class MockApplication:
    def __init__(self, backend=None):
        self.backend = backend
    
    def connect(self, path=None):
        print(f"[MOCK] Connected to application at {path}")
        return self
    
    def start(self, path):
        print(f"[MOCK] Started application at {path}")
        return self
    
    def window(self):
        return MockWindow()

class MockWindow:
    def __init__(self):
        self.element_info = Mock()
        self.element_info.name = "Mock Gigapixel Window"
    
    def set_focus(self):
        print("[MOCK] Window focused")
    
    def child_window(self, **kwargs):
        print(f"[MOCK] Found child window: {kwargs}")
        return MockControl()
    
    def wait(self, state, timeout=None):
        print(f"[MOCK] Waiting for {state} (timeout: {timeout})")
    
    def wait_not(self, state, timeout=None):
        print(f"[MOCK] Waiting for NOT {state} (timeout: {timeout})")
    
    def print_control_identifiers(self):
        print("[MOCK] Control identifiers printed")

class MockControl:
    def click_input(self):
        print("[MOCK] Control clicked")
    
    def wait(self, state, timeout=None):
        print(f"[MOCK] Control waiting for {state}")
    
    def wait_not(self, state, timeout=None):
        print(f"[MOCK] Control waiting for NOT {state}")
    
    def check(self):
        print("[MOCK] Control checked")
    
    def uncheck(self):
        print("[MOCK] Control unchecked")
    
    def set_value(self, value):
        print(f"[MOCK] Control value set to {value}")
    
    def set_text(self, text):
        print(f"[MOCK] Control text set to {text}")

class MockKeyboard:
    @staticmethod
    def send_keys(keys):
        print(f"[MOCK] Sent keys: {keys}")

class MockClipboard:
    @staticmethod
    def copy(text):
        print(f"[MOCK] Copied to clipboard: {text}")

class MockTimings:
    window_find_timeout = 0.5

# Mock the modules
sys.modules['pywinauto'] = Mock()
sys.modules['pywinauto.application'] = Mock()
sys.modules['pywinauto.keyboard'] = Mock()
sys.modules['pywinauto.timings'] = Mock()
sys.modules['clipboard'] = Mock()

# Set up the mock objects
import pywinauto
pywinauto.Application = MockApplication
pywinauto.ElementNotFoundError = Exception
pywinauto.timings = MockTimings()

import pywinauto.application
pywinauto.application.Application = MockApplication
pywinauto.application.ProcessNotFoundError = Exception

import pywinauto.keyboard
pywinauto.keyboard.send_keys = MockKeyboard.send_keys

import pywinauto.timings
pywinauto.timings.TimeoutError = Exception
pywinauto.timings.Timings = MockTimings

import clipboard
clipboard.copy = MockClipboard.copy

print("=" * 60)
print("GigaUp GUI - Mock Mode")
print("=" * 60)
print("This is a mock version for development/testing on non-Windows platforms.")
print("The GUI will work, but no actual image processing will occur.")
print("For full functionality, use Windows with Topaz Gigapixel AI installed.")
print("=" * 60)

try:
    # Now try to import and run the GUI
    from gigapixel.gui.main_window import GigaUpWindow
    
    # Create a mock executable path
    mock_exe_path = "C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe"
    
    print(f"Starting GUI with mock executable: {mock_exe_path}")
    
    # Start the GUI
    app = GigaUpWindow(mock_exe_path)
    
    # Add a note about mock mode
    import tkinter as tk
    mock_label = tk.Label(app.scrollable_frame, 
                         text="🔧 MOCK MODE - No actual processing will occur", 
                         fg="red", font=("Arial", 10, "bold"))
    mock_label.pack(pady=5)
    
    app.run()
    
except Exception as e:
    print(f"Error starting mock GUI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)