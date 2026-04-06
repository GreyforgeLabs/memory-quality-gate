# Scoring Model

`memory-quality-gate` scores each candidate across five dimensions, then applies a scope-aware threshold.

## Dimensions

| Dimension | Weight | What It Rewards |
|---|---:|---|
| Actionability | 30% | Rules, decisions, procedures, or explicit next-step value |
| Specificity | 25% | Concrete details such as dates, file paths, versions, identifiers, or URLs |
| Novelty | 20% | New information relative to an optional existing memory corpus |
| Reasoning | 15% | Causal explanation: why something matters, not just what happened |
| Outcome linkage | 10% | Evidence that the statement ties to an observed result |

## Default thresholds

| Scope | Threshold | Why |
|---|---:|---|
| `global` | `0.45` | Reusable cross-project rules are worth storing even when concise |
| `project` | `0.55` | Project memory should be concrete and useful on retrieval |
| `session` | `0.70` | Session memory is the easiest place for noise to accumulate |

## Technical-fact shortcut

Highly specific `global` and `project` entries get a small threshold reduction. The intent is simple: an operational fact with a file path, version, date, or identifier can still be worth keeping even when it is not written as a full decision memo.

## Novelty check

Novelty is intentionally cheap:

1. Normalize the candidate into lowercase tokens.
2. Compare token overlap against lines and paragraphs from the existing corpus.
3. Penalize heavy overlap and repeated five-word phrases.

No embedding model or LLM call is required.
