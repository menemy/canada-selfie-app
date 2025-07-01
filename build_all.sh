#!/bin/bash
echo "🍁 Canada Selfie App - Universal Builder 🍁"
echo

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    PLATFORM="Windows"
else
    PLATFORM="Linux"
fi

echo "Platform detected: $PLATFORM"
echo

# Menu
echo "Choose build type:"
echo "1) Executable only"
echo "2) macOS DMG (macOS only)"
echo "3) Both executable and DMG (macOS only)"
echo "4) Windows ZIP package (Windows only)"
echo

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "Building executable..."
        if [[ "$PLATFORM" == "macOS" ]]; then
            ./build_exe.sh
        else
            echo "Use build_exe.bat on Windows or install PyInstaller manually"
        fi
        ;;
    2)
        if [[ "$PLATFORM" == "macOS" ]]; then
            echo "Building DMG..."
            ./build_dmg.sh
        else
            echo "DMG creation is only supported on macOS"
            exit 1
        fi
        ;;
    3)
        if [[ "$PLATFORM" == "macOS" ]]; then
            echo "Building executable and DMG..."
            ./build_exe.sh
            if [ $? -eq 0 ]; then
                ./build_dmg.sh
            fi
        else
            echo "DMG creation is only supported on macOS"
            exit 1
        fi
        ;;
    4)
        if [[ "$PLATFORM" == "Windows" ]]; then
            echo "Building Windows ZIP package..."
            ./build_windows_zip.bat
        else
            echo "Windows ZIP package creation is only supported on Windows"
            exit 1
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo
echo "Build complete! 🍁"