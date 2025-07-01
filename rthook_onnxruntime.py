# Runtime hook for onnxruntime on Windows
import sys
import os

if sys.platform == 'win32':
    # Add the base directory to DLL search path
    import ctypes
    from ctypes import wintypes
    
    # Get the directory where the executable is located
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        base_dir = sys._MEIPASS
    else:
        # Running as script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add to DLL search path
    try:
        # For Windows 8+
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.AddDllDirectory.argtypes = [wintypes.LPCWSTR]
        kernel32.AddDllDirectory.restype = wintypes.HANDLE
        kernel32.AddDllDirectory(base_dir)
    except:
        # Fallback for older Windows
        os.environ['PATH'] = base_dir + os.pathsep + os.environ.get('PATH', '')
    
    # Also try to preload the onnxruntime DLL
    try:
        onnx_dll = os.path.join(base_dir, 'onnxruntime.dll')
        if os.path.exists(onnx_dll):
            ctypes.CDLL(onnx_dll)
    except:
        pass