# PyInstaller hook for scipy
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all scipy data files and binaries
datas, binaries, hiddenimports = collect_all('scipy')

# Add specific hidden imports that might be missed
hiddenimports += [
    'scipy._lib.messagestream',
    'scipy._cyutility', 
    'scipy.spatial.transform._rotation_groups',
    'scipy.special._cdflib',
    'scipy.special._ufuncs_cxx',
    'scipy._lib._ccallback_c',
    'scipy._lib._fpumode',
    'scipy._lib._testutils',
    'scipy._lib._tmpdirs',
    'scipy._lib._util',
    'scipy._lib.decorator',
    'scipy._lib.doccer',
    'scipy._lib._docscrape',
    'scipy._lib._gcutils',
    'scipy._lib._pep440',
    'scipy._lib._threadsafety',
    'scipy._lib._version',
    'scipy._lib.array_api_compat',
    'scipy._lib.array_api_compat.numpy',
    'scipy._lib.array_api_compat.numpy.fft',
    'scipy._lib.array_api_compat.numpy.linalg',
]

# Ensure all scipy submodules are included
hiddenimports += collect_submodules('scipy')