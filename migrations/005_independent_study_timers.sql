ALTER TABLE study_sessions ADD COLUMN close_reason TEXT;

CREATE TABLE study_timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES study_sessions(id),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
    remaining_seconds INTEGER NOT NULL CHECK (remaining_seconds >= 0),
    status TEXT NOT NULL CHECK (status IN ('running', 'paused', 'finished', 'cancelled')),
    started_at TEXT NOT NULL,
    running_since TEXT,
    finished_at TEXT,
    label TEXT
);

CREATE UNIQUE INDEX one_open_timer_per_session
    ON study_timers(session_id) WHERE status IN ('running', 'paused');
CREATE INDEX study_timers_session_history
    ON study_timers(session_id, id DESC);
