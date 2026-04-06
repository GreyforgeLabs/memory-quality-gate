# STARTHERE.md - AI Bootstrap Guide

> This file is designed for AI coding assistants. If you are a human,
> see [README.md](README.md) for the human-friendly guide.

## Quick Bootstrap

```bash
git clone https://github.com/GreyforgeLabs/memory-quality-gate.git && cd memory-quality-gate && ./scripts/setup.sh
```

## What This Project Does

`memory-quality-gate` filters memory candidates before they are persisted. It applies a deterministic five-dimension scoring model, supports novelty checks against an existing corpus, and exposes both a Python API and a CLI with no model calls or runtime dependencies.

## Project Structure

```text
memory-quality-gate/
  src/memory_quality_gate/  # package code and CLI entry point
  tests/                    # unit and CLI tests
  docs/scoring-model.md     # scoring dimensions and thresholds
  scripts/setup.sh          # idempotent local bootstrap
  pyproject.toml            # packaging and tool config
  README.md                 # human-facing docs
  STARTHERE.md              # this file
```

## Setup Prerequisites

- Python 3.11 or 3.12
- `python3 -m venv`
- Internet access for the initial `pip install -e .[dev]`

## Installation Steps

1. Clone: `git clone https://github.com/GreyforgeLabs/memory-quality-gate.git`
2. Enter directory: `cd memory-quality-gate`
3. Run setup: `./scripts/setup.sh`
4. Activate the environment: `. .venv/bin/activate`

## Verification

```bash
. .venv/bin/activate
memory-quality-gate check --text "Always run ./scripts/deploy.sh --dry-run before shipping v2.4.1 because it prevents partial deploys."
```

Expected behavior:
- exit code `0`
- output starts with `PASS`

## Key Entry Points

- `src/memory_quality_gate/core.py` - scoring engine and public dataclasses
- `src/memory_quality_gate/cli.py` - CLI entry point
- `src/memory_quality_gate/__main__.py` - `python -m memory_quality_gate`

## Configuration

- `--scope` chooses the quality bar: `global`, `project`, or `session`
- `--entry-type` affects outcome-linkage scoring
- `--existing-file` provides the comparison corpus for novelty scoring
- No environment variables are required

## Common Tasks

```bash
. .venv/bin/activate
python -m ruff check .
python -m pytest
memory-quality-gate score --file candidate.txt --existing-file existing_memory.md --format json
python -m build
python -m twine check dist/*
```
