# memory-quality-gate

Zero-LLM heuristic scoring for filtering memory candidates before they reach long-term storage.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![CI](https://github.com/GreyforgeLabs/memory-quality-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/GreyforgeLabs/memory-quality-gate/actions/workflows/ci.yml)

## Why This Exists

Most agent memory systems either store too much noisy text or spend money on an LLM judge before every write. This project takes the cheap path: score each candidate with deterministic heuristics that reward actionability, specificity, novelty, reasoning, and outcome linkage. The result is a practical gate you can run inside local agents, batch pipelines, or RAG ingestion jobs with zero model calls.

## Quick Start

```bash
git clone https://github.com/GreyforgeLabs/memory-quality-gate.git
cd memory-quality-gate
./scripts/setup.sh
. .venv/bin/activate
memory-quality-gate check --text "Always run ./scripts/deploy.sh --dry-run before shipping v2.4.1 because it prevents partial deploys."
```

## Features

- Five-dimension scoring model with explicit weights and scope-aware thresholds
- No runtime dependencies and no LLM or embedding calls
- Optional novelty check against an existing memory corpus
- Python API for direct integration into memory pipelines
- CLI for shell scripts, CI jobs, and local filtering

## Usage

```bash
memory-quality-gate score \
  --text "Always check release notes before bumping worker versions because retry semantics changed in v2.4.1." \
  --scope project
```

Example output:

```text
PASS score=0.705 threshold=0.480 scope=project
  actionability    0.70
  specificity      0.85
  novelty          0.80
  reasoning        0.60
  outcome_linkage  0.20
```

Novelty-aware scoring against an existing corpus:

```bash
memory-quality-gate check \
  --file candidate.txt \
  --existing-file existing_memory.md \
  --scope session \
  --format json
```

Python API:

```python
from memory_quality_gate import MemoryCandidate, QualityGate

gate = QualityGate(existing_content="Previously stored memory goes here.")
result = gate.evaluate(
    MemoryCandidate(
        text="Always rotate snapshot files after schema changes because stale fixtures mask migration bugs.",
        scope="project",
        entry_type="lesson",
    )
)

print(result.passed, round(result.weighted_score, 3), result.scores)
```

## Documentation

- [STARTHERE.md](STARTHERE.md) - AI coding client bootstrap
- [docs/scoring-model.md](docs/scoring-model.md) - Weights, thresholds, and novelty logic
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Development

```bash
. .venv/bin/activate
python -m ruff check .
python -m pytest
python -m build
python -m twine check dist/*
```

## Releases

- Push a `vX.Y.Z` tag to build the wheel and source distribution, verify metadata, and attach the artifacts to a GitHub Release.
- Use the manual `Publish PyPI` GitHub Actions workflow after configuring `GreyforgeLabs/memory-quality-gate` as a trusted publisher on PyPI.

## License

AGPL-3.0. See [LICENSE](LICENSE) for details.

---

Built by [Greyforge](https://greyforge.tech)
