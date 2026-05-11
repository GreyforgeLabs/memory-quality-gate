"""Public package surface for memory-quality-gate."""

from .core import (
    DEFAULT_MAX_CANDIDATE_CHARS,
    DEFAULT_MAX_EXISTING_CHARS,
    DEFAULT_MAX_EXISTING_SEGMENTS,
    DEFAULT_MAX_PHRASE_PROBES,
    DEFAULT_SCOPE_THRESHOLDS,
    DEFAULT_WEIGHTS,
    ENTRY_TYPES,
    SCOPES,
    SCORE_NAMES,
    MemoryCandidate,
    QualityGate,
    QualityResult,
)

__all__ = [
    "DEFAULT_MAX_CANDIDATE_CHARS",
    "DEFAULT_MAX_EXISTING_CHARS",
    "DEFAULT_MAX_EXISTING_SEGMENTS",
    "DEFAULT_MAX_PHRASE_PROBES",
    "DEFAULT_SCOPE_THRESHOLDS",
    "DEFAULT_WEIGHTS",
    "ENTRY_TYPES",
    "MemoryCandidate",
    "QualityGate",
    "QualityResult",
    "SCOPES",
    "SCORE_NAMES",
]
