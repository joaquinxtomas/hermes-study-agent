---
name: session-summary
description: Summarize a closed local study session from SQLite records.
---

# session-summary

Use Hermes' terminal tool from the project root to read the session with
`python3 scripts/study_cli.py session show SESSION_ID`, restore its latest
checkpoint with `session restore "SUBJECT"`, and read pending doubts with
`doubts pending --subject "SUBJECT"`. Use only these database results.

Return this structure, leaving unavailable fields empty rather than inventing
them:

```text
subject:
duration:
status:
worked_on:
pending_doubts:
checkpoint:
next_action:
```

Calculate duration from the stored `started_at` and `ended_at`. `worked_on` is
what the checkpoint records; identify the checkpoint and next action from the
latest stored checkpoint. This is a deterministic, source-data-based summary;
do not call an external LLM.
