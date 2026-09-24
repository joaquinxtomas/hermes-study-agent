CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    name TEXT NOT NULL,
    parent_topic_id INTEGER REFERENCES topics(id),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (subject_id, name)
);

ALTER TABLE doubts
    ADD COLUMN topic_id INTEGER REFERENCES topics(id);

CREATE TABLE sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    topic_id INTEGER REFERENCES topics(id),
    title TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (
        source_type IN ('textbook', 'guide', 'exam', 'notes', 'markdown', 'pdf', 'other')
    ),
    path TEXT NOT NULL UNIQUE,
    author TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE source_pages (
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    text TEXT NOT NULL,
    PRIMARY KEY (source_id, page_number)
);
