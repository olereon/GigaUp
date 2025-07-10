#!/usr/bin/env python3
"""
Script to package all GigaUp v2.0 files for easy transfer
Creates a Python script that recreates all the new files
"""

import os
import base64
from pathlib import Path

def create_installer_script():
    """Create a script that will recreate all v2.0 files"""
    
    new_files = [
        # Core new modules
        "gigapixel/models.py",
        "gigapixel/parameters.py", 
        "gigapixel/factory.py",
        "gigapixel/cli.py",
        
        # GUI modules
        "gigapixel/gui/__init__.py",
        "gigapixel/gui/main_window.py",
        "gigapixel/gui/widgets.py",
        "gigapixel/gui/utils.py",
        
        # Launcher scripts
        "run_gui.py",
        "run_cli.py",
        
        # Documentation
        "CLAUDE.md",
        "INSTALLATION.md",
    ]
    
    installer_content = '''#!/usr/bin/env python3
"""
GigaUp v2.0 File Installer
This script creates all the new v2.0 files in your GigaUp directory
"""

import os
import base64
from pathlib import Path

def install_v2_files():
    """Install all v2.0 files"""
    
    # File contents (base64 encoded to preserve formatting)
    files = {
'''
    
    # Add each file's content
    for file_path in new_files:
        if os.path.exists(file_path):
            print(f"Adding {file_path}...")
            with open(file_path, 'rb') as f:
                content = f.read()
                encoded = base64.b64encode(content).decode('utf-8')
                
                # Split long content into chunks for readability
                chunks = [encoded[i:i+80] for i in range(0, len(encoded), 80)]
                content_str = '\n        '.join(f'"{chunk}"' for chunk in chunks)
                
                installer_content += f'\n        "{file_path}": (\n        {content_str}\n        ),'
    
    installer_content += '''
    }
    
    print("GigaUp v2.0 File Installer")
    print("=" * 50)
    
    # Create directories and files
    for file_path, encoded_content in files.items():
        # Decode content
        content = base64.b64decode(encoded_content)
        
        # Create directory if needed
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(file_path_obj, 'wb') as f:
            f.write(content)
        
        print(f"✓ Created: {file_path}")
    
    print("\\n✅ All v2.0 files installed successfully!")
    print("\\nNext steps:")
    print("1. Install dependencies:")
    print("   pip install pywinauto clipboard loguru the-retry plyer")
    print("2. Run the GUI:")
    print("   python run_gui.py")
    print("3. Or run the CLI:")
    print("   python run_cli.py --help")

if __name__ == "__main__":
    install_v2_files()
'''
    
    # Write the installer script
    with open("install_v2_files.py", "w", encoding="utf-8") as f:
        f.write(installer_content)
    
    print("Created install_v2_files.py")
    print("\nTo install v2.0 files on Windows:")
    print("1. Copy install_v2_files.py to your GigaUp directory")
    print("2. Run: python install_v2_files.py")
    print("3. Install dependencies: pip install pywinauto clipboard loguru the-retry plyer")
    print("4. Run GUI: python run_gui.py")

if __name__ == "__main__":
    create_installer_script()