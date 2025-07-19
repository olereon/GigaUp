#!/usr/bin/env python3
"""
Test script for custom scale factor functionality in GigaUp.

This script tests the ability to set custom scale factors beyond the standard 
1x, 2x, 4x, and 6x options.
"""

import sys
from pathlib import Path
from loguru import logger

# Add gigapixel module to path
sys.path.insert(0, str(Path(__file__).parent))

from gigapixel import Gigapixel, get_model_factory

def test_custom_scale(exe_path: str, image_path: str, scale: str):
    """Test custom scale factor with the given image"""
    logger.info(f"Testing custom scale factor: {scale}")
    
    try:
        # Initialize Gigapixel
        gp = Gigapixel(exe_path=exe_path)
        logger.info("✓ Gigapixel initialized")
        
        # Get model factory
        factory = get_model_factory()
        
        # Create parameters with custom scale
        params = factory.create_processing_parameters(
            "standard_v2",  # Use standard model
            {"sharpen": 0.2, "denoise": 0.1},  # Some basic parameters
            scale  # Custom scale value
        )
        
        logger.info(f"✓ Created parameters with scale: {scale}")
        
        # Process the image
        output_path = Path(image_path).parent / f"output_{scale.replace('.', '_')}x.jpg"
        gp.process_with_model(image_path, params, output_suffix=f"_{scale.replace('.', '_')}x")
        
        logger.info(f"✓ Processing complete! Output: {output_path}")
        
    except Exception as e:
        logger.error(f"✗ Error during processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'gp' in locals():
            gp.stop()

def main():
    """Main function"""
    if len(sys.argv) < 4:
        print("Usage: python test_custom_scale.py <exe_path> <image_path> <scale>")
        print("Example: python test_custom_scale.py \"C:\\Program Files\\Topaz Labs LLC\\Topaz Gigapixel AI\\Topaz Gigapixel AI.exe\" image.jpg 1.5")
        sys.exit(1)
    
    exe_path = sys.argv[1]
    image_path = sys.argv[2]
    scale = sys.argv[3]
    
    # Validate scale
    try:
        scale_value = float(scale)
        if scale_value <= 0:
            raise ValueError("Scale must be positive")
    except ValueError as e:
        print(f"Invalid scale value: {scale} - {e}")
        sys.exit(1)
    
    # Test custom scale
    test_custom_scale(exe_path, image_path, scale)

if __name__ == "__main__":
    main()