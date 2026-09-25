"""SQLite persistence for topic knowledge, evidence and misconceptions."""
from contextlib import closing
from datetime import datetime
import knowledge_rules as rules
import study_store


class KnowledgeStoreError(Exception):
    """Invalid or unavailable knowledge data."""


def get_connection():
    return study_store.get_connection()


def _dict(row):
    return dict(row) if row is not None else None


def _rows(sql, parameters=()):
    with closing(get_connection()) as connection, connection:
        return [_dict(row) for row in connection.execute(sql, parameters)]


def _one(sql, parameters=()):
    with closing(get_connection()) as connection, connection:
        return _dict(connection.execute(sql, parameters).fetchone())


def _validate(dimension=None, status=None, evidence_type=None, result=None):
    for value, supported, label in ((dimension, rules.DIMENSIONS, "dimension"), (status, rules.STATUSES, "status"), (evidence_type, rules.EVIDENCE_TYPES, "evidence_type"), (result, rules.RESULTS, "result")):
        if value is not None and value not in supported:
            raise ValueError(f"Invalid {label}: {value}")


def initialize_topic_states(topic_id):
    with closing(get_connection()) as connection, connection:
        topic = connection.execute("SELECT id FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if topic is None:
            raise KnowledgeStoreError(f"No existe el topic con id {topic_id}.")
        for dimension in sorted(rules.DIMENSIONS):
            connection.execute("INSERT OR IGNORE INTO knowledge_states (topic_id, dimension, status) VALUES (?, ?, 'not_seen')", (topic_id, dimension))
    return list_knowledge_states(topic_id)


def get_knowledge_state(topic_id, dimension):
    _validate(dimension=dimension)
    return _one("SELECT * FROM knowledge_states WHERE topic_id = ? AND dimension = ?", (topic_id, dimension))


def list_knowledge_states(topic_id):
    return _rows("SELECT * FROM knowledge_states WHERE topic_id = ? ORDER BY dimension", (topic_id,))


def set_knowledge_state(topic_id, dimension, status):
    _validate(dimension, status)
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute("UPDATE knowledge_states SET status = ?, updated_at = ? WHERE topic_id = ? AND dimension = ?", (status, _now(), topic_id, dimension))
        if cursor.rowcount == 0:
            connection.execute("INSERT INTO knowledge_states (topic_id, dimension, status, updated_at) VALUES (?, ?, ?, ?)", (topic_id, dimension, status, _now()))
    return get_knowledge_state(topic_id, dimension)


def list_topics_by_status(dimension, status):
    _validate(dimension, status)
    return _rows("SELECT t.id AS topic_id, t.name AS topic_name, t.subject_id, s.name AS subject_name, k.dimension, k.status, k.updated_at FROM knowledge_states k JOIN topics t ON t.id = k.topic_id JOIN subjects s ON s.id = t.subject_id WHERE t.active = 1 AND k.dimension = ? AND k.status = ? ORDER BY s.name, t.name", (dimension, status))


def list_topics(subject_id=None):
    where, params = ("WHERE t.active = 1", [])
    if subject_id is not None:
        where += " AND t.subject_id = ?"
        params.append(subject_id)
    return _rows("SELECT t.id AS topic_id, t.name AS topic_name, s.name AS subject_name FROM topics t JOIN subjects s ON s.id = t.subject_id " + where + " ORDER BY s.name, t.name", tuple(params))


def list_evidence(topic_id, dimension=None):
    _validate(dimension=dimension)
    sql = "SELECT * FROM knowledge_evidence WHERE topic_id = ?"
    params = [topic_id]
    if dimension is not None:
        sql += " AND dimension = ?"
        params.append(dimension)
    return _rows(sql + " ORDER BY created_at DESC, id DESC", tuple(params))


def list_evidence_for_session(session_id):
    return _rows("SELECT * FROM knowledge_evidence WHERE session_id = ? ORDER BY created_at DESC, id DESC", (session_id,))


def get_recent_evidence(topic_id, limit=10):
    if limit < 0:
        raise ValueError("limit must be >= 0")
    return _rows("SELECT * FROM knowledge_evidence WHERE topic_id = ? ORDER BY created_at DESC, id DESC LIMIT ?", (topic_id, limit))


def record_transition(topic_id, dimension, evidence_type, result, details, new_status, session_id=None, doubt_id=None, source_id=None):
    _validate(dimension, new_status, evidence_type, result)
    if not details or not details.strip():
        raise ValueError("Evidence details cannot be empty")
    with closing(get_connection()) as connection, connection:
        previous = connection.execute("SELECT status FROM knowledge_states WHERE topic_id = ? AND dimension = ?", (topic_id, dimension)).fetchone()
        if previous is None:
            connection.execute("INSERT INTO knowledge_states (topic_id, dimension, status) VALUES (?, ?, 'not_seen')", (topic_id, dimension))
            previous_status = "not_seen"
        else:
            previous_status = previous["status"]
        cursor = connection.execute("INSERT INTO knowledge_evidence (topic_id, dimension, evidence_type, result, details, session_id, doubt_id, source_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (topic_id, dimension, evidence_type, result, details.strip(), session_id, doubt_id, source_id))
        if new_status != previous_status:
            connection.execute("UPDATE knowledge_states SET status = ?, updated_at = ? WHERE topic_id = ? AND dimension = ?", (new_status, _now(), topic_id, dimension))
        evidence_id = cursor.lastrowid
    return {"topic_id": topic_id, "dimension": dimension, "previous_status": previous_status, "new_status": new_status, "evidence_id": evidence_id}


def add_or_update_misconception(topic_id, description):
    description = " ".join(description.split())
    if not description:
        raise ValueError("Misconception description cannot be empty")
    with closing(get_connection()) as connection, connection:
        connection.execute("INSERT INTO misconceptions (topic_id, description) VALUES (?, ?) ON CONFLICT(topic_id, description) DO UPDATE SET occurrences = occurrences + 1, last_seen_at = CURRENT_TIMESTAMP, status = 'active'", (topic_id, description))
        row = connection.execute("SELECT * FROM misconceptions WHERE topic_id = ? AND description = ?", (topic_id, description)).fetchone()
        return _dict(row)


def list_misconceptions(topic_id=None, status=None):
    if status is not None and status not in {"active", "improving", "resolved"}:
        raise ValueError(f"Invalid misconception status: {status}")
    where, params = [], []
    if topic_id is not None:
        where.append("m.topic_id = ?")
        params.append(topic_id)
    if status is not None:
        where.append("m.status = ?")
        params.append(status)
    clause = " WHERE " + " AND ".join(where) if where else ""
    return _rows("SELECT m.*, t.name AS topic_name FROM misconceptions m JOIN topics t ON t.id = m.topic_id" + clause + " ORDER BY m.last_seen_at DESC, m.id DESC", tuple(params))


def resolve_misconception(misconception_id):
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute("UPDATE misconceptions SET status = 'resolved' WHERE id = ?", (misconception_id,))
        if not cursor.rowcount:
            raise KnowledgeStoreError(f"No existe la misconception con id {misconception_id}.")
        return _dict(connection.execute("SELECT * FROM misconceptions WHERE id = ?", (misconception_id,)).fetchone())


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")
