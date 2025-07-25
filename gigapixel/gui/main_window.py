import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, List, Dict, Any, Callable
import threading
import queue
import os
from pathlib import Path
import json
import winsound
import time

from ..gigapixel import Gigapixel, ProcessingJob, ProcessingCallback
from ..models import ModelCategory, AIModel
from ..parameters import ProcessingParameters
from ..factory import get_model_factory
from ..suffix_generator import generate_auto_suffix, parse_suffix_mode
from .widgets import CollapsibleFrame, ToolTip, ParameterWidget, ProgressFrame
from .utils import center_window, show_notification, play_completion_sound


class GUIProcessingCallback(ProcessingCallback):
    """Callback implementation for GUI updates"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def on_job_start(self, job: ProcessingJob):
        self.main_window.on_job_start(job)
    
    def on_job_progress(self, job: ProcessingJob, progress: float):
        self.main_window.on_job_progress(job, progress)
    
    def on_job_complete(self, job: ProcessingJob):
        self.main_window.on_job_complete(job)
    
    def on_job_error(self, job: ProcessingJob, error: str):
        self.main_window.on_job_error(job, error)
    
    def on_batch_start(self, jobs: List[ProcessingJob]):
        self.main_window.on_batch_start(jobs)
    
    def on_batch_complete(self, jobs: List[ProcessingJob]):
        self.main_window.on_batch_complete(jobs)


class GigaUpWindow:
    """Main application window for GigaUp desktop GUI"""
    
    def __init__(self, executable_path: Optional[str] = None):
        self.root = tk.Tk()
        self.root.title("GigaUp - Topaz Gigapixel AI Automation")
        self.root.geometry("800x900")
        self.root.minsize(600, 700)
        
        # Initialize backend
        self.gigapixel: Optional[Gigapixel] = None
        self.executable_path = executable_path
        self.model_factory = get_model_factory()
        
        # GUI state
        self.processing_queue = queue.Queue()
        self.current_jobs: List[ProcessingJob] = []
        self.selected_model: Optional[AIModel] = None
        self.current_parameters: Dict[str, Any] = {}
        
        # Initialize GUI
        self.setup_styles()
        self.create_widgets()
        self.create_menus()
        self.load_settings()
        
        # Center the window
        center_window(self.root)
        
        # Setup processing thread
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_processing = threading.Event()
    
    def setup_styles(self):
        """Setup custom styles for the application"""
        style = ttk.Style()
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 9))
        style.configure('Error.TLabel', foreground='red', font=('Arial', 9))
        style.configure('Success.TLabel', foreground='green', font=('Arial', 9))
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container with scrollable content
        main_canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        self.scrollable_frame = ttk.Frame(main_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollable container
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Title
        title_label = ttk.Label(self.scrollable_frame, text="GigaUp - Advanced Image Enhancement", 
                               style='Title.TLabel')
        title_label.pack(pady=(10, 20))
        
        # Input/Output paths section (always at top)
        self.create_path_section()
        
        # Collapsible tool sections
        self.create_tool_sections()
        
        # Progress and controls (always at bottom)
        self.create_progress_section()
        self.create_log_section()
        
        # Bind mouse wheel to canvas scrolling
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_path_section(self):
        """Create input/output path selection section"""
        path_frame = ttk.LabelFrame(self.scrollable_frame, text="Input/Output Paths", padding=10)
        path_frame.pack(fill="x", padx=10, pady=5)
        
        # Input path
        input_frame = ttk.Frame(path_frame)
        input_frame.pack(fill="x", pady=2)
        
        ttk.Label(input_frame, text="Input:").pack(side="left")
        self.input_path_var = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self.input_path_var)
        input_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        input_browse_btn = ttk.Button(input_frame, text="Browse Files", 
                                     command=self.browse_input_files)
        input_browse_btn.pack(side="right", padx=(0, 5))
        
        input_folder_btn = ttk.Button(input_frame, text="Browse Folder", 
                                     command=self.browse_input_folder)
        input_folder_btn.pack(side="right")
        
        # Output path
        output_frame = ttk.Frame(path_frame)
        output_frame.pack(fill="x", pady=2)
        
        ttk.Label(output_frame, text="Output:").pack(side="left")
        self.output_path_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_path_var)
        output_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        output_browse_btn = ttk.Button(output_frame, text="Browse Folder", 
                                      command=self.browse_output_folder)
        output_browse_btn.pack(side="right")
        
        # Add tooltips
        ToolTip(input_entry, "Select input image files or folder to process")
        ToolTip(output_entry, "Select output folder for enhanced images")
        
        # Export parameters section
        export_frame = ttk.LabelFrame(path_frame, text="Export Settings", padding=5)
        export_frame.pack(fill="x", pady=(10, 0))
        
        # Quality setting
        quality_frame = ttk.Frame(export_frame)
        quality_frame.pack(fill="x", pady=2)
        
        ttk.Label(quality_frame, text="Quality:").pack(side="left")
        self.quality_var = tk.IntVar(value=95)
        quality_spinbox = ttk.Spinbox(quality_frame, from_=1, to=100, textvariable=self.quality_var, width=10)
        quality_spinbox.pack(side="left", padx=(5, 0))
        ToolTip(quality_spinbox, "JPEG quality (1-100, default: 95)")
        
        # Prefix setting
        prefix_frame = ttk.Frame(export_frame)
        prefix_frame.pack(fill="x", pady=2)
        
        ttk.Label(prefix_frame, text="Prefix:").pack(side="left")
        self.prefix_var = tk.StringVar()
        prefix_entry = ttk.Entry(prefix_frame, textvariable=self.prefix_var, width=20)
        prefix_entry.pack(side="left", padx=(5, 0))
        ToolTip(prefix_entry, "Filename prefix (optional)")
        
        # Suffix mode
        suffix_frame = ttk.Frame(export_frame)
        suffix_frame.pack(fill="x", pady=2)
        
        ttk.Label(suffix_frame, text="Suffix:").pack(side="left")
        self.suffix_mode_var = tk.StringVar(value="auto")
        
        suffix_radio_frame = ttk.Frame(suffix_frame)
        suffix_radio_frame.pack(side="left", padx=(5, 0))
        
        ttk.Radiobutton(suffix_radio_frame, text="Auto", variable=self.suffix_mode_var, 
                       value="auto").pack(side="left")
        ttk.Radiobutton(suffix_radio_frame, text="Custom", variable=self.suffix_mode_var, 
                       value="custom").pack(side="left", padx=(10, 0))
        ttk.Radiobutton(suffix_radio_frame, text="None", variable=self.suffix_mode_var, 
                       value="none").pack(side="left", padx=(10, 0))
        
        self.custom_suffix_var = tk.StringVar()
        self.custom_suffix_entry = ttk.Entry(suffix_frame, textvariable=self.custom_suffix_var, width=20)
        self.custom_suffix_entry.pack(side="left", padx=(10, 0))
        
        # Enable/disable custom suffix entry based on mode
        def on_suffix_mode_changed(*args):
            if self.suffix_mode_var.get() == "custom":
                self.custom_suffix_entry.config(state="normal")
            else:
                self.custom_suffix_entry.config(state="disabled")
        
        self.suffix_mode_var.trace("w", on_suffix_mode_changed)
        on_suffix_mode_changed()  # Initialize state
        
        ToolTip(suffix_radio_frame, "Auto: Generate from parameters\nCustom: Use your text\nNone: No suffix")
        ToolTip(self.custom_suffix_entry, "Custom suffix text")
    
    def create_tool_sections(self):
        """Create collapsible sections for different tool categories"""
        # Container for tool sections
        tools_frame = ttk.Frame(self.scrollable_frame)
        tools_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Get models by category
        categories = [ModelCategory.ENHANCE, ModelCategory.SHARPEN, ModelCategory.DENOISE, 
                     ModelCategory.RESTORE, ModelCategory.LIGHTING]
        
        self.category_frames = {}
        self.model_widgets = {}
        
        for category in categories:
            models = self.model_factory.get_models_by_category(category)
            if models:
                # Create collapsible frame for this category
                category_frame = CollapsibleFrame(tools_frame, category.value, 
                                                collapsed=True if category != ModelCategory.ENHANCE else False)
                category_frame.pack(fill="x", pady=2)
                
                self.category_frames[category] = category_frame
                self.model_widgets[category] = {}
                
                # Add models for this category
                self.create_model_selection(category_frame.content_frame, category, models)
        
        # Scale selection (separate section)
        scale_frame = CollapsibleFrame(tools_frame, "Scale Options", collapsed=False)
        scale_frame.pack(fill="x", pady=2)
        self.create_scale_selection(scale_frame.content_frame)
        
        # Preset management
        preset_frame = CollapsibleFrame(tools_frame, "Presets", collapsed=True)
        preset_frame.pack(fill="x", pady=2)
        self.create_preset_section(preset_frame.content_frame)
    
    def create_model_selection(self, parent, category: ModelCategory, models: List[AIModel]):
        """Create model selection widgets for a category"""
        # Model selection
        model_frame = ttk.Frame(parent)
        model_frame.pack(fill="x", pady=5)
        
        ttk.Label(model_frame, text="Model:", style='Subtitle.TLabel').pack(anchor="w")
        
        # Create radio buttons for models
        model_var = tk.StringVar()
        self.model_widgets[category]['var'] = model_var
        self.model_widgets[category]['models'] = models
        
        for model in models:
            radio_frame = ttk.Frame(model_frame)
            radio_frame.pack(fill="x", pady=1)
            
            radio_btn = ttk.Radiobutton(radio_frame, text=model.display_name, 
                                       variable=model_var, value=model.name,
                                       command=lambda m=model: self.on_model_selected(m))
            radio_btn.pack(side="left")
            
            # Add tooltip with model description
            ToolTip(radio_btn, f"{model.description}\\n\\nClass: {model.model_class.value}")
        
        # Parameter widgets container
        param_frame = ttk.LabelFrame(model_frame, text="Parameters", padding=5)
        param_frame.pack(fill="x", pady=(10, 0))
        
        self.model_widgets[category]['param_frame'] = param_frame
        self.model_widgets[category]['param_widgets'] = {}
    
    def create_scale_selection(self, parent):
        """Create scale selection widgets"""
        scale_frame = ttk.Frame(parent)
        scale_frame.pack(fill="x", pady=5)
        
        ttk.Label(scale_frame, text="Scale Factor:", style='Subtitle.TLabel').pack(anchor="w")
        
        scales = ["1x", "2x", "4x", "6x"]
        self.scale_var = tk.StringVar(value="2x")
        
        scale_buttons_frame = ttk.Frame(scale_frame)
        scale_buttons_frame.pack(fill="x", pady=5)
        
        for scale in scales:
            radio_btn = ttk.Radiobutton(scale_buttons_frame, text=scale, 
                                       variable=self.scale_var, value=scale)
            radio_btn.pack(side="left", padx=10)
            
            ToolTip(radio_btn, f"Upscale images by {scale}")
        
        # Add custom scale option
        custom_radio = ttk.Radiobutton(scale_buttons_frame, text="Custom", 
                                      variable=self.scale_var, value="custom")
        custom_radio.pack(side="left", padx=10)
        ToolTip(custom_radio, "Use a custom scale factor")
        
        # Custom scale input frame
        custom_frame = ttk.Frame(scale_frame)
        custom_frame.pack(fill="x", pady=5)
        
        ttk.Label(custom_frame, text="Custom Scale:").pack(side="left", padx=(0, 5))
        
        self.custom_scale_var = tk.StringVar(value="1.5")
        self.custom_scale_entry = ttk.Entry(custom_frame, textvariable=self.custom_scale_var, width=10)
        self.custom_scale_entry.pack(side="left", padx=(0, 5))
        
        ToolTip(self.custom_scale_entry, "Enter custom scale factor (e.g., 1.33, 1.5, 3, 5)")
        
        # Update custom scale when entry changes
        def on_custom_scale_change(*args):
            if self.scale_var.get() == "custom":
                # Validate the custom scale value
                try:
                    scale_value = float(self.custom_scale_var.get())
                    if scale_value <= 0:
                        self.custom_scale_var.set("1.5")
                except ValueError:
                    self.custom_scale_var.set("1.5")
        
        self.custom_scale_var.trace("w", on_custom_scale_change)
        
        # Enable custom entry when custom radio is selected
        def on_scale_change(*args):
            if self.scale_var.get() == "custom":
                self.custom_scale_entry.configure(state="normal")
            else:
                self.custom_scale_entry.configure(state="disabled")
        
        self.scale_var.trace("w", on_scale_change)
        on_scale_change()  # Initialize state
    
    def get_scale_value(self):
        """Get the actual scale value, handling custom scale"""
        scale = self.scale_var.get()
        if scale == "custom":
            try:
                custom_value = float(self.custom_scale_var.get())
                if custom_value > 0:
                    return str(custom_value)
                else:
                    return "2x"  # Default fallback
            except ValueError:
                return "2x"  # Default fallback
        else:
            return scale
    
    def create_preset_section(self, parent):
        """Create preset management section"""
        preset_frame = ttk.Frame(parent)
        preset_frame.pack(fill="x", pady=5)
        
        # Preset selection
        preset_select_frame = ttk.Frame(preset_frame)
        preset_select_frame.pack(fill="x", pady=2)
        
        ttk.Label(preset_select_frame, text="Preset:").pack(side="left")
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_select_frame, textvariable=self.preset_var,
                                        state="readonly")
        self.preset_combo.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        preset_load_btn = ttk.Button(preset_select_frame, text="Load", 
                                    command=self.load_preset)
        preset_load_btn.pack(side="right", padx=(0, 5))
        
        # Preset management
        preset_mgmt_frame = ttk.Frame(preset_frame)
        preset_mgmt_frame.pack(fill="x", pady=2)
        
        self.preset_name_var = tk.StringVar()
        preset_name_entry = ttk.Entry(preset_mgmt_frame, textvariable=self.preset_name_var)
        preset_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        preset_save_btn = ttk.Button(preset_mgmt_frame, text="Save", 
                                    command=self.save_preset)
        preset_save_btn.pack(side="right", padx=(0, 5))
        
        preset_delete_btn = ttk.Button(preset_mgmt_frame, text="Delete", 
                                      command=self.delete_preset)
        preset_delete_btn.pack(side="right")
        
        # Update preset list
        self.update_preset_list()
    
    def create_progress_section(self):
        """Create progress and control section"""
        # Control buttons
        control_frame = ttk.Frame(self.scrollable_frame)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Process button
        self.process_btn = ttk.Button(control_frame, text="Start Processing", 
                                     command=self.start_processing, style='Accent.TButton')
        self.process_btn.pack(side="left", padx=(0, 10))
        
        # Stop button
        self.stop_btn = ttk.Button(control_frame, text="Stop", 
                                  command=self.stop_processing_jobs, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 10))
        
        # Clear queue button
        clear_btn = ttk.Button(control_frame, text="Clear Queue", 
                              command=self.clear_queue)
        clear_btn.pack(side="left")
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(control_frame, textvariable=self.status_var, 
                                style='Status.TLabel')
        status_label.pack(side="right")
        
        # Progress bar
        progress_frame = ttk.Frame(self.scrollable_frame)
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100)
        self.progress_bar.pack(fill="x")
        
        # Current job info
        self.current_job_var = tk.StringVar(value="No active job")
        current_job_label = ttk.Label(progress_frame, textvariable=self.current_job_var, 
                                     style='Status.TLabel')
        current_job_label.pack(pady=(5, 0))
    
    def create_log_section(self):
        """Create collapsible log viewer section"""
        log_frame = CollapsibleFrame(self.scrollable_frame, "Processing Log", collapsed=True)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Log text widget with scrollbar
        log_container = ttk.Frame(log_frame.content_frame)
        log_container.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(log_container, height=10, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", 
                                     command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # Log controls
        log_controls = ttk.Frame(log_frame.content_frame)
        log_controls.pack(fill="x", pady=(5, 0))
        
        clear_log_btn = ttk.Button(log_controls, text="Clear Log", 
                                  command=self.clear_log)
        clear_log_btn.pack(side="left")
        
        save_log_btn = ttk.Button(log_controls, text="Save Log", 
                                 command=self.save_log)
        save_log_btn.pack(side="left", padx=(5, 0))
    
    def create_menus(self):
        """Create application menus"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import JSON Config...", command=self.import_json_config)
        file_menu.add_command(label="Export JSON Config...", command=self.export_json_config)
        file_menu.add_separator()
        file_menu.add_command(label="Set Gigapixel Path...", command=self.set_executable_path)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Validate Settings", command=self.validate_settings)
        tools_menu.add_command(label="Test Connection", command=self.test_connection)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    # Event handlers
    
    def on_model_selected(self, model: AIModel):
        """Handle model selection"""
        self.selected_model = model
        self.update_parameter_widgets(model)
        self.log_message(f"Selected model: {model.display_name}")
    
    def update_parameter_widgets(self, model: AIModel):
        """Update parameter widgets for the selected model"""
        # Find the category frame
        category = model.category
        if category not in self.model_widgets:
            return
        
        param_frame = self.model_widgets[category]['param_frame']
        param_widgets = self.model_widgets[category]['param_widgets']
        
        # Clear existing parameter widgets
        for widget in param_frame.winfo_children():
            widget.destroy()
        param_widgets.clear()
        
        # Create new parameter widgets
        for param_name, param_def in model.parameters.items():
            param_widget = ParameterWidget(param_frame, param_name, param_def)
            param_widget.pack(fill="x", pady=2)
            param_widgets[param_name] = param_widget
            
            # Bind parameter changes
            param_widget.bind_change(lambda name=param_name, value=None: 
                                   self.on_parameter_changed(name, value))
    
    def on_parameter_changed(self, param_name: str, value: Any):
        """Handle parameter value changes"""
        self.current_parameters[param_name] = value
    
    # File/folder browsing
    
    def browse_input_files(self):
        """Browse for input image files"""
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
            ("All files", "*.*")
        ]
        files = filedialog.askopenfilenames(title="Select Input Images", 
                                          filetypes=filetypes)
        if files:
            self.input_path_var.set("; ".join(files))
    
    def browse_input_folder(self):
        """Browse for input folder"""
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_path_var.set(folder)
    
    def browse_output_folder(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path_var.set(folder)
    
    # Processing
    
    def start_processing(self):
        """Start the processing operation"""
        if not self.validate_inputs():
            return
        
        try:
            # Initialize Gigapixel if needed
            if not self.gigapixel:
                if not self.executable_path:
                    messagebox.showerror("Error", "Please set the Gigapixel executable path first")
                    return
                
                self.gigapixel = Gigapixel(self.executable_path)
                callback = GUIProcessingCallback(self)
                self.gigapixel.add_callback(callback)
            
            # Create processing jobs
            jobs = self.create_processing_jobs()
            if not jobs:
                messagebox.showwarning("Warning", "No valid input files found")
                return
            
            self.current_jobs = jobs
            
            # Start processing in separate thread
            self.stop_processing.clear()
            self.processing_thread = threading.Thread(
                target=self.process_jobs_thread, 
                args=(jobs,), 
                daemon=True
            )
            self.processing_thread.start()
            
            # Update UI
            self.process_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status_var.set("Processing...")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start processing: {e}")
            self.log_message(f"Error starting processing: {e}", "ERROR")
    
    def process_jobs_thread(self, jobs: List[ProcessingJob]):
        """Process jobs in background thread"""
        try:
            # Set export parameters before processing
            self._set_export_parameters()
            
            # Process the batch
            self.gigapixel.process_batch(jobs, continue_on_error=True)
        except Exception as e:
            self.log_message(f"Batch processing error: {e}", "ERROR")
        finally:
            # Update UI on main thread
            self.root.after(0, self.processing_finished)
    
    def processing_finished(self):
        """Handle processing completion"""
        self.process_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("Processing completed")
        self.progress_var.set(100)
        
        # Show notification
        show_notification("GigaUp", "Processing completed!")
        play_completion_sound()
    
    def stop_processing_jobs(self):
        """Stop processing"""
        self.stop_processing.set()
        self.status_var.set("Stopping...")
        self.log_message("Processing stopped by user", "WARNING")
    
    def validate_inputs(self) -> bool:
        """Validate input parameters"""
        if not self.input_path_var.get().strip():
            messagebox.showerror("Error", "Please select input files or folder")
            return False
        
        if not self.output_path_var.get().strip():
            messagebox.showerror("Error", "Please select output folder")
            return False
        
        if not self.selected_model:
            messagebox.showerror("Error", "Please select a processing model")
            return False
        
        return True
    
    def create_processing_jobs(self) -> List[ProcessingJob]:
        """Create processing jobs from current settings"""
        jobs = []
        input_path = self.input_path_var.get().strip()
        # Note: output_folder is used for validation only, actual output is set via export dialog
        output_folder = Path(self.output_path_var.get().strip()) if self.output_path_var.get().strip() else None
        
        # Get current parameter values
        current_params = {}
        if self.selected_model:
            category = self.selected_model.category
            if category in self.model_widgets:
                param_widgets = self.model_widgets[category]['param_widgets']
                for param_name, widget in param_widgets.items():
                    current_params[param_name] = widget.get_value()
        
        # Create processing parameters
        parameters = self.model_factory.create_processing_parameters(
            self.selected_model.name,
            current_params,
            self.get_scale_value()
        )
        
        # Parse input paths
        if ";" in input_path:
            # Multiple files
            file_paths = [Path(p.strip()) for p in input_path.split(";") if p.strip()]
        elif os.path.isfile(input_path):
            # Single file
            file_paths = [Path(input_path)]
        elif os.path.isdir(input_path):
            # Folder - find all image files
            folder = Path(input_path)
            extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
            file_paths = [f for f in folder.iterdir() 
                         if f.is_file() and f.suffix.lower() in extensions]
        else:
            return []
        
        # Create jobs (output_path will be set by export dialog)
        for file_path in file_paths:
            if file_path.exists():
                # Generate output filename based on suffix settings
                base_name = file_path.stem
                extension = file_path.suffix
                
                # Get suffix based on mode
                suffix_mode = self.suffix_mode_var.get()
                if suffix_mode == "auto":
                    # Generate auto suffix from parameters
                    scale_value = self.get_scale_value()
                    suffix = generate_auto_suffix(parameters, scale_value, self.quality_var.get())
                elif suffix_mode == "custom":
                    suffix = self.custom_suffix_var.get()
                    if not suffix.startswith("-") and suffix:
                        suffix = "-" + suffix
                else:
                    suffix = ""
                
                # Construct output filename
                prefix = self.prefix_var.get()
                output_filename = f"{prefix}{base_name}{suffix}{extension}"
                
                # Create job without output_path (will be set by export dialog)
                job = ProcessingJob(
                    input_path=file_path,
                    output_path=None,  # Will be set by export dialog
                    parameters=parameters
                )
                # Store the generated filename for reference
                job.output_filename = output_filename
                jobs.append(job)
        
        return jobs
    
    # Callback handlers
    
    def on_job_start(self, job: ProcessingJob):
        """Handle job start"""
        self.root.after(0, lambda: self.current_job_var.set(f"Processing: {job.input_path.name}"))
        self.root.after(0, lambda: self.log_message(f"Started processing: {job.input_path.name}"))
    
    def on_job_progress(self, job: ProcessingJob, progress: float):
        """Handle job progress"""
        self.root.after(0, lambda: self.progress_var.set(progress))
    
    def on_job_complete(self, job: ProcessingJob):
        """Handle job completion"""
        self.root.after(0, lambda: self.log_message(f"Completed: {job.input_path.name}", "SUCCESS"))
    
    def on_job_error(self, job: ProcessingJob, error: str):
        """Handle job error"""
        self.root.after(0, lambda: self.log_message(f"Error processing {job.input_path.name}: {error}", "ERROR"))
    
    def on_batch_start(self, jobs: List[ProcessingJob]):
        """Handle batch start"""
        self.root.after(0, lambda: self.log_message(f"Started batch processing {len(jobs)} files"))
    
    def on_batch_complete(self, jobs: List[ProcessingJob]):
        """Handle batch completion"""
        completed = len([j for j in jobs if j.status == "completed"])
        failed = len([j for j in jobs if j.status == "error"])
        self.root.after(0, lambda: self.log_message(
            f"Batch completed: {completed} successful, {failed} failed", "SUCCESS"))
    
    # Preset management
    
    def update_preset_list(self):
        """Update the preset list"""
        presets = self.model_factory.list_presets()
        self.preset_combo['values'] = presets
    
    def load_preset(self):
        """Load selected preset"""
        preset_name = self.preset_var.get()
        if not preset_name:
            return
        
        try:
            parameters = self.model_factory.load_preset(preset_name)
            if parameters:
                self.apply_preset_parameters(parameters)
                self.log_message(f"Loaded preset: {preset_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preset: {e}")
    
    def save_preset(self):
        """Save current settings as preset"""
        preset_name = self.preset_name_var.get().strip()
        if not preset_name:
            messagebox.showerror("Error", "Please enter a preset name")
            return
        
        if not self.selected_model:
            messagebox.showerror("Error", "Please select a model first")
            return
        
        try:
            # Get current parameters
            current_params = {}
            category = self.selected_model.category
            if category in self.model_widgets:
                param_widgets = self.model_widgets[category]['param_widgets']
                for param_name, widget in param_widgets.items():
                    current_params[param_name] = widget.get_value()
            
            # Create processing parameters
            parameters = self.model_factory.create_processing_parameters(
                self.selected_model.name,
                current_params,
                self.get_scale_value()
            )
            
            # Save preset
            self.model_factory.save_preset(preset_name, parameters)
            self.update_preset_list()
            self.log_message(f"Saved preset: {preset_name}")
            self.preset_name_var.set("")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset: {e}")
    
    def delete_preset(self):
        """Delete selected preset"""
        preset_name = self.preset_var.get()
        if not preset_name:
            return
        
        if messagebox.askyesno("Confirm", f"Delete preset '{preset_name}'?"):
            try:
                self.model_factory.delete_preset(preset_name)
                self.update_preset_list()
                self.preset_var.set("")
                self.log_message(f"Deleted preset: {preset_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete preset: {e}")
    
    def apply_preset_parameters(self, parameters: ProcessingParameters):
        """Apply loaded preset parameters to UI"""
        # Select the model
        model = parameters.model
        category = model.category
        
        if category in self.model_widgets:
            # Select the model radio button
            self.model_widgets[category]['var'].set(model.name)
            self.on_model_selected(model)
            
            # Set parameter values
            param_widgets = self.model_widgets[category]['param_widgets']
            for param_name, param_value in parameters.parameters.items():
                if param_name in param_widgets:
                    param_widgets[param_name].set_value(param_value)
        
        # Set scale
        if parameters.scale:
            self.scale_var.set(parameters.scale)
    
    # Utility methods
    
    def clear_queue(self):
        """Clear the processing queue"""
        self.current_jobs.clear()
        self.log_message("Processing queue cleared")
    
    def clear_log(self):
        """Clear the log text"""
        self.log_text.delete(1.0, tk.END)
    
    def save_log(self):
        """Save log to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Success", "Log saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {e}")
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    # Settings and configuration
    
    def load_settings(self):
        """Load application settings"""
        settings_file = Path.home() / ".gigapixel" / "gui_settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                if 'executable_path' in settings:
                    self.executable_path = settings['executable_path']
                
                if 'window_geometry' in settings:
                    self.root.geometry(settings['window_geometry'])
                
            except Exception as e:
                self.log_message(f"Failed to load settings: {e}", "WARNING")
    
    def save_settings(self):
        """Save application settings"""
        settings_file = Path.home() / ".gigapixel" / "gui_settings.json"
        settings_file.parent.mkdir(exist_ok=True)
        
        try:
            settings = {
                'executable_path': self.executable_path,
                'window_geometry': self.root.geometry()
            }
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
                
        except Exception as e:
            self.log_message(f"Failed to save settings: {e}", "WARNING")
    
    def set_executable_path(self):
        """Set Gigapixel executable path"""
        filename = filedialog.askopenfilename(
            title="Select Topaz Gigapixel AI Executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.executable_path = filename
            self.gigapixel = None  # Reset connection
            self.log_message(f"Gigapixel path set to: {filename}")
    
    def validate_settings(self):
        """Validate current settings"""
        errors = []
        
        if not self.executable_path:
            errors.append("Gigapixel executable path not set")
        elif not os.path.exists(self.executable_path):
            errors.append("Gigapixel executable not found")
        
        if not self.input_path_var.get().strip():
            errors.append("No input path specified")
        
        if not self.output_path_var.get().strip():
            errors.append("No output path specified")
        
        if not self.selected_model:
            errors.append("No model selected")
        
        if errors:
            messagebox.showerror("Validation Errors", "\\n".join(errors))
        else:
            messagebox.showinfo("Validation", "All settings are valid!")
    
    def test_connection(self):
        """Test connection to Gigapixel"""
        if not self.executable_path:
            messagebox.showerror("Error", "Please set Gigapixel executable path first")
            return
        
        try:
            test_gigapixel = Gigapixel(self.executable_path)
            messagebox.showinfo("Success", "Successfully connected to Gigapixel AI!")
            self.log_message("Connection test successful")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to Gigapixel: {e}")
            self.log_message(f"Connection test failed: {e}", "ERROR")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """GigaUp - Advanced Gigapixel AI Automation
        
Version: 2.0.0
Author: Enhanced by Claude
        
A comprehensive desktop tool for automating Topaz Gigapixel AI
with support for all the latest AI models and batch processing.
        
Features:
• Support for all AI model categories
• Advanced parameter control with value verification
• Batch processing with progress tracking
• Export settings (quality, prefix, suffix)
• Auto-suffix generation from parameters
• JSON configuration import/export
• Preset management
• Comprehensive logging
• Audio/visual notifications
• Processing completion detection"""
        
        messagebox.showinfo("About GigaUp", about_text)
    
    def _set_export_parameters(self):
        """Set export parameters in Gigapixel before processing"""
        # Get suffix based on mode
        suffix_mode = self.suffix_mode_var.get()
        suffix_config = {}
        
        if suffix_mode == "auto":
            # Auto mode - will generate suffix from parameters
            suffix_config = {"mode": "auto"}
            # For auto mode, we need to generate the suffix and set it
            if self.current_jobs:
                # Generate suffix from first job parameters
                scale_value = self.get_scale_value()
                auto_suffix = generate_auto_suffix(
                    self.current_jobs[0].parameters, 
                    scale_value, 
                    self.quality_var.get()
                )
                # Keep the dash - export dialog now handles it properly
                suffix_value = auto_suffix
            else:
                suffix_value = "1"  # Default if no jobs
        elif suffix_mode == "custom":
            suffix_value = self.custom_suffix_var.get()
            # Keep the dash - export dialog now handles it properly
        else:
            # None mode
            suffix_value = "0"
        
        # Set export parameters
        self.gigapixel.set_export_parameters(
            quality=self.quality_var.get(),
            prefix=self.prefix_var.get(),
            suffix=suffix_value
        )
        
        # Set output directory if specified
        output_path = self.output_path_var.get().strip()
        if output_path:
            self.gigapixel.set_output_directory(output_path)
    
    def import_json_config(self):
        """Import settings from JSON configuration file"""
        filename = filedialog.askopenfilename(
            title="Import JSON Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
            
            # Apply settings from config
            if 'input' in config:
                self.input_path_var.set(config['input'])
            
            if 'output' in config:
                self.output_path_var.set(config['output'])
            
            if 'executable' in config:
                self.executable_path = config['executable']
            
            if 'quality' in config:
                self.quality_var.set(config['quality'])
            
            if 'prefix' in config:
                self.prefix_var.set(config['prefix'])
            
            if 'suffix' in config:
                # Parse suffix mode
                suffix_config = parse_suffix_mode(config['suffix'])
                if suffix_config['mode'] == 'auto':
                    self.suffix_mode_var.set('auto')
                elif suffix_config['mode'] == 'custom':
                    self.suffix_mode_var.set('custom')
                    self.custom_suffix_var.set(suffix_config['value'])
                else:
                    self.suffix_mode_var.set('none')
            
            # Apply model and parameters
            if 'model' in config:
                # Find and select the model
                model_name = config['model']
                model = self.model_factory.get_model_by_name(model_name)
                if model:
                    # Find the category and select it
                    category = model.category
                    if category in self.model_widgets:
                        self.model_widgets[category]['var'].set(model.name)
                        self.on_model_selected(model)
                        
                        # Apply parameters if present
                        if 'parameters' in config:
                            param_widgets = self.model_widgets[category]['param_widgets']
                            for param_name, param_value in config['parameters'].items():
                                if param_name in param_widgets:
                                    param_widgets[param_name].set_value(param_value)
            
            # Apply scale
            if 'scale' in config:
                self.scale_var.set(config['scale'])
            elif 'width' in config:
                self.scale_var.set(f"w{config['width']}")
            elif 'height' in config:
                self.scale_var.set(f"h{config['height']}")
            
            self.log_message(f"Imported configuration from {filename}", "SUCCESS")
            messagebox.showinfo("Success", "Configuration imported successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import configuration: {e}")
            self.log_message(f"Failed to import configuration: {e}", "ERROR")
    
    def export_json_config(self):
        """Export current settings to JSON configuration file"""
        filename = filedialog.asksaveasfilename(
            title="Export JSON Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filename:
            return
        
        try:
            # Gather current settings
            config = {
                "input": self.input_path_var.get(),
                "output": self.output_path_var.get(),
                "executable": self.executable_path,
                "quality": self.quality_var.get(),
                "prefix": self.prefix_var.get()
            }
            
            # Handle suffix based on mode
            suffix_mode = self.suffix_mode_var.get()
            if suffix_mode == "auto":
                config["suffix"] = "auto"
            elif suffix_mode == "custom":
                config["suffix"] = self.custom_suffix_var.get()
            else:
                config["suffix"] = "0"
            
            # Add model and parameters
            if self.selected_model:
                config["model"] = self.selected_model.name
                
                # Get current parameter values
                category = self.selected_model.category
                if category in self.model_widgets:
                    param_widgets = self.model_widgets[category]['param_widgets']
                    parameters = {}
                    for param_name, widget in param_widgets.items():
                        parameters[param_name] = widget.get_value()
                    config["parameters"] = parameters
            
            # Add scale
            scale_value = self.scale_var.get()
            if scale_value.startswith('w'):
                config["width"] = scale_value[1:]
            elif scale_value.startswith('h'):
                config["height"] = scale_value[1:]
            else:
                config["scale"] = scale_value
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.log_message(f"Exported configuration to {filename}", "SUCCESS")
            messagebox.showinfo("Success", "Configuration exported successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export configuration: {e}")
            self.log_message(f"Failed to export configuration: {e}", "ERROR")
    
    def on_closing(self):
        """Handle application closing"""
        if self.processing_thread and self.processing_thread.is_alive():
            if messagebox.askyesno("Confirm Exit", "Processing is still running. Stop and exit?"):
                self.stop_processing.set()
            else:
                return
        
        self.save_settings()
        self.root.destroy()
    
    def run(self):
        """Start the GUI application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Main entry point for GUI application"""
    app = GigaUpWindow()
    app.run()


if __name__ == "__main__":
    main()