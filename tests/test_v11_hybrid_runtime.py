import json
import subprocess
import sys
from pathlib import Path

from agilang.hybrid_runtime import (
    HybridWebRuntime,
    compile_native_runtime,
    native_runtime_status,
    native_runtime_available,
    NativeNetRuntime,
)
from agilang.std import agilab_web_runtime


def test_hybrid_runtime_capability_object():
    rt = HybridWebRuntime("hybrid")
    caps = rt.capabilities()
    assert caps["mode"] == "hybrid"
    assert caps["python_http"] is True
    assert caps["c_http"] is True
    assert caps["c_websocket"] is True


def test_agilab_alias_from_std():
    rt = agilab_web_runtime("python")
    caps = rt.capabilities()
    assert caps["mode"] == "python"
    assert caps["python_websocket"] is True
    assert caps["c_websocket"] is False


def test_compile_and_load_native_runtime(tmp_path: Path):
    result = compile_native_runtime(tmp_path)
    assert result.ok, result.stderr
    assert result.library_path and result.library_path.exists()
    native = NativeNetRuntime(result.library_path, auto_build=False)
    assert "1.9.3" in native.version()
    assert native.selftest() is True
    caps = native.capabilities()
    assert caps["http"] is True
    assert caps["websocket"] is True
    assert caps["ping_pong"] is True


def test_native_runtime_status_builds_and_reports():
    status = native_runtime_status(build=True)
    assert status["build"]["ok"] is True, status["build"].get("stderr")
    assert status["library_exists"] is True
    assert status["native_selftest"] is True


def test_cli_runtime_status_and_example():
    root = Path(__file__).resolve().parents[1]
    status_proc = subprocess.run(
        [sys.executable, "-m", "agilang", "runtime", "status"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert status_proc.returncode == 0, status_proc.stderr
    payload = json.loads(status_proc.stdout)
    assert payload["agilang_runtime_version"] == "1.9.3"

    example_proc = subprocess.run(
        [sys.executable, "-m", "agilang", "run", "examples/native_hybrid_web_runtime.agi"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert example_proc.returncode == 0, example_proc.stderr
    assert "hybrid mode hybrid" in example_proc.stdout
