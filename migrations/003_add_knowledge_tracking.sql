CREATE TABLE knowledge_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL CHECK (dimension IN ('conceptual', 'procedural', 'independent_problem_solving', 'retention')),
    status TEXT NOT NULL CHECK (status IN ('not_seen', 'introduced', 'understood', 'practicing', 'independent', 'needs_review')),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (topic_id, dimension)
);
INSERT INTO knowledge_states (topic_id, dimension, status)
SELECT topics.id, dimensions.dimension, 'not_seen'
FROM topics
CROSS JOIN (
    SELECT 'conceptual' AS dimension
    UNION ALL SELECT 'procedural'
    UNION ALL SELECT 'independent_problem_solving'
    UNION ALL SELECT 'retention'
) AS dimensions;

CREATE TRIGGER initialize_topic_knowledge_states
AFTER INSERT ON topics
BEGIN
    INSERT INTO knowledge_states (topic_id, dimension, status) VALUES
        (NEW.id, 'conceptual', 'not_seen'),
        (NEW.id, 'procedural', 'not_seen'),
        (NEW.id, 'independent_problem_solving', 'not_seen'),
        (NEW.id, 'retention', 'not_seen');
END;

CREATE TABLE knowledge_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL CHECK (dimension IN ('conceptual', 'procedural', 'independent_problem_solving', 'retention')),
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('explanation', 'guided_exercise', 'independent_exercise', 'exam_question', 'doubt', 'review', 'self_assessment')),
    result TEXT NOT NULL CHECK (result IN ('correct', 'partially_correct', 'incorrect', 'completed', 'observed')),
    details TEXT NOT NULL,
    session_id INTEGER REFERENCES study_sessions(id),
    doubt_id INTEGER REFERENCES doubts(id),
    source_id INTEGER REFERENCES sources(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX knowledge_evidence_topic_created ON knowledge_evidence(topic_id, created_at DESC, id DESC);
CREATE TABLE misconceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'improving', 'resolved')),
    occurrences INTEGER NOT NULL DEFAULT 1 CHECK (occurrences > 0),
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (topic_id, description)
);
