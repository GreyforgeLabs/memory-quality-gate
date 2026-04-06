# Contributing to memory-quality-gate

This project is intentionally small: one scoring engine, one CLI, one test suite. Keep changes focused and keep the heuristics explainable.

## Getting Started

1. Fork the repository.
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/memory-quality-gate.git`
3. Enter the repo and run setup: `cd memory-quality-gate && ./scripts/setup.sh`
4. Activate the environment: `. .venv/bin/activate`
5. Create a branch: `git checkout -b your-feature`

## Development Workflow

1. Make your changes.
2. Run `python -m ruff check .` and `python -m pytest`.
3. Update docs when the scoring contract or CLI changes.
4. Commit with clear, descriptive messages.
5. Push to your fork and open a Pull Request.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) style:

```
feat: add new parsing mode
fix: handle empty input gracefully
docs: update installation steps
chore: update dependencies
```

## Pull Request Process

1. Fill out the PR template.
2. Ensure CI passes.
3. Keep PRs focused; one logical scoring or tooling change per PR.
4. Explain any heuristic change with a before/after example.

## Release Process

1. Update `pyproject.toml` and `CHANGELOG.md` for the intended version.
2. Run `. .venv/bin/activate && python -m ruff check . && python -m pytest && python -m build && python -m twine check dist/*`.
3. Create and push a `vX.Y.Z` tag that matches `project.version` in `pyproject.toml`.
4. Let the `Release` workflow publish GitHub release artifacts automatically.
5. Run the manual `Publish PyPI` workflow after PyPI trusted publishing is configured for this repo.

## Code Standards

- Preserve the zero-dependency runtime.
- Keep heuristics deterministic and cheap.
- Write tests for any scoring or CLI behavior change.
- No secrets, credentials, or internal paths in code, docs, or examples.
- Favor explicit thresholds and documented tradeoffs over opaque magic.

## Reporting Issues

Use the GitHub issue templates. For bugs, include the candidate text, expected behavior, actual result, and whether `existing_content` was involved.

## License

By contributing, you agree that your contributions will be licensed under the same license as this project (AGPL-3.0).

---

Built by [Greyforge](https://greyforge.tech)
