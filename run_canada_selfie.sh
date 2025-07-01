#!/bin/bash

# Canada Selfie App Launcher
echo "🍁 Starting Canada Selfie App, Eh! 🍁"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Run the Python app
python3 "$SCRIPT_DIR/canada_selfie_app.py"

echo "🍁 Thanks for using Canada Selfie App! 🍁"
