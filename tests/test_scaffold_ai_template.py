"""Test AI template scaffold generation and structure."""
from pathlib import Path
import subprocess
import sys
import os

from agilang.scaffold import create_project


def test_ai_template_generates_web_ui(tmp_path):
    """AI template should generate web UI with AGS templates."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    root = result.root

    # Core files
    assert (root / "src/main.agi").exists()
    assert (root / "src/model.agi").exists()

    # Web UI files
    assert (root / "resources/views/layout.ags").exists()
    assert (root / "resources/views/home.ags").exists()
    assert (root / "resources/views/predict.ags").exists()

    # Assets
    assert (root / "resources/assets/css/app.css").exists()
    assert (root / "resources/assets/js/ai-runtime.js").exists()

    # Documentation
    assert (root / "docs/AI_RUNBOOK.md").exists()


def test_ai_template_home_ags_contains_fetch_directive(tmp_path):
    """AI template home.ags should contain @fetch directive for live data."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    assert "@fetch" in home_ags
    assert "predictions" in home_ags


def test_ai_template_main_contains_api_routes(tmp_path):
    """AI template main.agi should contain prediction API routes."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    main_agi = (result.root / "src/main.agi").read_text(encoding="utf-8")
    assert "/predict" in main_agi
    assert "/api/predict" in main_agi
    assert "json_response" in main_agi


def test_ai_template_predict_ags_contains_loop(tmp_path):
    """AI template predict.ags should contain loop directive for predictions."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    predict_ags = (result.root / "resources/views/predict.ags").read_text(encoding="utf-8")
    assert "@fetch" in predict_ags
    assert "for" in predict_ags.lower()
    assert "predictions" in predict_ags


def test_ai_template_css_exists_and_has_styling(tmp_path):
    """AI template CSS should contain styling rules."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    css = (result.root / "resources/assets/css/app.css").read_text(encoding="utf-8")
    assert ":root" in css or "body" in css


def test_ai_template_js_runtime_exists(tmp_path):
    """AI template JS runtime should exist and contain fetch logic."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    js = (result.root / "resources/assets/js/ai-runtime.js").read_text(encoding="utf-8")
    assert "fetch" in js
    assert "updateElement" in js or "hydrate" in js


def test_ai_template_passes_agi_check(tmp_path):
    """AI template should pass agi check."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    proc = subprocess.run(
        [sys.executable, "-m", "agilang", "check", "src/main.agi"],
        cwd=result.root,
        text=True,
        capture_output=True,
        timeout=20,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    # agi check may have warnings but should not crash
    assert proc.returncode == 0, proc.stderr


def test_ai_template_model_agi_exists(tmp_path):
    """AI template should include model.agi for ML inference."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    assert (result.root / "src/model.agi").exists()
    model_agi = (result.root / "src/model.agi").read_text(encoding="utf-8")
    assert "ai_predict" in model_agi or "prediction" in model_agi.lower()


def test_ai_template_storage_dir_exists(tmp_path):
    """AI template should create storage directory for database."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    assert (result.root / "storage/.gitkeep").exists()
