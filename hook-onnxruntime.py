# PyInstaller hook for onnxruntime
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, is_module_satisfies
import os
import sys

# Collect all onnxruntime data files and binaries
datas, binaries, hiddenimports = collect_all('onnxruntime')

# Add specific hidden imports
hiddenimports += [
    'onnxruntime.capi',
    'onnxruntime.capi._pybind_state',
    'onnxruntime.capi.onnxruntime_pybind11_state',
]

# On Windows, we need to ensure the DLLs are properly collected
if sys.platform == 'win32':
    # Collect all DLLs from onnxruntime
    binaries += collect_dynamic_libs('onnxruntime', destdir='.')
    
    # Add numpy DLLs which onnxruntime depends on
    binaries += collect_dynamic_libs('numpy', destdir='.')