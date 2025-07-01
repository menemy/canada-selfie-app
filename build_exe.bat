@echo off
echo 🍁 Building Canada Selfie App executable... 🍁
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found, using system Python
)

REM Install PyInstaller if not installed
echo Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

REM Build the executable
echo Building executable...
pyinstaller canada_selfie.spec

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ✅ Build successful!
echo Executable created: dist\CanadaSelfieApp.exe
echo.

REM Optional: Test the executable
set /p test="Do you want to test the executable? (y/n): "
if /i "%test%"=="y" (
    echo Testing executable...
    cd dist
    CanadaSelfieApp.exe
)

pause