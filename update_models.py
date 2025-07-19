#!/usr/bin/env python3
"""
Script to update model parameters in models.py file
"""

import re

def update_models_file():
    """Update the models.py file with new parameter specifications"""
    
    with open('/home/olereon/workspace/github.com/olereon/GigaUp/gigapixel/models.py', 'r') as f:
        content = f.read()
    
    # Update sharpen, denoise, fix_compression parameters from decimal 0.0-1.0 to integer 1-100
    content = re.sub(
        r'"sharpen":\s*ModelParameter\("sharpen",\s*"decimal",\s*0\.0,\s*1\.0,\s*0\.0,',
        '"sharpen": ModelParameter("sharpen", "integer", 1, 100, 1,',
        content
    )
    
    content = re.sub(
        r'"denoise":\s*ModelParameter\("denoise",\s*"decimal",\s*0\.0,\s*1\.0,\s*0\.0,',
        '"denoise": ModelParameter("denoise", "integer", 1, 100, 1,',
        content
    )
    
    content = re.sub(
        r'"fix_compression":\s*ModelParameter\("fix_compression",\s*"decimal",\s*0\.0,\s*1\.0,\s*0\.0,',
        '"fix_compression": ModelParameter("fix_compression", "integer", 1, 100, 1,',
        content
    )
    
    # Add face_recovery parameter to models that don't have it yet
    # This regex looks for parameters dict closing brace and adds face_recovery before it
    def add_face_recovery(match):
        params_content = match.group(1)
        if 'face_recovery' not in params_content:
            # Add face_recovery parameter before the closing brace
            params_content = params_content.rstrip() + ',\n            "face_recovery": ModelParameter("face_recovery", "boolean", default_value=False, description="Enable face recovery processing")\n        '
        return f'parameters={{{params_content}}}'
    
    # Apply face_recovery addition to all model parameters
    content = re.sub(
        r'parameters=\{(.*?)\}',
        add_face_recovery,
        content,
        flags=re.DOTALL
    )
    
    with open('/home/olereon/workspace/github.com/olereon/GigaUp/gigapixel/models.py', 'w') as f:
        f.write(content)
    
    print("Models updated successfully!")

if __name__ == "__main__":
    update_models_file()