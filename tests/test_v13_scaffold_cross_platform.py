from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agilang.hybrid_runtime import native_platform_matrix
from agilang.scaffold import create_project, slugify_project_name


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return subprocess.run(
        [sys.executable, "-m", "agilang.cli", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=30,
        env=env,
    )


def test_slugify_multi_word_name() -> None:
    assert slugify_project_name("Test App Two") == "test-app-two"
    assert slugify_project_name("test_app_two") == "test-app-two"


def test_create_web_project_files(tmp_path: Path) -> None:
    result = create_project("Test App Two", directory=tmp_path)
    root = result.root
    assert root.name == "test-app-two"
    expected = [
        "agilang.toml",
        "src/main.agi",
        "src/realtime.agi",
        "templates/home.html",
        "templates/dashboard.html",
        "public/css/app.css",
        "public/js/app.js",
        "tests/test_main.agi",
        "deployment/NGINX.md",
        "deployment/CADDY.md",
        "README.md",
    ]
    for rel in expected:
        assert (root / rel).exists(), rel


def test_generated_project_runs_and_tests(tmp_path: Path) -> None:
    result = create_project("Smoke Web App", directory=tmp_path)
    root = result.root
    run_result = run_cli(root, "run")
    assert run_result.returncode == 0, run_result.stderr + run_result.stdout
    assert "dev check" in run_result.stdout
    test_result = run_cli(root, "test")
    assert test_result.returncode == 0, test_result.stderr + test_result.stdout
    assert "PASS" in test_result.stdout


def test_cli_new_accepts_multi_word_name(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "new", "test", "app", "two")
    assert result.returncode == 0, result.stderr + result.stdout
    assert (tmp_path / "test-app-two" / "src" / "main.agi").exists()


def test_platform_matrix_lists_windows_and_macos() -> None:
    matrix = native_platform_matrix()
    platforms = matrix["supported_platforms"]
    assert "windows-x86_64" in platforms
    assert "macos-x86_64" in platforms
    assert "macos-arm64" in platforms
    assert platforms["windows-x86_64"]["library_name"] == "agilang_net_runtime.dll"
    assert platforms["macos-arm64"]["library_name"] == "libagilang_net_runtime.dylib"
