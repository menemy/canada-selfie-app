@echo off
echo Building Canada Selfie App for Windows...
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM Install/upgrade PyInstaller and dependencies
echo Installing/upgrading dependencies...
pip install --upgrade pip
pip install --upgrade pyinstaller
pip install --upgrade -r requirements.txt

REM Build the executable with special Windows flags
echo Building executable...
pyinstaller canada_selfie.spec --clean --noconfirm

REM Check if build succeeded
if exist "dist\CanadaSelfieApp.exe" (
    echo.
    echo Build successful!
    echo Executable: dist\CanadaSelfieApp.exe
    
    REM Get file size
    for %%A in ("dist\CanadaSelfieApp.exe") do echo Size: %%~zA bytes
) else (
    echo.
    echo Build failed! Check the error messages above.
    exit /b 1
)

echo.
echo Done!
pause