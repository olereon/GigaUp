from enum import Enum
from typing import Optional, Dict, Any, Union, List, Callable
from pathlib import Path
import win32api
import win32con
import asyncio
import threading
from dataclasses import dataclass

from .logging import log, Level
from .exceptions import NotFile, ElementNotFound
from .models import AIModel, ModelClass, Scale as NewScale
from .parameters import ProcessingParameters, ParameterManager
from .factory import ModelFactory, get_model_factory

from pywinauto import ElementNotFoundError, timings
import clipboard
from loguru import logger
from pywinauto.application import Application, ProcessNotFoundError
from pywinauto.keyboard import send_keys
from pywinauto.timings import TimeoutError
from the_retry import retry


# Legacy enums for backward compatibility
class Scale(Enum):
    X1 = "1x"
    X2 = "2x"
    X4 = "4x"
    X6 = "6x"


class Mode(Enum):
    STANDARD = "Standard"
    HIGH_FIDELITY = "High fidelity"
    LOW_RESOLUTION = "Low res"
    TEXT_AND_SHAPES = "Text & shapes"
    ART_AND_CG = "Art & CG"
    RECOVERY = "Recovery"


@dataclass
class ProcessingJob:
    """Represents a processing job for batch operations"""
    input_path: Path
    output_path: Optional[Path] = None
    parameters: Optional[ProcessingParameters] = None
    status: str = "pending"
    progress: float = 0.0
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ProcessingCallback:
    """Callback interface for processing events"""
    def on_job_start(self, job: ProcessingJob):
        pass
    
    def on_job_progress(self, job: ProcessingJob, progress: float):
        pass
    
    def on_job_complete(self, job: ProcessingJob):
        pass
    
    def on_job_error(self, job: ProcessingJob, error: str):
        pass
    
    def on_batch_start(self, jobs: List[ProcessingJob]):
        pass
    
    def on_batch_complete(self, jobs: List[ProcessingJob]):
        pass


class Gigapixel:
    def __init__(self,
                 executable_path: Union[Path, str],
                 processing_timeout: int = 900) -> None:
        """
        :param executable_path: Path to the executable (Topaz Gigapixel AI.exe)
        :param processing_timeout: Timeout for processing in seconds
        """
        self._executable_path = executable_path
        if isinstance(executable_path, str):
            self._executable_path = Path(executable_path)

        # Initialize new model system
        self._model_factory = get_model_factory()
        self._parameter_manager = ParameterManager()
        
        # Processing state
        self._processing_jobs: List[ProcessingJob] = []
        self._current_job: Optional[ProcessingJob] = None
        self._callbacks: List[ProcessingCallback] = []
        self._batch_export_completed = False  # Flag to track batch export completion
        
        instance = self._get_gigapixel_instance()
        self._app = self._App(instance, processing_timeout, parent=self)

    class _App:
        def __init__(self, app: Application, processing_timeout: int, parent=None):
            timings.Timings.window_find_timeout = 0.2  # Reduced for faster response

            self.app = app
            self._processing_timeout = processing_timeout
            self._parent = parent  # Reference to parent Gigapixel object
            
            # Find the main window - try different patterns with better error handling
            main_window = None
            window_patterns = [
                ("Topaz Gigapixel AI", lambda: self.app.window(title="Topaz Gigapixel AI")),
                ("Gigapixel 8", lambda: self.app.window(title="Gigapixel 8")),
                ("Gigapixel with number", lambda: self.app.window(title_re="Gigapixel [0-9]+")),
                ("Any Gigapixel", lambda: self.app.window(title_re=".*Gigapixel.*")),
                ("Top level window", lambda: self.app.top_window()),
                ("Any window", lambda: self.app.window())
            ]
            
            for pattern_name, window_func in window_patterns:
                try:
                    logger.debug(f"Trying to find window with pattern: {pattern_name}")
                    main_window = window_func()
                    break
                except Exception as e:
                    logger.debug(f"Pattern '{pattern_name}' failed: {e}")
                    continue
            
            if main_window is None:
                raise Exception("Could not find Gigapixel main window with any pattern")
            
            self._main_window = main_window

            self.scale: Optional[Scale] = None
            self.mode: Optional[Mode] = None

            self._cancel_processing_button: Optional[Any] = None
            self._save_button: Optional[Any] = None
            self._scale_buttons: Dict[Scale, Any] = {}
            self._mode_buttons: Dict[Mode, Any] = {}

        @retry(
            expected_exception=(ElementNotFoundError,),
            attempts=5,
            backoff=0.5,
            exponential_backoff=True,
        )
        @log("Opening photo(s): {}", "Photo(s) opened", format=(1,), level=Level.DEBUG)
        def open_photo(self, photo_paths: Union[Path, List[Path]]) -> None:
            import time
            
            # Convert single path to list for uniform handling
            if isinstance(photo_paths, Path):
                photo_paths = [photo_paths]
            
            # Step 1: Focus the main window and wait for it to be ready
            logger.debug("Focusing main window and waiting for it to be ready")
            self._main_window.set_focus()
            time.sleep(0.2)  # Quick wait for window to be active
            
            # Step 2: Try to open file dialog - use Browse button as primary method
            dialog_opened = False
            
            # Method 1: Try clicking the "Browse images" button in the center of the screen
            logger.debug("Attempting to click Browse images button in center of screen")
            try:
                # Look for "Browse images" button which appears when no image is loaded
                browse_button = self._main_window.child_window(title="Browse images", control_type="Button")
                browse_button.click_input()
                logger.debug("✓ Clicked Browse button successfully")
                time.sleep(0.3)  # Quick wait for dialog to open
                dialog_opened = True
            except Exception as e:
                logger.debug(f"Browse button click failed: {e}")
            
            # Method 2: Fallback to Ctrl+O if Browse button didn't work
            if not dialog_opened:
                logger.debug("Fallback: Opening file dialog with Ctrl+O")
                send_keys('^o')
                time.sleep(0.3)  # Quick wait for dialog to open
            
            # Step 3: Verify the file dialog actually opened with stricter detection
            logger.debug("Verifying file dialog opened with strict detection...")
            dialog_confirmed = False
            
            try:
                # Look for actual file dialog window (separate from main window)
                # The file dialog should be a separate dialog window, not a child of main window
                app_dialogs = self.app.windows()
                for window in app_dialogs:
                    try:
                        window_title = window.element_info.name.lower()
                        if "open" in window_title or "browse" in window_title or "file" in window_title:
                            dialog_confirmed = True
                            break
                    except:
                        continue
                
                # Alternative: Look for file dialog specific elements
                if not dialog_confirmed:
                    try:
                        # Look for file name input field or file list in main window
                        file_input = self._main_window.child_window(control_type="Edit", title_re=".*[Ff]ile.*")
                        dialog_confirmed = True
                    except:
                        pass
                
                # Alternative: Look for common dialog buttons
                if not dialog_confirmed:
                    try:
                        open_button = self._main_window.child_window(title="Open", control_type="Button")
                        cancel_button = self._main_window.child_window(title="Cancel", control_type="Button")
                        # Both buttons should exist in a real file dialog
                        dialog_confirmed = True
                    except:
                        pass
                        
            except Exception as e:
                logger.debug(f"Dialog verification error: {e}")
            
            if not dialog_confirmed:
                logger.error("✗ File dialog did not open properly! Cannot proceed with file selection.")
                raise ElementNotFound("File dialog failed to open - cannot select file")
            
            logger.debug("✓ File dialog confirmed open, proceeding with file selection")
            
            # Step 4: Enter the file path(s)
            if len(photo_paths) == 1:
                logger.debug(f"Entering single file path: {photo_paths[0]}")
                # Normalize path for Windows - ensure single backslashes for Gigapixel app
                normalized_path = str(photo_paths[0]).replace('\\\\', '\\')
                clipboard.copy(normalized_path)
            else:
                logger.debug(f"Entering multiple file paths: {len(photo_paths)} files")
                # Format multiple paths as space-separated quoted strings (NO COMMAS!)
                # Format: "path1" "path2" "path3"
                normalized_paths = []
                for path in photo_paths:
                    # Normalize path for Windows - ensure single backslashes for Gigapixel app
                    normalized_path = str(path).replace('\\\\', '\\')
                    # Add quotes around each path
                    normalized_paths.append(f'"{normalized_path}"')
                
                # Join with spaces (no commas!)
                multi_path_string = ' '.join(normalized_paths)
                logger.debug(f"Multi-path string: {multi_path_string}")
                clipboard.copy(multi_path_string)
            
            send_keys('^v')
            time.sleep(0.1)  # Quick wait for path to be entered
            
            # Step 5: Click the "Open" button to confirm file selection
            try:
                logger.debug("Looking for and clicking Open button")
                open_button = self._main_window.child_window(title="Open", control_type="Button")
                open_button.click_input()
                logger.debug("✓ Clicked Open button")
            except:
                logger.debug("Could not find Open button, using Enter key instead")
                send_keys('{ENTER}')
            
            # Step 6: Wait for file to load and dialog to close
            logger.debug("Waiting for file to load and dialog to close...")
            time.sleep(0.5)  # Quick wait for file to load
            
            # Step 7: Verify that image loaded by checking for UI elements
            logger.debug("Verifying that image loaded successfully...")
            image_loaded = False
            max_retries = 3
            
            for retry in range(max_retries):
                logger.debug(f"Image loading verification attempt {retry + 1}/{max_retries}")
                
                # Method 1: Check for "Upscale" text/label (visible when image is loaded)
                try:
                    upscale_element = self._main_window.child_window(title="Upscale")
                    logger.debug("✓ Image loaded - found Upscale element")
                    image_loaded = True
                    break
                except:
                    pass
                
                # Method 2: Check for scale buttons (1x, 2x, 4x, 6x)
                try:
                    scale_button = self._main_window.child_window(title="2x")
                    logger.debug("✓ Image loaded - found scale button")
                    image_loaded = True
                    break
                except:
                    pass
                
                # Method 3: Check for "Export" button (appears when image is loaded)
                try:
                    export_button = self._main_window.child_window(title_re=".*Export.*")
                    logger.debug("✓ Image loaded - found Export button")
                    image_loaded = True
                    break
                except:
                    pass
                
                # Method 4: Check for model selection elements (High fidelity, Standard, etc.)
                try:
                    model_element = self._main_window.child_window(title="High fidelity")
                    logger.debug("✓ Image loaded - found model selection")
                    image_loaded = True
                    break
                except:
                    pass
                
                # Method 5: Check if Browse images button is no longer the prominent center button
                try:
                    browse_button = self._main_window.child_window(title="Browse images", control_type="Button")
                    # If we can still see the main Browse images button, the image didn't load
                    logger.debug("✗ Browse images button still visible, image may not have loaded")
                except:
                    # Browse images button is gone/changed, which suggests image loaded
                    logger.debug("✓ Image loaded - Browse images button no longer prominent")
                    image_loaded = True
                    break
                
                if not image_loaded and retry < max_retries - 1:
                    logger.debug(f"Image not detected as loaded, waiting and retrying...")
                    time.sleep(0.2)  # Wait before retrying
            
            if image_loaded:
                logger.info("✓ Image successfully loaded and verified")
                
                # Update window reference since the title likely changed to include the filename
                logger.debug("Updating window reference after image load...")
                try:
                    # Try to find the updated window with the new title
                    updated_window = None
                    window_patterns = [
                        ("Image filename window", lambda: self.app.window(title_re=f".*{photo_paths[0].stem}.*")),
                        ("Any Gigapixel window", lambda: self.app.window(title_re=".*Gigapixel.*")),
                        ("Current main window", lambda: self._main_window),  # Keep current if others fail
                    ]
                    
                    for pattern_name, window_func in window_patterns:
                        try:
                            test_window = window_func()
                            # Verify it's still the right window by checking for Upscale element
                            test_window.child_window(title="Upscale")
                            logger.debug(f"✓ Updated window reference using: {pattern_name}")
                            updated_window = test_window
                            break
                        except:
                            continue
                    
                    if updated_window and updated_window != self._main_window:
                        self._main_window = updated_window
                        logger.debug(f"✓ Window reference updated to: '{self._main_window.element_info.name}'")
                    else:
                        logger.debug("Window reference unchanged - keeping current window")
                        
                except Exception as e:
                    logger.debug(f"Could not update window reference: {e}, keeping current window")
                
            else:
                logger.error("✗ Could not verify that image loaded - this may cause subsequent operations to fail")
                # Don't fail completely, but warn that operations might not work
            
            if len(photo_paths) == 1:
                logger.info(f"File opening sequence completed for: {photo_paths[0].name}")
            else:
                logger.info(f"File opening sequence completed for {len(photo_paths)} files")
                

        @log("Saving photo", "Photo saved", level=Level.DEBUG)
        def save_photo(self) -> None:
            """Save photo using the Export button"""
            import time
            
            logger.debug("Looking for Export button to save image...")
            
            try:
                # Look for the Export button with various patterns
                export_patterns = [
                    ("Export button", lambda: self._main_window.child_window(title_re=".*Export.*", control_type="Button")),
                    ("Export 1 image", lambda: self._main_window.child_window(title="Export 1 image", control_type="Button")),
                    ("Export images", lambda: self._main_window.child_window(title_re=".*Export.*image.*", control_type="Button")),
                    ("Any Export", lambda: self._main_window.child_window(title_re=".*Export.*")),
                ]
                
                export_clicked = False
                for pattern_name, export_func in export_patterns:
                    try:
                        export_button = export_func()
                        export_button.click_input()
                        logger.debug(f"✓ Clicked Export button using: {pattern_name}")
                        export_clicked = True
                        break
                    except:
                        continue
                
                if not export_clicked:
                    logger.error("Could not find Export button")
                    # Fallback to old method
                    self._open_export_dialog()
                    
                    # Debug logging for export parameters
                    logger.debug("Checking for export parameters on self...")
                    logger.debug(f"  _export_quality: {hasattr(self, '_export_quality')} - {getattr(self, '_export_quality', 'NOT SET')}")
                    logger.debug(f"  _export_prefix: {hasattr(self, '_export_prefix')} - {getattr(self, '_export_prefix', 'NOT SET')}")
                    logger.debug(f"  _export_suffix: {hasattr(self, '_export_suffix')} - {getattr(self, '_export_suffix', 'NOT SET')}")
                    
                    # Set export parameters if provided
                    if (hasattr(self, '_export_quality') or 
                        hasattr(self, '_export_prefix') or 
                        hasattr(self, '_export_suffix')):
                        logger.debug("Found export parameters, calling _set_export_parameters")
                        self._set_export_parameters()
                    else:
                        logger.debug("No export parameters found, sending Enter to proceed")
                        send_keys('{ENTER}')
                else:
                    # Wait for export dialog to open
                    time.sleep(0.3)
                    
                    # Debug logging for export parameters (successful path)
                    logger.debug("Export button clicked successfully, checking parameters...")
                    logger.debug(f"  _export_quality: {hasattr(self, '_export_quality')} - {getattr(self, '_export_quality', 'NOT SET')}")
                    logger.debug(f"  _export_prefix: {hasattr(self, '_export_prefix')} - {getattr(self, '_export_prefix', 'NOT SET')}")
                    logger.debug(f"  _export_suffix: {hasattr(self, '_export_suffix')} - {getattr(self, '_export_suffix', 'NOT SET')}")
                    
                    # Set export parameters if provided
                    if (hasattr(self, '_export_quality') or 
                        hasattr(self, '_export_prefix') or 
                        hasattr(self, '_export_suffix')):
                        logger.debug("Found export parameters, calling _set_export_parameters")
                        self._set_export_parameters()
                    else:
                        logger.debug("No export parameters found, skipping parameter setting")
                        # Note: We don't send Enter here because the export process will handle it
                
                # Wait for processing to complete and auto-click Close window
                logger.debug("Waiting for processing to complete...")
                self._wait_for_processing_completion()
                
                # Close any remaining dialogs (using ESC as fallback)
                self._close_export_dialog()
                
            except Exception as e:
                logger.error(f"Error during export: {e}")
                # Fallback to old export method
                try:
                    self._open_export_dialog()
                    
                    # Set export parameters if provided
                    if (hasattr(self._app, '_export_quality') or 
                        hasattr(self._app, '_export_prefix') or 
                        hasattr(self._app, '_export_suffix')):
                        self._app._set_export_parameters()
                    else:
                        send_keys('{ENTER}')
                    
                    if self._cancel_processing_button is None:
                        self._cancel_processing_button = self._main_window.child_window(title="Close window",
                                                                                        control_type="Button",
                                                                                        depth=1)
                    self._cancel_processing_button.wait('visible', timeout=self._processing_timeout)
                    self._close_export_dialog()
                except Exception as fallback_error:
                    logger.error(f"Fallback export also failed: {fallback_error}")
                    raise

        @retry(
            expected_exception=(TimeoutError,),
            attempts=10,
            backoff=0.1,
            exponential_backoff=True,
        )
        @log("Opening export dialog", "Export dialog opened", level=Level.DEBUG)
        def _open_export_dialog(self) -> None:
            send_keys('^S')
            if self._save_button is None:
                self._save_button = self._main_window.child_window(title="Save", control_type="Button", depth=1)
        @retry(
            expected_exception=(ElementNotFoundError, ProcessNotFoundError, TimeoutError, Exception),
            attempts=10,
            backoff=0.1,
            exponential_backoff=True,
        )
        def _wait_for_processing_completion(self) -> None:
            """Wait for processing to complete and click 'Close window' button"""
            import time
            from pywinauto import Desktop
            
            try:
                logger.debug("Waiting for processing completion...")
                
                # Get processing jobs from parent
                processing_jobs = getattr(self._parent, '_processing_jobs', []) if self._parent else []
                if not processing_jobs:
                    logger.warning("No processing jobs available for completion detection")
                    return
                
                # Get the last file in the batch (this is what we're waiting for)
                last_file = processing_jobs[-1].input_path
                last_file_name = last_file.name  # Full filename with extension
                last_file_stem = last_file.stem  # Filename without extension
                
                # Get image file extensions from all files in batch
                image_extensions = {job.input_path.suffix.lower() for job in processing_jobs}
                logger.debug(f"Looking for window with last file: '{last_file_name}' (extensions: {image_extensions})")
                
                # Poll until we find the correct window and buttons
                start_time = time.time()
                max_wait_time = self._processing_timeout
                poll_interval = 1.0
                
                while (time.time() - start_time) < max_wait_time:
                    try:
                        # Search all windows for image files
                        desktop = Desktop(backend="uia")
                        target_window = None
                        current_file_window = None
                        
                        for window in desktop.windows():
                            if window.is_visible():
                                window_title = window.window_text()
                                if window_title:
                                    # Check if window title has an image extension
                                    for ext in image_extensions:
                                        if window_title.lower().endswith(ext):
                                            # This is an image file window
                                            # Check if it matches any file in our batch
                                            for job in processing_jobs:
                                                if (job.input_path.name in window_title or 
                                                    job.input_path.stem in window_title):
                                                    current_file_window = window
                                                    logger.debug(f"Found image file window: '{window_title}'")
                                                    
                                                    # Check if this is the LAST file (the one we're waiting for)
                                                    if (last_file_name in window_title or 
                                                        last_file_stem in window_title):
                                                        target_window = window
                                                        logger.debug(f"Found TARGET window (last file): '{window_title}'")
                                                        break
                                            break
                        
                        # If we found the target window (last file), check for completion buttons
                        if target_window:
                            logger.debug(f"Checking for completion buttons in target window...")
                            
                            close_button = None
                            export_again_button = None
                            
                            # Search for buttons in the target window
                            for button in target_window.descendants(control_type="Button"):
                                try:
                                    if button.is_visible() and button.is_enabled():
                                        title = button.window_text().strip()
                                        title_lower = title.lower()
                                        
                                        if title_lower == "close window":
                                            close_button = button
                                            logger.debug("Found 'Close window' button")
                                        elif title_lower == "export again":
                                            export_again_button = button
                                            logger.debug("Found 'Export again' button")
                                except:
                                    continue
                            
                            # Handle completion buttons first (processing is done)
                            # Check for completion buttons first - if they exist, export is already done
                            if close_button and export_again_button:
                                logger.info("Both completion buttons found - clicking 'Close window'")
                                close_button.click_input()
                                
                                # Mark batch as completed if multiple jobs
                                if self._parent and len(processing_jobs) > 1:
                                    self._parent._batch_export_completed = True
                                    for job in processing_jobs:
                                        if job.status != "completed":
                                            job.status = "completed"
                                            logger.debug(f"Marked {job.input_path.name} as completed (batch close)")
                                
                                return
                                
                            elif close_button:
                                logger.info("Found 'Close window' button only - clicking it")
                                close_button.click_input()
                                
                                # Mark batch as completed if multiple jobs
                                if self._parent and len(processing_jobs) > 1:
                                    self._parent._batch_export_completed = True
                                    for job in processing_jobs:
                                        if job.status != "completed":
                                            job.status = "completed"
                                            logger.debug(f"Marked {job.input_path.name} as completed (batch close)")
                                
                                return
                            
                            # Buttons not ready yet, continue waiting
                            logger.debug("Target window found but completion buttons not ready yet")
                        
                        elif current_file_window:
                            # We found a file window but it's not the last one yet
                            logger.debug(f"Found intermediate file window, waiting for last file: '{last_file_name}'")
                        
                        else:
                            # No image file window found yet
                            logger.debug("No image file window found yet, continuing to wait...")
                        
                        # Wait before next check
                        time.sleep(poll_interval)
                        elapsed = time.time() - start_time
                        if elapsed % 30 == 0:  # Log progress every 30 seconds
                            logger.debug(f"Still waiting for completion... ({elapsed:.0f}s elapsed)")
                        
                    except Exception as e:
                        logger.debug(f"Error during completion check: {e}")
                        time.sleep(poll_interval)
                
                # If we get here, timeout occurred
                logger.warning(f"Timeout waiting for completion after {max_wait_time}s")
                
            except Exception as e:
                logger.error(f"Error waiting for processing completion: {e}")        @log("Closing export dialog", "Export dialog closed", level=Level.DEBUG)
        def _close_export_dialog(self) -> None:
            send_keys('{ESC}')
            # Remove the old cancel button wait logic since we handle it in _wait_for_processing_completion
            try:
                if self._cancel_processing_button and self._cancel_processing_button.exists():
                    self._cancel_processing_button.wait_not('visible', timeout=0.1)
            except:
                pass
        
        def _set_export_parameters(self, auto_confirm: bool = True) -> None:
            """Set export parameters (quality, prefix, suffix) in the export dialog"""
            import time
            logger.debug("Setting export parameters...")
            
            try:
                # Find the export dialog window - it might be a child of the main window or a separate window
                export_dialog = None
                
                # Strategy 1: Look for "Export settings" text to identify the dialog
                try:
                    # Find all Text elements in the window hierarchy
                    all_elements = self._main_window.descendants()
                    export_settings_found = False
                    
                    for element in all_elements:
                        try:
                            element_info = element.element_info
                            if (element_info.control_type == "Text" and 
                                element_info.name and 
                                "Export settings" in element_info.name):
                                export_settings_found = True
                                logger.debug("Found 'Export settings' text - export dialog is open")
                                
                                # The export dialog is likely the parent or nearby container
                                # Try to find the containing dialog/pane
                                parent = element.parent()
                                while parent:
                                    parent_info = parent.element_info
                                    if parent_info.control_type in ["Dialog", "Pane", "Window"]:
                                        export_dialog = parent
                                        logger.debug(f"Found export dialog container: {parent_info.control_type}")
                                        break
                                    parent = parent.parent()
                                break
                        except:
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error searching for 'Export settings' text: {e}")
                
                # Strategy 2: Look for Export window as a separate top-level window
                if not export_dialog:
                    try:
                        app_windows = self._main_window.application.windows()
                        for window in app_windows:
                            try:
                                if "export" in window.window_text().lower():
                                    export_dialog = window
                                    logger.debug(f"Found export dialog as separate window: {window.window_text()}")
                                    break
                            except:
                                pass
                    except Exception as e:
                        logger.debug(f"Could not search for separate export window: {e}")
                
                # Strategy 3: Look for Export as a dialog/panel within main window
                if not export_dialog:
                    try:
                        # The export dialog might be a panel/dialog within the main window
                        export_dialog = self._main_window.child_window(title="Export", control_type="Pane")
                        logger.debug("Found export dialog as Pane within main window")
                    except:
                        try:
                            export_dialog = self._main_window.child_window(title_re=".*Export.*", found_index=0)
                            logger.debug("Found export dialog using title pattern")
                        except:
                            logger.debug("Could not find export dialog, using main window")
                            export_dialog = self._main_window
                    
                    # Store the export dialog reference for completion detection
                    self._export_dialog = export_dialog
                
                # Get all Edit and SpinBox controls in export dialog
                logger.debug("Searching for export fields...")
                all_edit_controls = []
                try:
                    for ctrl in export_dialog.descendants():
                        try:
                            ctrl_info = ctrl.element_info
                            if ctrl_info.control_type in ["Edit", "SpinBox"] and ctrl.is_visible():
                                ctrl_text = ctrl.window_text()
                                ctrl_rect = ctrl.rectangle()
                                all_edit_controls.append({
                                    'control': ctrl,
                                    'text': ctrl_text,
                                    'type': ctrl_info.control_type,
                                    'rect': ctrl_rect
                                })
                        except:
                            pass
                    
                    # Sort by position (top to bottom, left to right)
                    all_edit_controls.sort(key=lambda e: (e['rect'].top, e['rect'].left))
                    
                    # Log all controls for debugging
                    logger.debug(f"Found {len(all_edit_controls)} Edit/SpinBox controls in export dialog:")
                    for i, edit_info in enumerate(all_edit_controls):
                        logger.debug(f"  [{i}] {edit_info['type']}: text='{edit_info['text']}', pos=({edit_info['rect'].left},{edit_info['rect'].top})")
                    
                except Exception as e:
                    logger.debug(f"Error enumerating controls: {e}")
                
                # Based on the user's data, the Export dialog has these fields in order:
                # In the right panel (x > 3000): various numeric fields
                # In the left panel (x < 3000): 
                #   - Prefix field (empty text)
                #   - Suffix field (empty text)  
                #   - Quality field (numeric value)
                
                # Separate controls into left and right panels
                left_panel_controls = [e for e in all_edit_controls if e['rect'].left < 3000]
                right_panel_controls = [e for e in all_edit_controls if e['rect'].left >= 3000]
                
                logger.debug(f"Left panel has {len(left_panel_controls)} controls, right panel has {len(right_panel_controls)} controls")
                
                # Set quality if provided
                if hasattr(self, '_export_quality') and self._export_quality is not None:
                    try:
                        quality_control = None
                        
                        # Quality is typically the last control in the left panel
                        if left_panel_controls:
                            # Quality should be the last control in left panel (position 2, index 2)
                            if len(left_panel_controls) >= 3:
                                quality_control = left_panel_controls[2]['control']
                            else:
                                # Fallback: use the last control in left panel
                                quality_control = left_panel_controls[-1]['control']
                        
                        if quality_control:
                            # Check current value first
                            try:
                                current_value = quality_control.window_text().strip()
                                target_value = str(self._export_quality)
                                
                                if current_value == target_value:
                                    logger.debug(f"✓ Quality already set to {target_value}, skipping")
                                else:
                                    quality_control.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    send_keys(target_value)
                                    logger.debug(f"✓ Changed quality from '{current_value}' to {target_value}")
                            except Exception as e:
                                # If we can't read current value, just set it
                                quality_control.click_input()
                                time.sleep(0.1)
                                send_keys('^a')  # Select all
                                send_keys(str(self._export_quality))
                                logger.debug(f"✓ Set quality to {self._export_quality} (couldn't verify current value)")
                        else:
                            logger.debug("Could not find quality control")
                    except Exception as e:
                        logger.debug(f"Error setting quality: {e}")
                
                # Set prefix if provided
                if hasattr(self, '_export_prefix') and self._export_prefix:
                    try:
                        prefix_control = None
                        
                        # Prefix is typically the first control in the left panel
                        if left_panel_controls:
                            prefix_control = left_panel_controls[0]['control']
                        
                        if prefix_control:
                            # Check current value first
                            try:
                                current_value = prefix_control.window_text().strip()
                                target_value = self._export_prefix
                                
                                if current_value == target_value:
                                    logger.debug(f"✓ Prefix already set to '{target_value}', skipping")
                                else:
                                    prefix_control.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    send_keys(target_value)
                                    logger.debug(f"✓ Changed prefix from '{current_value}' to '{target_value}'")
                            except Exception as e:
                                # If we can't read current value, just set it
                                prefix_control.click_input()
                                time.sleep(0.1)
                                send_keys('^a')  # Select all
                                send_keys(self._export_prefix)
                                logger.debug(f"✓ Set prefix to '{self._export_prefix}' (couldn't verify current value)")
                        else:
                            logger.debug("Could not find prefix control")
                    except Exception as e:
                        logger.debug(f"Error setting prefix: {e}")
                
                # Set suffix if provided
                if hasattr(self, '_export_suffix') and self._export_suffix is not None:
                    try:
                        suffix_control = None
                        
                        # Suffix is typically the second control in the left panel
                        if left_panel_controls and len(left_panel_controls) >= 2:
                            suffix_control = left_panel_controls[1]['control']
                        
                        if suffix_control:
                            # Check current value first
                            try:
                                current_value = suffix_control.window_text().strip()
                                
                                # Determine target value based on suffix mode
                                if self._export_suffix == "1":
                                    target_value = "1"
                                elif self._export_suffix == "0":
                                    target_value = ""
                                else:
                                    target_value = self._export_suffix
                                
                                if current_value == target_value:
                                    logger.debug(f"✓ Suffix already set to '{target_value}', skipping")
                                else:
                                    suffix_control.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    
                                    if self._export_suffix == "0":
                                        send_keys('{DELETE}')  # Clear field
                                        logger.debug(f"✓ Changed suffix from '{current_value}' to '' (cleared)")
                                    else:
                                        send_keys(target_value)
                                        logger.debug(f"✓ Changed suffix from '{current_value}' to '{target_value}'")
                            except Exception as e:
                                # If we can't read current value, just set it as before
                                if self._export_suffix == "1":
                                    suffix_control.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    send_keys("1")  # Set value to "1"
                                    logger.debug("✓ Set suffix to '1' (couldn't verify current value)")
                                
                                elif self._export_suffix == "0":
                                    # For "0", clear the suffix field
                                    suffix_control.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    send_keys('{DELETE}')  # Clear field
                                    logger.debug("✓ Cleared suffix field (couldn't verify current value)")
                                
                                else:
                                    # Set custom suffix string
                                    suffix_control.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    send_keys(self._export_suffix)
                                    logger.debug(f"✓ Set suffix to '{self._export_suffix}' (couldn't verify current value)")
                        else:
                            logger.debug("Could not find suffix control")
                    except Exception as e:
                        logger.debug(f"Error setting suffix: {e}")
                
                # Press Enter or click Save to confirm (if auto_confirm is True)
                if auto_confirm:
                    time.sleep(0.1)
                    send_keys('{ENTER}')
                
            except Exception as e:
                logger.error(f"Error setting export parameters: {e}")
                # Continue with export even if parameters couldn't be set
                if auto_confirm:
                    send_keys('{ENTER}')

        def _find_export_field(self, field_type: str, export_dialog):
            """Legacy method kept for compatibility - now using position-based detection in _set_export_parameters"""
            logger.debug(f"_find_export_field called for {field_type} - this method is deprecated")
            return None

        @log("Setting processing options", "Processing options set", level=Level.DEBUG)
        def set_processing_options(self, scale: Optional[Scale] = None, mode: Optional[Mode] = None) -> None:
            if scale:
                self._set_scale(scale)
            if mode:
                self._set_mode(mode)

        def _set_scale(self, scale: Scale):
            if self.scale == scale:
                return

            try:
                logger.debug(f"Setting scale to {scale.value}")
                
                # The scale buttons (1x, 2x, 4x, 6x, Custom) are in a horizontal panel under "Upscale"
                # Try multiple approaches to find the scale button
                
                scale_button = None
                
                # Method 1: Try direct title match
                try:
                    scale_button = self._main_window.child_window(title=scale.value)
                except ElementNotFoundError:
                    pass
                
                # Method 2: Try with different control types
                if scale_button is None:
                    for control_type in ["Button", "RadioButton", None]:
                        try:
                            if control_type:
                                scale_button = self._main_window.child_window(
                                    title=scale.value, 
                                    control_type=control_type
                                )
                            else:
                                scale_button = self._main_window.child_window(title=scale.value)
                            break
                        except ElementNotFoundError:
                            continue
                
                # Method 3: Search more deeply in the UI hierarchy
                if scale_button is None:
                    try:
                        # Try to find the Upscale section first, then look for the button within it
                        upscale_section = self._main_window.child_window(title="Upscale")
                        scale_button = upscale_section.child_window(title=scale.value)
                        logger.debug(f"Found scale button in Upscale section: {scale.value}")
                    except ElementNotFoundError:
                        pass
                
                # Method 4: Try finding any button that contains the scale value
                if scale_button is None:
                    try:
                        scale_button = self._main_window.child_window(title_re=f".*{scale.value}.*", control_type="Button")
                        logger.debug(f"Found scale button with regex: .*{scale.value}.*")
                    except ElementNotFoundError:
                        pass
                
                if scale_button is None:
                    raise ElementNotFound(f"Scale button {scale.value} not found")
                
                # Click the scale button with verification
                logger.debug(f"Attempting to click scale button: {scale.value}")
                try:
                    # Try different click methods
                    try:
                        scale_button.click_input()
                        logger.debug(f"✓ Clicked scale button using click_input()")
                    except:
                        try:
                            scale_button.click()
                            logger.debug(f"✓ Clicked scale button using click()")
                        except:
                            # Fallback: try to set focus and use space/enter
                            scale_button.set_focus()
                            import time
                            time.sleep(0.1)
                            from pywinauto.keyboard import send_keys
                            send_keys(' ')  # Space to activate button
                            logger.debug(f"✓ Activated scale button using keyboard")
                    
                    self.scale = scale
                    logger.debug(f"✓ Scale successfully set to {scale.value}")
                    
                    # Cache the button for future use
                    self._scale_buttons[scale] = scale_button
                    
                except Exception as click_error:
                    logger.error(f"Failed to click scale button {scale.value}: {click_error}")
                    raise ElementNotFound(f"Scale button {scale.value} found but could not be clicked: {click_error}")
                
            except ElementNotFoundError:
                raise ElementNotFound(f"Scale button {scale.value} not found")

        def _set_mode(self, mode: Mode) -> None:
            if self.mode == mode:
                return

            try:
                if mode not in self._mode_buttons:
                    # Try multiple control types
                    for control_type in ["Button", "RadioButton", None]:
                        try:
                            if control_type:
                                self._mode_buttons[mode] = self._main_window.child_window(
                                    title=mode.value, 
                                    control_type=control_type
                                )
                            else:
                                self._mode_buttons[mode] = self._main_window.child_window(title=mode.value)
                            break
                        except ElementNotFoundError:
                            continue
                    
                    if mode not in self._mode_buttons:
                        raise ElementNotFoundError
                        
                self._mode_buttons[mode].click_input()
                self.mode = mode
                logger.debug(f"Mode set to {mode.value}")
            except ElementNotFoundError:
                # Try alternative UI element names
                alternative_names = {
                    Mode.STANDARD: ["Standard", "standard", "Standard v2"],
                    Mode.HIGH_FIDELITY: ["High fidelity", "High Fidelity", "high fidelity", "HiFi"],
                    Mode.LOW_RESOLUTION: ["Low res", "Low resolution", "low res", "Low Res"],
                    Mode.TEXT_AND_SHAPES: ["Text & shapes", "Text and shapes", "text & shapes", "Text"],
                    Mode.ART_AND_CG: ["Art & CG", "Art and CG", "art & cg", "CGI"],
                    Mode.RECOVERY: ["Recovery", "recovery", "Face Recovery"]
                }
                
                found = False
                for alt_name in alternative_names.get(mode, []):
                    for control_type in ["Button", "RadioButton", None]:
                        try:
                            if control_type:
                                alt_button = self._main_window.child_window(
                                    title=alt_name,
                                    control_type=control_type
                                )
                            else:
                                alt_button = self._main_window.child_window(title=alt_name)
                            alt_button.click_input()
                            self._mode_buttons[mode] = alt_button
                            self.mode = mode
                            logger.debug(f"Mode set to {mode.value} using alternative: {alt_name}, type: {control_type}")
                            found = True
                            break
                        except ElementNotFoundError:
                            continue
                    if found:
                        break
                
                if not found:
                    logger.error(f"Could not find mode button for {mode.value} - trying to continue anyway")
                    # Don't raise exception, just log and continue
                    # raise ElementNotFound(f"Mode button {mode.value} not found")

        def _print_elements(self):
            self._main_window.print_control_identifiers()
        
        @log("Setting advanced processing options", "Advanced processing options set", level=Level.DEBUG)
        def set_advanced_processing_options(self, parameters: ProcessingParameters) -> None:
            """Set processing options using the new parameter system"""
            # Set scale if specified
            if parameters.scale:
                self._set_scale_advanced(parameters.scale)
            
            # Set model-specific parameters
            self._set_model_parameters(parameters)
        
        def _set_scale_advanced(self, scale: str):
            """Set scale using string value (supports scale, width, height)"""
            try:
                # Check if it's a width or height parameter
                if scale.startswith('w') or scale.startswith('h'):
                    self._set_dimension(scale)
                    return
                
                # Convert string to Scale enum for backward compatibility
                scale_enum = None
                for s in Scale:
                    if s.value == scale:
                        scale_enum = s
                        break
                
                if scale_enum:
                    # Use standard scale button (1x, 2x, 4x, 6x)
                    self._set_scale(scale_enum)
                else:
                    # Custom scale value - use the Scale factor input field
                    logger.debug(f"Setting custom scale factor: {scale}")
                    import time  # Ensure time is imported
                    
                    # Find and set the Scale factor input field directly
                    scale_factor_set = False
                    
                    # Method 1: Look for Scale factor text and find nearby Edit control
                    try:
                        # Find the "Scale factor" text element
                        scale_texts = self._main_window.descendants(control_type="Text")
                        scale_factor_text = None
                        
                        for text in scale_texts:
                            try:
                                if text.element_info.name and "Scale factor" in text.element_info.name:
                                    scale_factor_text = text
                                    break
                            except:
                                continue
                        
                        if scale_factor_text:
                            # Get position of the text
                            text_rect = scale_factor_text.rectangle()
                            
                            # Find Edit controls near this text (to the right)
                            all_edits = self._main_window.descendants(control_type="Edit")
                            for edit in all_edits:
                                try:
                                    edit_rect = edit.rectangle()
                                    # Check if edit is to the right of text and at similar height
                                    if (edit_rect.left > text_rect.left and 
                                        edit_rect.left < text_rect.left + 200 and
                                        abs(edit_rect.top - text_rect.top) < 50):
                                        
                                        # Check current value first
                                        try:
                                            current_value = edit.window_text().strip()
                                            target_value = str(scale)
                                            
                                            if current_value == target_value:
                                                logger.debug(f"✓ Scale factor already set to {target_value}, skipping")
                                            else:
                                                # Click the input field to activate it
                                                edit.click_input()
                                                time.sleep(0.1)
                                                
                                                # Select all and type new value
                                                send_keys('^a')  # Select all
                                                time.sleep(0.1)
                                                send_keys(scale)  # Type the scale value
                                                time.sleep(0.1)
                                                send_keys('{ENTER}')  # Confirm
                                                
                                                logger.debug(f"✓ Changed scale factor from '{current_value}' to {scale} using input field near 'Scale factor' text")
                                        except Exception as e:
                                            # If we can't read current value, just set it
                                            edit.click_input()
                                            time.sleep(0.1)
                                            send_keys('^a')  # Select all
                                            time.sleep(0.1)
                                            send_keys(scale)  # Type the scale value
                                            time.sleep(0.1)
                                            send_keys('{ENTER}')  # Confirm
                                            logger.debug(f"✓ Set scale factor to {scale} using input field near 'Scale factor' text (couldn't verify current value)")
                                        scale_factor_set = True
                                        break
                                except Exception as e:
                                    logger.debug(f"Error with edit control: {e}")
                                    continue
                    except Exception as e:
                        logger.debug(f"Method 1 failed: {e}")
                    
                    # Method 2: Try the second Edit control (based on user feedback)
                    if not scale_factor_set:
                        try:
                            all_edits = self._main_window.descendants(control_type="Edit")
                            if len(all_edits) >= 2:
                                # Try the second edit control (index 1)
                                edit = all_edits[1]
                                logger.debug("Trying second Edit control based on user feedback")
                                
                                # Check current value first
                                try:
                                    current_value = edit.window_text().strip()
                                    target_value = str(scale)
                                    
                                    if current_value == target_value:
                                        logger.debug(f"✓ Scale factor already set to {target_value}, skipping")
                                    else:
                                        # Click the input field to activate it
                                        edit.click_input()
                                        time.sleep(0.1)
                                        
                                        # Select all and type new value
                                        send_keys('^a')  # Select all
                                        time.sleep(0.1)
                                        send_keys(scale)  # Type the scale value
                                        time.sleep(0.1)
                                        send_keys('{ENTER}')  # Confirm
                                        
                                        logger.debug(f"✓ Changed scale factor from '{current_value}' to {scale} using second Edit control")
                                except Exception as e:
                                    # If we can't read current value, just set it
                                    edit.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    time.sleep(0.1)
                                    send_keys(scale)  # Type the scale value
                                    time.sleep(0.1)
                                    send_keys('{ENTER}')  # Confirm
                                    logger.debug(f"✓ Set scale factor to {scale} using second Edit control (couldn't verify current value)")
                                scale_factor_set = True
                        except Exception as e:
                            logger.debug(f"Method 2 (second Edit control) failed: {e}")
                    
                    # Method 3: Try to find by looking for numeric Edit controls
                    if not scale_factor_set:
                        try:
                            all_edits = self._main_window.descendants(control_type="Edit")
                            for i, edit in enumerate(all_edits):
                                try:
                                    # Check if it's visible and enabled
                                    if edit.is_visible() and edit.is_enabled():
                                        current_value = ""
                                        try:
                                            current_value = edit.get_value()
                                        except:
                                            pass
                                        
                                        
                                        # Check if it looks like a scale input (numeric or empty)
                                        if current_value == "" or (current_value.replace(".", "").replace(",", "").isdigit()):
                                            target_value = str(scale)
                                            
                                            if current_value == target_value:
                                                logger.debug(f"✓ Scale factor already set to {target_value}, skipping")
                                                scale_factor_set = True
                                                break
                                            else:
                                                # Try to click and set value
                                                edit.click_input()
                                                time.sleep(0.1)
                                                
                                                send_keys('^a')  # Select all
                                                time.sleep(0.1)
                                                send_keys(scale)  # Type the scale value
                                                time.sleep(0.1)
                                                send_keys('{ENTER}')  # Confirm
                                                
                                                logger.debug(f"✓ Changed scale factor from '{current_value}' to {scale} using Edit control {i}")
                                                scale_factor_set = True
                                                break
                                except:
                                    continue
                        except Exception as e:
                            logger.debug(f"Method 3 failed: {e}")
                    
                    # Method 4: Click Custom button first, then try to find the input
                    if not scale_factor_set:
                        try:
                            custom_button = self._main_window.child_window(title="Custom", control_type="Button")
                            custom_button.click_input()
                            logger.debug("Clicked Custom button")
                            time.sleep(0.2)
                            
                            # Now try to find any active Edit control
                            all_edits = self._main_window.descendants(control_type="Edit")
                            for edit in all_edits:
                                try:
                                    if edit.has_keyboard_focus() or edit.is_enabled():
                                        edit.click_input()
                                        time.sleep(0.1)
                                        send_keys('^a' + scale + '{ENTER}')
                                        logger.debug(f"✓ Set scale factor to {scale} after clicking Custom")
                                        scale_factor_set = True
                                        break
                                except:
                                    continue
                        except:
                            pass
                    
                    if not scale_factor_set:
                        raise ElementNotFound(f"Could not find Scale factor input field to set custom scale: {scale}")
                        
                    logger.debug(f"✓ Custom scale successfully set to {scale}")
                    
            except ElementNotFoundError as e:
                raise ElementNotFound(f"Scale setting failed for {scale}: {e}")
        
        def _set_dimension(self, dimension: str):
            """Set width or height dimension"""
            import time
            
            try:
                dimension_type = dimension[0]  # 'w' or 'h'
                dimension_value = dimension[1:]  # numeric value
                
                logger.debug(f"Setting {dimension_type}{'width' if dimension_type == 'w' else 'height'} to {dimension_value}")
                
                # Find the appropriate input field
                # Look for Width or Height text elements and nearby edit controls
                all_texts = self._main_window.descendants(control_type="Text")
                target_text = "Width" if dimension_type == 'w' else "Height"
                
                dimension_text = None
                for text in all_texts:
                    try:
                        if text.element_info.name and target_text in text.element_info.name:
                            dimension_text = text
                            break
                    except:
                        continue
                
                if dimension_text:
                    # Get position of the text
                    text_rect = dimension_text.rectangle()
                    
                    # Find Edit controls near this text (to the right)
                    all_edits = self._main_window.descendants(control_type="Edit")
                    for edit in all_edits:
                        try:
                            edit_rect = edit.rectangle()
                            # Check if edit is to the right of text and at similar height
                            if (edit_rect.left > text_rect.left and 
                                edit_rect.left < text_rect.left + 200 and
                                abs(edit_rect.top - text_rect.top) < 50):
                                
                                # Check current value first
                                try:
                                    current_value = edit.window_text().strip()
                                    target_value = str(dimension_value)
                                    
                                    if current_value == target_value:
                                        logger.debug(f"✓ {target_text} already set to {target_value}, skipping")
                                    else:
                                        # Click the input field to activate it
                                        edit.click_input()
                                        time.sleep(0.1)
                                        
                                        # Select all and type new value
                                        send_keys('^a')  # Select all
                                        time.sleep(0.1)
                                        send_keys(dimension_value)  # Type the dimension value
                                        time.sleep(0.1)
                                        send_keys('{ENTER}')  # Confirm
                                        
                                        logger.debug(f"✓ Changed {target_text.lower()} from '{current_value}' to {dimension_value}")
                                except Exception as e:
                                    # If we can't read current value, just set it
                                    edit.click_input()
                                    time.sleep(0.1)
                                    send_keys('^a')  # Select all
                                    time.sleep(0.1)
                                    send_keys(dimension_value)  # Type the dimension value
                                    time.sleep(0.1)
                                    send_keys('{ENTER}')  # Confirm
                                    logger.debug(f"✓ Set {target_text.lower()} to {dimension_value} (couldn't verify current value)")
                                return
                        except Exception as e:
                            logger.debug(f"Error with edit control: {e}")
                            continue
                
                # Fallback: try to find any edit field that might be for dimensions
                logger.debug(f"Could not find {target_text} text, trying fallback method")
                all_edits = self._main_window.descendants(control_type="Edit")
                for edit in all_edits:
                    try:
                        current_value = edit.get_value()
                        # Look for numeric values that might be dimensions
                        if current_value and current_value.isdigit():
                            target_value = str(dimension_value)
                            
                            if current_value == target_value:
                                logger.debug(f"✓ Dimension already set to {target_value}, skipping")
                                return
                            else:
                                edit.click_input()
                                time.sleep(0.1)
                                send_keys('^a' + dimension_value + '{ENTER}')
                                logger.debug(f"✓ Changed dimension from '{current_value}' to {dimension_value} using fallback method")
                                return
                    except:
                        continue
                        
                raise ElementNotFound(f"Could not find {target_text} input field")
                
            except Exception as e:
                raise ElementNotFound(f"Failed to set {dimension}: {e}")
        
        def _set_model_parameters(self, parameters: ProcessingParameters):
            """Set model-specific parameters in the UI"""
            model = parameters.model
            
            # For v2.0, we primarily use legacy mode mapping since the new models
            # need to be mapped to the existing Gigapixel AI interface
            logger.debug(f"Setting model: {model.display_name} (using legacy mapping)")
            
            # Always use legacy mapping for reliability
            self._set_model_via_legacy_mapping(model)
            
            # Set individual parameters if the legacy UI supports them
            # Note: Most parameters will be ignored by legacy modes, but we log them
            # Skip parameters with default values (0.0) to avoid unnecessary warnings
            for param_name, param_value in parameters.parameters.items():
                # Skip default/zero values
                if isinstance(param_value, (int, float)) and param_value == 0.0:
                    continue
                logger.debug(f"Parameter {param_name} = {param_value} (may not be applied in legacy mode)")
                self._set_parameter_value(param_name, param_value)
        
        def _set_parameter_value(self, param_name: str, value: Any):
            """Set a specific parameter value in the UI"""
            try:
                param_control = None
                
                # For the main parameters (sharpen, denoise, fix_compression), find by position after PPI ComboBox
                if param_name in ["sharpen", "denoise", "fix_compression"]:
                    param_control = self._find_parameter_control_after_ppi(param_name)
                elif param_name in ["version", "enhancement", "creativity"]:
                    # Generative model button parameters (version: v1/v2, enhancement: None/Subtle, creativity: Low/Med/High/Max)
                    self._set_generative_button_parameter(param_name, value)
                    return
                elif param_name in ["detail", "texture", "prompt"]:
                    # Generative model numeric/text parameters - find Edit controls after the buttons
                    param_control = self._find_generative_numeric_control(param_name)
                    if getattr(self, '_debug_ui_mode', False) and param_control:
                        logger.debug(f"Found {param_name} control, will set value: {value}")
                elif param_name == "face_recovery":
                    # Face recovery - find it by searching all CheckBox controls after parameter controls
                    # Based on debugging, Face recovery is typically control #19 in the list
                    try:
                        # Get all visible CheckBox controls in the main window
                        checkboxes = []
                        for ctrl in self._main_window.descendants(control_type="CheckBox"):
                            try:
                                if ctrl.is_visible() and ctrl.is_enabled():
                                    checkboxes.append(ctrl)
                            except:
                                pass
                        
                        # Sort by position (top to bottom, then left to right)
                        checkboxes.sort(key=lambda c: (c.rectangle().top, c.rectangle().left))
                        
                        # Find the Face recovery checkbox using specific positioning rules
                        # 1. X coordinates should be >= PPI ComboBox x coordinates  
                        # 2. Should be located in the lower half of the screen
                        ppi_combobox = None
                        ppi_rect = None
                        screen_height = 0
                        
                        try:
                            ppi_combobox = self._main_window.child_window(title="PPI", control_type="ComboBox")
                            ppi_rect = ppi_combobox.rectangle()
                        except:
                            pass
                        
                        # Get screen height for lower half check
                        try:
                            main_rect = self._main_window.rectangle()
                            screen_height = main_rect.bottom
                        except:
                            screen_height = 1080  # Default fallback
                        
                        face_recovery_checkbox = None
                        
                        # Apply specific positioning rules for Face recovery
                        for checkbox in checkboxes:
                            try:
                                cb_rect = checkbox.rectangle()
                                
                                # Rule 1: X coordinates should be >= PPI x coordinates
                                if ppi_rect and cb_rect.left < ppi_rect.left:
                                    continue
                                
                                # Rule 2: Should be in lower half of screen
                                if cb_rect.top < (screen_height / 2):
                                    continue
                                
                                # If both rules pass, this is likely Face recovery
                                face_recovery_checkbox = checkbox
                                logger.debug(f"Found Face recovery candidate at Rect:({cb_rect.left},{cb_rect.top},{cb_rect.right},{cb_rect.bottom})")
                                break
                                
                            except:
                                pass
                        
                        # If positioning rules fail, DO NOT use unreliable fallback
                        if not face_recovery_checkbox:
                            logger.debug(f"Face recovery not found by positioning rules. PPI x-coord requirement: >={ppi_rect.left if ppi_rect else 'unknown'}")
                            logger.debug(f"Screen height: {screen_height}, lower half requirement: >{screen_height/2}")
                            # Log what checkboxes we found that didn't meet criteria
                            for checkbox in checkboxes:
                                try:
                                    cb_rect = checkbox.rectangle()
                                    reasons = []
                                    if ppi_rect and cb_rect.left < ppi_rect.left:
                                        reasons.append(f"x too small ({cb_rect.left} < {ppi_rect.left})")
                                    if cb_rect.top < (screen_height / 2):
                                        reasons.append(f"y too small ({cb_rect.top} < {screen_height/2})")
                                    if reasons:
                                        logger.debug(f"  Rejected checkbox at Rect:({cb_rect.left},{cb_rect.top},{cb_rect.right},{cb_rect.bottom}) - {', '.join(reasons)}")
                                except:
                                    pass
                            # Return early - will trigger debug mode below
                            logger.warning("Face recovery checkbox not found by positioning rules - will trigger debug mode")
                            face_recovery_checkbox = None
                        
                        if face_recovery_checkbox and isinstance(value, bool):
                            # Use direct coordinate clicking for Face recovery toggle
                            rect = face_recovery_checkbox.rectangle()
                            center_x = (rect.left + rect.right) // 2
                            center_y = (rect.top + rect.bottom) // 2
                            
                            logger.debug(f"Found Face recovery checkbox at Rect:({rect.left},{rect.top},{rect.right},{rect.bottom})")
                            
                            # Try pyautogui first, then fallback to win32api
                            click_success = False
                            
                            try:
                                import pyautogui
                                logger.debug(f"Using pyautogui to click Face recovery at ({center_x}, {center_y})")
                                pyautogui.click(center_x, center_y)
                                click_success = True
                            except ImportError:
                                # Fallback to win32api
                                try:
                                    import win32api
                                    import win32con
                                    logger.debug(f"Using win32api to click Face recovery at ({center_x}, {center_y})")
                                    win32api.SetCursorPos((center_x, center_y))
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                                    click_success = True
                                except ImportError:
                                    logger.warning("Neither pyautogui nor win32api available for coordinate clicking")
                            
                            if click_success:
                                logger.debug(f"Face recovery coordinate click completed")
                                logger.debug(f"Parameter face_recovery set to {value}")
                                return  # Skip the normal parameter setting logic
                            
                    except Exception as e:
                        logger.warning(f"Coordinate clicking failed for face_recovery: {e}")
                        # Fall back to normal control methods below
                    
                    # If coordinate clicking failed, fall back to normal control finding
                    if param_control is None:
                        param_control = self._find_parameter_control_after_ppi("face_recovery", control_type="CheckBox", offset=3)
                else:
                    # For other parameters, try title-based lookup
                    display_name = param_name.title().replace('_', ' ')
                    try:
                        param_control = self._main_window.child_window(title=display_name, control_type="Edit")
                    except ElementNotFoundError:
                        try:
                            param_control = self._main_window.child_window(title=display_name)
                        except ElementNotFoundError:
                            pass
                
                # Debug mode - show all available controls if none found
                if param_control is None:
                    logger.warning(f"Could not find UI control for parameter: {param_name}")
                    return
                
                # Set the value based on type
                if isinstance(value, bool):
                    # Handle checkbox/toggle - try comprehensive methods
                    methods_tried = []
                    success = False
                    
                    # Method 1: Try standard check/uncheck
                    if not success:
                        try:
                            if value:
                                param_control.check()
                            else:
                                param_control.uncheck()
                            methods_tried.append("check/uncheck - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"check/uncheck - FAILED: {e}")
                    
                    # Method 2: Try toggle method
                    if not success:
                        try:
                            current_state = param_control.get_toggle_state()
                            if (value and current_state == 0) or (not value and current_state == 1):
                                param_control.toggle()
                            methods_tried.append("toggle - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"toggle - FAILED: {e}")
                    
                    # Method 3: Simple click to toggle
                    if not success:
                        try:
                            param_control.click()
                            methods_tried.append("click - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"click - FAILED: {e}")
                    
                    # Method 4: Try setting as a property
                    if not success:
                        try:
                            param_control.set_check_state(1 if value else 0)
                            methods_tried.append("set_check_state - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"set_check_state - FAILED: {e}")
                    
                    # Method 5: Try double-click
                    if not success:
                        try:
                            param_control.double_click()
                            methods_tried.append("double_click - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"double_click - FAILED: {e}")
                    
                    # Method 6: Try right-click menu
                    if not success:
                        try:
                            param_control.right_click()
                            methods_tried.append("right_click - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"right_click - FAILED: {e}")
                    
                    # Method 7: Try keyboard space
                    if not success:
                        try:
                            param_control.set_focus()
                            param_control.type_keys(" ")  # Space key to toggle
                            methods_tried.append("space_key - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"space_key - FAILED: {e}")
                    
                    # Method 8: Try send_message
                    if not success:
                        try:
                            # BM_SETCHECK message for checkbox
                            param_control.send_message(0x00F1, 1 if value else 0, 0)
                            methods_tried.append("send_message - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"send_message - FAILED: {e}")
                    
                    # Method 9: Try invoke pattern
                    if not success:
                        try:
                            # UI Automation invoke pattern
                            param_control.invoke()
                            methods_tried.append("invoke - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"invoke - FAILED: {e}")
                    
                    # Method 10: Try automation pattern
                    if not success:
                        try:
                            # Direct automation element manipulation
                            element = param_control.element_info.element
                            toggle_pattern = element.GetCurrentPattern(10010)  # Toggle pattern
                            toggle_pattern.Toggle()
                            methods_tried.append("automation_toggle - SUCCESS")
                            success = True
                        except Exception as e:
                            methods_tried.append(f"automation_toggle - FAILED: {e}")
                    
                    if not success:
                        logger.warning(f"All checkbox methods failed for {param_name}. Methods tried: {methods_tried}")
                    else:
                        logger.debug(f"Successfully toggled {param_name} using one of the methods")
                elif isinstance(value, (int, float)):
                    # Handle slider/input field - check current value first
                    try:
                        # Check current value to avoid unnecessary operations
                        try:
                            current_value = param_control.window_text().strip()
                            if not current_value:
                                current_value = param_control.get_value()
                        except:
                            current_value = ""
                        
                        target_value = str(value)
                        
                        if current_value == target_value:
                            logger.debug(f"✓ Parameter {param_name} already set to {target_value}, skipping")
                        else:
                            # Try multiple methods to set the value
                            try:
                                # Method 1: Try set_value for sliders
                                param_control.set_value(str(value))
                                logger.debug(f"✓ Changed parameter {param_name} from '{current_value}' to {value} using set_value")
                            except:
                                try:
                                    # Method 2: Try set_text for input fields
                                    param_control.set_text(str(value))
                                    logger.debug(f"✓ Changed parameter {param_name} from '{current_value}' to {value} using set_text")
                                except:
                                    try:
                                        # Method 3: Try type_keys for text entry
                                        param_control.click()
                                        param_control.type_keys("^a" + str(value))
                                        logger.debug(f"✓ Changed parameter {param_name} from '{current_value}' to {value} using type_keys")
                                    except Exception as inner_e:
                                        logger.debug(f"✓ Set parameter {param_name} to {value} (couldn't verify current value, failed all methods: {inner_e})")
                                        raise Exception(f"Failed all value setting methods: {inner_e}")
                    except Exception as e:
                        raise Exception(f"Failed to set parameter {param_name}: {e}")
                elif isinstance(value, str):
                    # Handle text input - check current value first
                    # Check current value to avoid unnecessary operations
                    try:
                        current_value = param_control.window_text().strip()
                        if not current_value:
                            current_value = param_control.get_value()
                    except:
                        current_value = ""
                    
                    target_value = str(value).strip()
                    
                    if current_value == target_value:
                        logger.debug(f"✓ Parameter {param_name} already set to '{target_value}', skipping")
                    else:
                        try:
                            param_control.set_text(value)
                            logger.debug(f"✓ Changed parameter {param_name} from '{current_value}' to '{value}' using set_text")
                        except Exception as e:
                            # Fallback to type_keys
                            param_control.click()
                            param_control.type_keys("^a" + value)
                            logger.debug(f"✓ Changed parameter {param_name} from '{current_value}' to '{value}' using type_keys")
                
                logger.debug(f"Parameter {param_name} set to {value}")
                
                
            except Exception as e:
                logger.warning(f"Could not set parameter {param_name}: {e}")
        
        def _find_parameter_control_after_ppi(self, param_name: str, control_type: str = "Edit", offset: int = None):
            """Find parameter controls by their position after the PPI ComboBox"""
            try:
                # Find the PPI ComboBox first
                ppi_combobox = None
                try:
                    ppi_combobox = self._main_window.child_window(title="PPI", control_type="ComboBox")
                except ElementNotFoundError:
                    return None
                
                if not ppi_combobox:
                    return None
                
                # Get all controls of the specified type and find those after the PPI ComboBox
                target_controls = []
                try:
                    for ctrl in self._main_window.descendants(control_type=control_type):
                        try:
                            if ctrl.is_visible() and ctrl.is_enabled():
                                target_controls.append(ctrl)
                        except:
                            pass
                except:
                    return None
                
                # Sort controls by position (top to bottom, left to right)
                ppi_rect = ppi_combobox.rectangle()
                controls_after_ppi = []
                
                for ctrl in target_controls:
                    try:
                        ctrl_rect = ctrl.rectangle()
                        # Check if control is positioned after (below or to the right of) PPI ComboBox
                        if ctrl_rect.top > ppi_rect.top or (ctrl_rect.top == ppi_rect.top and ctrl_rect.left > ppi_rect.right):
                            controls_after_ppi.append(ctrl)
                    except:
                        pass
                
                # Sort by position (top to bottom, then left to right)
                controls_after_ppi.sort(key=lambda c: (c.rectangle().top, c.rectangle().left))
                
                # If offset is provided, use it directly
                if offset is not None:
                    if offset < len(controls_after_ppi):
                        return controls_after_ppi[offset]
                    return None
                
                # Map parameter names to their index in the sequence (for Edit controls)
                param_index = {
                    "sharpen": 0,        # First Edit control after PPI
                    "denoise": 1,        # Second Edit control after PPI  
                    "fix_compression": 2  # Third Edit control after PPI
                }
                
                index = param_index.get(param_name)
                if index is not None and index < len(controls_after_ppi):
                    return controls_after_ppi[index]
                
                return None
                
            except Exception as e:
                logger.debug(f"Error finding parameter control after PPI for {param_name}: {e}")
                return None
        
        
        
        def _set_model_via_legacy_mapping(self, model: AIModel):
            """Set model using the new dropdown-based model selection"""
            logger.debug(f"Setting model: {model.display_name}")
            
            # Map new models to their display names in the UI
            model_display_mapping = {
                # Enhance models
                "standard_v2": "Standard",
                "high_fidelity_v2": "High fidelity", 
                "low_resolution_v2": "Low res",
                "text_refine": "Text & shapes",
                "cgi": "Art & CG",
                "redefine": "Redefine",  # Generative model (if exists)
                "redefine_realistic": "Redefine realistic",  # Maps to exact UI model name
                "redefine_creative": "Redefine creative",    # Maps to exact UI model name
                "recover": "Recover",               # Main recover model - UI shows "Recover"
                "recovery": "Recover",              # Legacy alias
                "recovery_v2": "Recover",
                
                # Sharpen models
                "sharpen_standard": "Standard",
                "sharpen_strong": "Standard", 
                "lens_blur": "Standard",
                "lens_blur_v2": "Standard",
                "motion_blur": "Standard",
                "natural": "Standard",
                "refocus": "Standard",
                "super_focus": "Standard",
                "super_focus_v2": "Standard",
                
                # Denoise models
                "denoise_normal": "Standard",
                "denoise_strong": "Standard", 
                "denoise_extreme": "Standard",
                
                # Restore models
                "dust_scratch": "Recovery",
                
                # Lighting models
                "lighting_adjust": "Standard",
                "white_balance": "Standard",
            }
            
            target_model_name = model_display_mapping.get(model.name, "Standard")
            logger.debug(f"Target model: {target_model_name}")
            
            # Check current model first
            current_model = self._get_current_model_name()
            if current_model and current_model.strip() == target_model_name.strip():
                logger.debug(f"✓ Current model '{current_model}' already matches target '{target_model_name}', skipping model change")
                return
            
            logger.debug(f"Current model: '{current_model}' → Target model: '{target_model_name}'")
            
            # Open the model selection dropdown
            dropdown_opened = self._open_model_selection_dropdown()
            
            if dropdown_opened:
                # Try to click the model in the dropdown
                model_selected = self._click_model_in_dropdown(target_model_name)
                
                if not model_selected:
                    # Fallback to legacy mode selection if dropdown method fails
                    logger.warning(f"Could not select {target_model_name} from dropdown, trying legacy mode selection")
                    legacy_mode = self._get_legacy_mode_for_model(model.name)
                    if legacy_mode:
                        self._set_mode(legacy_mode)
            else:
                logger.error("Could not open model selection dropdown")
        
        def _get_current_model_name(self):
            """Get the name of the currently selected model"""
            try:
                # Look for no-title Button followed by Text element pattern
                all_children = self._main_window.descendants()
                
                for i, element in enumerate(all_children):
                    try:
                        element_info = element.element_info
                        
                        # Look for Button with no title
                        if (element_info.control_type == "Button" and 
                            (not element_info.name or element_info.name.strip() == "")):
                            
                            # Check if next element is Text with model name
                            if i + 1 < len(all_children):
                                next_element = all_children[i + 1]
                                next_info = next_element.element_info
                                
                                if (next_info.control_type == "Text" and 
                                    next_info.name and next_info.name.strip()):
                                    
                                    current_model = next_info.name.strip()
                                    logger.debug(f"Found current model: '{current_model}'")
                                    return current_model
                    except:
                        continue
                        
                logger.debug("Could not determine current model name")
                return None
                
            except Exception as e:
                logger.debug(f"Error getting current model name: {e}")
                return None
        
        def _set_generative_button_parameter(self, param_name: str, value: str):
            """Set generative model button parameters (version, enhancement, creativity)"""
            try:
                logger.debug(f"Setting generative button parameter {param_name} = {value}")
                
                # Get all Button controls in the main window
                buttons = []
                for ctrl in self._main_window.descendants(control_type="Button"):
                    try:
                        if ctrl.is_visible() and ctrl.is_enabled():
                            title = ctrl.window_text()
                            buttons.append({
                                'control': ctrl,
                                'title': title,
                                'rect': ctrl.rectangle()
                            })
                    except:
                        pass
                
                # Sort by position (top to bottom, left to right)
                buttons.sort(key=lambda b: (b['rect'].top, b['rect'].left))
                
                # Find the button with matching text
                target_button = None
                if param_name == "version":
                    # For Recover model: v1, v2 buttons
                    for button in buttons:
                        if button['title'].lower() == value.lower():
                            target_button = button['control']
                            break
                elif param_name == "enhancement":
                    # For Redefine realistic model: None, Subtle buttons
                    for button in buttons:
                        if button['title'].lower() == value.lower():
                            target_button = button['control']
                            break
                elif param_name == "creativity":
                    # For Redefine creative model: Low, Medium, High, Max buttons
                    for button in buttons:
                        if button['title'].lower() == value.lower():
                            target_button = button['control']
                            break
                
                if target_button:
                    logger.debug(f"Found {param_name} button: {value}")
                    target_button.click()
                    logger.debug(f"✓ Clicked {param_name} button: {value}")
                else:
                    logger.warning(f"Could not find {param_name} button with value: {value}")
                
            except Exception as e:
                logger.error(f"Error setting generative button parameter {param_name}: {e}")
        
        def _find_generative_numeric_control(self, param_name: str):
            """Find numeric/text Edit controls for generative models (detail, texture, prompt)"""
            try:
                logger.debug(f"Finding control for {param_name}")
                
                # Get all Edit controls in the main window
                edit_controls = []
                for ctrl in self._main_window.descendants(control_type="Edit"):
                    try:
                        if ctrl.is_visible() and ctrl.is_enabled():
                            edit_controls.append(ctrl)
                    except:
                        pass
                
                # Sort by position (top to bottom, left to right)
                edit_controls.sort(key=lambda c: (c.rectangle().top, c.rectangle().left))
                
                # Strategy depends on the parameter type
                if param_name == "prompt":
                    # Prompt field appears below the model-specific buttons
                    # For Redefine realistic: None/Subtle buttons
                    # For Redefine creative: Low/Medium/High/Max buttons
                    buttons = []
                    for ctrl in self._main_window.descendants(control_type="Button"):
                        try:
                            if ctrl.is_visible() and ctrl.is_enabled():
                                title = ctrl.window_text().lower()
                                # Check for both model's buttons
                                if title in ["none", "subtle", "low", "medium", "high", "max"]:
                                    buttons.append(ctrl)
                        except:
                            pass
                    
                    # Find Low button to use as reference for prompt field alignment
                    low_button = None
                    button_bottom = None
                    
                    for ctrl in self._main_window.descendants(control_type="Button"):
                        try:
                            if ctrl.is_visible() and ctrl.is_enabled():
                                title = ctrl.window_text().lower().strip()
                                if "low" in title:
                                    low_button = ctrl
                                    break
                        except:
                            pass
                    
                    if low_button:
                        # Get Low button position for reference
                        low_rect = low_button.rectangle()
                        button_bottom = low_rect.bottom
                        low_x = low_rect.left
                        
                        logger.debug(f"Using Low button reference - X: {low_x}, Bottom: {button_bottom}")
                        
                        # Look for Edit control below the buttons but in the same horizontal area
                        # Debug: log all Edit controls found below buttons
                        logger.debug(f"Looking for prompt field below buttons. Button bottom: {button_bottom}")
                        for ctrl in edit_controls:
                            try:
                                ctrl_rect = ctrl.rectangle()
                                if ctrl_rect.top > button_bottom:
                                    logger.debug(f"  Edit control at Rect:({ctrl_rect.left},{ctrl_rect.top},{ctrl_rect.right},{ctrl_rect.bottom})")
                            except:
                                pass
                        
                        # Strategy 1: Find prompt Edit control aligned with Low button
                        tolerance = 50  # Allow some variation in alignment
                        
                        for ctrl in edit_controls:
                            try:
                                ctrl_rect = ctrl.rectangle()
                                ctrl_width = ctrl_rect.right - ctrl_rect.left
                                ctrl_height = ctrl_rect.bottom - ctrl_rect.top
                                
                                # Prompt control characteristics:
                                # 1. Below the buttons
                                # 2. Aligned near Low button X position
                                # 3. Large width (approximately 400px)
                                # 4. Reasonable height (can be up to 105px for multiline)
                                if (ctrl_rect.top > button_bottom and 
                                    ctrl_rect.top < button_bottom + 200 and
                                    abs(ctrl_rect.left - low_x) < tolerance and  # Near Low button X
                                    ctrl_width > 300 and  # Large width (400px approximately)
                                    ctrl_height > 15 and ctrl_height < 120):  # Reasonable height (up to 105px)
                                    logger.debug(f"Found prompt control (Low-aligned) at Rect:({ctrl_rect.left},{ctrl_rect.top},{ctrl_rect.right},{ctrl_rect.bottom}), width={ctrl_width}")
                                    return ctrl
                            except:
                                pass
                        
                        # Strategy 2: Find the largest Edit control below buttons (fallback)
                        logger.debug("Strategy 1 failed, looking for largest Edit control")
                        largest_ctrl = None
                        largest_area = 0
                        
                        for ctrl in edit_controls:
                            try:
                                ctrl_rect = ctrl.rectangle()
                                ctrl_width = ctrl_rect.right - ctrl_rect.left
                                ctrl_height = ctrl_rect.bottom - ctrl_rect.top
                                ctrl_area = ctrl_width * ctrl_height
                                
                                if (ctrl_rect.top > button_bottom and 
                                    ctrl_rect.top < button_bottom + 200 and
                                    ctrl_width > 200 and  # Must be reasonably large
                                    ctrl_area > largest_area):
                                    largest_ctrl = ctrl
                                    largest_area = ctrl_area
                                    logger.debug(f"  Found large control candidate at Rect:({ctrl_rect.left},{ctrl_rect.top},{ctrl_rect.right},{ctrl_rect.bottom}), area={ctrl_area}")
                            except:
                                pass
                        
                        if largest_ctrl:
                            largest_rect = largest_ctrl.rectangle()
                            logger.debug(f"Selected largest prompt control at Rect:({largest_rect.left},{largest_rect.top},{largest_rect.right},{largest_rect.bottom})")
                            return largest_ctrl
                
                elif param_name == "texture":
                    # Texture control for Redefine creative - positioned after the creativity buttons
                    # Strategy: Find the prompt field first, then look for the next Edit control
                    
                    # First find the creativity buttons to use as reference points
                    low_button = None
                    max_button = None
                    button_bottom = None
                    
                    for ctrl in self._main_window.descendants(control_type="Button"):
                        try:
                            if ctrl.is_visible() and ctrl.is_enabled():
                                title = ctrl.window_text().lower().strip()
                                if "low" in title:
                                    low_button = ctrl
                                elif "max" in title:
                                    max_button = ctrl
                        except:
                            pass
                    
                    if low_button and max_button:
                        # Get button positions for reference
                        low_rect = low_button.rectangle()
                        max_rect = max_button.rectangle()
                        button_bottom = max(low_rect.bottom, max_rect.bottom)
                        
                        logger.debug(f"Using button references - Low: {low_rect.left}, Max: {max_rect.left}, Bottom: {button_bottom}")
                        
                        logger.debug(f"Looking for texture field below buttons. Button bottom: {button_bottom}")
                        
                        # Strategy 1: Look for Edit control aligned with Max button (texture position)
                        # Texture should be near Max button X position and below the buttons
                        max_x = max_rect.left
                        tolerance = 50  # Allow some variation in alignment
                        
                        for ctrl in edit_controls:
                            try:
                                ctrl_rect = ctrl.rectangle()
                                ctrl_width = ctrl_rect.right - ctrl_rect.left
                                ctrl_height = ctrl_rect.bottom - ctrl_rect.top
                                
                                # Look for Edit control that:
                                # 1. Is below the buttons
                                # 2. Is aligned near the Max button X position
                                # 3. Has small dimensions (texture field characteristics)
                                if (ctrl_rect.top > button_bottom and 
                                    ctrl_rect.top < button_bottom + 200 and
                                    abs(ctrl_rect.left - max_x) < tolerance and  # Near Max button X
                                    ctrl_width > 40 and ctrl_width < 100 and  # Small width
                                    ctrl_height > 20 and ctrl_height < 60):   # Small height
                                    logger.debug(f"Found texture control (Max-aligned) at Rect:({ctrl_rect.left},{ctrl_rect.top},{ctrl_rect.right},{ctrl_rect.bottom}), size={ctrl_width}x{ctrl_height}")
                                    return ctrl
                            except:
                                pass
                        
                        # Strategy 2: Look for the smallest Edit control in the parameter area
                        logger.debug("Strategy 1 failed, trying to find smallest Edit control")
                        smallest_ctrl = None
                        smallest_area = float('inf')
                        
                        for ctrl in edit_controls:
                            try:
                                ctrl_rect = ctrl.rectangle()
                                ctrl_width = ctrl_rect.right - ctrl_rect.left
                                ctrl_height = ctrl_rect.bottom - ctrl_rect.top
                                ctrl_area = ctrl_width * ctrl_height
                                
                                # Look for small Edit controls below buttons
                                if (ctrl_rect.top > button_bottom and 
                                    ctrl_rect.top < button_bottom + 300 and
                                    ctrl_width < 100 and ctrl_height < 60 and
                                    ctrl_area < smallest_area):
                                    smallest_ctrl = ctrl
                                    smallest_area = ctrl_area
                                    logger.debug(f"  Found small control candidate at Rect:({ctrl_rect.left},{ctrl_rect.top},{ctrl_rect.right},{ctrl_rect.bottom}), area={ctrl_area}")
                            except:
                                pass
                        
                        if smallest_ctrl:
                            smallest_rect = smallest_ctrl.rectangle()
                            logger.debug(f"Selected smallest texture control at Rect:({smallest_rect.left},{smallest_rect.top},{smallest_rect.right},{smallest_rect.bottom})")
                            return smallest_ctrl
                
                else:
                    # For other parameters (detail), use position-based logic
                    # These are typically after the standard parameters
                    ppi_combobox = None
                    try:
                        ppi_combobox = self._main_window.child_window(title="PPI", control_type="ComboBox")
                        ppi_rect = ppi_combobox.rectangle()
                    except:
                        ppi_rect = None
                    
                    if ppi_rect:
                        # Find Edit controls after the PPI but not in Face recovery area
                        screen_height = self._main_window.rectangle().bottom
                        
                        for ctrl in edit_controls:
                            try:
                                ctrl_rect = ctrl.rectangle()
                                # Should be:
                                # 1. Below PPI area
                                # 2. Not in the lower half of screen (where Face recovery is)
                                if (ctrl_rect.top > ppi_rect.bottom and 
                                    ctrl_rect.top < screen_height / 2 and
                                    ctrl_rect.left >= ppi_rect.left):
                                    logger.debug(f"Found {param_name} control at Rect:({ctrl_rect.left},{ctrl_rect.top},{ctrl_rect.right},{ctrl_rect.bottom})")
                                    return ctrl
                            except:
                                pass
                
                # Fallback: if we can't find by position, return None and trigger interactive debug
                logger.debug(f"Could not find {param_name} control by position logic")
                return None
                
            except Exception as e:
                logger.debug(f"Error finding generative control for {param_name}: {e}")
                return None
        
        def _open_model_selection_dropdown(self):
            """Open the model selection dropdown by clicking the no-title button"""
            import time
            
            logger.debug("Opening model selection dropdown...")
            
            try:
                # Look for the no-title Button that opens the dropdown
                all_children = self._main_window.descendants()
                dropdown_button = None
                
                for i, element in enumerate(all_children):
                    try:
                        element_info = element.element_info
                        
                        # Look for Button with no title
                        if (element_info.control_type == "Button" and 
                            (not element_info.name or element_info.name.strip() == "")):
                            
                            # Check if next element is Text with model name (confirms this is the right button)
                            if i + 1 < len(all_children):
                                next_element = all_children[i + 1]
                                next_info = next_element.element_info
                                
                                if (next_info.control_type == "Text" and 
                                    next_info.name and next_info.name.strip()):
                                    
                                    dropdown_button = element
                                    logger.debug(f"Found dropdown button (no title) followed by model text: '{next_info.name.strip()}'")
                                    break
                    except:
                        continue
                
                if dropdown_button:
                    # Click the dropdown button
                    try:
                        dropdown_button.click_input()
                        logger.debug("✓ Clicked dropdown button")
                        time.sleep(0.2)  # Quick wait for dropdown to open
                        return True
                        
                    except Exception as e:
                        logger.error(f"Failed to click dropdown button: {e}")
                        return False
                else:
                    logger.error("Could not find the no-title dropdown button")
                    return False
                    
            except Exception as e:
                logger.error(f"Error opening model selection dropdown: {e}")
                return False
        
        
        def _click_model_in_dropdown(self, model_name: str) -> bool:
            """Click on a specific model in the opened dropdown"""
            import time
            
            logger.debug(f"Looking for model '{model_name}' in dropdown...")
            
            try:
                # Wait a moment for dropdown to be fully loaded
                time.sleep(0.2)
                
                # Look for "Select a model" text first to confirm dropdown is open
                all_children = self._main_window.descendants()
                found_select_model = False
                model_element = None
                
                for i, element in enumerate(all_children):
                    try:
                        element_info = element.element_info
                        
                        # Look for "Select a model" text
                        if (element_info.control_type == "Text" and 
                            element_info.name and 
                            "Select a model" in element_info.name):
                            found_select_model = True
                            logger.debug("Found 'Select a model' text - dropdown is open")
                            continue
                        
                        # After finding "Select a model", look for the target model
                        if found_select_model:
                            if (element_info.control_type == "Text" and 
                                element_info.name and 
                                element_info.name.strip() == model_name.strip()):
                                model_element = element
                                logger.debug(f"Found model '{model_name}' as Text element")
                                break
                                
                    except:
                        continue
                
                if model_element:
                    # Click the model text element
                    try:
                        model_element.click_input()
                        logger.debug(f"✓ Clicked model '{model_name}' successfully")
                        
                        # Wait for selection to take effect and dropdown to close
                        time.sleep(0.2)
                        return True
                        
                    except Exception as e:
                        logger.error(f"Failed to click model element: {e}")
                        # Automatic selection failed
                        logger.debug("Automatic model selection failed")
                        return False
                else:
                    if not found_select_model:
                        logger.error("Could not find 'Select a model' text - dropdown may not be open")
                    else:
                        logger.error(f"Could not find model '{model_name}' in the dropdown list")
                    
                    # Model selection failed
                    logger.debug("Model selection failed")
                    return False
                
            except Exception as e:
                logger.error(f"Error selecting model from dropdown: {e}")
                # Model selection failed
                return False
        
        def _get_legacy_mode_for_model(self, model_name: str):
            """Get legacy mode mapping for fallback"""
            legacy_mapping = {
                "standard_v2": Mode.STANDARD,
                "high_fidelity_v2": Mode.HIGH_FIDELITY,
                "low_resolution_v2": Mode.LOW_RESOLUTION,
                "text_refine": Mode.TEXT_AND_SHAPES,
                "cgi": Mode.ART_AND_CG,
                "recovery": Mode.RECOVERY,
                "recovery_v2": Mode.RECOVERY,
            }
            return legacy_mapping.get(model_name, Mode.STANDARD)
        
        @log("Saving photo to specific path", "Photo saved to path", level=Level.DEBUG)
        def save_photo_to_path(self, output_path: Path) -> None:
            """Save photo to a specific output path"""
            self._open_export_dialog()
            
            
            logger.debug("Export dialog opened for save_photo_to_path")
            
            # Set export parameters if provided
            if (hasattr(self, '_export_quality') or 
                hasattr(self, '_export_prefix') or 
                hasattr(self, '_export_suffix')):
                logger.debug("Found export parameters, calling _set_export_parameters")
                self._set_export_parameters(auto_confirm=False)  # Don't auto-confirm since we'll do it below
                
            else:
                logger.debug("No export parameters found")
            
            # Set the output path in the save dialog
            try:
                # Use stored output directory if available, otherwise use provided path
                if hasattr(self, '_output_directory') and self._output_directory:
                    final_output_path = self._output_directory
                    logger.debug(f"Using stored output directory: {final_output_path}")
                else:
                    final_output_path = output_path
                    logger.debug(f"Using provided output path: {final_output_path}")
                
                # Clear current path and set new one
                send_keys('^a')  # Select all
                # Normalize path for Windows - ensure single backslashes for Gigapixel app
                normalized_output_path = str(final_output_path).replace('\\\\', '\\')
                clipboard.copy(normalized_output_path)
                send_keys('^v')  # Paste new path
                
                logger.debug(f"Looking for Save button to confirm export...")
                
                # Interactive debugging to find Save button
                if hasattr(self, '_debug_ui_mode') and self._debug_ui_mode:
                    print("\n🔧 DEBUG: Finding Save button in Export dialog")
                    print("Looking for interactive controls...")
                    
                    # Get all potentially interactable elements
                    interactable_elements = []
                    interactable_types = ["Button", "Edit", "ComboBox", "CheckBox"]
                    
                    try:
                        for element in self._main_window.descendants():
                            try:
                                element_info = element.element_info
                                control_type = element_info.control_type
                                
                                if control_type in interactable_types:
                                    title = element_info.name or "<No Title>"
                                    rect = element.rectangle()
                                    visible = element.is_visible()
                                    enabled = element.is_enabled()
                                    
                                    # Filter out elements that aren't useful
                                    if title in ["", " ", "Application", "Window"] and control_type in ["Group", "Pane"]:
                                        continue
                                    
                                    # Look for Save-related buttons specifically
                                    if control_type == "Button" and visible:
                                        title_lower = title.lower()
                                        if 'save' in title_lower or 'export' in title_lower or 'ok' in title_lower:
                                            interactable_elements.append({
                                                'element': element,
                                                'title': title,
                                                'type': control_type,
                                                'rect': rect,
                                                'visible': visible,
                                                'enabled': enabled
                                            })
                            except:
                                continue
                        
                        # Display the Save-related buttons
                        print(f"\nFound {len(interactable_elements)} Save-related buttons:")
                        print("-" * 80)
                        
                        for i, elem_data in enumerate(interactable_elements):
                            status = ""
                            if elem_data['visible'] and elem_data['enabled']:
                                status = "[ACTIVE]"
                            elif elem_data['visible']:
                                status = "[VISIBLE]"
                            else:
                                status = "[HIDDEN]"
                            
                            print(f"{i+1:3d}. {status:9} {elem_data['type']:12} | '{elem_data['title'][:40]:<40}' | Pos: ({elem_data['rect'].left},{elem_data['rect'].top})")
                        
                        print("-" * 80)
                        print("Enter the NUMBER of the Save button to click (or 0 to try automatic detection):")
                        
                        user_input = input("Save button number: ").strip()
                        if user_input and user_input != "0":
                            try:
                                button_num = int(user_input)
                                if 1 <= button_num <= len(interactable_elements):
                                    selected_button = interactable_elements[button_num - 1]['element']
                                    selected_button.click_input()
                                    logger.debug(f"✓ Clicked Save button (user selected: {interactable_elements[button_num - 1]['title']})")
                                    save_button_found = True
                            except:
                                pass
                    except Exception as e:
                        print(f"Error during interactive debugging: {e}")
                
                # Find and click the Save button automatically
                save_button_found = False
                if not save_button_found:
                    try:
                        # Simple approach: Look for Save button directly in main window
                        save_button = self._main_window.child_window(title="Save", control_type="Button")
                        if save_button.exists() and save_button.is_visible() and save_button.is_enabled():
                            save_button.click_input()
                            logger.debug("✓ Clicked Save button")
                            save_button_found = True
                    except Exception as e:
                        logger.debug(f"Could not find Save button with title 'Save': {e}")
                    
                    # Try SaveButton
                    if not save_button_found:
                        try:
                            save_button = self._main_window.child_window(title="SaveButton", control_type="Button")
                            if save_button.exists() and save_button.is_visible() and save_button.is_enabled():
                                save_button.click_input()
                                logger.debug("✓ Clicked SaveButton")
                                save_button_found = True
                        except:
                            pass
                    
                    # Try by automation id
                    if not save_button_found:
                        try:
                            save_button = self._main_window.child_window(auto_id="SaveButton", control_type="Button")
                            if save_button.exists() and save_button.is_visible() and save_button.is_enabled():
                                save_button.click_input()
                                logger.debug("✓ Clicked Save button by automation ID")
                                save_button_found = True
                        except:
                            pass
                    
                    
                # Fallback: Use Enter key
                if not save_button_found:
                    logger.debug("Save button not found, using Enter key as fallback")
                    send_keys('{ENTER}')
                
                # Wait for processing to complete and look for completion buttons
                logger.debug("Waiting for processing to complete...")
                self._wait_for_processing_completion()
                
                self._close_export_dialog()
                
            except Exception as e:
                logger.error(f"Error saving to specific path: {e}")
                # Fallback to regular save
                self.save_photo()

    @log(start="Getting Gigapixel instance...")
    @log(end="Got Gigapixel instance: {}", format=(-1,), level=Level.SUCCESS)
    def _get_gigapixel_instance(self) -> Application:
        try:
            instance = Application(backend="uia").connect(path=self._executable_path)
            return instance
        except ProcessNotFoundError:
            logger.debug("Gigapixel instance not found.")
            instance = self._open_topaz()
            return instance

    @log("Starting new Gigapixel instance...", "Started new Gigapixel instance: {}", format=(-1,), level=Level.DEBUG)
    def _open_topaz(self) -> Application:
        instance = Application(backend="uia").start(str(self._executable_path)).connect(path=self._executable_path)
        return instance

    @log("Checking path: {}", "Path is valid", format=(1,), level=Level.DEBUG)
    def _check_path(self, path: Path) -> None:
        if not path.is_file():
            raise NotFile(f"Path is not a file: {path}")

    @staticmethod
    def _remove_suffix(input_string: str, suffix: str) -> str:
        if suffix and input_string.endswith(suffix):
            return input_string[:-len(suffix)]
        return input_string
    
    def _set_english_layout(self) -> None:
        english_layout = 0x0409
        win32api.LoadKeyboardLayout(hex(english_layout), win32con.KLF_ACTIVATE)

    @log(start="Starting processing: {}", format=(1,))
    @log(end="Finished processing: {}", format=(1,), level=Level.SUCCESS)
    def process(self,
                photo_path: Union[Path, str],
                scale: Optional[Scale] = None,
                mode: Optional[Mode] = None,
                ) -> None:
        """
        Process a photo using Topaz Gigapixel AI

        :param photo_path: Path to the photo to be processed
        :param scale: Scale to be used for processing
        :param mode: Mode to be used for processing
        """
        if isinstance(photo_path, str):
            photo_path = Path(photo_path)
        
        self._set_english_layout()
        self._check_path(photo_path)

        self._app.open_photo(photo_path)
        self._app.set_processing_options(scale, mode)
        self._app.save_photo()
    
    # New enhanced methods for advanced model system
    
    def process_with_model(self,
                          photo_path: Union[Path, str],
                          processing_parameters: ProcessingParameters,
                          output_path: Optional[Union[Path, str]] = None) -> None:
        """
        Process a photo using the advanced model system
        
        :param photo_path: Path to the photo to be processed
        :param processing_parameters: Processing parameters including model and settings
        :param output_path: Optional output path (if different from default)
        """
        if isinstance(photo_path, str):
            photo_path = Path(photo_path)
        
        if output_path and isinstance(output_path, str):
            output_path = Path(output_path)
        
        self._set_english_layout()
        self._check_path(photo_path)
        
        # Create processing job
        job = ProcessingJob(
            input_path=photo_path,
            output_path=output_path,
            parameters=processing_parameters,
            status="processing"
        )
        
        self._current_job = job
        self._notify_callbacks('on_job_start', job)
        
        try:
            self._app.open_photo(photo_path)
            self._app.set_advanced_processing_options(processing_parameters)
            
            if output_path:
                self._app.save_photo_to_path(output_path)
            else:
                self._app.save_photo()
            
            job.status = "completed"
            self._notify_callbacks('on_job_complete', job)
            
        except Exception as e:
            job.status = "error"
            job.error = str(e)
            self._notify_callbacks('on_job_error', job, str(e))
            raise
        finally:
            self._current_job = None
    
    def process_batch(self,
                     jobs: List[ProcessingJob],
                     continue_on_error: bool = True) -> List[ProcessingJob]:
        """
        Process multiple photos in batch - optimized to group files with same parameters
        
        :param jobs: List of processing jobs
        :param continue_on_error: Whether to continue processing if one job fails
        :return: List of completed jobs with status updates
        """
        self._processing_jobs = jobs
        self._batch_export_completed = False  # Reset flag for new batch
        self._notify_callbacks('on_batch_start', jobs)
        
        completed_jobs = []
        
        # Group jobs by parameters to enable true batch processing
        from collections import defaultdict
        
        # Create parameter groups - jobs with identical parameters can be processed together
        param_groups = defaultdict(list)
        for job in jobs:
            # Create a key based on parameters (model, scale, etc.)
            param_key = (
                job.parameters.model.name if job.parameters.model else None,
                job.parameters.scale,
                str(job.parameters.parameters) if job.parameters.parameters else ""
            )
            param_groups[param_key].append(job)
        
        logger.info(f"Batch processing: {len(jobs)} total jobs grouped into {len(param_groups)} parameter sets")
        
        # Process each parameter group
        for param_key, group_jobs in param_groups.items():
            if len(group_jobs) == 1:
                # Single file - use individual processing
                job = group_jobs[0]
                try:
                    self.process_with_model(
                        job.input_path,
                        job.parameters,
                        job.output_path
                    )
                    completed_jobs.append(job)
                except Exception as e:
                    job.status = "error"
                    job.error = str(e)
                    logger.error(f"Error processing {job.input_path}: {e}")
                    
                    if not continue_on_error:
                        break
                        
                    completed_jobs.append(job)
            else:
                # Multiple files with same parameters - use batch processing
                logger.info(f"Batch processing {len(group_jobs)} files with identical parameters")
                try:
                    self._process_batch_group(group_jobs)
                    completed_jobs.extend(group_jobs)
                except Exception as e:
                    # Mark all jobs in group as failed
                    for job in group_jobs:
                        job.status = "error"
                        job.error = str(e)
                        logger.error(f"Error batch processing {job.input_path}: {e}")
                    
                    if not continue_on_error:
                        break
                        
                    completed_jobs.extend(group_jobs)
        
        self._notify_callbacks('on_batch_complete', completed_jobs)
        return completed_jobs
    
    def _process_batch_group(self, jobs: List[ProcessingJob]) -> None:
        """
        Process a group of jobs with identical parameters using true batch processing
        
        :param jobs: List of jobs with same parameters to process together
        """
        if not jobs:
            return
        
        self._set_english_layout()
        
        # All jobs in the group have the same parameters, so use the first one
        parameters = jobs[0].parameters
        input_paths = [job.input_path for job in jobs]
        
        logger.info(f"Starting batch group processing: {len(jobs)} files")
        
        # Step 1: Open all photos at once
        self._app.open_photo(input_paths)  # Use the updated open_photo method
        
        # Step 2: Set processing parameters (same for all files)
        self._app.set_advanced_processing_options(parameters)
        
        # Step 3: Process all files
        # For batch processing, we can either:
        # A) Save each file individually with custom output paths
        # B) Use batch save if output paths follow a pattern
        
        # For batch processing, we'll save each file individually to respect custom output paths
        # But first check if a batch export was already completed (e.g., user clicked "Export X images")
        for job in jobs:
            # Check if batch export was already completed - skip individual processing
            if self._batch_export_completed and job.status == "completed":
                logger.info(f"Skipping {job.input_path.name} - already completed by batch export")
                self._notify_callbacks('on_job_complete', job)
                continue
                
            try:
                self._current_job = job
                self._notify_callbacks('on_job_start', job)
                
                if job.output_path:
                    self._app.save_photo_to_path(job.output_path)
                else:
                    self._app.save_photo()
                
                job.status = "completed"
                self._notify_callbacks('on_job_complete', job)
                
            except Exception as e:
                job.status = "error"
                job.error = str(e)
                self._notify_callbacks('on_job_error', job, str(e))
                logger.error(f"Error saving {job.input_path}: {e}")
                # Continue with other files in the batch
            finally:
                self._current_job = None
        
        logger.info(f"Batch group processing completed: {len(jobs)} files")
    
    def process_preset_mode(self,
                           photo_paths: List[Union[Path, str]],
                           prompt: Optional[str] = None) -> None:
        """
        Process photos in preset mode - minimal intervention, uses Gigapixel's saved settings
        Optimized to process multiple files at once when possible
        
        :param photo_paths: List of photo paths to process
        :param prompt: Optional prompt for Redefine models
        """
        self._set_english_layout()
        
        # Convert all paths to Path objects and validate
        validated_paths = []
        for photo_path in photo_paths:
            if isinstance(photo_path, str):
                photo_path = Path(photo_path)
            
            self._check_path(photo_path)
            validated_paths.append(photo_path)
        
        if not validated_paths:
            logger.warning("No valid paths to process in preset mode")
            return
        
        logger.info(f"Processing {len(validated_paths)} files in preset mode")
        
        try:
            # Open all photos at once for batch processing
            self._app.open_photo(validated_paths)
            
            # If prompt is provided, try to set it
            if prompt:
                try:
                    logger.debug(f"Attempting to set prompt: {prompt}")
                    # Look for prompt field (for Redefine models)
                    prompt_patterns = [
                        lambda: self._app._main_window.child_window(title="Prompt", control_type="Edit"),
                        lambda: self._app._main_window.child_window(auto_id_re=".*prompt.*", control_type="Edit"),
                        lambda: self._app._main_window.child_window(title_re=".*prompt.*", control_type="Edit"),
                    ]
                    
                    prompt_control = None
                    for pattern in prompt_patterns:
                        try:
                            prompt_control = pattern()
                            break
                        except:
                            continue
                    
                    if prompt_control:
                        prompt_control.click_input()
                        time.sleep(0.1)
                        send_keys('^a')  # Select all
                        send_keys(prompt)
                        logger.debug(f"✓ Set prompt to: {prompt}")
                    else:
                        logger.debug("No prompt field found - may not be a Redefine model")
                except Exception as e:
                    logger.debug(f"Could not set prompt: {e}")
            
            # Save using current settings - in preset mode, we use batch save
            self._app.save_photo()
            
            logger.info(f"✓ Completed preset mode processing: {len(validated_paths)} files")
            
        except Exception as e:
            logger.error(f"Error processing files in preset mode: {e}")
            raise
    
    def add_callback(self, callback: ProcessingCallback):
        """Add a processing callback"""
        self._callbacks.append(callback)
    
    def set_export_parameters(self, quality: Optional[int] = None, prefix: Optional[str] = None, suffix: Optional[str] = None):
        """Set export parameters for all subsequent exports
        
        Args:
            quality: JPEG quality (1-100)
            prefix: Filename prefix
            suffix: Filename suffix (can be "0" to turn off, "1" to turn on, or custom string)
        """
        if quality is not None:
            self._app._export_quality = quality
        if prefix is not None:
            self._app._export_prefix = prefix
        if suffix is not None:
            self._app._export_suffix = suffix
    
    def set_output_directory(self, directory: str):
        """Set the output directory for exports
        
        Args:
            directory: Path to the output directory
        """
        self._app._output_directory = directory
    
    def remove_callback(self, callback: ProcessingCallback):
        """Remove a processing callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, method_name: str, *args):
        """Notify all callbacks of an event"""
        for callback in self._callbacks:
            if hasattr(callback, method_name):
                try:
                    getattr(callback, method_name)(*args)
                except Exception as e:
                    logger.error(f"Error in callback {method_name}: {e}")
    
    # Model and parameter management methods
    
    def get_available_models(self) -> List[AIModel]:
        """Get all available AI models"""
        return self._model_factory.get_all_models()
    
    def get_model_by_name(self, name: str) -> AIModel:
        """Get a model by name"""
        return self._model_factory.get_model_by_name(name)
    
    def create_processing_parameters(self, 
                                   model_name: str,
                                   parameters: Optional[Dict[str, Any]] = None,
                                   scale: Optional[str] = None) -> ProcessingParameters:
        """Create processing parameters"""
        return self._model_factory.create_processing_parameters(model_name, parameters, scale)
    
    def save_preset(self, name: str, parameters: ProcessingParameters):
        """Save processing parameters as a preset"""
        self._model_factory.save_preset(name, parameters)
    
    def load_preset(self, name: str) -> Optional[ProcessingParameters]:
        """Load a preset by name"""
        return self._model_factory.load_preset(name)
    
    def list_presets(self) -> List[str]:
        """List all available presets"""
        return self._model_factory.list_presets()
    
    def suggest_models(self, query: str, limit: int = 5) -> List[AIModel]:
        """Suggest models based on a search query"""
        return self._model_factory.suggest_models(query, limit)
    
    # Legacy compatibility methods
    
    def process_legacy(self,
                      photo_path: Union[Path, str],
                      scale: Optional[Union[Scale, str]] = None,
                      mode: Optional[Union[Mode, str]] = None) -> None:
        """
        Process using legacy interface (backward compatibility)
        
        :param photo_path: Path to the photo to be processed
        :param scale: Scale to be used for processing
        :param mode: Mode to be used for processing
        """
        # Convert to strings if enums
        scale_str = scale.value if isinstance(scale, Scale) else scale
        mode_str = mode.value if isinstance(mode, Mode) else mode
        
        # Create processing parameters from legacy values
        if mode_str:
            try:
                parameters = self._model_factory.create_from_legacy(mode_str, scale_str)
                self.process_with_model(photo_path, parameters)
            except Exception as e:
                logger.warning(f"Could not use advanced processing for legacy mode '{mode_str}': {e}")
                # Fall back to original processing
                self.process(photo_path, scale, mode)
        else:
            # No mode specified, use original processing
            self.process(photo_path, scale, mode)
