#!/bin/bash
echo "🍁 Building Canada Selfie App executable... 🍁"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found, using system Python"
fi

# Install PyInstaller if not installed
echo "Checking PyInstaller..."
python3 -c "import PyInstaller" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
rm -rf dist build

# Build the executable
echo "Building executable..."
pyinstaller canada_selfie.spec

if [ $? -ne 0 ]; then
    echo
    echo "Build failed!"
    exit 1
fi

echo
echo "✅ Build successful!"
echo "Executable created: dist/CanadaSelfieApp"
echo

# Optional: Test the executable
read -p "Do you want to test the executable? (y/n): " test
if [[ $test == "y" || $test == "Y" ]]; then
    echo "Testing executable..."
    cd dist
    ./CanadaSelfieApp
fi