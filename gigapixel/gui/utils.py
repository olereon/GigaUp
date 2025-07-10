import tkinter as tk
from tkinter import messagebox
import os
import sys
import threading
import time
from typing import Optional


def center_window(window: tk.Tk):
    """Center a window on the screen"""
    window.update_idletasks()
    
    # Get window dimensions
    width = window.winfo_width()
    height = window.winfo_height()
    
    # Get screen dimensions
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Calculate position
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    # Set window position
    window.geometry(f"{width}x{height}+{x}+{y}")


def show_notification(title: str, message: str, duration: int = 3000):
    """Show a system notification (Windows-specific implementation)"""
    try:
        if os.name == 'nt':  # Windows
            import plyer
            plyer.notification.notify(
                title=title,
                message=message,
                timeout=duration // 1000
            )
    except ImportError:
        # Fallback to messagebox if plyer not available
        messagebox.showinfo(title, message)
    except Exception:
        # Silent fail for notifications
        pass


def play_completion_sound():
    """Play a completion sound"""
    try:
        if os.name == 'nt':  # Windows
            import winsound
            # Play system default sound
            winsound.MessageBeep(winsound.MB_OK)
        else:
            # For other platforms, try to use system bell
            print('\a')  # ASCII bell character
    except ImportError:
        # Silent fail if sound module not available
        pass
    except Exception:
        # Silent fail for sound
        pass


def get_file_size_string(size_bytes: int) -> str:
    """Convert file size in bytes to human-readable string"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"


def validate_file_path(path: str) -> bool:
    """Validate if a file path is valid"""
    try:
        return os.path.isfile(path)
    except (OSError, TypeError):
        return False


def validate_directory_path(path: str) -> bool:
    """Validate if a directory path is valid"""
    try:
        return os.path.isdir(path)
    except (OSError, TypeError):
        return False


def create_directory_if_not_exists(path: str) -> bool:
    """Create directory if it doesn't exist"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except (OSError, PermissionError):
        return False


def get_supported_image_extensions() -> list:
    """Get list of supported image file extensions"""
    return ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']


def is_image_file(file_path: str) -> bool:
    """Check if a file is a supported image file"""
    try:
        _, ext = os.path.splitext(file_path.lower())
        return ext in get_supported_image_extensions()
    except (OSError, TypeError):
        return False


def find_image_files(directory: str) -> list:
    """Find all image files in a directory"""
    image_files = []
    if not os.path.isdir(directory):
        return image_files
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) and is_image_file(file_path):
                image_files.append(file_path)
    except (OSError, PermissionError):
        pass
    
    return sorted(image_files)


class BackgroundTask:
    """Helper class for running tasks in background threads"""
    
    def __init__(self, task_function, completion_callback=None, error_callback=None):
        self.task_function = task_function
        self.completion_callback = completion_callback
        self.error_callback = error_callback
        self.thread = None
        self.result = None
        self.error = None
        self.completed = False
        self.cancelled = False
    
    def start(self, *args, **kwargs):
        """Start the background task"""
        if self.thread is not None and self.thread.is_alive():
            return False  # Already running
        
        self.cancelled = False
        self.completed = False
        self.result = None
        self.error = None
        
        self.thread = threading.Thread(
            target=self._run_task,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        self.thread.start()
        return True
    
    def _run_task(self, *args, **kwargs):
        """Internal method to run the task"""
        try:
            self.result = self.task_function(*args, **kwargs)
            self.completed = True
            
            if self.completion_callback and not self.cancelled:
                self.completion_callback(self.result)
                
        except Exception as e:
            self.error = e
            self.completed = True
            
            if self.error_callback and not self.cancelled:
                self.error_callback(e)
    
    def cancel(self):
        """Cancel the task (note: this just sets a flag, actual cancellation depends on task implementation)"""
        self.cancelled = True
    
    def is_running(self) -> bool:
        """Check if the task is currently running"""
        return self.thread is not None and self.thread.is_alive()
    
    def is_completed(self) -> bool:
        """Check if the task has completed"""
        return self.completed
    
    def wait(self, timeout: Optional[float] = None):
        """Wait for the task to complete"""
        if self.thread:
            self.thread.join(timeout)


class ProgressTracker:
    """Helper class for tracking progress of operations"""
    
    def __init__(self, total_items: int = 0):
        self.total_items = total_items
        self.completed_items = 0
        self.start_time = time.time()
        self.callbacks = []
    
    def set_total(self, total: int):
        """Set the total number of items"""
        self.total_items = total
        self._notify_callbacks()
    
    def increment(self, amount: int = 1):
        """Increment the completed items counter"""
        self.completed_items = min(self.completed_items + amount, self.total_items)
        self._notify_callbacks()
    
    def set_progress(self, completed: int):
        """Set the current progress"""
        self.completed_items = min(max(completed, 0), self.total_items)
        self._notify_callbacks()
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0-100)"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time
    
    def get_estimated_time_remaining(self) -> Optional[float]:
        """Get estimated time remaining in seconds"""
        if self.completed_items == 0 or self.total_items == 0:
            return None
        
        elapsed = self.get_elapsed_time()
        rate = self.completed_items / elapsed
        remaining_items = self.total_items - self.completed_items
        
        if rate > 0:
            return remaining_items / rate
        return None
    
    def is_complete(self) -> bool:
        """Check if all items are completed"""
        return self.completed_items >= self.total_items
    
    def reset(self):
        """Reset the progress tracker"""
        self.completed_items = 0
        self.start_time = time.time()
        self._notify_callbacks()
    
    def add_callback(self, callback):
        """Add a progress callback function"""
        self.callbacks.append(callback)
    
    def _notify_callbacks(self):
        """Notify all callbacks of progress change"""
        for callback in self.callbacks:
            try:
                callback(self)
            except Exception:
                pass  # Ignore callback errors


def bind_mousewheel(widget, canvas):
    """Bind mousewheel scrolling to a canvas"""
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _bind_to_mousewheel(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def _unbind_from_mousewheel(event):
        canvas.unbind_all("<MouseWheel>")
    
    widget.bind('<Enter>', _bind_to_mousewheel)
    widget.bind('<Leave>', _unbind_from_mousewheel)


def safe_filename(filename: str) -> str:
    """Convert a string to a safe filename by removing/replacing invalid characters"""
    # Characters not allowed in Windows filenames
    invalid_chars = '<>:"/\\|?*'
    
    # Replace invalid characters with underscores
    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip(' .')
    
    # Ensure it's not empty
    if not safe_name:
        safe_name = "untitled"
    
    return safe_name


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length with optional suffix"""
    if len(text) <= max_length:
        return text
    
    if len(suffix) >= max_length:
        return text[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


class SettingsManager:
    """Helper class for managing application settings"""
    
    def __init__(self, settings_file: str):
        self.settings_file = settings_file
        self.settings = {}
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            import json
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.settings = {}
    
    def save_settings(self):
        """Save settings to file"""
        try:
            import json
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except IOError:
            pass  # Fail silently
    
    def get(self, key: str, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        """Set a setting value"""
        self.settings[key] = value
    
    def delete(self, key: str):
        """Delete a setting"""
        if key in self.settings:
            del self.settings[key]
    
    def has(self, key: str) -> bool:
        """Check if a setting exists"""
        return key in self.settings
    
    def clear(self):
        """Clear all settings"""
        self.settings.clear()


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)