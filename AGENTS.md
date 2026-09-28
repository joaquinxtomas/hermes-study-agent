# AGENTS.md — Hermes Study Agent

## 1. Purpose

This repository implements a personal study environment built around Hermes Agent.

Hermes acts as the **orchestrator**, not as the permanent storage layer.

The project is designed to provide:

- persistent study sessions;
- doubts and pending questions;
- academic progress tracking;
- source-grounded tutoring;
- multimodel routing;
- timed study sessions;
- visual explanations and diagrams;
- integration with academic materials;
- NotebookLM exports;
- future ActivityWatch integration;
- remote access to one central Hermes instance.

The project must remain modular, portable, privacy-conscious, and independent from any single AI provider.

---

# 2. Primary architectural principle

Always preserve this separation:

```text
Hermes
│
├── orchestration
├── reasoning
├── skills
└── tool selection

Study Agent Core
│
├── SQLite
├── deterministic Python
├── source retrieval
├── session state
└── configuration

External systems
│
├── Codex
├── lightweight models
├── NotebookLM
├── WhatsApp
├── ActivityWatch
├── Tailscale
└── visualization tools
```

Hermes must NOT become the only place where important study data exists.

Persistent user information must live in portable storage such as:

```text
SQLite
Markdown
JSON
YAML
CSV
```

---

# 3. Development philosophy

Prefer the simplest reliable solution.

Order of preference:

```text
1. deterministic code
2. local database query
3. lightweight model
4. general-purpose model
5. strong reasoning model
```

Do not use an LLM when normal code can solve the problem reliably.

Examples:

```text
start timer
→ code

mark doubt as resolved
→ SQLite

calculate study duration
→ code

classify an unstructured doubt
→ lightweight model

teach a difficult Physics concept
→ strong reasoning model
```

---

# 4. Incremental development

Do not implement several major subsystems at the same time unless explicitly requested.

The intended implementation order is:

```text
1. project structure
2. SQLite schema
3. database initialization
4. capture-doubt
5. study-session
6. session-summary
7. timers and checkpoints
8. Hermes integration
9. WhatsApp
10. model router
11. source engine
12. visual learning engine
13. NotebookLM
14. remote access
15. ActivityWatch
16. adaptive learning
```

When working on one stage:

- do not silently implement future stages;
- do not add speculative dependencies;
- do not create unused abstractions;
- do not add integrations that are not currently required.

---

# 5. Repository boundaries

The repository must distinguish between:

```text
PUBLIC / PORTABLE
├── source code
├── skills
├── migrations
├── documentation
├── tests
├── config examples
└── scripts

PRIVATE / LOCAL
├── study.db
├── academic materials
├── personal study history
├── API keys
├── authentication files
├── WhatsApp sessions
├── cookies
└── tokens
```

Never commit private information.

---

# 6. Secrets and credentials

Never write secrets directly into source code.

Never commit:

```text
.env
auth.json
credentials.json
tokens.json
API keys
OAuth tokens
WhatsApp sessions
NotebookLM cookies
Hermes credentials
```

Use environment variables or local configuration files excluded from Git.

If an integration requires secrets, document the expected variable name without providing a real value.

Example:

```text
DEEPSEEK_API_KEY
```

not:

```text
DEEPSEEK_API_KEY=real-secret-value
```

---

# 7. User data ownership

All meaningful learning data belongs to the user.

AI providers must be treated as replaceable processing components.

Never design the system so that the only copy of important information exists inside:

- Hermes memory;
- Codex;
- NotebookLM;
- OpenRouter;
- DeepSeek;
- any external provider.

The system must remain usable if any AI provider is replaced.

---

# 8. Database responsibility

SQLite is the initial structured persistence layer.

The database should contain structured state such as:

```text
subjects
topics
doubts
study_sessions
misconceptions
assessments
checkpoints
```

Do not store large academic source documents directly in SQLite unless a future requirement explicitly justifies it.

Prefer references and metadata.

---

# 9. Database migrations

All schema changes must be represented by migrations.

Do not manually mutate the production database schema.

Migration naming convention:

```text
001_initial_schema.sql
002_add_checkpoints.sql
003_add_source_metadata.sql
```

A migration must be:

- deterministic;
- reviewable;
- reproducible.

---

# 10. Configuration

Public configuration must use example files.

Example:

```text
config/study.example.yaml
```

Real user configuration should use:

```text
config/study.yaml
```

and must remain outside version control when it contains personal information or provider-specific configuration.

Avoid hardcoding:

```text
subjects
paths
providers
session durations
model names
user-specific behavior
```

whenever configuration is more appropriate.

---

# 11. Model routing

The project should support multiple model tiers.

Conceptual routing:

```text
Tier 0
→ deterministic code

Tier 1
→ lightweight / cheap model

Tier 2
→ general-purpose model

Tier 3
→ strong reasoning model such as Codex
```

Examples:

```text
capture doubt
→ Tier 1

classify note
→ Tier 1

generate study pack
→ Tier 2

plan study session
→ Tier 2

Physics tutoring
→ Tier 3

evaluate algorithm solution
→ Tier 3
```

Do not couple task names permanently to one provider.

Prefer:

```text
reasoning
general
utility
```

over provider names inside core logic.

Provider selection belongs in configuration.

---

# 12. Codex usage

Codex should be reserved primarily for tasks requiring strong reasoning.

Examples:

- Physics;
- Mathematics;
- Algorithms;
- debugging;
- evaluating solutions;
- generating adaptive exercises;
- Socratic tutoring.

Avoid using Codex for:

- updating a status;
- formatting metadata;
- querying SQLite;
- starting timers;
- basic classification.

---

# 13. Study session rules

A study session must support:

```text
start
pause
resume
checkpoint
close
restore
```

Sessions should distinguish:

```text
target_duration
hard_limit
```

Example:

```text
target_duration: 75 min
hard_limit: 90 min
```

Elapsed study time is calculated and persisted in SQLite; pauses do not count.
Local timer and session actions use the deterministic Study Core directly;
they do not search for or schedule cron jobs. A date-specific or recurring
reminder is a separate user request. SQLite remains authoritative. Do not claim
that a local timer will proactively notify unless a reminder was explicitly
requested and scheduled.

Do not keep an LLM invocation alive merely to measure time.
Elapsed time alone is never learning evidence.

---

# 14. Hard-stop behavior

Reaching the session hard limit must NOT discard context. Pause the session and
persist a checkpoint from the latest known context; a scheduled task cannot
assume access to the active tutoring conversation.

Before closing, create a checkpoint containing, when available:

```text
subject
topic
current source
exercise
current step
pending doubts
next action
```

The user should later be able to say:

```text
Continue Physics
```

and restore the relevant context.

---

# 15. Educational behavior

The Study Agent is intended to help the user learn, not merely produce answers.

When appropriate, prefer Socratic tutoring.

Default progression:

```text
1. ask
2. evaluate answer
3. minimal hint
4. conceptual hint
5. partial explanation
6. full solution
```

Do not reveal the complete solution immediately when the user is actively practicing unless:

- the user explicitly asks for it;
- the learning mode permits it;
- the user is blocked after appropriate hints.

---

# 16. Exam mode

During an exam:

```text
NO hints
NO corrections during the attempt
NO hidden topic disclosure
NO solution before completion
```

Allowed:

```text
clarification of ambiguous wording
```

After completion:

```text
evaluate
classify mistakes
update learning state
recommend review
```

---

# 17. Doubts

A doubt is a first-class object.

Minimum conceptual states:

```text
pending
studying
resolved
review
```

Capturing a doubt should not automatically start a tutoring session.

---

# 18. Misconceptions and recurring errors

Do not store only scores.

Recurring conceptual mistakes are important learning data.

Future exercise selection may use this information.

---

# 19. Knowledge model

Avoid representing knowledge as one arbitrary percentage.

Prefer multiple dimensions when useful:

```text
exposure
conceptual understanding
procedural ability
independent problem solving
retention
```

Do not fabricate precision when insufficient evidence exists.

---

# 20. Source-grounded answers

The system must support academic sources such as:

```text
books
PDFs
guides
lecture notes
past exams
Markdown notes
```

If the user explicitly asks for information according to a particular source, the answer must retrieve information from that source.

Do not silently substitute general model knowledge for the requested material.

If external knowledge is added, clearly distinguish it.

---

# 21. Source Engine

The future source pipeline should conceptually support:

```text
ingest
extract
chunk
metadata
index
retrieve
rank
cite
```

Original academic files must remain immutable.

Derived data should be stored separately.

---

# 22. Source metadata

Whenever possible, preserve metadata such as:

```text
source_id
subject
document type
chapter
section
page
exercise
topic
```

This metadata should make future retrieval understandable and auditable.

---

# 23. Visual learning

The agent should evaluate whether a visualization meaningfully improves understanding.

Prefer:

```text
Native HTML flow and architecture artifacts
→ processes, pipelines, software architecture

Native HTML roadmap artifacts
→ learning paths and prerequisites

Native HTML math artifacts (JSXGraph + SymPy)
→ functions, 2D geometry, coordinate systems, vector fields

Native HTML circuit artifacts (Schemdraw)
→ simple sequential electrical schematics

KaTeX, with MathJax fallback
→ LaTeX in artifact text

Mermaid
→ sequences, explicit export, fallback

Graphviz
→ trees, graphs, DAGs

Matplotlib
→ numeric relationships, study metrics

Excalidraw
→ spatial and intuitive diagrams
```

Do not generate a visualization merely because the tool exists.

---

# 24. NotebookLM

NotebookLM is a secondary consumption system.

It must not become the primary storage layer.

Stable workflow:

```text
Study Agent
→ Study Pack
→ Markdown / document
→ NotebookLM
→ Audio Overview
```

Direct NotebookLM automation should be treated as optional, experimental and replaceable.

---

# 25. ActivityWatch

ActivityWatch integration is future functionality.

Do not send raw continuous activity streams directly to an LLM.

Preferred architecture:

```text
ActivityWatch
→ deterministic processor
→ summarized study activity
→ Study Agent
```

---

# 26. Remote access

The intended deployment uses one central Hermes instance.

Initial host:

```text
personal home computer
```

Other devices should access this instance rather than maintaining independent study state.

Preferred private networking:

```text
Tailscale
```

Do not expose administrative Hermes services directly to the public Internet without an explicit security design.

---

# 27. WhatsApp

WhatsApp is intended as a lightweight interface for:

```text
quick capture
voice notes
photos
notifications
short queries
starting sessions
```

It is not the primary persistent storage layer.

Never design core state around WhatsApp message history.

---

# 28. Portability

The Study Agent should remain migratable.

Avoid unnecessary dependencies on:

```text
one operating system
one LLM
one cloud provider
one messaging service
one note-taking application
```

Prefer interfaces and configuration over provider-specific logic.

---

# 29. Public repository readiness

The project may eventually be open sourced.

Code should therefore avoid hardcoded personal assumptions.

The public repository should contain reusable behavior.

User-specific state belongs outside it.

---

# 30. Dependency discipline

Do not add a dependency unless:

1. it solves a current requirement;
2. the standard library is insufficient;
3. it is actively maintained or otherwise justified;
4. its purpose is documented.

Avoid large frameworks for trivial functionality.

---

# 31. Testing

New core behavior should eventually have tests.

Prioritize tests for:

```text
database migrations
session lifecycle
checkpoint restoration
model routing
source retrieval
state transitions
```

Tests must not require real secrets by default.

---

# 32. Logging

Logs must be useful for debugging without exposing sensitive data.

Never log:

```text
API keys
OAuth tokens
full cookies
passwords
private authentication headers
```

---

# 33. Error handling

Do not silently swallow important failures.

Failures involving:

```text
database writes
checkpoint creation
source ingestion
authentication
session persistence
```

must produce clear errors.

Prefer recoverable states where possible.

---

# 34. File changes

When modifying the repository:

- inspect existing files first;
- preserve established conventions;
- avoid unrelated refactors;
- keep changes scoped to the current task;
- explain significant architectural changes;
- do not delete user data.

---

# 35. Do not overbuild

This project intentionally starts small.

Do not introduce prematurely:

```text
microservices
Kubernetes
distributed databases
event buses
complex vector infrastructure
multi-agent swarms
large frontend frameworks
```

unless actual project requirements justify them.

SQLite and simple Python are preferred for the first versions.

---

# 36. Current first milestone

The first meaningful milestone is:

```text
Hermes
+
SQLite
+
capture-doubt
+
study-session
+
timer
+
checkpoint
+
session-summary
```

Everything else is secondary until this works reliably.

---

# 37. Current implementation order

When no more specific instruction exists, work in this order:

```text
1. AGENTS.md
2. study.example.yaml
3. 001_initial_schema.sql
4. init_db.py
5. capture-doubt
6. study-session
7. session-summary
8. tests
9. Hermes integration
```

Do not skip ahead without a clear reason.

---

# 38. Definition of a good contribution

A change is good when it makes the Study Agent:

```text
simpler
more reliable
more understandable
more portable
more private
more testable
or more useful for learning
```

A change is not automatically good because it uses more AI, more agents, or more technology.

---

# 39. Final principle

When uncertain between two designs, prefer the one that preserves:

```text
user ownership
provider independence
deterministic behavior
clear state
incremental development
pedagogical value
```

The purpose of the system is not to maximize automation.

The purpose is to create a reliable environment that helps the user study better.
