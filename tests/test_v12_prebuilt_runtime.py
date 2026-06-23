from pathlib import Path

from agilang.hybrid_runtime import (
    NativeNetRuntime,
    bundled_prebuilt_runtime,
    native_prebuilt_runtime_install,
    native_prebuilt_status,
    native_runtime_status,
)


def test_prebuilt_status_reports_current_platform_artifacts():
    status = native_prebuilt_status()
    assert "platform_tag" in status
    assert "library_name" in status
    assert isinstance(status["artifacts"], dict)
    if status["bundled_library"]:
        assert Path(status["bundled_library"]).exists()


def test_install_prebuilt_runtime_when_available(tmp_path):
    if bundled_prebuilt_runtime() is None:
        return
    installed = native_prebuilt_runtime_install(tmp_path)
    assert installed is not None
    assert installed.exists()
    rt = NativeNetRuntime(installed, auto_build=False)
    assert rt.selftest() is True
    assert rt.capabilities()["websocket"] is True


def test_runtime_status_includes_prebuilt_metadata():
    status = native_runtime_status(build=False)
    assert "platform_tag" in status
    assert "bundled_prebuilt_library" in status
    assert "bundled_prebuilt_artifacts" in status
