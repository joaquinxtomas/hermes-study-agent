ALTER TABLE study_sessions ADD COLUMN elapsed_seconds INTEGER NOT NULL DEFAULT 0
    CHECK (elapsed_seconds >= 0);
ALTER TABLE study_sessions ADD COLUMN running_since TEXT;
ALTER TABLE study_sessions ADD COLUMN target_notified_at TEXT;
ALTER TABLE study_sessions ADD COLUMN hard_limit_notified_at TEXT;
ALTER TABLE study_sessions ADD COLUMN target_cron_id TEXT;
ALTER TABLE study_sessions ADD COLUMN hard_limit_cron_id TEXT;

UPDATE study_sessions SET running_since = started_at WHERE status = 'active';
