#!/usr/bin/env python3
"""
Standalone mock version of GigaUp GUI - No dependencies required!
This version mocks ALL dependencies for easy testing
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock
import importlib.util

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Mock ALL dependencies before any imports
class MockLoguru:
    """Mock loguru logger"""
    def __init__(self):
        self.debug = self.info = self.warning = self.error = self.success = lambda *args, **kwargs: None
        self.log = lambda level, msg, *args, **kwargs: None

# Mock the-retry decorator
def mock_retry(**kwargs):
    def decorator(func):
        return func
    return decorator

# Mock Windows-specific modules
class MockWin32:
    def LoadKeyboardLayout(self, layout, flag):
        return True

class MockWin32Con:
    KLF_ACTIVATE = 1

class MockWinsound:
    MB_OK = 0
    @staticmethod
    def MessageBeep(sound_type):
        pass

# Install all mocks
sys.modules['loguru'] = Mock()
sys.modules['loguru'].logger = MockLoguru()
sys.modules['the_retry'] = Mock()
sys.modules['the_retry'].retry = mock_retry
sys.modules['win32api'] = MockWin32()
sys.modules['win32con'] = MockWin32Con()
sys.modules['winsound'] = MockWinsound()

# Mock pywinauto and related modules
class MockApplication:
    def __init__(self, backend=None):
        self.backend = backend
    
    def connect(self, path=None):
        return self
    
    def start(self, path):
        return self
    
    def window(self):
        return MockWindow()

class MockWindow:
    def __init__(self):
        self.element_info = Mock()
        self.element_info.name = "Mock Window"
    
    def set_focus(self):
        pass
    
    def child_window(self, **kwargs):
        return MockControl()
    
    def wait(self, state, timeout=None):
        pass
    
    def wait_not(self, state, timeout=None):
        pass
    
    def print_control_identifiers(self):
        pass

class MockControl:
    def click_input(self):
        pass
    
    def wait(self, state, timeout=None):
        pass
    
    def wait_not(self, state, timeout=None):
        pass
    
    def check(self):
        pass
    
    def uncheck(self):
        pass
    
    def set_value(self, value):
        pass
    
    def set_text(self, text):
        pass

class MockKeyboard:
    @staticmethod
    def send_keys(keys):
        pass

class MockClipboard:
    @staticmethod
    def copy(text):
        pass

class MockTimings:
    window_find_timeout = 0.5
    
    class Timings:
        window_find_timeout = 0.5

# Install pywinauto mocks
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
pywinauto.timings.Timings = MockTimings.Timings

import clipboard
clipboard.copy = MockClipboard.copy

# Import standard library modules we'll need
import loguru
import the_retry

print("=" * 60)
print("GigaUp GUI - Standalone Mock Mode")
print("=" * 60)
print("This is a standalone mock version with zero dependencies.")
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
    
    # Also mock the notification system to prevent errors
    try:
        import plyer
    except ImportError:
        sys.modules['plyer'] = Mock()
        sys.modules['plyer'].notification = Mock()
        sys.modules['plyer'].notification.notify = lambda **kwargs: None
    
    print("\nGUI started successfully! Close the window to exit.")
    app.run()
    
except Exception as e:
    print(f"Error starting mock GUI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)