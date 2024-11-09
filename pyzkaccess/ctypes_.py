# pylint: disable=wildcard-import, unused-wildcard-import, unused-import, ungrouped-imports
"""This module is intended to safety import Windows-specific features
from `ctypes` stdlib module on non-windows platform -- they are
replaced by mock objects. Despite the code which uses that features
becomes partially unoperable in this case, we can import it and
generate documentation
"""
import warnings
from ctypes import *  # noqa
from typing import Any, NoReturn, TypeVar

from pyzkaccess.exceptions import UnsupportedPlatformError

T = TypeVar("T")


class MockDLL:
    """Mocks `ctypes.WinDLL` object on non-windows platform. Just
    raises `UnsupportedPlatformError` on any call
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __getattr__(self: T, value: Any) -> T:
        # pdoc3 issue workaround, https://stackoverflow.com/questions/49271586/valueerror-wrapper-loop-when-unwrapping
        if value == "__wrapped__":
            raise AttributeError
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise UnsupportedPlatformError()


try:
    from ctypes import WinDLL, windll
except ImportError:
    warnings.warn(
        "ctypes.WinDLL is not available on this platform. ctypes.WinDLL calls will fail", category=ImportWarning
    )
    WinDLL = MockDLL  # type: ignore
    windll = MockDLL()  # type: ignore
