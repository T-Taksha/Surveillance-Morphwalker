@echo off
REM ============================================================
REM Conda Environment Setup for Raspberry Pi Robot Project
REM ============================================================

echo.
echo ============================================================
echo   Raspberry Pi Robot - Conda Environment Setup
echo ============================================================
echo.

REM Initialize conda for this shell
echo Initializing conda...
call C:\Users\Vijhortha\anaconda3\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Could not activate conda base environment
    pause
    exit /b 1
)

REM Activate myenv
echo Activating myenv environment...
call conda activate myenv
if %errorlevel% neq 0 (
    echo ERROR: Could not activate myenv environment
    echo Creating myenv environment...
    call conda create -n myenv python=3.9 -y
    call conda activate myenv
)

echo.
echo [1/4] Installing core dependencies...
echo.
call conda install -y opencv numpy flask
if %errorlevel% neq 0 (
    echo Using pip for opencv...
    call pip install opencv-python numpy flask
)

echo.
echo [2/4] Installing additional packages via pip...
call pip install imutils flask-cors

echo.
echo [3/4] Installing RPi.GPIO (will fail on Windows - this is normal)...
call pip install RPi.GPIO
if %errorlevel% neq 0 (
    echo Note: RPi.GPIO failed - using mock GPIO for development
)

echo.
echo [4/4] Installing YOLO (ultralytics) for object detection...
echo This may take several minutes...
call pip install ultralytics

echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo Verifying installation...
python -c "import cv2, numpy, flask; print('✓ Core packages installed successfully!')"
echo.
echo Your conda environment 'myenv' is ready!
echo.
echo To run the robot system:
echo   conda activate myenv
echo   python main.py --mode autonomous
echo.
echo ============================================================
pause
