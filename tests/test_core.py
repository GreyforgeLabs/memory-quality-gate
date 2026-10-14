import pytest

from memory_quality_gate import DEFAULT_WEIGHTS, MemoryCandidate, QualityGate


def test_detailed_project_memory_passes() -> None:
    gate = QualityGate()
    result = gate.evaluate(
        MemoryCandidate(
            text=(
                "Always check docs/scoring-model.md before changing thresholds because "
                "the retrieval workers rely on the 2026-04-06 scoring contract."
            ),
            scope="project",
            entry_type="decision",
        )
    )

    assert result.passed is True
    assert result.weighted_score >= result.threshold
    assert result.scores["actionability"] >= 0.5
    assert result.scores["specificity"] >= 0.45


def test_conversational_noise_is_rejected() -> None:
    gate = QualityGate()
    result = gate.evaluate(MemoryCandidate(text="ok"))

    assert result.passed is False
    assert result.rejection_reason.startswith("Hard veto")


def test_duplicate_content_drops_novelty() -> None:
    existing = (
        "Always check docs/scoring-model.md before changing thresholds because "
        "retrieval workers rely on the current scoring contract."
    )
    gate = QualityGate(existing_content=existing)
    result = gate.evaluate(
        MemoryCandidate(
            text=(
                "Always check docs/scoring-model.md before changing thresholds because "
                "retrieval workers rely on the current scoring contract."
            )
        )
    )

    assert result.scores["novelty"] <= 0.2
    assert result.passed is False


def test_completed_entries_get_outcome_bonus() -> None:
    gate = QualityGate()
    general = gate.evaluate(
        MemoryCandidate(
            text="Release note deployed to docs/releases/2026-04-06.md.",
            entry_type="general",
        )
    )
    completed = gate.evaluate(
        MemoryCandidate(
            text="Release note deployed to docs/releases/2026-04-06.md.",
            entry_type="completed",
        )
    )

    assert completed.scores["outcome_linkage"] > general.scores["outcome_linkage"]


def test_session_scope_is_stricter() -> None:
    gate = QualityGate()
    text = (
        "Always run ./scripts/deploy.sh --dry-run before shipping v2.4.1 because "
        "it prevents partial deploys."
    )

    project = gate.evaluate(MemoryCandidate(text=text, scope="project"))
    session = gate.evaluate(MemoryCandidate(text=text, scope="session"))

    assert project.passed is True
    assert session.passed is False


def test_invalid_candidate_scope_is_rejected() -> None:
    with pytest.raises(ValueError, match="scope"):
        MemoryCandidate(text="Always check docs/scoring-model.md.", scope="tenant")


def test_oversized_candidate_is_rejected() -> None:
    gate = QualityGate(max_candidate_chars=20)

    with pytest.raises(ValueError, match="candidate.text exceeds"):
        gate.evaluate_text("x" * 21)


def test_oversized_existing_content_is_rejected() -> None:
    with pytest.raises(ValueError, match="existing_content exceeds"):
        QualityGate(existing_content="x" * 21, max_existing_chars=20)


def test_malformed_weights_are_rejected() -> None:
    weights = dict(DEFAULT_WEIGHTS)
    weights["actionability"] = 0.99

    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        QualityGate(weights=weights)


def test_empty_custom_weights_are_rejected() -> None:
    with pytest.raises(ValueError, match="weights must define exactly"):
        QualityGate(weights={})


def test_empty_custom_thresholds_are_rejected() -> None:
    with pytest.raises(ValueError, match="thresholds must define exactly"):
        QualityGate(thresholds={})


def test_json_dict_can_redact_candidate_text() -> None:
    result = QualityGate().evaluate_text(
        "Always check docs/scoring-model.md because retrieval workers depend on it."
    )

    payload = result.to_dict(redact_candidate_text=True)

    assert payload["candidate"]["text"] == "[redacted]"


def test_percentages_and_delimited_paths_count_as_specific() -> None:
    gate = QualityGate()

    def specificity(text: str) -> float:
        return gate.evaluate_text(text).scores["specificity"]

    assert specificity("Latency fell by 50% after the cache warmup landed.") == 0.25
    assert specificity("The retrieval contract lives in docs/scoring-model.md.") == 0.25
    assert specificity("Keep the worker settings in `config.toml` for now.") == 0.25
    assert specificity('The resolver reads "/etc/hosts" before DNS.') == 0.25
    assert specificity("Compare notes across a.md b.md c.md today.") == 0.75


def test_reason_and_why_labels_count_as_reasoning() -> None:
    gate = QualityGate()

    assert (
        gate.evaluate_text("Pinned the worker image. Reason: cold caches").scores["reasoning"]
        == 0.6
    )
    assert (
        gate.evaluate_text("Pinned the worker image. Why: cold caches").scores["reasoning"] == 0.6
    )


def test_exact_threshold_boundary_passes_without_float_noise() -> None:
    # 0.03 + 0.15 + 0.06 + 0.09 + 0.07 is exactly 0.40, the effective global bar;
    # naive float summation produced 0.39999999999999997 and rejected it.
    gate = QualityGate(existing_content="worker. shard every lists nightly rebuilt layer cache")
    result = gate.evaluate_text(
        "Release cache layer v1.2.3 rebuilt nightly because docs/cache-notes.md lists "
        "every shard worker.",
        scope="global",
        entry_type="completed",
    )

    assert result.scores == {
        "actionability": 0.1,
        "specificity": 0.6,
        "novelty": 0.3,
        "reasoning": 0.6,
        "outcome_linkage": 0.7,
    }
    assert result.weighted_score == 0.4
    assert result.threshold == 0.4
    assert result.passed is True


def test_specificity_shortcut_never_raises_a_custom_threshold() -> None:
    gate = QualityGate(thresholds={"global": 0.30, "project": 0.55, "session": 0.70})
    result = gate.evaluate_text("Pin v1.2.3 in src/app.py and docs/x.md here", scope="global")

    assert result.scores["specificity"] >= 0.45
    assert result.threshold == 0.30
    assert (
        QualityGate().evaluate_text("Pin v1.2.3 in src/app.py and docs/x.md here").threshold == 0.48
    )


def test_scores_are_clean_decimals() -> None:
    result = QualityGate().evaluate_text(
        "Always run ./scripts/deploy.sh --dry-run before shipping v2.4.1 because "
        "it prevents partial deploys."
    )

    assert result.to_dict()["scores"]["actionability"] == 0.8
    assert all(score == round(score, 2) for score in result.scores.values())


def test_to_dict_returns_independent_scores() -> None:
    result = QualityGate().evaluate_text("Always check docs/scoring-model.md before release.")
    payload = result.to_dict()
    payload["scores"]["novelty"] = -1.0

    assert result.scores["novelty"] == 0.8


def test_non_ascii_duplicates_are_detected() -> None:
    memory = "日本語のメモはここにあります。設定ファイルを確認してください。"
    accented = "Vérifier la clé de déploiement après chaque mise à jour du schéma."

    assert QualityGate(existing_content=memory).evaluate_text(memory).scores["novelty"] == 0.1
    assert QualityGate(existing_content=accented).evaluate_text(accented).scores["novelty"] == 0.1


def test_batch_novelty_matches_one_shot_novelty() -> None:
    existing = "\n".join(
        [
            "Always check docs/scoring-model.md before changing thresholds.",
            "Retry workers back off for 30 seconds because the queue throttles bursts.",
            "Deploy previews run on port 8443 while the staging cache warms up.",
            "Snapshot fixtures rotate after every schema migration in src/db/schema.py.",
        ]
    )
    candidates = [
        "Always check docs/scoring-model.md before changing thresholds.",
        "Retry workers back off for 30 seconds because the queue throttles.",
        "The queue throttles bursts so retry workers back off for a while now.",
        "Deploy previews run on port 8443 while staging warms up the cache today.",
        "Rotate snapshot fixtures after schema changes in src/db/schema.py always.",
        "Completely unrelated note about lunch plans and coffee machines downstairs.",
    ]
    batch_gate = QualityGate(existing_content=existing)
    batch = [
        r.scores["novelty"]
        for r in batch_gate.evaluate_many([MemoryCandidate(text=text) for text in candidates])
    ]
    one_shot = [
        QualityGate(existing_content=existing).evaluate_text(text).scores["novelty"]
        for text in candidates
    ]

    assert batch_gate._token_index is not None
    assert batch == one_shot
    assert len(set(batch)) >= 4


def test_scope_and_entry_type_aliases_stay_importable() -> None:
    import typing

    from memory_quality_gate import ENTRY_TYPES, SCOPES
    from memory_quality_gate.core import EntryType, Scope

    assert typing.get_args(Scope) == SCOPES
    assert typing.get_args(EntryType) == ENTRY_TYPES


def test_non_string_threshold_keys_raise_value_error() -> None:
    thresholds = {"global": 0.45, "project": 0.55, "session": 0.70, 1: 0.5}

    with pytest.raises(ValueError, match="unknown 1"):
        QualityGate(thresholds=thresholds)
