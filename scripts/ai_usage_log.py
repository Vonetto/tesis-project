from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "docs" / "ai_usage" / "prompt_history.sqlite3"
DEFAULT_JSONL_PATH = PROJECT_ROOT / "docs" / "ai_usage" / "prompt_history.jsonl"
SCHEMA_VERSION = "1"

CATEGORIES = (
    "architecture",
    "data-methodology",
    "analysis-audit",
    "modeling",
    "implementation",
    "debugging",
    "planning-decision",
    "workflow-governance",
    "documentation",
    "other-structural",
)

RESULT_STATUSES = ("planned", "completed", "partial", "blocked")
SOURCES = ("codex", "claude", "chatgpt", "other")

JSON_COLUMNS = ("input_refs_json", "artifacts_json", "tools_json", "tags_json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_required(value: str | None, field: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"`{field}` no puede estar vacío.")
    return normalized


def read_prompt(prompt: str | None, prompt_file: str | None) -> str:
    if prompt is not None:
        return normalize_required(prompt, "prompt")
    if prompt_file == "-":
        return normalize_required(sys.stdin.read(), "prompt")
    if prompt_file:
        return normalize_required(Path(prompt_file).read_text(encoding="utf-8"), "prompt")
    raise ValueError("Se requiere `--prompt` o `--prompt-file`.")


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = DELETE")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prompt_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_uuid TEXT NOT NULL UNIQUE,
            recorded_at_utc TEXT NOT NULL,
            project TEXT NOT NULL,
            session_id TEXT,
            source TEXT NOT NULL,
            model TEXT,
            prompt_text TEXT NOT NULL,
            prompt_summary TEXT NOT NULL,
            category TEXT NOT NULL,
            relevance_reason TEXT NOT NULL,
            requested_outcome TEXT NOT NULL,
            ai_use_summary TEXT NOT NULL,
            result_status TEXT NOT NULL,
            input_refs_json TEXT NOT NULL DEFAULT '[]',
            artifacts_json TEXT NOT NULL DEFAULT '[]',
            tools_json TEXT NOT NULL DEFAULT '[]',
            tags_json TEXT NOT NULL DEFAULT '[]',
            notes TEXT,
            prompt_sha256 TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_prompt_events_recorded_at
            ON prompt_events(recorded_at_utc);
        CREATE INDEX IF NOT EXISTS idx_prompt_events_category
            ON prompt_events(category);
        CREATE INDEX IF NOT EXISTS idx_prompt_events_prompt_sha256
            ON prompt_events(prompt_sha256);
        """
    )
    connection.execute(
        """
        INSERT INTO metadata(key, value)
        VALUES ('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (SCHEMA_VERSION,),
    )
    connection.commit()


def decode_row(row: sqlite3.Row) -> dict[str, Any]:
    decoded = dict(row)
    for column in JSON_COLUMNS:
        decoded[column.removesuffix("_json")] = json.loads(decoded.pop(column))
    return decoded


def fetch_all(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM prompt_events ORDER BY recorded_at_utc, id"
    ).fetchall()
    return [decode_row(row) for row in rows]


def sync_jsonl(connection: sqlite3.Connection, jsonl_path: Path) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as output:
        for row in fetch_all(connection):
            output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(temporary_path, jsonl_path)


def record_event(
    connection: sqlite3.Connection,
    *,
    project: str,
    session_id: str | None,
    source: str,
    model: str | None,
    prompt_text: str,
    prompt_summary: str,
    category: str,
    relevance_reason: str,
    requested_outcome: str,
    ai_use_summary: str,
    result_status: str,
    input_refs: Iterable[str],
    artifacts: Iterable[str],
    tools: Iterable[str],
    tags: Iterable[str],
    notes: str | None,
) -> int:
    prompt_text = normalize_required(prompt_text, "prompt_text")
    values = {
        "event_uuid": str(uuid.uuid4()),
        "recorded_at_utc": utc_now(),
        "project": normalize_required(project, "project"),
        "session_id": session_id.strip() if session_id else None,
        "source": source,
        "model": model.strip() if model else None,
        "prompt_text": prompt_text,
        "prompt_summary": normalize_required(prompt_summary, "prompt_summary"),
        "category": category,
        "relevance_reason": normalize_required(relevance_reason, "relevance_reason"),
        "requested_outcome": normalize_required(requested_outcome, "requested_outcome"),
        "ai_use_summary": normalize_required(ai_use_summary, "ai_use_summary"),
        "result_status": result_status,
        "input_refs_json": json.dumps(list(input_refs), ensure_ascii=False),
        "artifacts_json": json.dumps(list(artifacts), ensure_ascii=False),
        "tools_json": json.dumps(list(tools), ensure_ascii=False),
        "tags_json": json.dumps(list(tags), ensure_ascii=False),
        "notes": notes.strip() if notes else None,
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
    }
    columns = ", ".join(values)
    placeholders = ", ".join(f":{column}" for column in values)
    cursor = connection.execute(
        f"INSERT INTO prompt_events ({columns}) VALUES ({placeholders})",
        values,
    )
    connection.commit()
    return int(cursor.lastrowid)


def print_list(connection: sqlite3.Connection, limit: int, category: str | None) -> None:
    query = """
        SELECT id, recorded_at_utc, category, result_status, prompt_summary
        FROM prompt_events
    """
    params: list[Any] = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY recorded_at_utc DESC, id DESC LIMIT ?"
    params.append(limit)
    rows = connection.execute(query, params).fetchall()
    if not rows:
        print("Sin prompts registrados.")
        return
    for row in rows:
        print(
            f"{row['id']:>4}  {row['recorded_at_utc']}  "
            f"{row['category']:<20}  {row['result_status']:<9}  "
            f"{row['prompt_summary']}"
        )


def markdown_export(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Historial de prompts relevantes",
        "",
        f"Generado: {utc_now()}",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['id']}. {row['prompt_summary']}",
                "",
                f"- Fecha UTC: `{row['recorded_at_utc']}`",
                f"- Categoría: `{row['category']}`",
                f"- Estado: `{row['result_status']}`",
                f"- Fuente: `{row['source']}`",
                f"- Razón: {row['relevance_reason']}",
                f"- Resultado solicitado: {row['requested_outcome']}",
                "",
                "**Prompt**",
                "",
                row["prompt_text"],
                "",
                "**Uso de IA**",
                "",
                row["ai_use_summary"],
                "",
            ]
        )
        for label, key in (
            ("Entradas", "input_refs"),
            ("Artefactos", "artifacts"),
            ("Herramientas", "tools"),
            ("Tags", "tags"),
        ):
            if row[key]:
                lines.append(f"- {label}: " + ", ".join(f"`{item}`" for item in row[key]))
        if row["notes"]:
            lines.append(f"- Notas: {row['notes']}")
        lines.append("")
    return "\n".join(lines)


def export_rows(
    connection: sqlite3.Connection,
    output_path: Path,
    export_format: str,
) -> None:
    rows = fetch_all(connection)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "jsonl":
        with output_path.open("w", encoding="utf-8") as output:
            for row in rows:
                output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return
    if export_format == "markdown":
        output_path.write_text(markdown_export(rows), encoding="utf-8")
        return
    if export_format == "csv":
        fieldnames = list(rows[0]) if rows else [
            "id",
            "event_uuid",
            "recorded_at_utc",
            "project",
            "prompt_text",
            "prompt_summary",
            "category",
            "relevance_reason",
            "requested_outcome",
            "ai_use_summary",
            "result_status",
        ]
        with output_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        key: json.dumps(value, ensure_ascii=False)
                        if isinstance(value, list)
                        else value
                        for key, value in row.items()
                    }
                )
        return
    raise ValueError(f"Formato no soportado: {export_format}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Registro auditable de prompts relevantes.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Inicializa la base y sincroniza JSONL.")

    record_parser = subparsers.add_parser("record", help="Registra un prompt relevante.")
    prompt_group = record_parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    record_parser.add_argument("--summary", required=True)
    record_parser.add_argument("--category", choices=CATEGORIES, required=True)
    record_parser.add_argument("--relevance-reason", required=True)
    record_parser.add_argument("--requested-outcome", required=True)
    record_parser.add_argument("--ai-use-summary", required=True)
    record_parser.add_argument("--status", choices=RESULT_STATUSES, default="completed")
    record_parser.add_argument("--project", default=PROJECT_ROOT.name)
    record_parser.add_argument("--session-id")
    record_parser.add_argument("--source", choices=SOURCES, default="codex")
    record_parser.add_argument("--model")
    record_parser.add_argument("--input-ref", action="append", default=[])
    record_parser.add_argument("--artifact", action="append", default=[])
    record_parser.add_argument("--tool", action="append", default=[])
    record_parser.add_argument("--tag", action="append", default=[])
    record_parser.add_argument("--notes")

    list_parser = subparsers.add_parser("list", help="Lista registros recientes.")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--category", choices=CATEGORIES)

    show_parser = subparsers.add_parser("show", help="Muestra una entrada completa.")
    show_parser.add_argument("id", type=int)

    subparsers.add_parser("stats", help="Resume conteos por categoría y estado.")

    export_parser = subparsers.add_parser("export", help="Exporta el historial.")
    export_parser.add_argument("--format", choices=("jsonl", "csv", "markdown"), required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    connection = connect(args.db)
    try:
        initialize_database(connection)
        if args.command == "init":
            sync_jsonl(connection, args.jsonl)
            print(f"Base inicializada: {args.db}")
            print(f"JSONL sincronizado: {args.jsonl}")
        elif args.command == "record":
            event_id = record_event(
                connection,
                project=args.project,
                session_id=args.session_id,
                source=args.source,
                model=args.model,
                prompt_text=read_prompt(args.prompt, args.prompt_file),
                prompt_summary=args.summary,
                category=args.category,
                relevance_reason=args.relevance_reason,
                requested_outcome=args.requested_outcome,
                ai_use_summary=args.ai_use_summary,
                result_status=args.status,
                input_refs=args.input_ref,
                artifacts=args.artifact,
                tools=args.tool,
                tags=args.tag,
                notes=args.notes,
            )
            sync_jsonl(connection, args.jsonl)
            print(f"Prompt registrado con id={event_id}")
        elif args.command == "list":
            print_list(connection, max(args.limit, 1), args.category)
        elif args.command == "show":
            row = connection.execute(
                "SELECT * FROM prompt_events WHERE id = ?", (args.id,)
            ).fetchone()
            if row is None:
                raise SystemExit(f"No existe el registro id={args.id}.")
            print(json.dumps(decode_row(row), ensure_ascii=False, indent=2, sort_keys=True))
        elif args.command == "stats":
            total = connection.execute("SELECT COUNT(*) FROM prompt_events").fetchone()[0]
            print(f"Total: {total}")
            for row in connection.execute(
                """
                SELECT category, result_status, COUNT(*) AS n
                FROM prompt_events
                GROUP BY category, result_status
                ORDER BY category, result_status
                """
            ):
                print(f"{row['category']:<20} {row['result_status']:<9} {row['n']}")
        elif args.command == "export":
            export_rows(connection, args.output, args.format)
            print(f"Exportación escrita: {args.output}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
