from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(args: list[str], *, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "memory_quality_gate", *args],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_check_returns_zero_on_pass() -> None:
    text = (
        "Always run ./scripts/deploy.sh --dry-run before shipping v2.4.1 because "
        "it prevents partial deploys."
    )
    proc = run_cli(
        [
            "check",
            "--text",
            text,
            "--format",
            "json",
        ]
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["passed"] is True


def test_cli_check_returns_two_on_fail() -> None:
    proc = run_cli(
        [
            "check",
            "--text",
            "noted",
            "--format",
            "json",
        ]
    )

    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["passed"] is False


def test_cli_rejects_oversized_file(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.txt"
    candidate.write_text("x" * 11, encoding="utf-8")

    proc = run_cli(
        [
            "score",
            "--file",
            str(candidate),
            "--max-input-bytes",
            "10",
        ]
    )

    assert proc.returncode == 2
    assert "exceeds maximum size of 10 bytes" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_cli_rejects_oversized_stdin() -> None:
    proc = run_cli(
        [
            "score",
            "--max-input-bytes",
            "10",
        ],
        stdin="x" * 11,
    )

    assert proc.returncode == 2
    assert "stdin exceeds maximum size of 10 bytes" in proc.stderr


def test_cli_redacts_candidate_text_in_json() -> None:
    proc = run_cli(
        [
            "score",
            "--text",
            "Always check docs/scoring-model.md because retrieval workers depend on it.",
            "--format",
            "json",
            "--redact-text",
        ]
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["candidate"]["text"] == "[redacted]"
