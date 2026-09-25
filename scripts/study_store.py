"""Local SQLite operations for study subjects, doubts, sessions and checkpoints."""

from contextlib import closing
from datetime import datetime
import os
from pathlib import Path
import sqlite3


DATABASE_PATH = Path(os.environ.get(
    "STUDY_DB_PATH", Path(__file__).resolve().parent.parent / "storage" / "study.db"
))
DOUBT_STATUSES = {"pending", "studying", "resolved", "review"}


class StudyStoreError(Exception):
    """Base error for invalid study data or state transitions."""


class NotFoundError(StudyStoreError):
    """Requested subject, doubt or session does not exist."""


class InvalidStatusError(StudyStoreError):
    """A requested status is not supported."""


def get_connection() -> sqlite3.Connection:
    if not DATABASE_PATH.is_file():
        raise StudyStoreError(
            f"No existe la base de datos: {DATABASE_PATH}. "
            "Ejecuta python3 scripts/init_db.py primero."
        )
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    if "active" in result:
        result["active"] = bool(result["active"])
    return result


def _rows(sql: str, parameters: tuple = ()) -> list[dict]:
    with closing(get_connection()) as connection, connection:
        return [_dict(row) for row in connection.execute(sql, parameters)]


def _one(sql: str, parameters: tuple = ()) -> dict | None:
    with closing(get_connection()) as connection, connection:
        return _dict(connection.execute(sql, parameters).fetchone())


def _write(sql: str, parameters: tuple = ()) -> int:
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(sql, parameters)
        return cursor.lastrowid


def add_subject(name: str, subject_type: str | None = None) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("El nombre de la materia no puede estar vacío.")
    try:
        _write(
            "INSERT INTO subjects (name, type) VALUES (?, ?)",
            (name, subject_type),
        )
    except sqlite3.IntegrityError as error:
        if "subjects.name" in str(error):
            raise StudyStoreError(f"La materia ya existe: {name}") from error
        raise
    return get_subject_by_name(name)


def list_subjects(active_only: bool = True) -> list[dict]:
    where = "WHERE active = 1" if active_only else ""
    return _rows(f"SELECT * FROM subjects {where} ORDER BY name")


def get_subject_by_name(name: str) -> dict | None:
    return _one("SELECT * FROM subjects WHERE name = ?", (name.strip(),))


def set_subject_active(subject_id: int, active: bool) -> dict:
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "UPDATE subjects SET active = ? WHERE id = ?",
            (int(active), subject_id),
        )
        if not cursor.rowcount:
            raise NotFoundError(f"No existe la materia con id {subject_id}.")
        return _dict(connection.execute(
            "SELECT * FROM subjects WHERE id = ?", (subject_id,)
        ).fetchone())


def add_doubt(subject_id: int, text: str, status: str = "pending", topic_id: int | None = None) -> dict:
    if status not in DOUBT_STATUSES:
        raise InvalidStatusError(f"Estado de duda no válido: {status}")
    if not text.strip():
        raise ValueError("El texto de la duda no puede estar vacío.")
    doubt_id = _write(
        "INSERT INTO doubts (subject_id, text, status, topic_id) VALUES (?, ?, ?, ?)",
        (subject_id, text.strip(), status, topic_id),
    )
    return _one("SELECT * FROM doubts WHERE id = ?", (doubt_id,))


def list_doubts(subject_id: int | None = None, status: str | None = None) -> list[dict]:
    if status is not None and status not in DOUBT_STATUSES:
        raise InvalidStatusError(f"Estado de duda no válido: {status}")
    where, parameters = [], []
    if subject_id is not None:
        where.append("subject_id = ?")
        parameters.append(subject_id)
    if status is not None:
        where.append("status = ?")
        parameters.append(status)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return _rows(f"SELECT * FROM doubts {clause} ORDER BY created_at, id", tuple(parameters))


def list_pending_doubts(subject_id: int | None = None) -> list[dict]:
    return list_doubts(subject_id=subject_id, status="pending")


def update_doubt_status(doubt_id: int, status: str) -> dict:
    if status not in DOUBT_STATUSES:
        raise InvalidStatusError(f"Estado de duda no válido: {status}")
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "UPDATE doubts SET status = ?, resolved_at = ? WHERE id = ?",
            (status, _now() if status == "resolved" else None, doubt_id),
        )
        if not cursor.rowcount:
            raise NotFoundError(f"No existe la duda con id {doubt_id}.")
        return _dict(connection.execute(
            "SELECT * FROM doubts WHERE id = ?", (doubt_id,)
        ).fetchone())


def resolve_doubt(doubt_id: int) -> dict:
    return update_doubt_status(doubt_id, "resolved")


def start_session(subject_id: int, target_minutes: int, hard_limit_minutes: int) -> dict:
    if target_minutes <= 0:
        raise ValueError("target_minutes debe ser mayor que cero.")
    if hard_limit_minutes < target_minutes:
        raise ValueError("hard_limit_minutes debe ser >= target_minutes.")
    session_id = _write(
        "INSERT INTO study_sessions "
        "(subject_id, started_at, target_minutes, hard_limit_minutes) "
        "VALUES (?, ?, ?, ?)",
        (subject_id, _now(), target_minutes, hard_limit_minutes),
    )
    return _one("SELECT * FROM study_sessions WHERE id = ?", (session_id,))


def get_active_session(subject_id: int | None = None) -> dict | None:
    if subject_id is None:
        return _one(
            "SELECT * FROM study_sessions WHERE status = 'active' "
            "ORDER BY id DESC LIMIT 1"
        )
    return _one(
        "SELECT * FROM study_sessions WHERE status = 'active' AND subject_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (subject_id,),
    )


def _change_session_status(session_id: int, from_status: str, status: str) -> dict:
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "UPDATE study_sessions SET status = ? WHERE id = ? AND status = ?",
            (status, session_id, from_status),
        )
        if not cursor.rowcount:
            exists = connection.execute(
                "SELECT status FROM study_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if exists is None:
                raise NotFoundError(f"No existe la sesión con id {session_id}.")
            raise StudyStoreError(
                f"No se puede cambiar la sesión {session_id} de "
                f"{exists['status']} a {status}."
            )
        return _dict(connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone())


def pause_session(session_id: int) -> dict:
    return _change_session_status(session_id, "active", "paused")


def resume_session(session_id: int) -> dict:
    return _change_session_status(session_id, "paused", "active")


def close_session(session_id: int, status: str = "completed") -> dict:
    if status not in {"completed", "cancelled"}:
        raise InvalidStatusError("Una sesión solo se puede cerrar como completed o cancelled.")
    with closing(get_connection()) as connection, connection:
        row = connection.execute(
            "SELECT status FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No existe la sesión con id {session_id}.")
        if row["status"] not in {"active", "paused"}:
            raise StudyStoreError(f"La sesión {session_id} ya está cerrada.")
        connection.execute(
            "UPDATE study_sessions SET status = ?, ended_at = ? WHERE id = ?",
            (status, _now(), session_id),
        )
        return _dict(connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone())


def create_checkpoint(session_id: int, current_topic: str | None = None,
                      current_source: str | None = None,
                      current_exercise: str | None = None,
                      current_step: str | None = None,
                      next_action: str | None = None) -> dict:
    checkpoint_id = _write(
        "INSERT INTO checkpoints "
        "(session_id, current_topic, current_source, current_exercise, current_step, next_action) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, current_topic, current_source, current_exercise, current_step, next_action),
    )
    return _one("SELECT * FROM checkpoints WHERE id = ?", (checkpoint_id,))


def get_latest_checkpoint(session_id: int) -> dict | None:
    return _one(
        "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    )


def get_latest_checkpoint_for_subject(subject_id: int) -> dict | None:
    return _one(
        "SELECT c.* FROM checkpoints c "
        "JOIN study_sessions s ON s.id = c.session_id "
        "WHERE s.subject_id = ? ORDER BY c.id DESC LIMIT 1",
        (subject_id,),
    )


def get_session(session_id: int) -> dict | None:
    return _one(
        "SELECT s.*, sub.name AS subject_name FROM study_sessions s "
        "JOIN subjects sub ON sub.id = s.subject_id WHERE s.id = ?",
        (session_id,),
    )


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
