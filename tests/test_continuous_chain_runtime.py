import json
import os
import subprocess
import sys
from pathlib import Path


def test_chain_start_continuous_bounded_run_persists_slots(tmp_path):
    project = tmp_path / "chain"
    project.mkdir()
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agilang.cli_runtime",
            "chain",
            "start",
            "--mode",
            "sbq-beacon",
            "--continuous",
            "--slot-seconds",
            "1",
            "--max-slots",
            "2",
        ],
        cwd=project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    assert proc.returncode == 0, proc.stderr
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert lines[0]["continuous"] is True
    slot_events = [line for line in lines if line.get("event") == "slot"]
    assert len(slot_events) == 2
    assert slot_events[-1]["slot"] == 2
    assert (project / "storage" / "beacon.sqlite").exists()


def test_chain_start_dry_run_reports_continuous_capability(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agilang.cli_runtime",
            "chain",
            "start",
            "--mode",
            "sbq-beacon",
            "--dry-run",
            "--continuous",
        ],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])},
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["continuous"] is True
    assert "--continuous" in payload["message"]
