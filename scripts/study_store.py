"""Local SQLite operations for study subjects, doubts, sessions and checkpoints."""

from contextlib import closing
from datetime import datetime, timedelta
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
    now = _now()
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        open_sessions = connection.execute(
            "SELECT * FROM study_sessions WHERE status IN ('active', 'paused') ORDER BY id DESC"
        ).fetchall()
        for old_session in open_sessions:
            _interrupt_session(connection, old_session, now)
        cursor = connection.execute(
            "INSERT INTO study_sessions "
            "(subject_id, started_at, target_minutes, hard_limit_minutes, running_since) "
            "VALUES (?, ?, ?, ?, ?)",
            (subject_id, now, target_minutes, hard_limit_minutes, now),
        )
        session_id = cursor.lastrowid
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


def start_study_timer(session_id: int, duration_minutes: int, label: str | None = None) -> dict:
    if isinstance(duration_minutes, bool) or not isinstance(duration_minutes, int) or duration_minutes < 1:
        raise ValueError("duration_minutes debe ser un entero mayor que cero.")
    now = _now()
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        session = connection.execute(
            "SELECT status FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if session is None:
            raise NotFoundError(f"No existe la sesión {session_id}.")
        if session["status"] != "active":
            raise StudyStoreError("El timer requiere una sesión de estudio activa.")
        _finish_due_timer(connection, session_id, now)
        if connection.execute(
            "SELECT 1 FROM study_timers WHERE session_id = ? AND status IN ('running', 'paused')",
            (session_id,),
        ).fetchone():
            raise StudyStoreError("Ya hay un timer activo o pausado en esta sesión.")
        cursor = connection.execute(
            "INSERT INTO study_timers "
            "(session_id, duration_seconds, remaining_seconds, status, started_at, running_since, label) "
            "VALUES (?, ?, ?, 'running', ?, ?, ?)",
            (session_id, duration_minutes * 60, duration_minutes * 60, now, now,
             label.strip()[:120] if label and label.strip() else None),
        )
        return _timer_payload(connection, cursor.lastrowid, now)


def get_current_study_timer(session_id: int | None = None, now: str | None = None) -> dict | None:
    current = now or _now()
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        where, params = ("WHERE t.session_id = ?", (session_id,)) if session_id else ("", ())
        row = connection.execute(
            "SELECT t.id FROM study_timers t JOIN study_sessions s ON s.id = t.session_id "
            f"{where} {'AND' if where else 'WHERE'} t.status IN ('running', 'paused') "
            "ORDER BY t.id DESC LIMIT 1", params,
        ).fetchone()
        if row is None:
            row = connection.execute(
                "SELECT id FROM study_timers WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                (session_id,),
            ).fetchone() if session_id is not None else connection.execute(
                "SELECT id FROM study_timers ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        _finish_due_timer(connection, timer_id=row["id"], now=current)
        return _timer_payload(connection, row["id"], current)


def list_study_timers(session_id: int) -> list[dict]:
    with closing(get_connection()) as connection, connection:
        return [_timer_payload(connection, row["id"], _now()) for row in connection.execute(
            "SELECT id FROM study_timers WHERE session_id = ? ORDER BY id", (session_id,)
        )]


def pause_study_timer(session_id: int | None = None) -> dict:
    return _transition_study_timer("pause", session_id)


def resume_study_timer(session_id: int | None = None) -> dict:
    return _transition_study_timer("resume", session_id)


def stop_study_timer(session_id: int | None = None) -> dict:
    return _transition_study_timer("stop", session_id)


def _transition_study_timer(action: str, session_id: int | None) -> dict:
    now = _now()
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        where, params = ("AND session_id = ?", (session_id,)) if session_id else ("", ())
        desired = "running" if action in {"pause", "stop"} else "paused"
        statuses = "status IN ('running', 'paused')" if action == "stop" else "status = ?"
        values = (*params,) if action == "stop" else (desired, *params)
        row = connection.execute(
            "SELECT * FROM study_timers WHERE " + statuses + " " + where + " ORDER BY id DESC LIMIT 1",
            values,
        ).fetchone()
        if row is None:
            message = "No hay un timer activo." if action != "resume" else "No hay un timer pausado."
            raise StudyStoreError(message)
        if action == "resume":
            session = connection.execute(
                "SELECT status FROM study_sessions WHERE id = ?", (row["session_id"],)
            ).fetchone()
            if session["status"] != "active":
                raise StudyStoreError("Reanudá la sesión de estudio antes de reanudar el timer.")
        remaining = _timer_remaining(row, now)
        if remaining <= 0:
            _finish_due_timer(connection, timer_id=row["id"], now=now)
            raise StudyStoreError("El timer ya terminó.")
        if action == "pause":
            connection.execute(
                "UPDATE study_timers SET status='paused', remaining_seconds=?, running_since=NULL WHERE id=?",
                (remaining, row["id"]),
            )
        elif action == "resume":
            connection.execute(
                "UPDATE study_timers SET status='running', running_since=? WHERE id=?",
                (now, row["id"]),
            )
        else:
            connection.execute(
                "UPDATE study_timers SET status='cancelled', remaining_seconds=?, running_since=NULL, finished_at=? WHERE id=?",
                (remaining, now, row["id"]),
            )
        return _timer_payload(connection, row["id"], now)


def _finish_due_timer(connection: sqlite3.Connection, session_id: int | None = None,
                      now: str | None = None, timer_id: int | None = None) -> None:
    current = now or _now()
    where, params = (("id = ?", (timer_id,)) if timer_id is not None
                     else ("session_id = ? AND status = 'running'", (session_id,)))
    rows = connection.execute(f"SELECT * FROM study_timers WHERE {where}", params).fetchall()
    for row in rows:
        if row["status"] == "running" and _timer_remaining(row, current) <= 0:
            connection.execute(
                "UPDATE study_timers SET status='finished', remaining_seconds=0, running_since=NULL, finished_at=? WHERE id=?",
                (current, row["id"]),
            )


def _pause_session_timer(connection: sqlite3.Connection, session_id: int, now: str) -> None:
    row = connection.execute(
        "SELECT * FROM study_timers WHERE session_id=? AND status='running' ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    if row:
        remaining = _timer_remaining(row, now)
        if remaining <= 0:
            _finish_due_timer(connection, timer_id=row["id"], now=now)
        else:
            connection.execute(
                "UPDATE study_timers SET status='paused', remaining_seconds=?, running_since=NULL WHERE id=?",
                (remaining, row["id"]),
            )


def _timer_remaining(row: dict, now: str) -> int:
    remaining = row["remaining_seconds"] or 0
    if row["status"] == "running" and row["running_since"]:
        elapsed = int((datetime.fromisoformat(now) - datetime.fromisoformat(row["running_since"])).total_seconds())
        return max(0, remaining - max(0, elapsed))
    return remaining


def _timer_payload(connection: sqlite3.Connection, timer_id: int, now: str) -> dict:
    row = connection.execute("SELECT * FROM study_timers WHERE id = ?", (timer_id,)).fetchone()
    result = _dict(row)
    result["remaining_seconds"] = _timer_remaining(row, now)
    result["deadline"] = (
        (datetime.fromisoformat(now) + timedelta(seconds=result["remaining_seconds"])).isoformat(timespec="seconds")
        if row["status"] == "running" else None
    )
    return result


def _interrupt_session(connection: sqlite3.Connection, row: dict, now: str) -> None:
    session_id = row["id"]
    _finish_due_timer(connection, session_id=session_id, now=now)
    connection.execute(
        "UPDATE study_timers SET status='cancelled', running_since=NULL, finished_at=? "
        "WHERE session_id=? AND status IN ('running', 'paused')", (now, session_id),
    )
    latest = connection.execute(
        "SELECT * FROM checkpoints WHERE session_id=? ORDER BY id DESC LIMIT 1", (session_id,)
    ).fetchone()
    connection.execute(
        "INSERT INTO checkpoints (session_id, current_topic, current_source, current_exercise, current_step, next_action) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, latest["current_topic"] if latest else None,
         latest["current_source"] if latest else None,
         latest["current_exercise"] if latest else None,
         latest["current_step"] if latest else None,
         "Sesión cerrada al iniciar otra; retomar desde este checkpoint."),
    )
    elapsed = _elapsed_seconds(row, now)
    connection.execute(
        "UPDATE study_sessions SET status='cancelled', close_reason='replaced', ended_at=?, "
        "elapsed_seconds=?, running_since=NULL WHERE id=?",
        (now, elapsed, session_id),
    )


def pause_session(session_id: int) -> dict:
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        now = _now()
        row = connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No existe la sesión {session_id}.")
        if row["status"] != "active":
            raise StudyStoreError(f"No se puede pausar una sesión en estado {row['status']}.")
        elapsed = _elapsed_seconds(row, now)
        if elapsed >= row["hard_limit_minutes"] * 60:
            _apply_hard_limit(connection, row, elapsed, now)
            return _dict(connection.execute(
                "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
            ).fetchone())
        connection.execute(
            "UPDATE study_sessions SET status = 'paused', elapsed_seconds = ?, running_since = NULL WHERE id = ?",
            (elapsed, session_id),
        )
        _pause_session_timer(connection, session_id, now)
        return _dict(connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone())


def resume_session(session_id: int) -> dict:
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No existe la sesión {session_id}.")
        if row["status"] != "paused":
            raise StudyStoreError(f"No se puede reanudar una sesión en estado {row['status']}.")
        if row["hard_limit_notified_at"]:
            raise StudyStoreError("La sesión alcanzó su límite máximo; inicia una nueva sesión para continuar.")
        if connection.execute(
            "SELECT 1 FROM study_sessions WHERE status = 'active' AND id != ? LIMIT 1",
            (session_id,),
        ).fetchone():
            raise StudyStoreError("Ya hay otra sesión activa; pausala o cerrala antes de reanudar.")
        connection.execute(
            "UPDATE study_sessions SET status = 'active', running_since = ? WHERE id = ?",
            (_now(), session_id),
        )
        timer = connection.execute(
            "SELECT id FROM study_timers WHERE session_id = ? AND status = 'paused' ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if timer:
            connection.execute(
                "UPDATE study_timers SET status='running', running_since=? WHERE id=?",
                (_now(), timer["id"]),
            )
        return _dict(connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone())


def close_session(session_id: int, status: str = "completed") -> dict:
    if status not in {"completed", "cancelled"}:
        raise InvalidStatusError("Una sesión solo se puede cerrar como completed o cancelled.")
    current = _now()
    row = _one("SELECT * FROM study_sessions WHERE id = ?", (session_id,))
    if row is None:
        raise NotFoundError(f"No existe la sesión {session_id}.")
    if row["status"] == "active" and _elapsed_seconds(row, current) >= row["hard_limit_minutes"] * 60:
        fire_session_timer(session_id, "hard_limit", current)
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        current = _now()
        row = connection.execute(
            "SELECT status FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No existe la sesión con id {session_id}.")
        if row["status"] not in {"active", "paused"}:
            raise StudyStoreError(f"La sesión {session_id} ya está cerrada.")
        elapsed = _elapsed_seconds(connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone(), current)
        connection.execute(
            "UPDATE study_sessions SET status = ?, ended_at = ?, elapsed_seconds = ?, running_since = NULL WHERE id = ?",
            (status, current, elapsed, session_id),
        )
        connection.execute(
            "UPDATE study_timers SET status='cancelled', running_since=NULL, finished_at=? "
            "WHERE session_id=? AND status IN ('running', 'paused')",
            (current, session_id),
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


def get_latest_session(status: str | None = None) -> dict | None:
    if status is not None and status not in {"active", "paused", "completed", "cancelled"}:
        raise InvalidStatusError(f"Estado de sesión no válido: {status}")
    where = "WHERE s.status = ?" if status else ""
    parameters = (status,) if status else ()
    return _one(
        "SELECT s.*, sub.name AS subject_name FROM study_sessions s "
        "JOIN subjects sub ON sub.id = s.subject_id "
        f"{where} ORDER BY s.id DESC LIMIT 1",
        parameters,
    )


def session_timer(session_id: int, now: str | None = None) -> dict:
    row = _one("SELECT * FROM study_sessions WHERE id = ?", (session_id,))
    if row is None:
        raise NotFoundError(f"No existe la sesión {session_id}.")
    current = now or _now()
    elapsed = _elapsed_seconds(row, current)
    target = row["target_minutes"] * 60
    limit = row["hard_limit_minutes"] * 60
    return {
        "session_id": session_id,
        "status": row["status"],
        "elapsed_seconds": elapsed,
        "target_remaining_seconds": max(0, target - elapsed),
        "hard_limit_remaining_seconds": max(0, limit - elapsed),
        "target_notified": bool(row["target_notified_at"]),
        "hard_limit_reached": bool(row["hard_limit_notified_at"]),
        "target_cron_id": row["target_cron_id"],
        "hard_limit_cron_id": row["hard_limit_cron_id"],
        "target_at": _timer_deadline(row, target, current) if row["status"] == "active" and not row["target_notified_at"] else None,
        "hard_limit_at": _timer_deadline(row, limit, current) if row["status"] == "active" else None,
    }


def set_session_timer_job(session_id: int, event: str, job_id: str | None) -> dict:
    column = {"target": "target_cron_id", "hard_limit": "hard_limit_cron_id"}.get(event)
    if column is None:
        raise ValueError("event debe ser target o hard_limit.")
    if job_id is not None and (not job_id.strip() or len(job_id) > 200):
        raise ValueError("job_id debe tener entre 1 y 200 caracteres.")
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            f"UPDATE study_sessions SET {column} = ? WHERE id = ?",
            (job_id.strip() if job_id else None, session_id),
        )
        if not cursor.rowcount:
            raise NotFoundError(f"No existe la sesión {session_id}.")
    return session_timer(session_id)


def clear_session_timer_jobs(session_id: int) -> dict:
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "UPDATE study_sessions SET target_cron_id = NULL, hard_limit_cron_id = NULL WHERE id = ?",
            (session_id,),
        )
        if not cursor.rowcount:
            raise NotFoundError(f"No existe la sesión {session_id}.")
    return session_timer(session_id)


def fire_session_timer(session_id: int, event: str, now: str | None = None) -> dict:
    if event not in {"target", "hard_limit"}:
        raise ValueError("event debe ser target o hard_limit.")
    current = now or _now()
    stamp_column = "target_notified_at" if event == "target" else "hard_limit_notified_at"
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No existe la sesión {session_id}.")
        elapsed = _elapsed_seconds(row, current)
        threshold = (row["target_minutes"] if event == "target" else row["hard_limit_minutes"]) * 60
        if (row["status"] == "paused" and event == "hard_limit"
                and elapsed >= threshold and not row["hard_limit_notified_at"]):
            _apply_hard_limit(connection, row, elapsed, current)
            row = connection.execute(
                "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            checkpoint = connection.execute(
                "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,)
            ).fetchone()
            return {"notify": True, "event": event, "timer": _timer_data(row, elapsed), "checkpoint": _dict(checkpoint)}
        if row["status"] != "active":
            return {"notify": False, "reason": "session_not_active", "timer": _timer_data(row, elapsed)}
        if row[stamp_column]:
            return {"notify": False, "reason": "already_notified", "timer": _timer_data(row, elapsed)}
        if elapsed < threshold:
            return {"notify": False, "reason": "not_due", "timer": _timer_data(row, elapsed)}

        if event == "target":
            connection.execute(
                "UPDATE study_sessions SET target_notified_at = ? WHERE id = ?",
                (current, session_id),
            )
            return {"notify": True, "event": event, "timer": _timer_data(row, elapsed)}

        checkpoint = _apply_hard_limit(connection, row, elapsed, current)
        row = connection.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return {
            "notify": True, "event": event, "timer": _timer_data(row, elapsed),
            "checkpoint": _dict(checkpoint),
        }


def _apply_hard_limit(connection: sqlite3.Connection, row: dict, elapsed: int, now: str) -> sqlite3.Row:
    session_id = row["id"]
    _pause_session_timer(connection, session_id, now)
    connection.execute(
        "UPDATE study_sessions SET status = 'paused', elapsed_seconds = ?, running_since = NULL, "
        "hard_limit_notified_at = COALESCE(hard_limit_notified_at, ?), "
        "target_notified_at = CASE WHEN ? >= target_minutes * 60 THEN COALESCE(target_notified_at, ?) ELSE target_notified_at END, "
        "target_cron_id = NULL, hard_limit_cron_id = NULL WHERE id = ?",
        (elapsed, now, elapsed, now, session_id),
    )
    checkpoint = connection.execute(
        "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,)
    ).fetchone()
    connection.execute(
        "INSERT INTO checkpoints (session_id, current_topic, current_source, current_exercise, current_step, next_action) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, checkpoint["current_topic"] if checkpoint else None,
         checkpoint["current_source"] if checkpoint else None,
         checkpoint["current_exercise"] if checkpoint else None,
         checkpoint["current_step"] if checkpoint else None,
         "Límite de sesión alcanzado; retomar desde el último punto guardado."),
    )
    return connection.execute(
        "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY id DESC LIMIT 1", (session_id,)
    ).fetchone()


def _elapsed_seconds(row: dict, now: str) -> int:
    elapsed = row["elapsed_seconds"] or 0
    if row["running_since"]:
        started = datetime.fromisoformat(row["running_since"])
        current = datetime.fromisoformat(now)
        elapsed += max(0, int((current - started).total_seconds()))
    return elapsed


def _timer_deadline(row: dict, threshold: int, now: str) -> str:
    remaining = max(0, threshold - _elapsed_seconds(row, now))
    return (datetime.fromisoformat(now) + timedelta(seconds=remaining)).isoformat(timespec="seconds")


def _timer_data(row: dict, elapsed: int) -> dict:
    return {
        "session_id": row["id"], "status": row["status"], "elapsed_seconds": elapsed,
        "target_remaining_seconds": max(0, row["target_minutes"] * 60 - elapsed),
        "hard_limit_remaining_seconds": max(0, row["hard_limit_minutes"] * 60 - elapsed),
    }


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
