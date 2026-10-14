# Scoring Model

`memory-quality-gate` scores each candidate across five dimensions, then applies a scope-aware threshold.

## Dimensions

| Dimension | Weight | What It Rewards |
|---|---:|---|
| Actionability | 30% | Rules, decisions, procedures, or explicit next-step value |
| Specificity | 25% | Concrete details such as dates, percentages, file paths, versions, identifiers, or URLs |
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

Highly specific `global` and `project` entries (specificity of at least 0.45) get a threshold reduction of 0.07, floored at 0.40; the shortcut never raises a custom threshold that is already below 0.40. The intent is simple: an operational fact with a file path, version, date, or identifier can still be worth keeping even when it is not written as a full decision memo.

## Novelty check

Novelty is intentionally cheap:

1. Normalize the candidate into lowercase word tokens (Unicode letters and digits plus `_./:-`, three or more characters, minus a short stopword list).
2. Compare token overlap against each non-empty line of the existing corpus (up to `max_existing_segments` lines).
3. Penalize heavy overlap and repeated five-word phrases (up to `max_phrase_probes` probes).

No embedding model or LLM call is required. A long-lived `QualityGate` builds an inverted token index and a compact word-trigram filter on its second novelty lookup; both are exact accelerators, so batch and one-shot scoring return the same scores.

## Score precision

Component scores are multiples of 0.05 and the weighted score is rounded to ten decimal places before the threshold comparison, so a candidate that lands exactly on its threshold passes.
