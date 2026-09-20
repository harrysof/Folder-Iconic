@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on your PATH.
    echo Install Python 3 from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

python -c "import PIL, numpy" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages: Pillow, numpy
    python -m pip install --user Pillow numpy
)

python folder_iconic.py
if errorlevel 1 pause
endlocal
