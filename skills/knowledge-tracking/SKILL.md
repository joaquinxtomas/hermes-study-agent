---
name: knowledge-tracking
description: Query and record evidence-backed topic knowledge states and recurring misconceptions.
---

# knowledge-tracking

Use only the local SQLite CLI results. The code applies all state transitions; never update a state based on model judgment. State labels are discrete and must be explained with recorded evidence. Never describe them as an absolute measure of mastery.

## Query

- List topics: `python3 scripts/study_cli.py knowledge topics list [--subject "Física II"]`
- Show a topic, all four dimensions, evidence and active misconceptions: `python3 scripts/study_cli.py knowledge status show TOPIC_ID`
- Find topics: `python3 scripts/study_cli.py knowledge status list DIMENSION STATUS`
- Evidence: `python3 scripts/study_cli.py knowledge evidence list TOPIC_ID [--dimension DIMENSION]`
- Misconceptions: `python3 scripts/study_cli.py knowledge misconceptions list [--topic-id ID] [--status active]`

When explaining a state, identify its dimension, status, and the specific evidence records that support it. If evidence is absent, say so. For “what to review,” list topics in `needs_review` and cite their latest relevant evidence; do not schedule or rank them.

## Record evidence

Use `python3 scripts/study_cli.py knowledge evidence add TOPIC_ID DIMENSION TYPE RESULT "OBSERVABLE DETAILS"` and optional `--session-id`, `--doubt-id`, or `--source-id`. Supported dimensions: `conceptual`, `procedural`, `independent_problem_solving`, `retention`. Evidence types: `explanation`, `guided_exercise`, `independent_exercise`, `exam_question`, `doubt`, `review`, `self_assessment`. Results: `correct`, `partially_correct`, `incorrect`, `completed`, `observed`.

Details describe what happened, such as “Confundió las ecuaciones de carga y descarga al resolver sin ayuda.” Do not invent evidence. Guided work never demonstrates independence. A linked doubt is recorded as observed evidence and never downgrades state.

## Misconceptions

Record a concrete, observable error with `python3 scripts/study_cli.py knowledge misconceptions add TOPIC_ID "DESCRIPTION"`; exact repeated descriptions increment occurrences. Resolve using `python3 scripts/study_cli.py knowledge misconceptions resolve ID`. Do not merge descriptions by semantic guess.

Supported statuses are `not_seen`, `introduced`, `understood`, `practicing`, `independent`, and `needs_review`. Knowledge tracking reflects only evidence stored in this system; it is not an absolute measure of ability.
