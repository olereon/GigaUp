#!/usr/bin/env python3
"""
Command-line interface for GigaUp - Topaz Gigapixel AI Automation
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

from .gigapixel import Gigapixel, ProcessingJob
from .models import ModelCategory, AIModel
from .factory import get_model_factory
from .parameters import ProcessingParameters
from .exceptions import GigapixelException
from .suffix_generator import generate_auto_suffix, parse_suffix_mode


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="GigaUp - Advanced Topaz Gigapixel AI Automation Tool",
        epilog="For more information, visit: https://github.com/olereon/GigaUp"
    )
    
    # Required arguments (or use --json)
    parser.add_argument(
        "input",
        nargs="*",  # Changed from "+" to "*" to allow optional when using --json
        help="Input image file(s) or directory to process"
    )
    
    parser.add_argument(
        "-e", "--executable",
        help="Path to Topaz Gigapixel AI executable"
    )
    
    # JSON config option
    parser.add_argument(
        "--json",
        help="Path to JSON configuration file containing all parameters"
    )
    
    # Output options
    parser.add_argument(
        "-o", "--output",
        help="Output directory (default: same as input with '_enhanced' suffix)"
    )
    
    # Model selection
    parser.add_argument(
        "-m", "--model",
        help="AI model to use (use --list-models to see available models)"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all available AI models and exit"
    )
    
    parser.add_argument(
        "--model-info",
        help="Show detailed information about a specific model"
    )
    
    # Size options (mutually exclusive)
    size_group = parser.add_mutually_exclusive_group()
    size_group.add_argument(
        "-s", "--scale",
        help="Scale factor for upscaling (e.g., 1x, 2x, 4x, 6x, 1.5, 3.5)"
    )
    size_group.add_argument(
        "-w", "--width",
        type=int,
        help="Target width in pixels (max 16384, maintains aspect ratio)"
    )
    size_group.add_argument(
        "--height", 
        type=int,
        help="Target height in pixels (max 16384, maintains aspect ratio)"
    )
    
    # Parameters
    parser.add_argument(
        "-p", "--parameters",
        help="Model parameters as JSON string or file path"
    )
    
    # Preset management
    parser.add_argument(
        "--preset",
        help="Use a saved preset"
    )
    
    parser.add_argument(
        "--save-preset",
        help="Save current settings as a preset with given name"
    )
    
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List all saved presets and exit"
    )
    
    # Export options
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=95,
        help="Output image quality (1-100, default: 95)"
    )
    
    parser.add_argument(
        "--suffix",
        default="auto",
        help="Output filename suffix: 0=empty+toggle off, 1=empty+toggle on, 'string'=custom suffix+toggle off, 'auto'=generate suffix from parameters (default: auto)"
    )
    
    parser.add_argument(
        "--prefix",
        default="",
        help="Output filename prefix (default: empty)"
    )
    
    # Legacy compatibility
    parser.add_argument(
        "--legacy-mode",
        choices=["Standard", "High fidelity", "Low res", "Text & shapes", "Art & CG", "Recovery"],
        help="Use legacy mode for backward compatibility"
    )
    
    # Processing options
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        default=True,
        help="Continue processing other files if one fails (default: True)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Processing timeout in seconds (default: 900)"
    )
    
    # Output options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output except errors"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually processing"
    )
    
    parser.add_argument(
        "--debug-ui",
        action="store_true",
        help="Enable UI debugging mode to manually identify parameter controls"
    )
    
    parser.add_argument(
        "--preset-mode",
        action="store_true",
        help="Preset mode: use Gigapixel's saved settings, only open files and set prompt if provided"
    )
    
    return parser


def list_models():
    """List all available AI models"""
    factory = get_model_factory()
    categories = [ModelCategory.ENHANCE, ModelCategory.SHARPEN, ModelCategory.DENOISE, 
                 ModelCategory.RESTORE, ModelCategory.LIGHTING]
    
    print("Available AI Models:")
    print("=" * 50)
    
    for category in categories:
        models = factory.get_models_by_category(category)
        if models:
            print(f"\n{category.value}:")
            print("-" * (len(category.value) + 1))
            
            for model in models:
                class_indicator = "[G]" if model.model_class.name == "GENERATIVE" else "[S]"
                print(f"  {class_indicator} {model.name:<20} - {model.display_name}")
                if len(model.description) > 60:
                    desc = model.description[:57] + "..."
                else:
                    desc = model.description
                print(f"      {desc}")
    
    print("\nLegend: [S] = Standard, [G] = Generative")


def show_model_info(model_name: str):
    """Show detailed information about a specific model"""
    try:
        factory = get_model_factory()
        model = factory.get_model_by_name(model_name)
        
        print(f"Model Information: {model.display_name}")
        print("=" * (len(model.display_name) + 19))
        print(f"Name: {model.name}")
        print(f"Category: {model.category.value}")
        print(f"Class: {model.model_class.value}")
        print(f"Description: {model.description}")
        
        if model.parameters:
            print("\nParameters:")
            print("-" * 11)
            for param_name, param_def in model.parameters.items():
                print(f"  {param_name}:")
                print(f"    Type: {param_def.param_type}")
                if param_def.min_value is not None or param_def.max_value is not None:
                    print(f"    Range: {param_def.min_value} - {param_def.max_value}")
                if param_def.default_value is not None:
                    print(f"    Default: {param_def.default_value}")
                if param_def.description:
                    print(f"    Description: {param_def.description}")
                if param_def.max_length:
                    print(f"    Max length: {param_def.max_length}")
                print()
        else:
            print("\nNo configurable parameters.")
            
    except Exception as e:
        print(f"Error: Model '{model_name}' not found. Use --list-models to see available models.")
        sys.exit(1)


def list_presets():
    """List all saved presets"""
    factory = get_model_factory()
    presets = factory.list_presets()
    
    if not presets:
        print("No saved presets found.")
        return
    
    print("Saved Presets:")
    print("=" * 14)
    for preset in presets:
        try:
            preset_data = factory.load_preset(preset)
            if preset_data:
                print(f"  {preset:<20} - {preset_data.model.display_name} ({preset_data.scale or 'no scale'})")
            else:
                print(f"  {preset:<20} - (invalid preset)")
        except Exception:
            print(f"  {preset:<20} - (error loading)")


def validate_scale(scale_str: str) -> str:
    """Validate scale value and return it if valid"""
    # Check if it's a standard scale
    if scale_str in ["1x", "2x", "4x", "6x"]:
        return scale_str
    
    # Try to parse as custom scale
    try:
        # Remove 'x' suffix if present
        if scale_str.endswith('x'):
            scale_str = scale_str[:-1]
        
        scale_value = float(scale_str)
        if scale_value <= 0:
            print(f"Error: Scale must be positive, got {scale_value}")
            sys.exit(1)
        
        # Return as string without 'x' suffix for custom scales
        return str(scale_value)
    except ValueError:
        print(f"Error: Invalid scale value '{scale_str}'. Use standard scales (1x, 2x, 4x, 6x) or custom values (e.g., 1.5, 3.5)")
        sys.exit(1)


def validate_dimensions(args) -> str:
    """Validate dimension arguments and return the appropriate size parameter"""
    size_count = sum([bool(args.scale), bool(args.width), bool(args.height)])
    
    if size_count == 0:
        # Default to 2x scale
        return "2x"
    elif size_count > 1:
        print("Error: Multiple image size values. Please provide only one of: --scale, --width, or --height")
        sys.exit(1)
    
    if args.scale:
        return validate_scale(args.scale)
    elif args.width:
        if args.width <= 0 or args.width > 16384:
            print(f"Error: Width must be between 1 and 16384, got {args.width}")
            sys.exit(1)
        return f"w{args.width}"
    elif args.height:
        if args.height <= 0 or args.height > 16384:
            print(f"Error: Height must be between 1 and 16384, got {args.height}")
            sys.exit(1)
        return f"h{args.height}"
        

def validate_quality(quality: int) -> int:
    """Validate quality parameter"""
    if quality < 1 or quality > 100:
        print(f"Error: Quality must be between 1 and 100, got {quality}")
        sys.exit(1)
    return quality


def load_json_config(json_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file with enhanced parsing for Windows paths"""
    try:
        with open(json_path, 'r') as f:
            content = f.read()
        
        # Try to parse as-is first
        try:
            config = json.loads(content)
            return config
        except json.JSONDecodeError:
            # If parsing fails, try to fix common issues
            import re
            
            # Fix 1: Add missing commas in arrays
            # Pattern: "text" "text" -> "text", "text"
            fixed_content = re.sub(r'"\s+"', '", "', content)
            
            # Fix 2: Convert single backslashes to double backslashes for JSON validity
            # Simple approach: replace all single backslashes with double backslashes in strings
            # First, find all strings and fix backslashes within them
            import re
            
            def fix_backslashes_in_strings(match):
                # Get the string content (without quotes)
                string_content = match.group(1)
                # Replace single backslashes with double backslashes, but avoid double-escaping
                # If we see \\, keep it as \\\\, if we see \, make it \\\\
                result = ""
                i = 0
                while i < len(string_content):
                    if string_content[i] == '\\':
                        if i + 1 < len(string_content) and string_content[i + 1] == '\\':
                            # Already escaped, keep as double backslash
                            result += '\\\\\\\\'
                            i += 2
                        else:
                            # Single backslash, make it double
                            result += '\\\\\\\\'
                            i += 1
                    else:
                        result += string_content[i]
                        i += 1
                # Return with quotes
                return '"' + result + '"'
            
            # Apply to all strings in JSON  
            fixed_content = re.sub(r'"([^"]*)"', fix_backslashes_in_strings, fixed_content)
            
            try:
                config = json.loads(fixed_content)
                print("⚠️  JSON file had formatting issues but was automatically fixed during parsing")
                return config
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in config file even after attempted fixes: {e}")
                print(f"Original content around error:")
                lines = content.split('\n')
                if hasattr(e, 'lineno') and e.lineno:
                    start = max(0, e.lineno - 2)
                    end = min(len(lines), e.lineno + 1)
                    for i, line in enumerate(lines[start:end], start + 1):
                        marker = " >>> " if i == e.lineno else "     "
                        print(f"{marker}{i:3d}: {line}")
                sys.exit(1)
                
    except FileNotFoundError:
        print(f"Error: JSON config file not found: {json_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading JSON config: {e}")
        sys.exit(1)


def parse_parameters(param_string: str) -> Dict[str, Any]:
    """Parse parameters from JSON string or file"""
    if not param_string:
        return {}
    
    # Check if it's a file path
    if os.path.isfile(param_string):
        try:
            with open(param_string, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading parameter file: {e}")
            sys.exit(1)
    else:
        # Try to parse as JSON string
        try:
            return json.loads(param_string)
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues like single quotes
            try:
                import re
                # Handle common cases where users use single quotes
                # Replace single quotes with double quotes for simple key-value pairs
                fixed_string = param_string
                # Replace single quotes around keys and string values
                fixed_string = re.sub(r"'([^']+)':", r'"\1":', fixed_string)
                fixed_string = re.sub(r":\s*'([^']*)'", r': "\1"', fixed_string) 
                # Handle numeric values (no quotes needed)
                return json.loads(fixed_string)
            except json.JSONDecodeError:
                # Try to fix unquoted keys and string values (common when shell strips quotes)
                try:
                    # Add quotes around unquoted keys: {key: value} -> {"key": value}
                    fixed_string = re.sub(r'{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'{"\1":', fixed_string)
                    fixed_string = re.sub(r',\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r', "\1":', fixed_string)
                    
                    # Add quotes around unquoted string values
                    # First handle simple word values: "key": value -> "key": "value"
                    fixed_string = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])', r': "\1"\2', fixed_string)
                    
                    # Then handle multi-word string values up to comma or closing brace
                    # This captures strings with spaces like: prompt:hello world -> prompt:"hello world"
                    fixed_string = re.sub(r':\s*([^,}]+?)(?=[,}])', lambda m: f': "{m.group(1).strip()}"' if not m.group(1).strip().startswith('"') and not m.group(1).strip().replace('.','').replace('-','').isdigit() else m.group(0), fixed_string)
                    
                    return json.loads(fixed_string)
                except json.JSONDecodeError:
                    # Try alternative parsing using eval (safer with ast.literal_eval)
                    try:
                        import ast
                        # This handles Python dict syntax which is more forgiving
                        result = ast.literal_eval(param_string)
                        if isinstance(result, dict):
                            return result
                        else:
                            raise ValueError("Not a dictionary")
                    except (ValueError, SyntaxError):
                        print(f"Error parsing parameters: {e}")
                        print(f"Input received: {repr(param_string)}")
                        print(f"Examples of valid formats:")
                        print(f'  JSON with quotes: \'{{"sharpen": 66, "denoise": 55}}\'')
                        print(f'  Unquoted keys: \'{{sharpen: 66, denoise: 55}}\'')
                        print(f"  Double-quoted string: '{{\"sharpen\": 66, \"denoise\": 55}}'")
                        sys.exit(1)


def get_input_files(input_paths: List[str]) -> List[Path]:
    """Get list of input files from paths"""
    input_files = []
    
    for input_path in input_paths:
        path = Path(input_path)
        
        if path.is_file():
            # Single file
            input_files.append(path)
        elif path.is_dir():
            # Directory - find all image files
            extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
            for file_path in path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    input_files.append(file_path)
        else:
            print(f"Warning: Path not found: {input_path}")
    
    return input_files


def create_processing_jobs(args, input_files: List[Path]) -> List[ProcessingJob]:
    """Create processing jobs from arguments and input files"""
    factory = get_model_factory()
    jobs = []
    
    # Determine output directory
    if args.output and args.output.strip():
        output_dir = Path(args.output)
    else:
        # Use same directory as first input file with '_enhanced' suffix
        if input_files:
            first_input = input_files[0]
            if first_input.parent.name.endswith('_enhanced'):
                output_dir = first_input.parent
            else:
                output_dir = first_input.parent / f"{first_input.parent.name}_enhanced"
        else:
            output_dir = Path.cwd() / "enhanced"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine processing parameters
    if args.preset:
        # Load from preset
        try:
            parameters = factory.load_preset(args.preset)
            if not parameters:
                print(f"Error: Preset '{args.preset}' not found")
                sys.exit(1)
        except Exception as e:
            print(f"Error loading preset: {e}")
            sys.exit(1)
    elif args.legacy_mode:
        # Use legacy mode
        try:
            validated_size = validate_dimensions(args)
            parameters = factory.create_from_legacy(args.legacy_mode, validated_size)
        except Exception as e:
            print(f"Error creating parameters from legacy mode: {e}")
            sys.exit(1)
    elif args.model:
        # Use specified model
        try:
            parsed_params = parse_parameters(args.parameters) if args.parameters else {}
            validated_size = validate_dimensions(args)
            parameters = factory.create_processing_parameters(args.model, parsed_params, validated_size)
        except Exception as e:
            print(f"Error creating processing parameters: {e}")
            sys.exit(1)
    else:
        print("Error: Must specify --model, --preset, or --legacy-mode")
        sys.exit(1)
    
    # Generate output filenames with suffix/prefix handling
    validated_size = validate_dimensions(args)
    suffix_config = parse_suffix_mode(args.suffix)
    
    # Create jobs
    for input_file in input_files:
        # Generate base filename
        base_name = input_file.stem
        extension = input_file.suffix
        
        # Generate suffix
        if suffix_config["mode"] == "auto":
            auto_suffix = generate_auto_suffix(parameters, validated_size, args.quality)
        elif suffix_config["mode"] == "custom":
            auto_suffix = suffix_config["value"]
        else:
            auto_suffix = ""
        
        # Build output filename
        output_name = f"{args.prefix}{base_name}{auto_suffix}{extension}"
        output_file = output_dir / output_name
        
        job = ProcessingJob(
            input_path=input_file,
            output_path=output_file,
            parameters=parameters
        )
        jobs.append(job)
    
    return jobs


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Load JSON config if provided
    if args.json:
        config = load_json_config(args.json)
        
        # Override args with JSON config values
        if 'executable' in config:
            args.executable = config['executable']
        if 'input' in config:
            if isinstance(config['input'], list):
                args.input = config['input']
            else:
                args.input = [config['input']]
        if 'output' in config:
            args.output = config['output']
        if 'model' in config:
            args.model = config['model']
        if 'scale' in config:
            args.scale = config['scale']
        if 'width' in config:
            args.width = config['width']
        if 'height' in config:
            args.height = config['height']
        if 'parameters' in config:
            args.parameters = json.dumps(config['parameters']) if isinstance(config['parameters'], dict) else config['parameters']
        if 'quality' in config:
            args.quality = config['quality']
        if 'prefix' in config:
            args.prefix = config['prefix']
        if 'suffix' in config:
            args.suffix = config['suffix']
        if 'preset' in config:
            args.preset = config['preset']
        if 'continue_on_error' in config:
            args.continue_on_error = config['continue_on_error']
        if 'timeout' in config:
            args.timeout = config['timeout']
        if 'preset_mode' in config:
            args.preset_mode = config['preset_mode']
        if 'prompt' in config and args.preset_mode:
            # Special handling for preset mode prompt
            args.preset_prompt = config['prompt']
    
    # Handle informational commands
    if args.list_models:
        list_models()
        return
    
    if args.model_info:
        show_model_info(args.model_info)
        return
    
    if args.list_presets:
        list_presets()
        return
    
    # Validate required arguments
    if not args.executable:
        print("Error: Gigapixel executable path is required. Use -e or --json with 'executable' field")
        sys.exit(1)
        
    if not os.path.exists(args.executable):
        print(f"Error: Gigapixel executable not found: {args.executable}")
        sys.exit(1)
    
    if not args.input:
        print("Error: Input files are required. Provide input files or use --json with 'input' field")
        sys.exit(1)
    
    # Validate quality parameter
    if hasattr(args, 'quality') and args.quality is not None:
        args.quality = validate_quality(args.quality)
    
    # Get input files
    input_files = get_input_files(args.input)
    if not input_files:
        print("Error: No valid input files found")
        sys.exit(1)
    
    if not args.quiet:
        print(f"Found {len(input_files)} input files")
    
    # Initialize Gigapixel early for preset mode
    try:
        if args.verbose:
            print(f"Initializing Gigapixel with executable: {args.executable}")
        
        gigapixel = Gigapixel(args.executable, args.timeout)
        
        # Enable debug UI mode if requested
        if args.debug_ui:
            gigapixel._debug_ui_mode = True
            gigapixel._app._debug_ui_mode = True  # Set on the _App instance too
            print("🔧 Interactive UI debugging mode enabled")
        
        # Set quality and prefix first
        gigapixel.set_export_parameters(quality=args.quality, prefix=args.prefix)
        
        # Set suffix parameter - we'll set the actual suffix value later after creating jobs
        suffix_config = parse_suffix_mode(args.suffix)
        if suffix_config["mode"] == "auto":
            # For auto mode, we'll set the actual generated suffix later
            pass  # Will be set after job creation
        elif suffix_config["toggle_on"]:
            # Enable suffix with empty value (mode "1")
            gigapixel.set_export_parameters(suffix="1")
        elif suffix_config["mode"] == "custom":
            # Set custom suffix
            gigapixel.set_export_parameters(suffix=suffix_config["value"])
        else:
            # Disable suffix (mode "0")
            gigapixel.set_export_parameters(suffix="0")
        
    except Exception as e:
        print(f"Error initializing Gigapixel: {e}")
        sys.exit(1)
    
    # Handle preset mode differently
    if args.preset_mode:
        # In preset mode, we skip all parameter setup and just process with current settings
        if not args.quiet:
            print("Running in preset mode - using Gigapixel's saved settings")
        
        # Get prompt if provided in JSON config
        prompt = getattr(args, 'preset_prompt', None)
        
        try:
            gigapixel.process_preset_mode(input_files, prompt)
            if not args.quiet:
                print(f"\nPreset mode completed: {len(input_files)} files processed")
            return
        except Exception as e:
            if args.verbose:
                import traceback
                traceback.print_exc()
            else:
                print(f"Error in preset mode: {e}")
            sys.exit(1)
    
    # Normal mode - create processing jobs
    jobs = create_processing_jobs(args, input_files)
    
    # Set auto-generated suffix if using auto mode
    suffix_config = parse_suffix_mode(args.suffix)
    if suffix_config["mode"] == "auto" and jobs:
        # Generate the auto suffix for the first job (all jobs use same parameters)
        validated_size = validate_dimensions(args)
        auto_suffix = generate_auto_suffix(jobs[0].parameters, validated_size, args.quality)
        # Keep the leading dash for proper file name delineation
        # Set the auto-generated suffix in export parameters
        gigapixel.set_export_parameters(suffix=auto_suffix)
        if not args.quiet:
            print(f"Auto-generated suffix: '{auto_suffix}'")
    
    # Save preset if requested
    if args.save_preset:
        try:
            factory = get_model_factory()
            if jobs:
                factory.save_preset(args.save_preset, jobs[0].parameters)
                print(f"Preset saved as: {args.save_preset}")
            else:
                print("Error: No jobs created, cannot save preset")
                sys.exit(1)
        except Exception as e:
            print(f"Error saving preset: {e}")
            sys.exit(1)
    
    # Dry run mode
    if args.dry_run:
        print("\nDry run - showing what would be processed:")
        print("=" * 45)
        for i, job in enumerate(jobs, 1):
            print(f"{i:3d}. {job.input_path.name}")
            print(f"     Input:  {job.input_path}")
            print(f"     Output: {job.output_path}")
            print(f"     Model:  {job.parameters.model.display_name}")
            print(f"     Scale:  {job.parameters.scale or 'default'}")
            if job.parameters.parameters:
                print(f"     Params: {job.parameters.parameters}")
            print()
        return
    
    # Process jobs
    try:
        if not args.quiet:
            print(f"\nProcessing {len(jobs)} files...")
        
        class CLICallback:
            def __init__(self, quiet=False, verbose=False):
                self.quiet = quiet
                self.verbose = verbose
                self.completed = 0
                self.total = 0
            
            def on_batch_start(self, jobs):
                self.total = len(jobs)
                if not self.quiet:
                    print(f"Starting batch processing of {self.total} files")
            
            def on_job_start(self, job):
                if self.verbose:
                    print(f"Processing: {job.input_path.name}")
            
            def on_job_complete(self, job):
                self.completed += 1
                if not self.quiet:
                    print(f"[{self.completed}/{self.total}] Completed: {job.input_path.name}")
            
            def on_job_error(self, job, error):
                print(f"Error processing {job.input_path.name}: {error}")
            
            def on_batch_complete(self, jobs):
                completed = len([j for j in jobs if j.status == "completed"])
                failed = len([j for j in jobs if j.status == "error"])
                if not self.quiet:
                    print(f"\nBatch completed: {completed} successful, {failed} failed")
    
        # Add callback
        callback = CLICallback(args.quiet, args.verbose)
        gigapixel.add_callback(callback)
        
        # Process batch
        completed_jobs = gigapixel.process_batch(jobs, args.continue_on_error)
        
        # Summary
        successful = len([j for j in completed_jobs if j.status == "completed"])
        failed = len([j for j in completed_jobs if j.status == "error"])
        
        if not args.quiet:
            print(f"\nProcessing completed:")
            print(f"  Successful: {successful}")
            print(f"  Failed: {failed}")
            print(f"  Total: {len(completed_jobs)}")
        
        # Exit with error code if any jobs failed
        if failed > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        sys.exit(1)
    except GigapixelException as e:
        print(f"Gigapixel error: {e}")
        sys.exit(1)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()