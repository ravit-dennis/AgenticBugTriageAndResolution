from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agentic_triage.models import AgentRunState


class SQLiteRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    issue_number INTEGER NOT NULL,
                    commit_sha TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    symptoms TEXT NOT NULL,
                    root_cause TEXT NOT NULL,
                    files_json TEXT NOT NULL,
                    fix_pattern TEXT NOT NULL,
                    tests_json TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS memory_search USING fts5(
                    symptoms,
                    root_cause,
                    fix_pattern,
                    content='memories',
                    content_rowid='id'
                );

                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memory_search(rowid, symptoms, root_cause, fix_pattern)
                    VALUES (new.id, new.symptoms, new.root_cause, new.fix_pattern);
                END;

                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memory_search(
                        memory_search, rowid, symptoms, root_cause, fix_pattern
                    )
                    VALUES (
                        'delete', old.id, old.symptoms, old.root_cause,
                        old.fix_pattern
                    );
                    INSERT INTO memory_search(rowid, symptoms, root_cause, fix_pattern)
                    VALUES (new.id, new.symptoms, new.root_cause, new.fix_pattern);
                END;
                """
            )

    def save_run(self, state: AgentRunState) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    run_id, issue_number, commit_sha, stage, state_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    stage = excluded.stage,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state.run_id,
                    state.issue.number,
                    state.commit_sha,
                    state.stage.value,
                    state.model_dump_json(),
                    state.updated_at.isoformat(),
                ),
            )

    def load_run(self, run_id: str) -> AgentRunState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentRunState.model_validate_json(row["state_json"])

    def record_memory(
        self,
        state: AgentRunState,
        *,
        symptoms: str,
        fix_pattern: str,
        tests: list[str],
        outcome: str,
    ) -> int:
        if state.diagnosis is None:
            raise ValueError("Cannot record memory without a diagnosis")

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT id FROM memories WHERE run_id = ?",
                (state.run_id,),
            ).fetchone()
            if existing is not None:
                connection.execute(
                    """
                    UPDATE memories SET
                        commit_sha = ?,
                        symptoms = ?,
                        root_cause = ?,
                        files_json = ?,
                        fix_pattern = ?,
                        tests_json = ?,
                        outcome = ?,
                        created_at = ?
                    WHERE id = ?
                    """,
                    (
                        state.commit_sha,
                        symptoms,
                        state.diagnosis.root_cause,
                        json.dumps(state.diagnosis.supporting_files),
                        fix_pattern,
                        json.dumps(tests),
                        outcome,
                        state.updated_at.isoformat(),
                        int(existing["id"]),
                    ),
                )
                return int(existing["id"])
            cursor = connection.execute(
                """
                INSERT INTO memories (
                    run_id, commit_sha, symptoms, root_cause, files_json,
                    fix_pattern, tests_json, outcome, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.run_id,
                    state.commit_sha,
                    symptoms,
                    state.diagnosis.root_cause,
                    json.dumps(state.diagnosis.supporting_files),
                    fix_pattern,
                    json.dumps(tests),
                    outcome,
                    state.updated_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def search_memories(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT memories.id, memories.run_id, memories.commit_sha,
                       memories.symptoms, memories.root_cause,
                       memories.fix_pattern, memories.outcome
                FROM memory_search
                JOIN memories ON memories.id = memory_search.rowid
                WHERE memory_search MATCH ?
                ORDER BY bm25(memory_search)
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [dict(row) for row in rows]
