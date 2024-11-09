import http.client
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from pyzkaccess._setup import (
    PULL_SDK_DLLS,
    PULL_SDK_FETCH_URL,
    StepFailedError,
    _copy_files,
    _fetch_and_extract,
    _install_dlls,
    setup,
    step,
)


@pytest.fixture
def empty_zip() -> bytes:
    return b"PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


class TestStep:
    @pytest.mark.parametrize("simple,expect", [(True, "> Test step: TESTOK\n"), (False, "> Test step\nTEST")])
    def test_step__on_success__should_print_messages_to_stdout(self, capsys, simple, expect) -> None:
        with step("Test step", simple=simple):
            sys.stdout.write("TEST")

        captured = capsys.readouterr()

        assert captured.out == expect
        assert captured.err == ""

    @pytest.mark.parametrize(
        "simple,expect_out,expect_err",
        [(True, "> Test step: ERROR\n", "\nERROR: Test error\n"), (False, "> Test step\n", "\nERROR: Test error\n")],
    )
    def test_step__on_step_error__should_print_messages_to_stdout_and_stderr_and_exit_with_code_3(
        self, capsys, simple, expect_out, expect_err
    ) -> None:
        with pytest.raises(SystemExit) as exc:
            with step("Test step", simple=simple):
                raise StepFailedError("Test error")

        assert exc.value.code == 3

        captured = capsys.readouterr()

        assert captured.out == expect_out
        assert captured.err == expect_err

    def test_step__on_other_error__should_reraise_exception(self, capsys) -> None:
        with pytest.raises(ValueError):
            with step("Test step"):
                raise ValueError("Test error")

        captured = capsys.readouterr()

        assert captured.out == "> Test step: "
        assert captured.err == ""


class TestSetup:
    def test_setup__if_success_and_sdk_installed__should_do_nothing(
        self, mocker, tmp_path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("SystemRoot", str(tmp_path))
        lib_root = tmp_path / "SysWOW64"
        lib_root.mkdir()
        for dll in PULL_SDK_DLLS:
            (lib_root / dll).touch()
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**31 - 1)
        mocker.patch("pyzkaccess._setup.platform.machine", return_value="AMD64")

        setup(interactive=False, path=None)

        captured = capsys.readouterr()
        assert "Setup complete, everything looks good!" in captured.out

    @pytest.mark.parametrize("platform", ["linux", "darwin", "cygwin", "msys", "win16", "win64"])
    def test_setup__on_unsupported_os__should_exit(self, mocker, platform, capsys) -> None:
        mocker.patch("pyzkaccess._setup.sys.platform", platform)

        with pytest.raises(SystemExit) as exc:
            setup(interactive=False, path=None)

        captured = capsys.readouterr()
        assert exc.value.code == 3
        assert f"OS '{platform}' is not supported" in captured.err

    def test_setup__on_unsupported_python_bits__should_exit(self, mocker, capsys) -> None:
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**63 - 1)

        with pytest.raises(SystemExit) as exc:
            setup(interactive=False, path=None)

        captured = capsys.readouterr()
        assert exc.value.code == 3
        assert "Python version must be 32-bit" in captured.err

    def test_setup__on_missing_system_root__should_exit(self, mocker, monkeypatch, capsys) -> None:
        monkeypatch.delenv("SystemRoot", raising=False)
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**31 - 1)

        with pytest.raises(SystemExit) as exc:
            setup(interactive=False, path=None)

        captured = capsys.readouterr()
        assert exc.value.code == 3
        assert "SystemRoot environment variable is not set" in captured.err

    @pytest.mark.parametrize("machine_platform,lib_dir_name", [("AMD64", "SysWOW64"), ("x86", "System32")])
    def test_setup__on_missing_library_root__should_exit(
        self, machine_platform, lib_dir_name, mocker, tmp_path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("SystemRoot", str(tmp_path))
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**31 - 1)
        mocker.patch("pyzkaccess._setup.platform.machine", return_value=machine_platform)

        with pytest.raises(SystemExit) as exc:
            setup(interactive=False, path=None)

        captured = capsys.readouterr()
        assert exc.value.code == 3
        assert f"Library root '{tmp_path / lib_dir_name}' not found" in captured.err

    def test_setup__if_need_to_install_sdk_non_interactive__should_fetch_and_install(
        self, mocker, tmp_path_factory, monkeypatch
    ) -> None:
        system_root = tmp_path_factory.mktemp("Windows")
        monkeypatch.setenv("SystemRoot", str(system_root))
        lib_root = system_root / "SysWOW64"
        lib_root.mkdir()
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**31 - 1)
        mocker.patch("pyzkaccess._setup.platform.machine", return_value="AMD64")
        sdk_dir = tmp_path_factory.mktemp("sdk")
        fetch_and_extract_mock = mocker.patch("pyzkaccess._setup._fetch_and_extract", return_value=sdk_dir)
        install_dlls_mock = mocker.patch("pyzkaccess._setup._install_dlls")

        setup(interactive=False, path=None)

        fetch_and_extract_mock.assert_called_once_with(PULL_SDK_FETCH_URL)
        install_dlls_mock.assert_called_once_with(sdk_dir, lib_root, False)

    def test_setup__if_need_to_install_sdk_interactive__should_fetch_and_install_asking_path(
        self, mocker, tmp_path_factory, monkeypatch
    ) -> None:
        system_root = tmp_path_factory.mktemp("Windows")
        monkeypatch.setenv("SystemRoot", str(system_root))
        lib_root = system_root / "SysWOW64"
        lib_root.mkdir()
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**31 - 1)
        mocker.patch("pyzkaccess._setup.platform.machine", lreturn_value="AMD64")
        mocker.patch("pyzkaccess._setup.input", return_value="http://example.com/sdk.zip")
        sdk_dir = tmp_path_factory.mktemp("sdk")
        fetch_and_extract_mock = mocker.patch("pyzkaccess._setup._fetch_and_extract", return_value=sdk_dir)
        install_dlls_mock = mocker.patch("pyzkaccess._setup._install_dlls")

        setup(interactive=True, path=None)

        fetch_and_extract_mock.assert_called_once_with("http://example.com/sdk.zip")
        install_dlls_mock.assert_called_once_with(sdk_dir, lib_root, True)

    def test_setup__if_need_to_install_sdk_interactive_and_default_input_accepted__should_fetch_and_install_by_default(
        self, mocker, tmp_path_factory, monkeypatch
    ) -> None:
        system_root = tmp_path_factory.mktemp("Windows")
        monkeypatch.setenv("SystemRoot", str(system_root))
        lib_root = system_root / "SysWOW64"
        lib_root.mkdir()
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**31 - 1)
        mocker.patch("pyzkaccess._setup.platform.machine", return_value="AMD64")
        mocker.patch("pyzkaccess._setup.input", return_value="")
        sdk_dir = tmp_path_factory.mktemp("sdk")
        fetch_and_extract_mock = mocker.patch("pyzkaccess._setup._fetch_and_extract", return_value=sdk_dir)
        install_dlls_mock = mocker.patch("pyzkaccess._setup._install_dlls")

        setup(interactive=True, path=None)

        fetch_and_extract_mock.assert_called_once_with(PULL_SDK_FETCH_URL)
        install_dlls_mock.assert_called_once_with(sdk_dir, lib_root, True)

    def test_setup__if_need_to_install_sdk_with_path_interactive__should_fetch_and_install_without_asking_path(
        self, mocker, tmp_path_factory, monkeypatch
    ) -> None:
        system_root = tmp_path_factory.mktemp("Windows")
        monkeypatch.setenv("SystemRoot", str(system_root))
        lib_root = system_root / "SysWOW64"
        lib_root.mkdir()
        mocker.patch("pyzkaccess._setup.sys.platform", "win32")
        mocker.patch("pyzkaccess._setup.sys.maxsize", 2**31 - 1)
        mocker.patch("pyzkaccess._setup.platform.machine", return_value="AMD64")
        input_mock = mocker.patch("pyzkaccess._setup.input")
        sdk_dir = tmp_path_factory.mktemp("sdk")
        fetch_and_extract_mock = mocker.patch("pyzkaccess._setup._fetch_and_extract", return_value=sdk_dir)
        install_dlls_mock = mocker.patch("pyzkaccess._setup._install_dlls")

        setup(interactive=True, path="http://example.com/sdk.zip")

        fetch_and_extract_mock.assert_called_once_with("http://example.com/sdk.zip")
        install_dlls_mock.assert_called_once_with(sdk_dir, lib_root, True)
        input_mock.assert_not_called()


class FetchAndExtract:
    def test_fetch_and_extract__on_http_path__should_download_and_extract_files(self, mocker, empty_zip) -> None:
        response_stub = Mock(spec=http.client.HTTPResponse, spec_set=True, status=200, read=lambda: empty_zip)
        urlopen_mock = mocker.patch("pyzkaccess._setup.urllib.request.urlopen", return_value=response_stub)

        res = _fetch_and_extract("http://example.com/sdk.zip")

        assert res.is_dir()
        urlopen_mock.assert_called_once_with("http://example.com/sdk.zip", stream=True)

    def test_fetch_and_extract__on_directory_path__should_return_path(self, tmp_path) -> None:
        res = _fetch_and_extract(str(tmp_path))

        assert res == tmp_path

    def test_fetch_and_extract__on_zip_path__should_extract_zip(self, tmp_path, empty_zip) -> None:
        zip_path = tmp_path / "sdk.zip"
        zip_path.write_bytes(empty_zip)

        res = _fetch_and_extract(str(zip_path))

        assert res.is_dir()
        assert not zip_path.exists()

    def test_fetch_and_extract__on_invalid_path__should_exit(self) -> None:
        with pytest.raises(SystemExit) as exc:
            _fetch_and_extract("invalid")

        assert exc.value.code == 3
        assert "File or directory 'invalid' not found" in str(exc.value)


class TestInstallDlls:
    @pytest.mark.parametrize("subdir", ["", "SDK_Ver1.2.3.4"])
    def test_install_dlls__and_sdk_in_path__should_install_dlls(self, mocker, tmp_path_factory, subdir) -> None:
        mocker.patch("pyzkaccess._setup.windll.shell32.IsUserAnAdmin", return_value=True)
        lib_root = tmp_path_factory.mktemp("SysWOW64")
        sdk_dir = tmp_path_factory.mktemp("sdk")
        (sdk_dir / subdir).mkdir(parents=True, exist_ok=True)
        for f in PULL_SDK_DLLS:
            (sdk_dir / f).touch()

        _install_dlls(sdk_dir, lib_root, False)

        assert all((lib_root / dll).exists() for dll in PULL_SDK_DLLS)

    @pytest.mark.parametrize("subdir", ["", "SDK_Ver1.2.3.4"])
    def test_install_dlls__sdk_not_found__should_install_dlls(self, mocker, tmp_path_factory, subdir) -> None:
        mocker.patch("pyzkaccess._setup.windll.shell32.IsUserAnAdmin", return_value=True)
        lib_root = tmp_path_factory.mktemp("SysWOW64")
        sdk_dir = tmp_path_factory.mktemp("sdk")
        (sdk_dir / subdir).mkdir(parents=True, exist_ok=True)
        for f in PULL_SDK_DLLS[1:]:
            (sdk_dir / f).touch()

        with pytest.raises(StepFailedError) as exc:
            _install_dlls(sdk_dir, lib_root, False)

        assert f"PULL SDK not found in '{sdk_dir / subdir}'" in str(exc.value)
        assert not all((lib_root / dll).exists() for dll in PULL_SDK_DLLS)


class TestCopyFiles:
    @pytest.mark.parametrize("is_admin,use_uac", [(True, False), (True, True), (False, False)])
    def test_copy_files__if_user_is_admin_or_uac_not_used__should_copy_in_python(
        self, mocker, tmp_path_factory, is_admin, use_uac
    ) -> None:
        mocker.patch("pyzkaccess._setup.windll.shell32.IsUserAnAdmin", return_value=is_admin)
        lib_root = tmp_path_factory.mktemp("SysWOW64")
        src_dir = tmp_path_factory.mktemp("sdk")
        for dll in PULL_SDK_DLLS:
            (src_dir / dll).touch()

        _copy_files(src_dir, Path("*.dll"), lib_root, use_uac)

        assert all((lib_root / dll).exists() for dll in PULL_SDK_DLLS)

    def test_copy_files__if_user_is_not_admin_and_uac_used__should_copy_with_uac(
        self, mocker, tmp_path_factory
    ) -> None:
        mocker.patch("pyzkaccess._setup.windll.shell32.IsUserAnAdmin", return_value=False)
        elevated_command_mock = mocker.patch("pyzkaccess._setup._elevated_command")
        lib_root = tmp_path_factory.mktemp("SysWOW64")
        src_dir = tmp_path_factory.mktemp("sdk")
        for dll in PULL_SDK_DLLS:
            (src_dir / dll).touch()

        _copy_files(src_dir, Path("*.dll"), lib_root, True)

        elevated_command_mock.assert_called_once_with(
            "cmd", ["/c", "copy", "/Y", str(src_dir / "*.dll"), str(lib_root)]
        )
        assert not all((lib_root / dll).exists() for dll in PULL_SDK_DLLS)
