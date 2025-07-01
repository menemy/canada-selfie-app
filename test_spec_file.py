#!/usr/bin/env python3
"""Test script to validate PyInstaller spec file structure"""

import os
import sys

# Check spec file exists
if not os.path.exists('canada_selfie.spec'):
    print('[ERROR] canada_selfie.spec not found')
    sys.exit(1)

# Read spec file
with open('canada_selfie.spec', 'r') as f:
    spec_content = f.read()

# Check for required PyInstaller components
required_components = ['Analysis', 'PYZ', 'EXE', 'datas', 'hiddenimports']
missing = []
for component in required_components:
    if component not in spec_content:
        missing.append(component)

if missing:
    print(f'[ERROR] Spec file missing required components: {missing}')
    sys.exit(1)

print('[OK] PyInstaller spec file structure is valid')