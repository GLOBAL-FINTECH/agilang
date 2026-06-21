from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agilang.cgi_runtime import handle_cgi_request, shared_hosting_capabilities, write_shared_hosting_files
from agilang.scaffold import create_project


def run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return subprocess.run([sys.executable, "-m", "agilang.cli", *args], cwd=str(cwd), text=True, capture_output=True, timeout=30, env=env)


def test_shared_hosting_capabilities() -> None:
    caps = shared_hosting_capabilities()
    assert caps["classic_cgi"] is True
    assert caps["cpanel_public_html_scaffold"] is True
    assert caps["plesk_httpdocs_scaffold"] is True


def test_hosting_scaffold_files(tmp_path: Path) -> None:
    project = create_project("Panel App", directory=tmp_path).root
    result = write_shared_hosting_files(project, entry="src/main.agi")
    for rel in ["public_html/.htaccess", "public_html/app.cgi", "public_html/app.fcgi", "passenger_wsgi.py", "deployment/CPANEL_PLESK_CGI_FASTCGI.md"]:
        assert (project / rel).exists(), rel
    assert result.mode == "auto"


def test_generated_project_includes_shared_hosting_files(tmp_path: Path) -> None:
    project = create_project("Shared Host App", directory=tmp_path).root
    assert (project / "public_html" / "app.cgi").exists()
    assert (project / "public_html" / "app.fcgi").exists()
    assert (project / "public_html" / ".htaccess").exists()
    assert (project / "passenger_wsgi.py").exists()


def test_cgi_handle_request(tmp_path: Path, monkeypatch) -> None:
    project = create_project("CGI Smoke App", directory=tmp_path).root
    monkeypatch.chdir(project)
    env = {"REQUEST_METHOD": "GET", "REQUEST_URI": "/health", "QUERY_STRING": "", "CONTENT_LENGTH": "0", "SERVER_SOFTWARE": "Apache/cPanel"}
    resp = handle_cgi_request("src/main.agi", environ=env, body=b"")
    assert resp.status == 200
    assert b"ok" in resp.to_bytes()


def test_cli_hosting_scaffold(tmp_path: Path) -> None:
    project = create_project("CLI Hosting App", directory=tmp_path).root
    result = run_cli(project, "hosting", "scaffold", "--entry", "src/main.agi")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "public_html" / "app.cgi").exists()
    caps = run_cli(project, "hosting", "capabilities")
    assert caps.returncode == 0, caps.stdout + caps.stderr
    assert "classic_cgi" in caps.stdout
