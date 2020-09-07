"""This module is intended to safety import Windows-specific features
from `ctypes` stdlib module on non-windows platform -- they are
replaced by mock objects. Despite the code which uses that features
becomes partially unoperable in this case, we can import it and
generate documentation for instance
"""
import warnings
from ctypes import *  # noqa
from unittest.mock import Mock

try:
    from ctypes import WinDLL  # noqa
except ImportError:
    warnings.warn(
        'ctypes.WinDLL is not available on non-Windows system. The code is not functional on '
        'current platform, but in order to be able import it we mock WinDLL with '
        'unittest.mock.Mock object'
    )
    WinDLL = Mock()
