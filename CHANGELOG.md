# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.1] - 2026-10-14

### Performance

- Novelty scoring against an existing corpus is about 6x faster per candidate for long-lived gates: an inverted token index and a compact word-trigram filter are built on the second novelty lookup, so one-shot CLI runs never pay for them and results are identical
- Dimension scoring stops counting regex matches once a score saturates, so very long candidates no longer scan the whole text once per dimension
- `import memory_quality_gate` no longer imports `typing`, and the CLI no longer imports `pathlib` or (for text output) `json`
- `QualityResult.to_dict()` builds the candidate payload directly instead of using `dataclasses.asdict`
- Added `scripts/bench.py`, a reproducible benchmark for import time, CLI wall time and throughput on a generated corpus

### Fixed

- Percentages such as `50%` now count toward specificity
- File paths at the end of a sentence, inside backticks or quotes, or listed back to back now count toward specificity
- `reason:` and `why:` labels now count toward reasoning
- A candidate whose weighted score lands exactly on its threshold now passes; scores are rounded so binary floating-point noise (for example `0.39999999999999997` against `0.40`) no longer decides the result, and JSON scores print as clean decimals
- The specificity shortcut no longer raises a custom threshold that is already below 0.40
- Novelty now tokenizes Unicode letters, so verbatim duplicates in non-ASCII text (for example Japanese or accented French) are detected
- Non-string keys in custom thresholds or weights raise `ValueError` instead of an internal `TypeError`
- `QualityResult.to_dict()` returns a copy of the scores
- CLI: an explicit `--text ""` is scored instead of falling through to stdin; a closed stdin reports the usage error instead of a traceback
- `scripts/setup.sh` accepts every Python from 3.11 up, matching `requires-python`

### Changed

- CI runs on Python 3.11, 3.12, 3.13 and 3.14; package classifiers list 3.13 and 3.14
- README example output and the scoring-model document now match actual behaviour

## [0.2.0] - 2026-09-06

### Added

- Runtime validation for direct API scope, entry type, threshold, weight, and input-size settings
- Default CLI and library input caps for candidate text and existing-corpus content
- `--redact-text` for safer JSON output in logs

### Security

- Hardened the manual PyPI publish workflow so it only publishes validated `vX.Y.Z` tags that match `pyproject.toml`
- Reduced default GitHub Actions token exposure for CI and release build jobs

## [0.1.0] - 2026-04-06

### Added

- Standalone Python package for heuristic memory scoring
- Five-dimension scoring engine with scope-aware thresholds
- CLI commands for scoring and pass/fail checks
- Novelty checks against an optional existing memory corpus
- Pytest suite, Ruff config, and GitHub Actions CI
- Tagged release workflow with GitHub release artifacts and manual PyPI publish workflow
- Real README, STARTHERE bootstrap, and scoring model documentation
