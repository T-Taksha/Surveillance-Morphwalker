@echo off
REM ============================================================
REM Environment Setup Script for Raspberry Pi Robot Project
REM ============================================================
REM This script sets up the Python environment and installs
REM all required dependencies for the robot control system.
REM ============================================================

echo.
echo ============================================================
echo   Raspberry Pi Robot - Environment Setup
echo ============================================================
echo.

REM Check if Python is installed
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

python --version
echo Python found!
echo.

REM Check if pip is installed
echo [2/5] Checking pip installation...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip is not installed!
    echo Installing pip...
    python -m ensurepip --upgrade
)

python -m pip --version
echo pip found!
echo.

REM Upgrade pip
echo [3/5] Upgrading pip to latest version...
python -m pip install --upgrade pip
echo.

REM Create virtual environment (optional but recommended)
echo [4/5] Setting up virtual environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created!
) else (
    echo Virtual environment already exists.
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install required packages
echo [5/5] Installing required packages...
echo This may take several minutes...
echo.

REM Install core dependencies
echo Installing core dependencies...
python -m pip install opencv-python numpy flask imutils

REM Install RPi.GPIO (will fail on Windows, but that's okay for development)
echo.
echo Installing RPi.GPIO (may fail on Windows - this is normal)...
python -m pip install RPi.GPIO
if %errorlevel% neq 0 (
    echo Note: RPi.GPIO installation failed. This is expected on Windows.
    echo The code will use mock GPIO for development.
)

REM Install optional dependencies
echo.
echo Installing optional dependencies...
python -m pip install flask-cors Pillow requests pandas

REM Install YOLO (ultralytics) - optional but recommended
echo.
echo Installing YOLO (ultralytics) for object detection...
echo This may take a while...
python -m pip install ultralytics

echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo Virtual environment is activated.
echo.
echo To run the robot system:
echo   1. Make sure virtual environment is activated (venv\Scripts\activate)
echo   2. Run: python main.py --mode autonomous
echo.
echo To deactivate virtual environment:
echo   deactivate
echo.
echo ============================================================
pause
