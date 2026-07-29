from __future__ import annotations

import json
import sqlite3

from scripts.ai_usage_log import (
    export_rows,
    initialize_database,
    record_event,
    sync_jsonl,
)


def test_record_and_sync_jsonl(tmp_path):
    db_path = tmp_path / "history.sqlite3"
    jsonl_path = tmp_path / "history.jsonl"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)

    event_id = record_event(
        connection,
        project="tesis-project",
        session_id="thread-1",
        source="codex",
        model=None,
        prompt_text="Construir una auditoría reproducible.",
        prompt_summary="Construir auditoría",
        category="analysis-audit",
        relevance_reason="Define una tarea metodológica.",
        requested_outcome="Auditoría documentada.",
        ai_use_summary="La IA implementó y verificó la auditoría.",
        result_status="completed",
        input_refs=["input.parquet"],
        artifacts=["audit.py"],
        tools=["apply_patch"],
        tags=["audit"],
        notes=None,
    )
    sync_jsonl(connection, jsonl_path)

    assert event_id == 1
    rows = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    payload = json.loads(rows[0])
    assert payload["prompt_text"] == "Construir una auditoría reproducible."
    assert payload["input_refs"] == ["input.parquet"]
    assert payload["artifacts"] == ["audit.py"]


def test_markdown_export_contains_prompt_and_ai_use(tmp_path):
    db_path = tmp_path / "history.sqlite3"
    output_path = tmp_path / "history.md"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    record_event(
        connection,
        project="tesis-project",
        session_id=None,
        source="codex",
        model=None,
        prompt_text="Definir una regla de modelamiento.",
        prompt_summary="Regla de modelamiento",
        category="modeling",
        relevance_reason="Cambia el criterio del modelo.",
        requested_outcome="Regla explícita.",
        ai_use_summary="La IA documentó la decisión.",
        result_status="completed",
        input_refs=[],
        artifacts=["notes.md"],
        tools=[],
        tags=["model"],
        notes="Sin datos sensibles.",
    )

    export_rows(connection, output_path, "markdown")
    content = output_path.read_text(encoding="utf-8")
    assert "Definir una regla de modelamiento." in content
    assert "La IA documentó la decisión." in content
    assert "`notes.md`" in content
