"""Command line interface for memory-quality-gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    DEFAULT_MAX_CANDIDATE_CHARS,
    DEFAULT_MAX_EXISTING_CHARS,
    MemoryCandidate,
    QualityGate,
)


class CliInputError(ValueError):
    """Raised for user-fixable CLI input failures."""


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        text = _resolve_text(args)
        existing_content = _load_existing_content(args.existing_file, args.max_existing_bytes)
        gate = QualityGate(
            existing_content=existing_content,
            max_candidate_chars=args.max_input_bytes,
            max_existing_chars=args.max_existing_bytes,
        )
        result = gate.evaluate(
            MemoryCandidate(text=text, scope=args.scope, entry_type=args.entry_type)
        )
    except (CliInputError, TypeError, ValueError) as exc:
        parser.error(str(exc))

    if args.format == "json":
        print(json.dumps(result.to_dict(redact_candidate_text=args.redact_text), indent=2))
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
        "--max-input-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_CANDIDATE_CHARS,
        help=(
            "Maximum UTF-8 bytes accepted for --text, --file, or stdin "
            f"(default: {DEFAULT_MAX_CANDIDATE_CHARS})."
        ),
    )
    parser.add_argument(
        "--max-existing-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_EXISTING_CHARS,
        help=(
            "Maximum UTF-8 bytes accepted for --existing-file "
            f"(default: {DEFAULT_MAX_EXISTING_CHARS})."
        ),
    )
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
    parser.add_argument(
        "--redact-text",
        action="store_true",
        help="Replace candidate.text with [redacted] in JSON output.",
    )


def _resolve_text(args: argparse.Namespace) -> str:
    if args.text:
        _validate_text_bytes(args.text, "--text", args.max_input_bytes)
        return args.text
    if args.file:
        return _read_text_file(args.file, "--file", args.max_input_bytes)
    if not sys.stdin.isatty():
        piped = _read_stdin(args.max_input_bytes)
        if piped.strip():
            return piped
    raise SystemExit("Provide --text, --file, or piped stdin input.")


def _load_existing_content(path: str | None, max_bytes: int) -> str:
    if not path:
        return ""
    return _read_text_file(path, "--existing-file", max_bytes)


def _read_text_file(path_text: str, label: str, max_bytes: int) -> str:
    path = Path(path_text)
    try:
        if path.is_dir():
            raise CliInputError(f"{label} points to a directory: {path}")
        if path.exists() and path.stat().st_size > max_bytes:
            raise CliInputError(f"{label} exceeds maximum size of {max_bytes} bytes: {path}")
        with path.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except CliInputError:
        raise
    except OSError as exc:
        raise CliInputError(f"cannot read {label} {path}: {exc.strerror}") from exc

    if len(data) > max_bytes:
        raise CliInputError(f"{label} exceeds maximum size of {max_bytes} bytes: {path}")
    return _decode_utf8(data, label)


def _read_stdin(max_bytes: int) -> str:
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is None:
        text = sys.stdin.read(max_bytes + 1)
        _validate_text_bytes(text, "stdin", max_bytes)
        return text

    data = buffer.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise CliInputError(f"stdin exceeds maximum size of {max_bytes} bytes")
    return _decode_utf8(data, "stdin")


def _decode_utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CliInputError(f"{label} must be valid UTF-8 text") from exc


def _validate_text_bytes(text: str, label: str, max_bytes: int) -> None:
    if len(text.encode("utf-8")) > max_bytes:
        raise CliInputError(f"{label} exceeds maximum size of {max_bytes} bytes")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


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
