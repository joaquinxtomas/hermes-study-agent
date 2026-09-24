---
name: visual-explain
description: Create a local visual artifact when it improves a study explanation.
---

# visual-explain

Use only when a diagram or plot makes a process, structure, relationship, or
numeric pattern clearer. Keep the explanation useful without the artifact and
describe what the reader should notice.

1. Classify the requested visual as `process`, `architecture`, `sequence`,
   `tree`, `graph`, `dag`, `function`, `numeric_data`, or `study_metrics`.
   If there is no clear visual benefit, answer in text without creating one.
2. Build a JSON Visual Request with `type`, `title`, optional `subject`,
   `topic`, `source`, `data`, and `output_format`. Supply semantic nodes/edges,
   participants/messages, or numeric x/y series as appropriate. Never provide
   renderer source code.
3. From the repository root, pipe that JSON to
   `python3 scripts/visual_router.py`. The deterministic router selects the
   renderer. Do not write SQL, Mermaid, DOT, or plotting code from this skill.
4. Include the returned artifact path with the answer. Explain the visual and
   cite the registered source when the content came from a source. Do not claim
   that a renderer produced an image when it returned source only or reported
   an unavailable optional program.

Mermaid always saves `.mmd` source and attempts an additional `.svg` when
`mmdc` is installed. If SVG rendering fails, it warns and keeps the `.mmd`.
Graphviz saves `.dot` source (and can create PNG when requested if `dot` is
installed); plots save `.png` when Matplotlib is installed. Artifacts are
stored in `diagrams/generated/`.
