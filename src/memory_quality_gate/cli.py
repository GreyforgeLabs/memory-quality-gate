"""Command line interface for memory-quality-gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import MemoryCandidate, QualityGate


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    text = _resolve_text(args)
    existing_content = _load_existing_content(args.existing_file)
    gate = QualityGate(existing_content=existing_content)
    result = gate.evaluate(
        MemoryCandidate(text=text, scope=args.scope, entry_type=args.entry_type)
    )

    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_text_result(result)

    if args.command == "check":
        return 0 if result.passed else 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memory-quality-gate",
        description="Score memory candidates without calling an LLM.",
    )
    subparsers = parser.add_subparsers(dest="command")

    for command in ("score", "check"):
        subparser = subparsers.add_parser(command)
        _add_shared_arguments(subparser)

    return parser


def _add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text", help="Candidate text to score.")
    parser.add_argument("--file", help="Read candidate text from a file.")
    parser.add_argument(
        "--scope",
        choices=("global", "project", "session"),
        default="project",
        help="Memory scope. Session uses the strictest threshold.",
    )
    parser.add_argument(
        "--entry-type",
        choices=("general", "decision", "lesson", "completed", "product_update"),
        default="general",
        help="Entry type used for outcome-linkage scoring.",
    )
    parser.add_argument(
        "--existing-file",
        help="Optional text corpus used for novelty checks.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )


def _resolve_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        piped = sys.stdin.read()
        if piped.strip():
            return piped
    raise SystemExit("Provide --text, --file, or piped stdin input.")


def _load_existing_content(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


def _print_text_result(result) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(
        f"{status} score={result.weighted_score:.3f} "
        f"threshold={result.threshold:.3f} scope={result.candidate.scope}"
    )
    for name, score in result.scores.items():
        print(f"  {name:16} {score:.2f}")
    if result.rejection_reason:
        print(f"  reason            {result.rejection_reason}")


if __name__ == "__main__":
    raise SystemExit(main())
