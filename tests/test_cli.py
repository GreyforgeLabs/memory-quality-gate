from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli_check_returns_zero_on_pass() -> None:
    text = (
        "Always run ./scripts/deploy.sh --dry-run before shipping v2.4.1 because "
        "it prevents partial deploys."
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "memory_quality_gate",
            "check",
            "--text",
            text,
            "--format",
            "json",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["passed"] is True


def test_cli_check_returns_two_on_fail() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "memory_quality_gate",
            "check",
            "--text",
            "noted",
            "--format",
            "json",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["passed"] is False
