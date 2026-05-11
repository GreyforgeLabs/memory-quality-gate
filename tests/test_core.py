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
