---
name: visual-explain
description: Create a local visual artifact when it improves a study explanation.
---

# visual-explain

Use only when a diagram or plot makes a process, structure, relationship, or
numeric pattern clearer. Keep the explanation useful without the artifact and
describe what the reader should notice.

1. Classify the requested visual as `flow`, `process`, `architecture`,
   `pipeline`, `sequence`, `tree`, `graph`, `dag`, `function`, `numeric_data`,
   or `study_metrics`.
   If there is no clear visual benefit, answer in text without creating one.
2. Build a JSON Visual Request with `type`, `title`, optional `subject`,
   `topic`, `source`, `subtitle`, `description`, `notes`, `data`, and `output_format`. Supply semantic nodes/edges,
   participants/messages, or numeric x/y series as appropriate. Never provide
   renderer source code.
3. For `flow`, `process`, `architecture`, and `pipeline`, describe nodes with
   `id`, `title`, `role`, and optional `subtitle`/`description`; describe
   directed connections with `from`, `to`, optional `label`/`style`. The
   native renderer chooses layout. Never provide coordinates. These types use
   the Native Visual Artifact Engine as the primary presentation. Mermaid is
   an export/fallback; use it as the primary visual only if native rendering
   fails or the user explicitly requests Mermaid.
4. From the repository root, pipe that JSON to
   `python3 scripts/visual_router.py`. The deterministic router selects the
   renderer. Do not write SQL, Mermaid, DOT, or plotting code from this skill.
5. Prefer the returned `presentation_artifact` when present; retain
   `technical_asset` for portability/debugging. Explain the visual and cite
   the registered source when the content came from a source. Do not claim
   that a renderer produced an image when it returned source only or reported
   an unavailable optional program.

Native flows produce standalone HTML with real HTML nodes and SVG connectors.
The router also saves Mermaid `.mmd` by default and attempts `.svg` when
`output_format` is `svg` and `mmdc` is installed. If SVG rendering fails, it
warns and keeps the `.mmd`.
Graphviz saves `.dot` source (and can create PNG when requested if `dot` is
installed); plots save `.png` when Matplotlib is installed. When a rendered SVG
or PNG exists, the router also creates a standalone HTML artifact in
`diagrams/generated/`. Mermaid/DOT source is never presented as an image.
