---
name: visual-explain
description: Create a local visual artifact when it improves a study explanation.
---

# visual-explain

Use only when a diagram or plot makes a process, structure, relationship, or
numeric pattern clearer. Keep the explanation useful without the artifact and
describe what the reader should notice.

1. Decide whether a visual materially improves the explanation. If not, answer
   in text without creating an artifact. Classify useful visuals as `flow`,
   `process`, `architecture`, `pipeline`, `roadmap`, `sequence`, `tree`, `graph`, `dag`,
   `function`, `geometry`, `coordinate_system`, `vector_field`, `circuit`,
   `numeric_data`, or `study_metrics`.
   Choose `roadmap` for a learning path, prerequisites, staged mastery, or a
   study plan with a clear main route and optional topics. Do not use it for
   software architecture, execution flow, or every educational explanation.
2. For `flow`, `process`, `architecture`, `pipeline`, `roadmap`, `function`,
   `geometry`, `coordinate_system`, `vector_field`, and `circuit`, hand off to
   `native-visual-artifacts` to create the semantic nodes and edges. That skill
   owns the native spec; this skill owns visual usefulness and intent. Roadmap
   uses sections, a main path, and branches; mathematics uses coordinate data
   or expressions; circuits use ordered components.
3. For other types, build a JSON Visual Request with `type`, `title`, optional
   `subject`, `topic`, `source`, `subtitle`, `description`, `notes`, `data`, and
   `output_format`. Supply participants/messages or numeric x/y series as
   appropriate. Never provide renderer source code.
4. For the non-native types in step 3, pipe the JSON to
   `.venv/bin/python scripts/visual_router.py` from the repository root. The native
   skill invokes the same router and handles its artifact delivery, including
   presentation preference. Do not write SQL, Mermaid, DOT, or plotting code
   from this skill.
5. For non-native results, prefer the returned `presentation_artifact` when present; retain
   `technical_asset` for portability/debugging. Explain the visual and cite
   the registered source when the content came from a source. Do not claim
   that a renderer produced an image when it returned source only or reported
   an unavailable optional program.

`native-visual-artifacts` documents native behavior, mathematical/physics
HTML artifacts, and its Mermaid export for graph-based types.
Graphviz saves `.dot` source (and can create PNG when requested if `dot` is
installed); numeric data and study metrics save `.png` when Matplotlib is installed. When a rendered SVG
or PNG exists, the router also creates a standalone HTML artifact in
`diagrams/generated/`. Mermaid/DOT source is never presented as an image.
