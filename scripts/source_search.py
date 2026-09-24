"""Deterministic lexical search over the locally extracted source pages."""

from contextlib import closing
import re
import unicodedata

import study_store


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _snippet(text: str, terms: list[str], max_length: int = 420) -> str:
    folded, positions = [], []
    for index, char in enumerate(text):
        for normalized in unicodedata.normalize("NFKD", char.casefold()):
            if not unicodedata.combining(normalized):
                folded.append(normalized)
                positions.append(index)
    normalized_text = "".join(folded)
    match = next(
        (normalized_text.find(term) for term in sorted(terms, key=len, reverse=True)
         if normalized_text.find(term) >= 0),
        0,
    )
    position = positions[match] if positions else 0
    start = max(0, position - max_length // 3)
    end = min(len(text), start + max_length)
    prefix = "…" if start else ""
    suffix = "…" if end < len(text) else ""
    return prefix + " ".join(text[start:end].split()) + suffix


def search_sources(query: str, source_id: int | None = None,
                   subject_id: int | None = None, topic_id: int | None = None,
                   limit: int = 5) -> list[dict]:
    normalized_query = _normalize(query).strip()
    terms = list(dict.fromkeys(re.findall(r"[\w]+", normalized_query)))
    if not terms:
        raise ValueError("La consulta debe contener al menos un término.")
    if limit <= 0:
        raise ValueError("limit debe ser mayor que cero.")

    conditions, parameters = ["s.active = 1"], []
    for column, value in (("s.id", source_id), ("s.subject_id", subject_id),
                          ("s.topic_id", topic_id)):
        if value is not None:
            conditions.append(f"{column} = ?")
            parameters.append(value)
    sql = (
        "SELECT s.id AS source_id, s.title AS source_title, p.page_number, p.text "
        "FROM source_pages p JOIN sources s ON s.id = p.source_id WHERE "
        + " AND ".join(conditions)
    )

    # ponytail: O(n) page scan suits the initial local library; use SQLite FTS if it grows slow.
    with closing(study_store.get_connection()) as connection, connection:
        pages = connection.execute(sql, tuple(parameters)).fetchall()

    results = []
    for page in pages:
        normalized_text = _normalize(page["text"])
        matched_terms = sum(term in normalized_text for term in terms)
        if not matched_terms:
            continue
        frequency = sum(normalized_text.count(term) for term in terms)
        relevance = matched_terms / len(terms) + min(frequency, 10) * 0.01
        if normalized_query in normalized_text:
            relevance += 0.5
        results.append({
            "source_id": page["source_id"],
            "source_title": page["source_title"],
            "page_number": page["page_number"],
            "snippet": _snippet(page["text"], terms),
            "relevance": round(relevance, 3),
        })
    results.sort(key=lambda result: (
        -result["relevance"], result["source_title"].casefold(), result["page_number"]
    ))
    return results[:limit]
