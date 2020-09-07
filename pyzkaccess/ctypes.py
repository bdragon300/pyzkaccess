import warnings
from ctypes import *  # noqa
from unittest.mock import Mock

try:
    from ctypes import WinDLL  # noqa
except ImportError:
    warnings.warn(
        'ctypes.WinDLL is not available on non-Windows system. The code is not functional on this '
        'platform, but in order to be able import it we mock WinDLL with unittest.mock.Mock object'
    )
    WinDLL = Mock()
