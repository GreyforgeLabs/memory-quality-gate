"""Heuristic memory-quality scoring with no model calls."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from itertools import islice
from math import isfinite

# ``typing`` costs a few milliseconds to import, so the Literal aliases are only
# built for type checkers and, lazily, for runtime access via ``__getattr__``.
TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Literal

    Scope = Literal["global", "project", "session"]
    EntryType = Literal["general", "decision", "lesson", "completed", "product_update"]

SCOPES: tuple[Scope, ...] = ("global", "project", "session")
ENTRY_TYPES: tuple[EntryType, ...] = (
    "general",
    "decision",
    "lesson",
    "completed",
    "product_update",
)
SCORE_NAMES = (
    "actionability",
    "specificity",
    "novelty",
    "reasoning",
    "outcome_linkage",
)

DEFAULT_MAX_CANDIDATE_CHARS = 1_000_000
DEFAULT_MAX_EXISTING_CHARS = 5_000_000
DEFAULT_MAX_EXISTING_SEGMENTS = 20_000
DEFAULT_MAX_PHRASE_PROBES = 5_000

DEFAULT_WEIGHTS = {
    "actionability": 0.30,
    "specificity": 0.25,
    "novelty": 0.20,
    "reasoning": 0.15,
    "outcome_linkage": 0.10,
}

DEFAULT_SCOPE_THRESHOLDS: dict[Scope, float] = {
    "global": 0.45,
    "project": 0.55,
    "session": 0.70,
}

_STOPWORDS = frozenset(
    "a an and are as at be by for from in is it of on or that the this to was were with".split()
)

_ACTIONABLE_PATTERNS = re.compile(
    r"\b(always|avoid|check|confirm|do not|don't|ensure|fix|if .{0,40} then|"
    r"must|never|next step|policy|prefer|procedure|read|recommended|require|"
    r"rule|run|should|step|use|verify|write|workaround)\b",
    re.IGNORECASE,
)

_SPECIFIC_PATTERNS = re.compile(
    r"(\$\d[\d,.]*|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,3}%|\bport \d+\b|"
    r"\b(issue|pr) #?\d+\b|\bcommit [a-f0-9]{7,40}\b|"
    r"\bv?\d+\.\d+(?:\.\d+)?\b|"
    r"\b[A-Z_]{2,}=\S+\b|"
    r"https?://\S+|"
    r"(?<![\w./-])[\w./-]+\.(?:md|txt|py|json|yaml|yml|toml|ini|cfg|sh|sql|ts|tsx|js)(?![\w/-])|"
    r"(?<![\w./-])\.{0,2}/[\w./-]+)",
    re.IGNORECASE,
)

_REASONING_PATTERNS = re.compile(
    r"\b(?:(?:because|caused by|ensures?|means?|prevents?|results? in|"
    r"since|so that|therefore|this allows?|this avoids?|this fixes?|"
    r"to avoid|to ensure|to prevent)\b|(?:reason|why):)",
    re.IGNORECASE,
)

_OUTCOME_PATTERNS = re.compile(
    r"\b(confirmed|deployed|discovered|eliminated|failed|fixed|found|"
    r"improved|landed|live|merged|passed|reduced|resolved|running|shipped|"
    r"validated|verified|worked)\b",
    re.IGNORECASE,
)

_VETO_PATTERNS = re.compile(
    r"^(ack|done|got it|looks good|no|noted|ok|okay|sure|thanks|understood|yes)\.?$",
    re.IGNORECASE,
)

# Runs of 3+ token characters; shorter runs are never tokens, so they are skipped
# by the regex instead of being filtered in Python.
_TOKEN_PATTERN = re.compile(r"[\w./:-]{3,}")

# Every component score is a multiple of 0.05 and every weighted sum is compared
# against a threshold with at most a few decimals, so rounding removes binary
# floating-point noise (e.g. 0.39999999999999997 failing a 0.40 bar).
_SCORE_DIGITS = 10
_MATCH_CAP = 5


def __getattr__(name: str) -> object:
    """Build the ``Scope``/``EntryType`` Literal aliases on first runtime access."""
    if name in ("Scope", "EntryType"):
        from typing import Literal

        globals()["Scope"] = Literal[SCOPES]
        globals()["EntryType"] = Literal[ENTRY_TYPES]
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(slots=True, frozen=True)
class MemoryCandidate:
    """A single memory candidate to score."""

    text: str
    scope: Scope = "project"
    entry_type: EntryType = "general"

    def __post_init__(self) -> None:
        """Validate direct API inputs that type hints cannot enforce at runtime."""
        if not isinstance(self.text, str):
            raise TypeError("MemoryCandidate.text must be a string")
        if self.scope not in SCOPES:
            raise ValueError(f"MemoryCandidate.scope must be one of: {', '.join(SCOPES)}")
        if self.entry_type not in ENTRY_TYPES:
            raise ValueError(f"MemoryCandidate.entry_type must be one of: {', '.join(ENTRY_TYPES)}")


@dataclass(slots=True, frozen=True)
class QualityResult:
    """Final scoring result for a candidate."""

    candidate: MemoryCandidate
    scores: dict[str, float]
    weighted_score: float
    threshold: float
    passed: bool
    rejection_reason: str = ""

    def to_dict(self, *, redact_candidate_text: bool = False) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        candidate = self.candidate
        return {
            "candidate": {
                "text": "[redacted]" if redact_candidate_text else candidate.text,
                "scope": candidate.scope,
                "entry_type": candidate.entry_type,
            },
            "scores": dict(self.scores),
            "weighted_score": round(self.weighted_score, 3),
            "threshold": round(self.threshold, 3),
            "passed": self.passed,
            "rejection_reason": self.rejection_reason,
        }


class QualityGate:
    """Evaluate memory candidates against a cheap heuristic quality bar."""

    def __init__(
        self,
        existing_content: str = "",
        thresholds: dict[Scope, float] | None = None,
        weights: dict[str, float] | None = None,
        max_candidate_chars: int | None = DEFAULT_MAX_CANDIDATE_CHARS,
        max_existing_chars: int | None = DEFAULT_MAX_EXISTING_CHARS,
        max_existing_segments: int = DEFAULT_MAX_EXISTING_SEGMENTS,
        max_phrase_probes: int = DEFAULT_MAX_PHRASE_PROBES,
    ) -> None:
        if not isinstance(existing_content, str):
            raise TypeError("existing_content must be a string")
        self.max_candidate_chars = _validate_optional_positive_int(
            max_candidate_chars, "max_candidate_chars"
        )
        self.max_existing_chars = _validate_optional_positive_int(
            max_existing_chars, "max_existing_chars"
        )
        self.max_existing_segments = _validate_positive_int(
            max_existing_segments, "max_existing_segments"
        )
        self.max_phrase_probes = _validate_positive_int(max_phrase_probes, "max_phrase_probes")
        _validate_text_size(
            existing_content,
            "existing_content",
            self.max_existing_chars,
        )

        self.existing_content = existing_content
        self.thresholds = _validate_thresholds(
            DEFAULT_SCOPE_THRESHOLDS if thresholds is None else thresholds
        )
        self.weights = _validate_weights(DEFAULT_WEIGHTS if weights is None else weights)
        self._existing_segments = self._prepare_segments(
            existing_content,
            self.max_existing_segments,
        )
        self._haystack = existing_content.lower()
        # Novelty indexes are built on the second novelty lookup, so one-shot callers
        # such as the CLI never pay for them while batch callers amortize them.
        self._novelty_lookups = 0
        self._token_index: dict[str, list[int]] | None = None
        self._trigram_bits: bytearray | None = None
        self._trigram_mask = 0

    def evaluate(self, candidate: MemoryCandidate) -> QualityResult:
        """Score a single candidate."""
        _validate_text_size(candidate.text, "candidate.text", self.max_candidate_chars)
        text = candidate.text.strip()
        threshold = self.thresholds[candidate.scope]

        if _VETO_PATTERNS.match(text) or len(text) < 15:
            return QualityResult(
                candidate=candidate,
                scores={},
                weighted_score=0.0,
                threshold=threshold,
                passed=False,
                rejection_reason="Hard veto: conversational noise or too little content",
            )

        scores = {
            "actionability": self._score_actionability(text),
            "specificity": self._score_specificity(text),
            "novelty": self._score_novelty(text),
            "reasoning": self._score_reasoning(text),
            "outcome_linkage": self._score_outcome_linkage(text, candidate.entry_type),
        }

        weighted_score = round(
            sum(self.weights[name] * score for name, score in scores.items()), _SCORE_DIGITS
        )
        effective_threshold = threshold

        # Highly specific facts are still useful even when they are not framed as rules.
        # The shortcut only ever lowers the bar, never raises a custom threshold below 0.40.
        if scores["specificity"] >= 0.45 and candidate.scope in ("global", "project"):
            effective_threshold = min(threshold, round(max(0.40, threshold - 0.07), _SCORE_DIGITS))

        passed = weighted_score >= effective_threshold
        reason = ""
        if not passed:
            reason = self._rejection_reason(scores)

        return QualityResult(
            candidate=candidate,
            scores=scores,
            weighted_score=weighted_score,
            threshold=effective_threshold,
            passed=passed,
            rejection_reason=reason,
        )

    def evaluate_text(
        self,
        text: str,
        scope: Scope = "project",
        entry_type: EntryType = "general",
    ) -> QualityResult:
        """Convenience wrapper around :meth:`evaluate`."""
        return self.evaluate(MemoryCandidate(text=text, scope=scope, entry_type=entry_type))

    def evaluate_many(self, candidates: list[MemoryCandidate]) -> list[QualityResult]:
        """Score many candidates in order."""
        return [self.evaluate(candidate) for candidate in candidates]

    @staticmethod
    def _prepare_segments(existing_content: str, max_segments: int) -> list[set[str]]:
        segments: list[set[str]] = []
        for raw_segment in existing_content.splitlines():
            tokens = _normalized_tokens(raw_segment)
            if tokens:
                segments.append(tokens)
            if len(segments) >= max_segments:
                break
        return segments

    @staticmethod
    def _score_actionability(text: str) -> float:
        matches = _count_matches(_ACTIONABLE_PATTERNS, text)
        if matches == 0:
            return 0.10
        if matches == 1:
            return 0.50
        if matches == 2:
            return 0.70
        return round(min(1.0, 0.70 + (matches - 2) * 0.10), 2)

    @staticmethod
    def _score_specificity(text: str) -> float:
        matches = _count_matches(_SPECIFIC_PATTERNS, text)
        length_bonus = 0.10 if len(text) > 80 else 0.0
        return round(min(1.0, matches * 0.25 + length_bonus), 2)

    def _score_novelty(self, text: str) -> float:
        if not self._existing_segments:
            return 0.80

        candidate_tokens = _normalized_tokens(text)
        if not candidate_tokens:
            return 0.60

        self._novelty_lookups += 1
        if self._token_index is None and self._novelty_lookups > 1:
            self._build_novelty_index()

        if self._token_index is None:
            shared_max = max(len(candidate_tokens & tokens) for tokens in self._existing_segments)
        else:
            # Count shared tokens per segment through the inverted index; this yields
            # the same best overlap as intersecting the candidate with every segment.
            shared: Counter[int] = Counter()
            for token in candidate_tokens:
                postings = self._token_index.get(token)
                if postings is not None:
                    shared.update(postings)
            shared_max = max(shared.values(), default=0)
        best_overlap = shared_max / len(candidate_tokens)
        if best_overlap >= 0.85:
            return 0.10

        if self._has_phrase_overlap(text):
            return 0.20
        if best_overlap >= 0.65:
            return 0.30
        if best_overlap >= 0.45:
            return 0.55
        return 0.80

    def _build_novelty_index(self) -> None:
        index: dict[str, list[int]] = {}
        for position, tokens in enumerate(self._existing_segments):
            for token in tokens:
                index.setdefault(token, []).append(position)
        # A one-hash bit filter of every in-line word trigram in the corpus, sized at
        # about 16 bits per word (2 MiB for the 5 MB default cap). A false positive
        # only costs the exact substring scan, so results never change.
        mask = (1 << max(16, (2 * len(self._haystack)).bit_length())) - 1
        bits = bytearray((mask >> 3) + 1)
        for line in self._haystack.splitlines():
            words = line.split()
            for trigram in zip(words, words[1:], words[2:], strict=False):
                slot = hash(trigram) & mask
                bits[slot >> 3] |= 1 << (slot & 7)
        self._trigram_bits = bits
        self._trigram_mask = mask
        self._token_index = index

    def _has_phrase_overlap(self, text: str) -> bool:
        haystack = self._haystack
        bits = self._trigram_bits
        mask = self._trigram_mask
        words = text.lower().split()
        phrase_count = min(max(0, len(words) - 4), self.max_phrase_probes)
        for index in range(phrase_count):
            # A probe's three inner words are single-space-delimited on both sides, so
            # they can only occur in the corpus as consecutive words of one line: skip
            # the substring scan when the filter has never seen that trigram.
            if bits is not None:
                slot = hash(tuple(words[index + 1 : index + 4])) & mask
                if not bits[slot >> 3] >> (slot & 7) & 1:
                    continue
            probe = " ".join(words[index : index + 5])
            if len(probe) >= 20 and probe in haystack:
                return True
        return False

    @staticmethod
    def _score_reasoning(text: str) -> float:
        matches = _count_matches(_REASONING_PATTERNS, text)
        if matches == 0:
            return 0.20
        if matches == 1:
            return 0.60
        return round(min(1.0, 0.60 + (matches - 1) * 0.20), 2)

    @staticmethod
    def _score_outcome_linkage(text: str, entry_type: EntryType) -> float:
        matches = _count_matches(_OUTCOME_PATTERNS, text)
        if entry_type in ("completed", "product_update"):
            return round(max(0.70, min(1.0, matches * 0.30 + 0.40)), 2)
        if matches == 0:
            return 0.20
        return round(min(1.0, 0.40 + matches * 0.20), 2)

    @staticmethod
    def _rejection_reason(scores: dict[str, float]) -> str:
        weakest = min(scores, key=scores.get)
        if scores["novelty"] <= 0.30:
            return "Likely duplicate of existing memory"
        if scores["specificity"] <= 0.25:
            return "Too vague to retrieve reliably later"
        if scores["actionability"] <= 0.30:
            return "Low actionability; reads more like a log than a memory"
        if scores["reasoning"] <= 0.20:
            return f"Below threshold; missing enough reasoning detail ({weakest})"
        return f"Below threshold; weakest dimension was {weakest}"


def _count_matches(pattern: re.Pattern[str], text: str) -> int:
    # Every component score saturates by its fifth match, so stop scanning there:
    # long inputs no longer pay for a full findall() per dimension.
    return sum(1 for _ in islice(pattern.finditer(text), _MATCH_CAP))


def _normalized_tokens(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower())).difference(_STOPWORDS)


def _validate_text_size(text: str, label: str, max_chars: int | None) -> None:
    if max_chars is not None and len(text) > max_chars:
        raise ValueError(f"{label} exceeds maximum length of {max_chars} characters")


def _validate_optional_positive_int(value: int | None, label: str) -> int | None:
    if value is None:
        return None
    return _validate_positive_int(value, label)


def _validate_positive_int(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _require_exact_keys(mapping: dict, expected: tuple[str, ...], label: str) -> None:
    missing = [key for key in expected if key not in mapping]
    extra = sorted(str(key) for key in mapping if key not in expected)
    if missing or extra:
        detail = [f"missing {', '.join(missing)}"] if missing else []
        if extra:
            detail.append(f"unknown {', '.join(extra)}")
        raise ValueError(f"{label} must define exactly {', '.join(expected)} ({'; '.join(detail)})")


def _validate_thresholds(thresholds: dict[Scope, float]) -> dict[Scope, float]:
    _require_exact_keys(thresholds, SCOPES, "thresholds")
    validated: dict[Scope, float] = {}
    for scope in SCOPES:
        value = thresholds[scope]
        if not _is_finite_number(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"threshold for {scope} must be a finite number between 0 and 1")
        validated[scope] = float(value)
    return validated


def _validate_weights(weights: dict[str, float]) -> dict[str, float]:
    _require_exact_keys(weights, SCORE_NAMES, "weights")
    validated: dict[str, float] = {}
    for name in SCORE_NAMES:
        value = weights[name]
        if not _is_finite_number(value) or value < 0.0:
            raise ValueError(f"weight for {name} must be a finite non-negative number")
        validated[name] = float(value)

    if abs(sum(validated.values()) - 1.0) > 0.000001:
        raise ValueError("weights must sum to 1.0")
    return validated


def _is_finite_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float) and isfinite(value)
