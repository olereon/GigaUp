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
    
    # Required arguments
    parser.add_argument(
        "input",
        nargs="+",
        help="Input image file(s) or directory to process"
    )
    
    parser.add_argument(
        "-e", "--executable",
        required=True,
        help="Path to Topaz Gigapixel AI executable"
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
                # Try to fix unquoted keys (common when shell strips quotes)
                try:
                    # Add quotes around unquoted keys: {key: value} -> {"key": value}
                    fixed_string = re.sub(r'{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'{"\1":', fixed_string)
                    fixed_string = re.sub(r',\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r', "\1":', fixed_string)
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
    if args.output:
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
    if not os.path.exists(args.executable):
        print(f"Error: Gigapixel executable not found: {args.executable}")
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
    
    # Create processing jobs
    jobs = create_processing_jobs(args, input_files)
    
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
    
    # Initialize Gigapixel
    try:
        if args.verbose:
            print(f"Initializing Gigapixel with executable: {args.executable}")
        
        gigapixel = Gigapixel(args.executable, args.timeout)
        
        # Process jobs
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