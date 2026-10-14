#!/usr/bin/env python3
"""Reproducible local benchmark for memory-quality-gate.

Generates a deterministic synthetic corpus in memory (and one temporary file
inside the repository for the CLI run), then reports median timings as JSON:

- import wall time of ``import memory_quality_gate`` (subprocess, minus bare startup)
- CLI wall time for ``check --text`` and ``check --existing-file``
- library throughput in candidates/second with and without a novelty corpus

Usage: python scripts/bench.py [--src PATH] [--runs N]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WORDS = (
    "worker retry cache deploy schema migration fixture snapshot index queue "
    "token budget latency timeout config release rollback probe health shard "
    "replica lease lock vault ledger agent memory corpus gate score novelty "
    "planner runner build target branch merge review audit metric trace"
).split()
# A Zipf-distributed vocabulary of a few thousand pseudo-words, closer to real notes
# than a tiny fixed word list: a few very common words and a long tail of rare ones.
_SYLLABLES = "ka lo mi ren tor vex sal dun pri qua zel mor nit fae bru gol".split()
VOCAB = WORDS + sorted(
    {a + b + c for a in _SYLLABLES for b in _SYLLABLES for c in ("", "s", "er", "ing")}
)
ZIPF = [1 / (rank + 1) for rank in range(len(VOCAB))]
LEADS = ("Always", "Never", "Prefer", "Verify", "Check", "Remember", "Note", "Use")
REASONS = ("because", "so that", "to avoid", "since", "which means")
OUTCOMES = ("fixed", "verified", "shipped", "reduced", "failed", "merged", "")
SPECIFICS = (
    "src/{w}/{w2}.py",
    "docs/{w}-{w2}.md",
    "v{a}.{b}.{c}",
    "2026-{m:02d}-{d:02d}",
    "port {p}",
    "PR #{p}",
    "{a}{b}%",
    "https://example.test/{w}/{w2}",
)


def make_sentence(rng: random.Random) -> str:
    def spec() -> str:
        return rng.choice(SPECIFICS).format(
            w=rng.choice(WORDS),
            w2=rng.choice(WORDS),
            a=rng.randint(0, 9),
            b=rng.randint(0, 9),
            c=rng.randint(0, 30),
            m=rng.randint(1, 12),
            d=rng.randint(1, 28),
            p=rng.randint(80, 9999),
        )

    body = " ".join(rng.choices(VOCAB, ZIPF, k=rng.randint(4, 14)))
    parts = [rng.choice(LEADS), body, spec()]
    if rng.random() < 0.6:
        parts += [rng.choice(REASONS), " ".join(rng.choices(VOCAB, ZIPF, k=5)), spec()]
    outcome = rng.choice(OUTCOMES)
    if outcome:
        parts.append(f"and it {outcome}")
    return " ".join(parts) + "."


def corpus(seed: int, lines: int) -> list[str]:
    rng = random.Random(seed)
    return [make_sentence(rng) for _ in range(lines)]


def median_wall(cmd: list[str], env: dict[str, str], runs: int) -> float:
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def throughput(gate, candidates, repeats: int) -> float:
    rates = []
    for _ in range(repeats):
        start = time.perf_counter()
        gate.evaluate_many(candidates)
        rates.append(len(candidates) / (time.perf_counter() - start))
    return statistics.median(rates)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=str(ROOT / "src"))
    parser.add_argument("--runs", type=int, default=21)
    parser.add_argument("--existing-lines", type=int, default=5000)
    parser.add_argument("--candidates", type=int, default=2000)
    args = parser.parse_args()

    src = str(Path(args.src).resolve())
    sys.path.insert(0, src)
    from memory_quality_gate import MemoryCandidate, QualityGate

    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": src}
    # Warm the bytecode cache once so every timed run measures the same thing.
    subprocess.run([sys.executable, "-c", "import memory_quality_gate.cli"], env=env)

    existing = corpus(1, args.existing_lines)
    fresh = corpus(2, args.candidates)
    rng = random.Random(3)
    # One in five candidates repeats a stored memory to exercise duplicate paths.
    candidates = [
        MemoryCandidate(text=rng.choice(existing) if i % 5 == 0 else fresh[i])
        for i in range(args.candidates)
    ]
    existing_text = "\n".join(existing)

    text = (
        "Always run ./scripts/deploy.sh --dry-run before shipping v2.4.1 because "
        "it prevents partial deploys."
    )
    bare = median_wall([sys.executable, "-c", "pass"], env, args.runs)
    imp = median_wall([sys.executable, "-c", "import memory_quality_gate"], env, args.runs)
    cli = [sys.executable, "-m", "memory_quality_gate", "check", "--text", text]
    cli_text = median_wall(cli, env, args.runs)
    with tempfile.NamedTemporaryFile("w", dir=ROOT, suffix=".bench.md", delete=False) as handle:
        handle.write(existing_text)
        existing_path = handle.name
    try:
        cli_existing = median_wall([*cli, "--existing-file", existing_path], env, args.runs)
    finally:
        os.unlink(existing_path)

    start = time.perf_counter()
    gate_corpus = QualityGate(existing_content=existing_text)
    build_s = time.perf_counter() - start

    report = {
        "python": sys.version.split()[0],
        "src": src,
        "runs": args.runs,
        "existing_lines": len(existing),
        "existing_bytes": len(existing_text.encode()),
        "candidates": len(candidates),
        "bare_python_ms": round(bare * 1000, 2),
        "import_ms": round((imp - bare) * 1000, 2),
        "cli_check_text_ms": round(cli_text * 1000, 2),
        "cli_check_existing_ms": round(cli_existing * 1000, 2),
        "gate_build_with_corpus_ms": round(build_s * 1000, 2),
        "throughput_no_corpus_per_s": round(throughput(QualityGate(), candidates, 5)),
        "throughput_with_corpus_per_s": round(throughput(gate_corpus, candidates[:400], 3)),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
