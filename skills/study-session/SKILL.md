---
name: study-session
description: Start, pause, resume, stop, inspect, and finish study sessions or local study timers.
---

# Study sessions and local timers

SQLite is the source of truth. Use the `study_fastpath` tools directly for
session and timer actions; do not use `skill_view`, `tool_search`, `terminal`,
or cron to start, pause, resume, stop, or inspect a local timer.

## Intent routing

- “Poneme 20 minutos”, “timer de estudio”, “pausá”, “reanuda”, “cuánto queda”
  → `study_timer_*` / `study_session_status`.
- “Iniciá una sesión de Física sobre Gauss” → `study_session_start`, passing
  the exact existing subject and topic. Defaults are 75 target minutes and a
  90 minute hard limit. Starting another session checkpoints and closes the
  open session before creating the new one.
- “Terminá la sesión” → `study_session_end` with `completed` unless the user
  cancels. “Pará el timer” → `study_timer_stop`; it stops only the countdown,
  leaving the study session open.
- “Recordame mañana” or a recurring/date-specific reminder → reminder or
  automation tools. A local countdown is not a reminder, and a timer request
  must not trigger cron discovery.

## Fast path behavior

Make one direct tool call, then give a short confirmation. Start or update
state before explaining. A study session and its countdowns are separate
records: multiple sequential timer blocks belong to one session. Only one
timer may be running or paused at a time. Starting another timer in the same
subject reuses the open session; switching subjects closes the old session
with a checkpoint. Pausing/stopping a timer does not pause/close its session.

When the user enters an explicit Hermes command, `/study-timer 25`,
`/study-timer pausa`, `/study-timer reanudar`, `/study-timer detener`, or
`/study-timer estado`, let the plugin command handle it directly. Do not route
that command through the model or call a second tool.

Timer start requires a whole duration in minutes. Pass the current conversation
subject when known; otherwise reuse the open session's subject. With no open
session, infer a subject only if exactly one active subject exists. If the
subject is ambiguous or none exists, ask which existing subject to associate.
Do not invent a subject. Pause and resume target the current timer.
In Hermes Desktop, the
Study Timer panel opens when a timer starts and remains available in the status
bar; its controls call Study Core directly. The panel requires the optional
Desktop half of `study-fastpath` to be enabled. Outside Desktop, tool responses
and the current session status remain available. Status returns the current
session and timer state. If no fast path tool is available, use the Study CLI
as a fallback and make only the needed call.

Timer and session state are deterministic and stored in SQLite. Without a
separate reminder request, the tools do not schedule a Hermes cron job. The
Desktop panel shows the countdown and signals completion while Hermes is open;
it does not promise an alert while the app is closed. At a session hard limit,
Study Core preserves its checkpoint behavior.

## Restore and learning tracking

Restore a prior checkpoint only when asked to continue a session. Capture a
topic with the session start tool when supplied. Record learning evidence only
for an actual explanation, answer, exercise, or review, linked using the
session ID; elapsed time alone never proves learning.
