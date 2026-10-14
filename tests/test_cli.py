from __future__ import annotations

import json
import os
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


def test_cli_explicit_empty_text_does_not_read_stdin() -> None:
    proc = run_cli(["score", "--text", ""], stdin="Always check docs/scoring-model.md first.")

    assert proc.returncode == 0
    assert proc.stdout.startswith("FAIL score=0.000")
    assert "Hard veto" in proc.stdout


def test_cli_closed_stdin_reports_usage_error() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "memory_quality_gate", "score"],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
        preexec_fn=lambda: os.close(0),
    )

    assert proc.returncode == 1
    assert "Provide --text, --file, or piped stdin input." in proc.stderr
    assert "Traceback" not in proc.stderr


def test_cli_rejects_directory_file(tmp_path: Path) -> None:
    proc = run_cli(["score", "--file", str(tmp_path)])

    assert proc.returncode == 2
    assert "--file points to a directory" in proc.stderr


def test_cli_startup_skips_unused_stdlib_modules() -> None:
    # Compare with the stdlib modules the CLI genuinely needs; the package must not
    # add these itself (json is imported only for --format json).
    probe = "import sys; {}; print(sorted(m for m in ('json', 'pathlib') if m in sys.modules))"

    def loaded(statement: str) -> str:
        return subprocess.run(
            [sys.executable, "-c", probe.format(statement)],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    baseline = loaded("import argparse, collections, dataclasses, itertools, math, re, typing")
    assert loaded("import memory_quality_gate.cli") == baseline
