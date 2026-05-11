# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
