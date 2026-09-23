---
name: capture-doubt
description: Save a study doubt or list pending doubts from local SQLite.
---

# capture-doubt

## Capture

1. Identify the doubt text and the subject. If either is unclear, ask before
   writing anything. Preserve the user's text verbatim, including punctuation;
   do not correct or paraphrase it.
2. Confirm the subject already exists with
   `python3 scripts/study_cli.py subjects list`.
3. If it does not exist, ask before adding it. Never infer permission to create
   a subject from a doubt.
4. Save with
   `python3 scripts/study_cli.py doubts add "SUBJECT" "DOUBT TEXT"`.
5. Report the stored subject, text and status from the command result.

## Pending doubts

When asked to list pending doubts, query SQLite with
`python3 scripts/study_cli.py doubts pending --subject "SUBJECT"`. Omit
`--subject` to list them across subjects. Report only records returned by the
command; do not answer from conversation memory.

Run the command with Hermes' terminal tool from the project root. Do not write
SQL directly or claim success unless the command returns a saved record. Saving
a doubt never starts a tutoring session.

Example: for “No entiendo por qué el flujo atraviesa las tapas” in Física II,
save that exact text with status `pending`.
