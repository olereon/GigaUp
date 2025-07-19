#!/usr/bin/env python3
"""
Fix ModelParameter syntax errors in models.py
"""

import re

def fix_model_parameters():
    """Fix all ModelParameter calls to use keyword arguments properly"""
    
    with open('/home/olereon/workspace/github.com/olereon/GigaUp/gigapixel/models.py', 'r') as f:
        content = f.read()
    
    # Pattern to match ModelParameter with positional description argument
    # ModelParameter("name", "type", min, max, default, "description")
    pattern = r'ModelParameter\("([^"]+)",\s*"([^"]+)",\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*"([^"]+)"\)'
    
    def replace_match(match):
        name, param_type, min_val, max_val, default_val, description = match.groups()
        return f'ModelParameter("{name}", "{param_type}", {min_val}, {max_val}, {default_val}, description="{description}")'
    
    # Apply the replacement
    content = re.sub(pattern, replace_match, content)
    
    # Also handle cases with only 5 arguments (no min/max)
    # ModelParameter("name", "type", default, "description")
    pattern2 = r'ModelParameter\("([^"]+)",\s*"([^"]+)",\s*([^,]+),\s*"([^"]+)"\)'
    
    def replace_match2(match):
        name, param_type, default_val, description = match.groups()
        return f'ModelParameter("{name}", "{param_type}", {default_val}, description="{description}")'
    
    content = re.sub(pattern2, replace_match2, content)
    
    with open('/home/olereon/workspace/github.com/olereon/GigaUp/gigapixel/models.py', 'w') as f:
        f.write(content)
    
    print("Fixed ModelParameter syntax!")

if __name__ == "__main__":
    fix_model_parameters()