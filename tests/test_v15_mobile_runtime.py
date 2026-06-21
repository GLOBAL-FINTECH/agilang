from agilang.mobile_runtime import (
    mobile_runtime_matrix,
    mobile_runtime_capabilities,
    create_mobile_native_bridge,
)


def test_mobile_runtime_matrix_has_android_ios_targets():
    matrix = mobile_runtime_matrix()
    targets = matrix["targets"]
    assert "android-arm64-v8a" in targets
    assert "android-x86_64" in targets
    assert "ios-arm64" in targets
    assert "ios-simulator-arm64" in targets
    assert targets["android-arm64-v8a"]["library_name"] == "libagilang_net_runtime.so"
    assert targets["ios-arm64"]["library_name"] == "libagilang_net_runtime.a"


def test_mobile_runtime_capabilities_are_explicit():
    caps = mobile_runtime_capabilities()
    assert caps["react_native_expo_client"] is True
    assert caps["android_native_bridge_source"] is True
    assert caps["ios_swift_bridge_source"] is True
    assert caps["native_media_engine"] is False


def test_mobile_native_bridge_scaffold(tmp_path):
    result = create_mobile_native_bridge("Test App Native", directory=tmp_path, target="both")
    assert (result.root / "android/agilang-runtime/CMakeLists.txt").exists()
    assert (result.root / "ios/AgilangRuntimeBridge.swift").exists()
    assert (result.root / "src/agilangNativeRuntime.ts").exists()
    assert any("mobile-runtime.json" in str(p) for p in result.files)


def test_cli_mobile_platform_matrix(capsys):
    from agilang.cli import main
    try:
        main(["mobile", "platform-matrix"])
    except SystemExit as exc:
        assert exc.code in (0, None)
    output = capsys.readouterr().out
    assert "android-arm64-v8a" in output
    assert "ios-arm64" in output
