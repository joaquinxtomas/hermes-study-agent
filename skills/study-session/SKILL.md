---
name: study-session
description: Manage local study sessions and restore their checkpoints.
---

# study-session

Run the commands below with Hermes' terminal tool from the project root. Use
only returned SQLite records as confirmation; never write SQL directly.

- **Start:** look up the exact subject with `subjects list`. Read
  `study.default_session.target_minutes` and `hard_limit_minutes` from
  `config/study.yaml` if it exists, otherwise from
  `config/study.example.yaml`. Start with
  `python3 scripts/study_cli.py session start "SUBJECT" --target-minutes N --hard-limit-minutes N`.
- **Pause / resume:** use `session pause SESSION_ID` or
  `session resume SESSION_ID` with the ID returned at start.
- **Checkpoint:** save the available context with
  `session checkpoint SESSION_ID` and the relevant flags:
  `--current-topic`, `--current-source`, `--current-exercise`, `--current-step`,
  `--next-action`.
- **Close:** use `session close SESSION_ID --status completed` (or `cancelled`
  when the user cancels).
- **Restore:** use `session restore "SUBJECT"`; report the latest checkpoint
  returned from SQLite. If none exists, say so.

Flow: resolve subject → start session → work → checkpoint → close. No timers,
cron, scheduler or timed notifications are implemented. A checkpoint can be
saved manually at any point, including before a session is closed.
