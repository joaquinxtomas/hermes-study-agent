"""SQLite metadata and extracted-page storage for academic sources."""

from contextlib import closing
from pathlib import Path
import sqlite3

import study_store


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MATERIALS_DIR = PROJECT_ROOT / "materials"
SOURCE_TYPES = {"textbook", "guide", "exam", "notes", "markdown", "pdf", "other"}


def _one(sql: str, parameters: tuple = ()) -> dict | None:
    with closing(study_store.get_connection()) as connection, connection:
        row = connection.execute(sql, parameters).fetchone()
        return dict(row) if row else None


def _rows(sql: str, parameters: tuple = ()) -> list[dict]:
    with closing(study_store.get_connection()) as connection, connection:
        return [dict(row) for row in connection.execute(sql, parameters)]


def _source_path(path: str | Path) -> str:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    candidate = candidate.resolve()
    materials = MATERIALS_DIR.resolve()
    try:
        relative_path = candidate.relative_to(materials)
    except ValueError as error:
        raise ValueError("Las fuentes deben estar dentro de materials/.") from error
    return (Path("materials") / relative_path).as_posix()


def add_topic(subject_id: int, name: str, parent_topic_id: int | None = None) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("El nombre del tema no puede estar vacío.")
    with closing(study_store.get_connection()) as connection, connection:
        if parent_topic_id is not None:
            parent = connection.execute(
                "SELECT subject_id FROM topics WHERE id = ?", (parent_topic_id,)
            ).fetchone()
            if parent is None:
                raise study_store.NotFoundError(f"No existe el tema padre {parent_topic_id}.")
            if parent["subject_id"] != subject_id:
                raise study_store.StudyStoreError(
                    "El tema padre debe pertenecer a la misma materia."
                )
        try:
            cursor = connection.execute(
                "INSERT INTO topics (subject_id, name, parent_topic_id) VALUES (?, ?, ?)",
                (subject_id, name, parent_topic_id),
            )
        except sqlite3.IntegrityError as error:
            if "topics.subject_id, topics.name" in str(error):
                raise study_store.StudyStoreError(
                    f"El tema ya existe en esta materia: {name}"
                ) from error
            raise
        return dict(connection.execute(
            "SELECT * FROM topics WHERE id = ?", (cursor.lastrowid,)
        ).fetchone())


def list_topics(subject_id: int | None = None, active_only: bool = True) -> list[dict]:
    conditions, parameters = [], []
    if subject_id is not None:
        conditions.append("subject_id = ?")
        parameters.append(subject_id)
    if active_only:
        conditions.append("active = 1")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return _rows(f"SELECT * FROM topics {where} ORDER BY subject_id, name", tuple(parameters))


def add_source(subject_id: int, title: str, source_type: str, path: str | Path,
               topic_id: int | None = None, author: str | None = None) -> dict:
    title = title.strip()
    if not title:
        raise ValueError("El título de la fuente no puede estar vacío.")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Tipo de fuente no válido: {source_type}")
    stored_path = _source_path(path)
    with closing(study_store.get_connection()) as connection, connection:
        if topic_id is not None:
            topic = connection.execute(
                "SELECT subject_id FROM topics WHERE id = ?", (topic_id,)
            ).fetchone()
            if topic is None:
                raise study_store.NotFoundError(f"No existe el tema {topic_id}.")
            if topic["subject_id"] != subject_id:
                raise study_store.StudyStoreError(
                    "El tema debe pertenecer a la misma materia que la fuente."
                )
        try:
            cursor = connection.execute(
                "INSERT INTO sources (subject_id, topic_id, title, source_type, path, author) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (subject_id, topic_id, title, source_type, stored_path, author),
            )
        except sqlite3.IntegrityError as error:
            if "sources.path" in str(error):
                raise study_store.StudyStoreError(
                    f"Ya existe una fuente registrada con este path: {stored_path}"
                ) from error
            raise
        return dict(connection.execute(
            "SELECT * FROM sources WHERE id = ?", (cursor.lastrowid,)
        ).fetchone())


def list_sources(subject_id: int | None = None, topic_id: int | None = None,
                 active_only: bool = True) -> list[dict]:
    conditions, parameters = [], []
    if subject_id is not None:
        conditions.append("subject_id = ?")
        parameters.append(subject_id)
    if topic_id is not None:
        conditions.append("topic_id = ?")
        parameters.append(topic_id)
    if active_only:
        conditions.append("active = 1")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return _rows(f"SELECT * FROM sources {where} ORDER BY title, id", tuple(parameters))


def get_source_by_id(source_id: int) -> dict | None:
    return _one("SELECT * FROM sources WHERE id = ?", (source_id,))


def find_sources_by_title(title: str) -> list[dict]:
    title = title.strip()
    if not title:
        return []
    return _rows(
        "SELECT * FROM sources WHERE active = 1 AND title LIKE ? COLLATE NOCASE "
        "ORDER BY title, id",
        (f"%{title}%",),
    )


def add_source_page(source_id: int, page_number: int, text: str) -> dict:
    if page_number <= 0:
        raise ValueError("page_number debe ser mayor que cero.")
    with closing(study_store.get_connection()) as connection, connection:
        connection.execute(
            "INSERT INTO source_pages (source_id, page_number, text) VALUES (?, ?, ?) "
            "ON CONFLICT(source_id, page_number) DO UPDATE SET text = excluded.text",
            (source_id, page_number, text),
        )
        return dict(connection.execute(
            "SELECT * FROM source_pages WHERE source_id = ? AND page_number = ?",
            (source_id, page_number),
        ).fetchone())


def replace_source_pages(source_id: int, pages: list[str]) -> None:
    with closing(study_store.get_connection()) as connection, connection:
        if connection.execute(
            "SELECT 1 FROM sources WHERE id = ?", (source_id,)
        ).fetchone() is None:
            raise study_store.NotFoundError(f"No existe la fuente {source_id}.")
        connection.execute("DELETE FROM source_pages WHERE source_id = ?", (source_id,))
        connection.executemany(
            "INSERT INTO source_pages (source_id, page_number, text) VALUES (?, ?, ?)",
            [(source_id, number, text) for number, text in enumerate(pages, 1)],
        )


def get_source_pages(source_id: int) -> list[dict]:
    return _rows(
        "SELECT source_id, page_number, text FROM source_pages "
        "WHERE source_id = ? ORDER BY page_number",
        (source_id,),
    )


def set_source_active(source_id: int, active: bool) -> dict:
    with closing(study_store.get_connection()) as connection, connection:
        cursor = connection.execute(
            "UPDATE sources SET active = ? WHERE id = ?", (int(active), source_id)
        )
        if not cursor.rowcount:
            raise study_store.NotFoundError(f"No existe la fuente {source_id}.")
        return dict(connection.execute(
            "SELECT * FROM sources WHERE id = ?", (source_id,)
        ).fetchone())
