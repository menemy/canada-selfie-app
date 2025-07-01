# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Canada Selfie App - A PyQt5 desktop application for taking selfies with Canadian-themed effects, filters, and AI-powered background removal.

## Key Commands

### Running the Application
```bash
# Recommended method (includes venv activation)
./run_canada_selfie.sh

# Alternative method
source venv/bin/activate
python3 canada_selfie_app.py
```

### Setup & Dependencies
```bash
# Create virtual environment (if needed)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Architecture

This is a single-file PyQt5 application (`canada_selfie_app.py`) with:

- **Main Class**: `CanadaSelfieApp(QMainWindow)` - Handles UI and all functionality
- **Event-Driven**: Uses Qt signals/slots for UI interactions
- **Real-time Processing**: OpenCV integration for webcam feed at ~33 FPS
- **AI Features**: Optional background removal using rembg (U²-Net model)

### Key Components:

1. **Camera Management**: Multi-camera support with QCamera enumeration
2. **Effects System**: Maple overlays, color filters, beaver graphics
3. **Background Removal**: AI-powered using rembg (requires M1+ Mac for best performance)
4. **UI Organization**: Compact 800x600 window with grouped controls

## Development Notes

- No test suite exists - manual testing required
- No linting configuration - follow existing code style
- Single-file architecture - all features in `canada_selfie_app.py`
- Virtual environment included in repo for convenience
- Platform-optimized for macOS, especially Apple Silicon

## Feature Implementation Pattern

When adding new effects or features:
1. Add UI controls in `initUI()` method
2. Create effect method following pattern of existing effects (e.g., `apply_maple_overlay()`)
3. Connect to video processing pipeline in `update_frame()`
4. Follow Canadian theme consistency (colors: #FF0000 red, #FFFFFF white)