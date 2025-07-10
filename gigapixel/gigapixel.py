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
            self._main_window = self.app.window()

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
            while photo_path.name not in self._main_window.element_info.name:
                logger.debug("Trying to open photo")
                self._main_window.set_focus()
                send_keys('{ESC}^o')
                clipboard.copy(str(photo_path))
                send_keys('^v {ENTER}{ESC}')
                

        @log("Saving photo", "Photo saved", level=Level.DEBUG)
        def save_photo(self) -> None:
            self._open_export_dialog()

            send_keys('{ENTER}')
            if self._cancel_processing_button is None:
                self._cancel_processing_button = self._main_window.child_window(title="Close window",
                                                                                control_type="Button",
                                                                                depth=1)
            self._cancel_processing_button.wait('visible', timeout=self._processing_timeout)

            self._close_export_dialog()

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
                if scale not in self._scale_buttons:
                    self._scale_buttons[scale] = self._main_window.child_window(title=scale.value)
                self._scale_buttons[scale].click_input()
            except ElementNotFoundError:
                raise ElementNotFound(f"Scale button {scale.value} not found")
            self.scale = scale
            logger.debug(f"Scale set to {scale.value}")

        def _set_mode(self, mode: Mode) -> None:
            if self.mode == mode:
                return

            try:
                if mode not in self._mode_buttons:
                    self._mode_buttons[mode] = self._main_window.child_window(title=mode.value)
                self._mode_buttons[mode].click_input()
            except ElementNotFoundError:
                raise ElementNotFound(f"Mode button {mode.value} not found")
            self.mode = mode
            logger.debug(f"Mode set to {mode.value}")

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
            
            # For now, we'll map the new models to existing UI elements
            # This is a simplified implementation - in a real scenario, 
            # you'd need to map each model to specific UI automation
            
            try:
                # Try to find and click the model button by display name
                model_button = self._main_window.child_window(title=model.display_name)
                model_button.click_input()
                logger.debug(f"Model set to {model.display_name}")
                
                # Set individual parameters
                for param_name, param_value in parameters.parameters.items():
                    self._set_parameter_value(param_name, param_value)
                    
            except ElementNotFoundError:
                # Fallback to legacy mode mapping
                self._set_model_via_legacy_mapping(model)
        
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
            """Fallback to legacy mode mapping for compatibility"""
            # Map new models to legacy modes for UI automation
            legacy_mapping = {
                "standard_v2": Mode.STANDARD,
                "high_fidelity_v2": Mode.HIGH_FIDELITY,
                "low_resolution_v2": Mode.LOW_RESOLUTION,
                "text_refine": Mode.TEXT_AND_SHAPES,
                "cgi": Mode.ART_AND_CG,
                "recovery": Mode.RECOVERY,
                "recovery_v2": Mode.RECOVERY
            }
            
            legacy_mode = legacy_mapping.get(model.name)
            if legacy_mode:
                self._set_mode(legacy_mode)
            else:
                logger.warning(f"No legacy mapping found for model: {model.name}")
        
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
