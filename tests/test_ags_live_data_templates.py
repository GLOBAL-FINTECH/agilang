"""Test AGS templates with live data rendering (@fetch and @live directives)."""
from pathlib import Path
import subprocess
import sys
import os

from agilang.scaffold import create_project


def test_ai_template_ags_files_contain_fetch_directive(tmp_path):
    """AI template AGS files should contain @fetch directives."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    root = result.root

    home_ags = (root / "resources/views/home.ags").read_text(encoding="utf-8")
    predict_ags = (root / "resources/views/predict.ags").read_text(encoding="utf-8")

    assert "@fetch" in home_ags
    assert "@fetch" in predict_ags


def test_blockchain_template_ags_files_contain_fetch_directive(tmp_path):
    """Blockchain template AGS files should contain @fetch directives."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    root = result.root

    home_ags = (root / "resources/views/home.ags").read_text(encoding="utf-8")
    blockchain_ags = (root / "resources/views/blockchain.ags").read_text(encoding="utf-8")

    assert "@fetch" in home_ags
    assert "@fetch" in blockchain_ags


def test_ai_template_ags_fetch_points_to_api_endpoint(tmp_path):
    """AI template @fetch should point to valid API endpoints."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    
    assert "/predict" in home_ags
    assert "from" in home_ags


def test_blockchain_template_ags_fetch_points_to_api_endpoint(tmp_path):
    """Blockchain template @fetch should point to valid API endpoints."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    
    assert "/blockchain" in home_ags
    assert "from" in home_ags


def test_ai_template_ags_contains_loop_directive(tmp_path):
    """AI template AGS should contain loop directives for data iteration."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    predict_ags = (result.root / "resources/views/predict.ags").read_text(encoding="utf-8")
    
    assert "for" in predict_ags.lower()
    assert "endfor" in predict_ags.lower() or "{{%" in predict_ags


def test_blockchain_template_ags_contains_loop_directive(tmp_path):
    """Blockchain template AGS should contain loop directives for data iteration."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    blockchain_ags = (result.root / "resources/views/blockchain.ags").read_text(encoding="utf-8")
    
    assert "for" in blockchain_ags.lower()
    assert "endfor" in blockchain_ags.lower() or "{{%" in blockchain_ags


def test_ai_template_ags_contains_page_directive(tmp_path):
    """AI template AGS should contain @page directive for SEO."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    
    assert "@page" in home_ags
    assert "title" in home_ags


def test_blockchain_template_ags_contains_page_directive(tmp_path):
    """Blockchain template AGS should contain @page directive for SEO."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    
    assert "@page" in home_ags
    assert "title" in home_ags


def test_ai_template_layout_ags_contains_seo_placeholder(tmp_path):
    """AI template layout.ags should contain SEO placeholder."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    layout_ags = (result.root / "resources/views/layout.ags").read_text(encoding="utf-8")
    
    assert "{{{" in layout_ags
    assert "seo" in layout_ags.lower()


def test_blockchain_template_layout_ags_contains_seo_placeholder(tmp_path):
    """Blockchain template layout.ags should contain SEO placeholder."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    layout_ags = (result.root / "resources/views/layout.ags").read_text(encoding="utf-8")
    
    assert "{{{" in layout_ags
    assert "seo" in layout_ags.lower()


def test_ai_template_ags_data_binding_syntax(tmp_path):
    """AI template AGS should use correct data binding syntax."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    
    assert "{{{" in home_ags or "{{" in home_ags


def test_blockchain_template_ags_data_binding_syntax(tmp_path):
    """Blockchain template AGS should use correct data binding syntax."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    home_ags = (result.root / "resources/views/home.ags").read_text(encoding="utf-8")
    
    assert "{{{" in home_ags or "{{" in home_ags


def test_ai_template_js_runtime_hydrates_data(tmp_path):
    """AI template JS runtime should contain hydration logic."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    js = (result.root / "resources/assets/js/ai-runtime.js").read_text(encoding="utf-8")
    
    assert "hydrate" in js or "DOMContentLoaded" in js


def test_blockchain_template_js_runtime_hydrates_data(tmp_path):
    """Blockchain template JS runtime should contain hydration logic."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    js = (result.root / "resources/assets/js/blockchain-runtime.js").read_text(encoding="utf-8")
    
    assert "hydrate" in js or "DOMContentLoaded" in js


def test_ai_template_main_agi_has_render_ags_function(tmp_path):
    """AI template main.agi should use render_ags function."""
    result = create_project("ai app", directory=tmp_path, template="ai")
    main_agi = (result.root / "src/main.agi").read_text(encoding="utf-8")
    
    assert "render_ags" in main_agi


def test_blockchain_template_main_agi_has_render_ags_function(tmp_path):
    """Blockchain template main.agi should use render_ags function."""
    result = create_project("chain app", directory=tmp_path, template="blockchain")
    main_agi = (result.root / "src/main.agi").read_text(encoding="utf-8")
    
    assert "render_ags" in main_agi
