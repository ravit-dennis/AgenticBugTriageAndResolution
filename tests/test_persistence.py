from agentic_triage.models import Diagnosis, Risk, Severity, Stage
from agentic_triage.persistence import SQLiteRepository


def test_run_round_trips_through_sqlite(tmp_path, run_state) -> None:
    repository = SQLiteRepository(tmp_path / "agent.db")
    run_state.transition(Stage.REPRODUCE, "Reproducing")

    repository.save_run(run_state)
    loaded = repository.load_run(run_state.run_id)

    assert loaded is not None
    assert loaded.stage is Stage.REPRODUCE
    assert loaded.messages == ["Reproducing"]


def test_memory_is_searchable(tmp_path, run_state) -> None:
    repository = SQLiteRepository(tmp_path / "agent.db")
    run_state.diagnosis = Diagnosis(
        root_cause="Article tag filter used the author field",
        supporting_files=["backend/controllers/articles.js"],
        severity=Severity.MEDIUM,
        risk=Risk.LOW,
        confidence=0.95,
    )

    memory_id = repository.record_memory(
        run_state,
        symptoms="Filtering articles by tag returns unrelated records",
        fix_pattern="Use the tag association in the query predicate",
        tests=["articles filtering regression"],
        outcome="validated_pr",
    )
    results = repository.search_memories("tag filter")

    assert memory_id > 0
    assert len(results) == 1
    assert results[0]["root_cause"] == run_state.diagnosis.root_cause
