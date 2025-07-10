@echo off
echo Installing GigaUp v2.0 dependencies and fixes...
echo.

echo Step 1: Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install pywinauto clipboard loguru the-retry plyer

if %errorlevel% == 0 (
    echo.
    echo ✅ Dependencies installed successfully!
    echo.
    
    echo Step 2: Pulling latest fixes from repository...
    git pull origin main
    
    if %errorlevel% == 0 (
        echo ✅ Latest fixes pulled successfully!
        echo.
        echo Starting GigaUp GUI...
        python run_gui.py
    ) else (
        echo ⚠️ Could not pull latest changes. Running with current version...
        python run_gui.py
    )
) else (
    echo.
    echo ❌ Installation failed. Please try manually:
    echo pip install pywinauto clipboard loguru the-retry plyer
    pause
)