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
        
        instance = self._get_gigapixel_instance()
        self._app = self._App(instance, processing_timeout)

    class _App:
        def __init__(self, app: Application, processing_timeout: int):
            timings.Timings.window_find_timeout = 0.5

            self.app = app
            self._processing_timeout = processing_timeout
            
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
                    logger.debug(f"Found main window with '{pattern_name}': {main_window.element_info.name}")
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
        @log("Opening photo: {}", "Photo opened", format=(1,), level=Level.DEBUG)
        def open_photo(self, photo_path: Path) -> None:
            import time
            
            # Step 1: Focus the main window and wait for it to be ready
            logger.debug("Focusing main window and waiting for it to be ready")
            self._main_window.set_focus()
            time.sleep(1.5)  # Give more time for window to be active
            
            # Step 2: Try to open file dialog - use Browse button as primary method
            dialog_opened = False
            
            # Method 1: Try clicking the "Browse images" button in the center of the screen
            logger.debug("Attempting to click Browse images button in center of screen")
            try:
                # Look for "Browse images" button which appears when no image is loaded
                browse_button = self._main_window.child_window(title="Browse images", control_type="Button")
                browse_button.click_input()
                logger.debug("✓ Clicked Browse button successfully")
                time.sleep(2.0)  # Wait for dialog to open
                dialog_opened = True
            except Exception as e:
                logger.debug(f"Browse button click failed: {e}")
            
            # Method 2: Fallback to Ctrl+O if Browse button didn't work
            if not dialog_opened:
                logger.debug("Fallback: Opening file dialog with Ctrl+O")
                send_keys('^o')
                time.sleep(2.0)  # Wait for dialog to open
            
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
                            logger.debug(f"✓ Found file dialog window: '{window.element_info.name}'")
                            dialog_confirmed = True
                            break
                    except:
                        continue
                
                # Alternative: Look for file dialog specific elements
                if not dialog_confirmed:
                    try:
                        # Look for file name input field or file list in main window
                        file_input = self._main_window.child_window(control_type="Edit", title_re=".*[Ff]ile.*")
                        logger.debug("✓ Found file input field in dialog")
                        dialog_confirmed = True
                    except:
                        pass
                
                # Alternative: Look for common dialog buttons
                if not dialog_confirmed:
                    try:
                        open_button = self._main_window.child_window(title="Open", control_type="Button")
                        cancel_button = self._main_window.child_window(title="Cancel", control_type="Button")
                        # Both buttons should exist in a real file dialog
                        logger.debug("✓ Found Open and Cancel buttons - file dialog confirmed")
                        dialog_confirmed = True
                    except:
                        pass
                        
            except Exception as e:
                logger.debug(f"Dialog verification error: {e}")
            
            if not dialog_confirmed:
                logger.error("✗ File dialog did not open properly! Cannot proceed with file selection.")
                raise ElementNotFound("File dialog failed to open - cannot select file")
            
            logger.debug("✓ File dialog confirmed open, proceeding with file selection")
            
            # Step 4: Enter the file path
            logger.debug(f"Entering file path: {photo_path}")
            clipboard.copy(str(photo_path))
            send_keys('^v')
            time.sleep(1.0)  # Wait for path to be entered
            
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
            time.sleep(4.0)  # Give more time for file to load
            
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
                    time.sleep(3.0)  # Wait longer before retrying
            
            if image_loaded:
                logger.info("✓ Image successfully loaded and verified")
                
                # Update window reference since the title likely changed to include the filename
                logger.debug("Updating window reference after image load...")
                try:
                    # Try to find the updated window with the new title
                    updated_window = None
                    window_patterns = [
                        ("Image filename window", lambda: self.app.window(title_re=f".*{photo_path.stem}.*")),
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
            
            logger.info(f"File opening sequence completed for: {photo_path.name}")
                

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
                    send_keys('{ENTER}')
                else:
                    # Wait for export process to start
                    time.sleep(2.0)
                
                # Wait for processing to complete
                if self._cancel_processing_button is None:
                    self._cancel_processing_button = self._main_window.child_window(title="Close window",
                                                                                    control_type="Button",
                                                                                    depth=1)
                self._cancel_processing_button.wait('visible', timeout=self._processing_timeout)

                # Close any remaining dialogs
                self._close_export_dialog()
                
            except Exception as e:
                logger.error(f"Error during export: {e}")
                # Fallback to old export method
                try:
                    self._open_export_dialog()
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
            self._save_button.wait('visible', timeout=0.1)
        
        @retry(
            expected_exception=(TimeoutError,),
            attempts=10,
            backoff=0.1,
            exponential_backoff=True,
        )
        @log("Closing export dialog", "Export dialog closed", level=Level.DEBUG)
        def _close_export_dialog(self) -> None:
            send_keys('{ESC}')
            self._cancel_processing_button.wait_not('visible', timeout=0.1)

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
                    logger.debug(f"Found scale button with direct title: {scale.value}")
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
                            logger.debug(f"Found scale button with control type {control_type}: {scale.value}")
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
                            time.sleep(0.2)
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
            """Set scale using string value"""
            try:
                # Convert string to Scale enum for backward compatibility
                scale_enum = None
                for s in Scale:
                    if s.value == scale:
                        scale_enum = s
                        break
                
                if scale_enum:
                    self._set_scale(scale_enum)
                else:
                    # Try to find scale button directly by string
                    scale_button = self._main_window.child_window(title=scale)
                    scale_button.click_input()
                    logger.debug(f"Scale set to {scale}")
            except ElementNotFoundError:
                raise ElementNotFound(f"Scale button {scale} not found")
        
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
                # This is a simplified implementation
                # In reality, you'd need specific UI automation for each parameter type
                
                # Try to find parameter control by name
                param_control = self._main_window.child_window(title=param_name)
                
                if isinstance(value, bool):
                    # Handle checkbox/toggle
                    if value:
                        param_control.check()
                    else:
                        param_control.uncheck()
                elif isinstance(value, (int, float)):
                    # Handle slider/input field
                    param_control.set_value(str(value))
                elif isinstance(value, str):
                    # Handle text input
                    param_control.set_text(value)
                
                logger.debug(f"Parameter {param_name} set to {value}")
                
            except ElementNotFoundError:
                logger.warning(f"Could not find UI control for parameter: {param_name}")
            except Exception as e:
                logger.warning(f"Could not set parameter {param_name}: {e}")
        
        def _set_model_via_legacy_mapping(self, model: AIModel):
            """Set model using the new dropdown-based model selection"""
            logger.debug(f"Setting model: {model.display_name}")
            
            # First, we need to open the model selection dropdown
            self._open_model_selection_dropdown()
            
            # Map new models to their display names in the UI
            model_display_mapping = {
                # Enhance models
                "standard_v2": "Standard",
                "high_fidelity_v2": "High fidelity", 
                "low_resolution_v2": "Low res",
                "text_refine": "Text & shapes",
                "cgi": "Art & CG",
                "redefine": "Redefine",  # Generative model
                "recovery": "Recovery",
                "recovery_v2": "Recovery",
                
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
            logger.debug(f"Looking for model: {target_model_name}")
            
            # Try to click the model in the dropdown
            model_selected = self._click_model_in_dropdown(target_model_name)
            
            if not model_selected:
                # Fallback to legacy mode selection if dropdown method fails
                logger.warning(f"Could not select {target_model_name} from dropdown, trying legacy mode selection")
                legacy_mode = self._get_legacy_mode_for_model(model.name)
                if legacy_mode:
                    self._set_mode(legacy_mode)
        
        def _open_model_selection_dropdown(self):
            """Open the model selection dropdown by clicking the left arrow button"""
            import time
            
            logger.debug("Opening model selection dropdown...")
            
            try:
                # Look for the left arrow button near the model selection area
                # Try multiple approaches to find the dropdown trigger
                
                # Method 1: Look for left arrow or expand button
                dropdown_opened = False
                arrow_patterns = [
                    ("Left arrow", lambda: self._main_window.child_window(title="<", control_type="Button")),
                    ("Arrow button", lambda: self._main_window.child_window(title="◀", control_type="Button")),
                    ("Expand arrow", lambda: self._main_window.child_window(control_type="Button", title_re=".*arrow.*")),
                    ("Model dropdown", lambda: self._main_window.child_window(title_re=".*model.*", control_type="Button")),
                ]
                
                for pattern_name, button_func in arrow_patterns:
                    try:
                        arrow_button = button_func()
                        arrow_button.click_input()
                        logger.debug(f"✓ Clicked dropdown arrow using: {pattern_name}")
                        dropdown_opened = True
                        break
                    except:
                        continue
                
                # Method 2: Look for the model selection area and click on it
                if not dropdown_opened:
                    try:
                        # The model selection area might be a clickable region
                        model_area_patterns = [
                            ("Model selection area", lambda: self._main_window.child_window(title_re=".*High fidelity.*")),
                            ("Current model", lambda: self._main_window.child_window(title_re=".*Standard.*")),
                            ("Model panel", lambda: self._main_window.child_window(control_type="Group", title_re=".*model.*")),
                        ]
                        
                        for pattern_name, area_func in model_area_patterns:
                            try:
                                model_area = area_func()
                                model_area.click_input()
                                logger.debug(f"✓ Clicked model area using: {pattern_name}")
                                dropdown_opened = True
                                break
                            except:
                                continue
                
                # Method 3: Try to find any clickable element that might open the dropdown
                if not dropdown_opened:
                    try:
                        # Look for elements near Dimensions/Pixel density as mentioned
                        dimensions_area = self._main_window.child_window(title="Dimensions")
                        # Look for clickable elements near it
                        nearby_buttons = self._main_window.children(control_type="Button")
                        for button in nearby_buttons:
                            try:
                                # Try clicking buttons near the dimensions area
                                button.click_input()
                                logger.debug("✓ Clicked potential dropdown button near Dimensions")
                                dropdown_opened = True
                                break
                            except:
                                continue
                    except:
                        pass
                
                if dropdown_opened:
                    time.sleep(1.0)  # Wait for dropdown to open
                    logger.debug("✓ Model selection dropdown opened")
                else:
                    logger.warning("Could not open model selection dropdown")
                    
            except Exception as e:
                logger.error(f"Error opening model selection dropdown: {e}")
        
        def _click_model_in_dropdown(self, model_name: str) -> bool:
            """Click on a specific model in the opened dropdown"""
            import time
            
            logger.debug(f"Looking for model '{model_name}' in dropdown...")
            
            try:
                # Wait a moment for dropdown to be fully loaded
                time.sleep(0.5)
                
                # Try multiple approaches to find the model
                model_patterns = [
                    ("Direct title", lambda: self._main_window.child_window(title=model_name)),
                    ("Button type", lambda: self._main_window.child_window(title=model_name, control_type="Button")),
                    ("List item", lambda: self._main_window.child_window(title=model_name, control_type="ListItem")),
                    ("Text element", lambda: self._main_window.child_window(title=model_name, control_type="Text")),
                    ("Any element", lambda: self._main_window.child_window(title_re=f".*{model_name}.*")),
                ]
                
                for pattern_name, model_func in model_patterns:
                    try:
                        model_element = model_func()
                        model_element.click_input()
                        logger.debug(f"✓ Selected model '{model_name}' using: {pattern_name}")
                        
                        # Wait for selection to take effect
                        time.sleep(1.0)
                        return True
                    except:
                        continue
                
                logger.warning(f"Could not find model '{model_name}' in dropdown")
                return False
                
            except Exception as e:
                logger.error(f"Error selecting model from dropdown: {e}")
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
            
            # Set the output path in the save dialog
            try:
                # Clear current path and set new one
                send_keys('^a')  # Select all
                clipboard.copy(str(output_path))
                send_keys('^v')  # Paste new path
                
                # Confirm save
                send_keys('{ENTER}')
                
                if self._cancel_processing_button is None:
                    self._cancel_processing_button = self._main_window.child_window(title="Close window",
                                                                                    control_type="Button",
                                                                                    depth=1)
                self._cancel_processing_button.wait('visible', timeout=self._processing_timeout)
                
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
        Process multiple photos in batch
        
        :param jobs: List of processing jobs
        :param continue_on_error: Whether to continue processing if one job fails
        :return: List of completed jobs with status updates
        """
        self._processing_jobs = jobs
        self._notify_callbacks('on_batch_start', jobs)
        
        completed_jobs = []
        
        for job in jobs:
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
        
        self._notify_callbacks('on_batch_complete', completed_jobs)
        return completed_jobs
    
    def add_callback(self, callback: ProcessingCallback):
        """Add a processing callback"""
        self._callbacks.append(callback)
    
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
