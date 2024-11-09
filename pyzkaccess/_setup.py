__all__ = ["setup"]
import contextlib
import ctypes
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from ctypes import POINTER, c_char_p, c_int, c_ulong, c_void_p
from ctypes.wintypes import BOOL, DWORD, HANDLE, HINSTANCE, HKEY, HWND
from pathlib import Path
from typing import Any, Final, Iterable, Iterator, Optional, Tuple

from pyzkaccess.ctypes_ import windll

PULL_SDK_FETCH_URL: Final[str] = "https://server.zkteco.eu/ddfb/pull_sdk.zip"
PULL_SDK_SUBDIR_GLOB: Final[str] = "SDK*"
PULL_SDK_DLLS: Final[Tuple[str, ...]] = (
    "plcommpro.dll",
    "plcomms.dll",
    "plrscagent.dll",
    "plrscomm.dll",
    "pltcpcomm.dll",
    "plusbcomm.dll",
)


class StepFailedError(Exception):
    pass


@contextlib.contextmanager
def step(title: str, simple: bool = True) -> Iterator[None]:
    sys.stdout.write(f"> {title}" + (": " if simple else "\n"))
    sys.stdout.flush()
    try:
        yield
        if simple:
            sys.stdout.write("OK\n")
    except StepFailedError as e:
        if simple:
            sys.stdout.write("ERROR\n")
        sys.stderr.write(f"\nERROR: {e}\n")
        sys.exit(3)


def setup(interactive: bool, path: Optional[str]) -> None:
    with step("Operating system"):
        if sys.platform != "win32":
            raise StepFailedError(
                f"OS '{sys.platform}' is not supported\n"
                f"Only Windows/Wine 32-bit platform is supported (this is a limitation of PULL SDK)\n"
                f"See the docs https://bdragon300.github.io/pyzkaccess/#installation for more information\n"
            )
        sys.stdout.write("[win32] ")

    with step("Python version"):
        if sys.maxsize.bit_length() > 32:
            raise StepFailedError(
                f"Python version must be 32-bit, but {sys.maxsize.bit_length() + 1} bit version installed\n"
                f"32-bit Python is available to download at https://www.python.org/downloads/windows/\n"
                f"See the docs https://bdragon300.github.io/pyzkaccess/#installation for more information\n"
            )
        sys.stdout.write("[32-bit] ")

    with step("System root"):
        system_root = os.environ.get("SystemRoot")
        if system_root is None:
            raise StepFailedError(
                "SystemRoot environment variable is not set\n"
                "This variable must be present on Windows platform, please check OS settings\n"
            )
        sys.stdout.write(f"[{system_root}] ")

    with step("Library root"):
        is_win64 = platform.machine().endswith("64")
        lib_root = Path(system_root) / ("SysWOW64" if is_win64 else "System32")
        if not lib_root.exists():
            raise StepFailedError(
                f"Library root '{lib_root}' not found\n"
                f"Please check the OS settings or contact the system administrator\n"
            )
        sys.stdout.write(f"[{lib_root}] ")

    with step("Install ZKTeco PULL SDK", simple=False):
        already_installed = all((lib_root / f).exists() for f in PULL_SDK_DLLS)
        if not already_installed:
            if interactive and path is None:
                path = input(
                    f">> Enter HTTP URL, zip archive or directory with PULL SDK [default: {PULL_SDK_FETCH_URL}]: "
                )
            if not path:
                path = PULL_SDK_FETCH_URL

            sdk_contents_dir = _fetch_and_extract(path)
            _install_dlls(sdk_contents_dir, lib_root, interactive)
        else:
            sys.stdout.write(">> PULL SDK already installed\n")

    sys.stdout.write("Setup complete, everything looks good!\n")


def _fetch_and_extract(any_path: str) -> Path:
    if any_path.startswith("http"):
        sys.stdout.write(f">> Downloading PULL SDK files from {any_path}...\n")
        with contextlib.closing(urllib.request.urlopen(any_path)) as resp:
            with tempfile.NamedTemporaryFile(delete=False) as fp:
                fp.write(resp.read())
                any_path = fp.name

    fs_path = Path(any_path)
    if fs_path.is_dir():
        return fs_path

    if fs_path.is_file():
        tmpdir = Path(tempfile.mkdtemp())
        sys.stdout.write(f">> Extracting PULL SDK files from zip archive '{fs_path}' to directory '{tmpdir}'\n")
        with zipfile.ZipFile(str(fs_path), "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        return tmpdir

    raise StepFailedError(f"File or directory '{any_path}' not found")


def _install_dlls(source_dir: Path, lib_root: Path, use_uac: bool) -> None:
    # Check if all required dlls are present in the source directory
    sdk_found = all((source_dir / f).exists() for f in PULL_SDK_DLLS)
    # Archive from the official website contains dlls in a subdirectory
    if not sdk_found:
        subdirs = list(source_dir.glob(PULL_SDK_SUBDIR_GLOB))
        if subdirs:
            source_dir = Path(subdirs[0])
            sdk_found = all((source_dir / f).exists() for f in PULL_SDK_DLLS)

        if not sdk_found:
            raise StepFailedError(
                f"PULL SDK not found in '{source_dir}'. \n"
                f"Please check the path contains the following files: {PULL_SDK_DLLS}"
            )

    files_glob = Path("*.dll")
    sys.stdout.write(f">> Copying PULL SDK from {source_dir / files_glob} to {lib_root}...\n")
    _copy_files(source_dir, files_glob, lib_root, use_uac)


class ShellExecuteInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("fMask", c_ulong),
        ("hwnd", HWND),
        ("lpVerb", c_char_p),
        ("lpFile", c_char_p),
        ("lpParameters", c_char_p),
        ("lpDirectory", c_char_p),
        ("nShow", c_int),
        ("hInstApp", HINSTANCE),
        ("lpIDList", c_void_p),
        ("lpClass", c_char_p),
        ("hKeyClass", HKEY),
        ("dwHotKey", DWORD),
        ("hIcon", HANDLE),
        ("hProcess", HANDLE),
    ]

    def __init__(self, **kw: Any) -> None:
        super().__init__()
        self.cbSize = ctypes.sizeof(self)  # pylint: disable=invalid-name
        for field_name, field_value in kw.items():
            setattr(self, field_name, field_value)


def _copy_files(source_dir: Path, files_glob: Path, destination: Path, use_uac: bool) -> None:
    files = list(source_dir.glob(str(files_glob)))
    if not windll.shell32.IsUserAnAdmin() and use_uac:
        # Run command with showing UAC prompt
        # The `copy` command does not support copying several files at once, so pass the glob pattern
        sys.stdout.write(">> Copying with elevated permissions...\n")
        _elevated_command("cmd", ["/c", "copy", "/Y", str(source_dir / files_glob), str(destination)])
        sys.stdout.write("\n".join(f">>> {f}" for f in files) + "\n")
    else:
        for file in files:
            sys.stdout.write(f">>> {file}\n")
            shutil.copy(file, destination)


# Windows stuff

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_NO_CONSOLE = 0x00008000

PShellExecuteInfo = POINTER(ShellExecuteInfo)

ShellExecuteEx = windll.shell32.ShellExecuteExA
ShellExecuteEx.argtypes = (PShellExecuteInfo,)
ShellExecuteEx.restype = BOOL

WaitForSingleObject = windll.kernel32.WaitForSingleObject
WaitForSingleObject.argtypes = (HANDLE, DWORD)
WaitForSingleObject.restype = DWORD

CloseHandle = windll.kernel32.CloseHandle
CloseHandle.argtypes = (HANDLE,)
CloseHandle.restype = BOOL


def _elevated_command(command: str, args: Iterable[str]) -> None:

    params = ShellExecuteInfo(
        fMask=SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE,
        hwnd=None,
        lpVerb=b"runas",
        lpFile=command.encode("cp1252"),
        lpParameters=subprocess.list2cmdline(args).encode("cp1252"),
        nShow=1,
    )

    if not ShellExecuteEx(ctypes.byref(params)):
        raise ctypes.WinError()

    handle = params.hProcess
    ret = DWORD()
    WaitForSingleObject(handle, -1)

    if windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(ret)) == 0:
        raise ctypes.WinError()

    CloseHandle(handle)
