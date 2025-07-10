import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional, Union
import time

from ..models import ModelParameter


class CollapsibleFrame(ttk.Frame):
    """A collapsible frame widget with expand/collapse functionality"""
    
    def __init__(self, parent, title: str = "", collapsed: bool = False, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title = title
        self.collapsed = collapsed
        self._callbacks = []
        
        # Create header frame
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill="x", pady=(0, 2))
        
        # Toggle button
        self.toggle_button = ttk.Button(
            self.header_frame,
            text=self._get_toggle_text(),
            command=self.toggle,
            width=3
        )
        self.toggle_button.pack(side="left", padx=(0, 5))
        
        # Title label
        self.title_label = ttk.Label(
            self.header_frame,
            text=self.title,
            font=("Arial", 10, "bold")
        )
        self.title_label.pack(side="left", anchor="w")
        
        # Content frame
        self.content_frame = ttk.Frame(self)
        if not self.collapsed:
            self.content_frame.pack(fill="both", expand=True, padx=(20, 0))
    
    def _get_toggle_text(self) -> str:
        """Get the toggle button text based on state"""
        return "−" if not self.collapsed else "+"
    
    def toggle(self):
        """Toggle the collapsed state"""
        self.collapsed = not self.collapsed
        self.toggle_button.config(text=self._get_toggle_text())
        
        if self.collapsed:
            self.content_frame.pack_forget()
        else:
            self.content_frame.pack(fill="both", expand=True, padx=(20, 0))
        
        # Notify callbacks
        for callback in self._callbacks:
            callback(self.collapsed)
    
    def expand(self):
        """Expand the frame"""
        if self.collapsed:
            self.toggle()
    
    def collapse(self):
        """Collapse the frame"""
        if not self.collapsed:
            self.toggle()
    
    def bind_toggle(self, callback: Callable[[bool], None]):
        """Bind a callback for toggle events"""
        self._callbacks.append(callback)


class ToolTip:
    """Tooltip widget that shows help text on hover"""
    
    def __init__(self, widget, text: str, delay: int = 1500):
        self.widget = widget
        self.text = text
        self.delay = delay  # Delay in milliseconds
        
        self.tooltip_window = None
        self.after_id = None
        
        # Bind events
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)
    
    def on_enter(self, event=None):
        """Handle mouse enter event"""
        self.schedule_tooltip()
    
    def on_leave(self, event=None):
        """Handle mouse leave event"""
        self.cancel_tooltip()
        self.hide_tooltip()
    
    def on_motion(self, event=None):
        """Handle mouse motion - restart the timer"""
        self.cancel_tooltip()
        self.schedule_tooltip()
    
    def schedule_tooltip(self):
        """Schedule tooltip to show after delay"""
        self.after_id = self.widget.after(self.delay, self.show_tooltip)
    
    def cancel_tooltip(self):
        """Cancel scheduled tooltip"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
    
    def show_tooltip(self):
        """Show the tooltip"""
        if self.tooltip_window:
            return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip content
        frame = ttk.Frame(self.tooltip_window, relief="solid", borderwidth=1)
        frame.pack()
        
        label = ttk.Label(
            frame,
            text=self.text,
            background="lightyellow",
            relief="flat",
            font=("Arial", 9),
            wraplength=300
        )
        label.pack(padx=2, pady=2)
    
    def hide_tooltip(self):
        """Hide the tooltip"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class ParameterWidget(ttk.Frame):
    """A widget for editing model parameters"""
    
    def __init__(self, parent, param_name: str, param_def: ModelParameter, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.param_name = param_name
        self.param_def = param_def
        self.change_callbacks = []
        
        self._create_widget()
    
    def _create_widget(self):
        """Create the appropriate widget based on parameter type"""
        # Label
        label_text = self.param_name.replace("_", " ").title()
        self.label = ttk.Label(self, text=f"{label_text}:")
        self.label.pack(side="left", anchor="w", padx=(0, 5))
        
        # Add tooltip with description
        if self.param_def.description:
            tooltip_text = self.param_def.description
            if self.param_def.min_value is not None or self.param_def.max_value is not None:
                tooltip_text += f"\\nRange: {self.param_def.min_value} - {self.param_def.max_value}"
            if self.param_def.default_value is not None:
                tooltip_text += f"\\nDefault: {self.param_def.default_value}"
            ToolTip(self.label, tooltip_text)
        
        # Create input widget based on parameter type
        if self.param_def.param_type == "boolean":
            self._create_boolean_widget()
        elif self.param_def.param_type == "integer":
            self._create_integer_widget()
        elif self.param_def.param_type == "decimal":
            self._create_decimal_widget()
        elif self.param_def.param_type == "text":
            self._create_text_widget()
        else:
            # Fallback to text entry
            self._create_text_widget()
    
    def _create_boolean_widget(self):
        """Create checkbox for boolean parameter"""
        self.var = tk.BooleanVar()
        if self.param_def.default_value is not None:
            self.var.set(self.param_def.default_value)
        
        self.widget = ttk.Checkbutton(
            self,
            variable=self.var,
            command=self._on_change
        )
        self.widget.pack(side="left")
    
    def _create_integer_widget(self):
        """Create spinbox for integer parameter"""
        self.var = tk.IntVar()
        if self.param_def.default_value is not None:
            self.var.set(int(self.param_def.default_value))
        
        # Determine range
        from_val = self.param_def.min_value if self.param_def.min_value is not None else -999999
        to_val = self.param_def.max_value if self.param_def.max_value is not None else 999999
        
        self.widget = ttk.Spinbox(
            self,
            from_=from_val,
            to=to_val,
            textvariable=self.var,
            width=10,
            command=self._on_change
        )
        self.widget.pack(side="left")
        self.widget.bind("<KeyRelease>", lambda e: self._on_change())
    
    def _create_decimal_widget(self):
        """Create scale and entry for decimal parameter"""
        container = ttk.Frame(self)
        container.pack(side="left", fill="x", expand=True)
        
        self.var = tk.DoubleVar()
        if self.param_def.default_value is not None:
            self.var.set(float(self.param_def.default_value))
        
        # Entry for exact value
        self.widget = ttk.Entry(container, textvariable=self.var, width=8)
        self.widget.pack(side="left", padx=(0, 5))
        self.widget.bind("<KeyRelease>", lambda e: self._on_change())
        
        # Scale for easy adjustment
        if (self.param_def.min_value is not None and 
            self.param_def.max_value is not None):
            
            self.scale = ttk.Scale(
                container,
                from_=self.param_def.min_value,
                to=self.param_def.max_value,
                variable=self.var,
                orient="horizontal",
                length=100,
                command=lambda x: self._on_change()
            )
            self.scale.pack(side="left")
    
    def _create_text_widget(self):
        """Create entry for text parameter"""
        self.var = tk.StringVar()
        if self.param_def.default_value is not None:
            self.var.set(str(self.param_def.default_value))
        
        # Determine width based on max_length
        width = min(50, self.param_def.max_length) if self.param_def.max_length else 20
        
        self.widget = ttk.Entry(
            self,
            textvariable=self.var,
            width=width
        )
        self.widget.pack(side="left", fill="x", expand=True)
        self.widget.bind("<KeyRelease>", lambda e: self._on_change())
        
        # Show character count for text fields with max_length
        if self.param_def.max_length:
            self.char_count_label = ttk.Label(
                self,
                text=f"0/{self.param_def.max_length}",
                font=("Arial", 8)
            )
            self.char_count_label.pack(side="right", padx=(5, 0))
            self.var.trace_add("write", self._update_char_count)
    
    def _update_char_count(self, *args):
        """Update character count display"""
        if hasattr(self, 'char_count_label'):
            current_length = len(self.var.get())
            max_length = self.param_def.max_length
            self.char_count_label.config(text=f"{current_length}/{max_length}")
            
            # Change color if approaching limit
            if current_length > max_length * 0.9:
                self.char_count_label.config(foreground="red")
            elif current_length > max_length * 0.7:
                self.char_count_label.config(foreground="orange")
            else:
                self.char_count_label.config(foreground="black")
    
    def _on_change(self):
        """Handle parameter value change"""
        value = self.get_value()
        for callback in self.change_callbacks:
            callback(self.param_name, value)
    
    def get_value(self) -> Any:
        """Get the current parameter value"""
        if hasattr(self, 'var'):
            value = self.var.get()
            
            # Validate and convert value
            try:
                if self.param_def.param_type == "integer":
                    int_value = int(value)
                    # Clamp to valid range
                    if self.param_def.min_value is not None:
                        int_value = max(int_value, int(self.param_def.min_value))
                    if self.param_def.max_value is not None:
                        int_value = min(int_value, int(self.param_def.max_value))
                    return int_value
                elif self.param_def.param_type == "decimal":
                    float_value = float(value)
                    # Clamp to valid range
                    if self.param_def.min_value is not None:
                        float_value = max(float_value, self.param_def.min_value)
                    if self.param_def.max_value is not None:
                        float_value = min(float_value, self.param_def.max_value)
                    return round(float_value, 3)  # Round to avoid precision issues
                elif self.param_def.param_type == "boolean":
                    return bool(value)
                else:
                    return str(value)
            except (ValueError, TypeError):
                return self.param_def.default_value
        
        return self.param_def.default_value
    
    def set_value(self, value: Any):
        """Set the parameter value"""
        if hasattr(self, 'var'):
            try:
                if self.param_def.param_type == "boolean":
                    self.var.set(bool(value))
                elif self.param_def.param_type == "integer":
                    self.var.set(int(value))
                elif self.param_def.param_type == "decimal":
                    self.var.set(float(value))
                else:
                    self.var.set(str(value))
            except (ValueError, TypeError):
                # If conversion fails, use default value
                if self.param_def.default_value is not None:
                    self.set_value(self.param_def.default_value)
    
    def bind_change(self, callback: Callable[[str, Any], None]):
        """Bind a callback for value changes"""
        self.change_callbacks.append(callback)
    
    def reset_to_default(self):
        """Reset parameter to default value"""
        if self.param_def.default_value is not None:
            self.set_value(self.param_def.default_value)


class ProgressFrame(ttk.Frame):
    """A frame containing progress indicators and job information"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.current_job = None
        self.total_jobs = 0
        self.completed_jobs = 0
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create progress widgets"""
        # Overall progress
        overall_label = ttk.Label(self, text="Overall Progress:", font=("Arial", 9, "bold"))
        overall_label.pack(anchor="w")
        
        self.overall_progress = ttk.Progressbar(self, mode="determinate")
        self.overall_progress.pack(fill="x", pady=(2, 5))
        
        # Current job progress
        job_label = ttk.Label(self, text="Current Job:", font=("Arial", 9, "bold"))
        job_label.pack(anchor="w")
        
        self.job_progress = ttk.Progressbar(self, mode="indeterminate")
        self.job_progress.pack(fill="x", pady=(2, 5))
        
        # Status labels
        self.status_label = ttk.Label(self, text="Ready", font=("Arial", 9))
        self.status_label.pack(anchor="w")
        
        self.job_label = ttk.Label(self, text="No active job", font=("Arial", 8))
        self.job_label.pack(anchor="w")
        
        self.stats_label = ttk.Label(self, text="", font=("Arial", 8))
        self.stats_label.pack(anchor="w")
    
    def start_batch(self, total_jobs: int):
        """Start a new batch of jobs"""
        self.total_jobs = total_jobs
        self.completed_jobs = 0
        self.overall_progress.config(maximum=total_jobs, value=0)
        self.update_status("Processing...")
        self.update_stats()
    
    def start_job(self, job_name: str):
        """Start processing a specific job"""
        self.current_job = job_name
        self.job_progress.config(mode="indeterminate")
        self.job_progress.start()
        self.job_label.config(text=f"Processing: {job_name}")
    
    def complete_job(self, success: bool = True):
        """Complete the current job"""
        if success:
            self.completed_jobs += 1
        
        self.job_progress.stop()
        self.job_progress.config(mode="determinate", value=100)
        self.overall_progress.config(value=self.completed_jobs)
        self.update_stats()
        
        if self.completed_jobs >= self.total_jobs:
            self.complete_batch()
    
    def complete_batch(self):
        """Complete the entire batch"""
        self.job_progress.stop()
        self.update_status("Completed")
        self.job_label.config(text="All jobs completed")
        self.current_job = None
    
    def update_status(self, status: str):
        """Update the main status"""
        self.status_label.config(text=status)
    
    def update_stats(self):
        """Update statistics display"""
        if self.total_jobs > 0:
            remaining = self.total_jobs - self.completed_jobs
            self.stats_label.config(
                text=f"Completed: {self.completed_jobs}, Remaining: {remaining}, Total: {self.total_jobs}"
            )
        else:
            self.stats_label.config(text="")
    
    def reset(self):
        """Reset all progress indicators"""
        self.job_progress.stop()
        self.job_progress.config(value=0)
        self.overall_progress.config(value=0)
        self.current_job = None
        self.total_jobs = 0
        self.completed_jobs = 0
        self.update_status("Ready")
        self.job_label.config(text="No active job")
        self.stats_label.config(text="")


class LogViewer(ttk.Frame):
    """A widget for displaying and managing log messages"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.auto_scroll = True
        self.max_lines = 1000
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create log viewer widgets"""
        # Text widget with scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill="both", expand=True)
        
        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            height=10,
            font=("Consolas", 9)
        )
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Controls frame
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill="x", pady=(5, 0))
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(
            controls_frame,
            text="Auto-scroll",
            variable=self.auto_scroll_var,
            command=self._on_auto_scroll_change
        )
        auto_scroll_check.pack(side="left")
        
        # Clear button
        clear_btn = ttk.Button(controls_frame, text="Clear", command=self.clear)
        clear_btn.pack(side="left", padx=(10, 0))
        
        # Copy button
        copy_btn = ttk.Button(controls_frame, text="Copy All", command=self.copy_all)
        copy_btn.pack(side="left", padx=(5, 0))
        
        # Configure text tags for different log levels
        self.text_widget.tag_configure("INFO", foreground="black")
        self.text_widget.tag_configure("SUCCESS", foreground="green")
        self.text_widget.tag_configure("WARNING", foreground="orange")
        self.text_widget.tag_configure("ERROR", foreground="red")
        self.text_widget.tag_configure("DEBUG", foreground="blue")
    
    def add_message(self, message: str, level: str = "INFO", timestamp: bool = True):
        """Add a message to the log"""
        if timestamp:
            time_str = time.strftime("%H:%M:%S")
            full_message = f"[{time_str}] {level}: {message}\\n"
        else:
            full_message = f"{message}\\n"
        
        # Insert message with appropriate tag
        self.text_widget.insert(tk.END, full_message, level)
        
        # Limit number of lines
        self._limit_lines()
        
        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.text_widget.see(tk.END)
    
    def _limit_lines(self):
        """Limit the number of lines in the text widget"""
        lines = int(self.text_widget.index(tk.END).split('.')[0])
        if lines > self.max_lines:
            # Remove oldest lines
            lines_to_remove = lines - self.max_lines
            self.text_widget.delete(1.0, f"{lines_to_remove}.0")
    
    def _on_auto_scroll_change(self):
        """Handle auto-scroll setting change"""
        self.auto_scroll = self.auto_scroll_var.get()
    
    def clear(self):
        """Clear all log messages"""
        self.text_widget.delete(1.0, tk.END)
    
    def copy_all(self):
        """Copy all log content to clipboard"""
        content = self.text_widget.get(1.0, tk.END)
        self.text_widget.clipboard_clear()
        self.text_widget.clipboard_append(content)
    
    def get_content(self) -> str:
        """Get all log content as string"""
        return self.text_widget.get(1.0, tk.END)