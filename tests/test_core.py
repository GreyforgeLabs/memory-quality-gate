from memory_quality_gate import MemoryCandidate, QualityGate


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
