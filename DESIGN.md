# Hermes Study Agent — Visual Design

This is the visual source of truth for standalone educational artifacts. Use it
when changing renderer presentation; semantic specs and layout algorithms keep
their own type-specific responsibilities.

## Principles

- Clarity and readable hierarchy come before decoration or density.
- Use grouping and spatial order before adding more connectors. Preserve the
  main route and make branches easy to trace.
- Keep one card pattern per artifact family. Titles are concise; secondary
  context belongs in subtitles, disclosures, notes, or relation lists.
- Adapt to the artifact container with Wide, Compact, and Narrow compositions.
  Hermes Preview is commonly compact; do not infer layout from monitor size.
- Keep artifacts standalone and offline. Use system fonts and local assets.
- Meet contrast and keyboard-focus needs. Hover is supplemental; focus must
  expose the same useful emphasis.
- Hover and focus may emphasize a node and its immediate relations, but must
  not move or resize the diagram unexpectedly.

## Tokens

| Token | Value |
| --- | --- |
| Font | `system-ui, sans-serif` |
| Debug font | `ui-monospace, monospace` |
| Spacing | 4, 8, 12, 16, 24, 32, 48 px |
| Card padding | 12–16 px |
| Card radius | 10–12 px |
| Surface radius | 16–18 px |
| Card width | 208 px minimum, 248 px preferred, 320 px maximum where the layout allows |
| Body text | 15–16 px, line-height 1.5 |
| Card title | 15–18 px, line-height 1.25–1.3 |
| Subtitle | 12–19 px by artifact family; always secondary to the title |
| Artifact title | 27–45 px, line-height 1.1–1.16 |
| Connector | 2 px, orthogonal, visible against its surface |
| Focus | 2–3 px outline with 2–3 px offset |
| Shadow | Optional, one subtle layer only; never needed to define hierarchy |

### Color semantics

The artifact families retain distinct accents where color carries domain
meaning. Use color with labels, shape, border, or line style; never make color
the only distinction.

| Use | Light / neutral | Dark / diagram canvas |
| --- | --- | --- |
| General HTML wrapper surface / ink | `#f4f5f7` / `#20242b` | `#17191d` / `#edf0f4` |
| Flow surface / ink | `#f3f5f6` / `#1d292e` | `#151b1d` / `#edf3f2` |
| Flow accent / edge | `#20756d` / `#507f79` | `#8ed5c5` / `#a0beb8` |
| Math surface / ink | `#f3f5f8` / `#18202c` | `#111923` / `#eef4fb` |
| Math accent | `#1d69c9` | `#7fb7ff` |
| Architecture and roadmap canvas / ink | — | `#090f1b` / `#f8fafc` |
| Architecture and roadmap surface / border | — | `#111c2b` / `#334155` |
| Architecture and roadmap accent | — | `#67e8f9` |
| Supporting muted text | `#596b73` | `#94a3b8` or `#aebed0` |
| Optional / low emphasis | muted ink + dashed border | `#b8c3d1` + dashed border |
| Specialization | — | `#d6b4fb` / `#c084fc` |
| Keyboard focus | accent outline | `#fbbf24` outline |

Architecture role accents use the current Graphviz palette: input `#94a3b8`,
source/tool `#22d3ee`, process `#34d399`, agent `#c084fc`, storage `#a78bfa`,
decision `#fb7185`, output `#fbbf24`. In flow cards, these roles use restrained
border accents; role names remain visible as text.

Light/dark flow and math surfaces follow `prefers-color-scheme`. Architecture
and roadmap diagrams use a dark canvas so their embedded SVG and importance
colors remain legible. Do not recolor a mathematical curve to indicate a
component role.

## Artifact grammar

- **Architecture:** show real components and only their meaningful relations;
  preserve cycles and use a compact overview before subsystem detail.
- **Flow / process / pipeline:** preserve execution order, branch and merge
  structure. Keep connectors orthogonal and labels only where they disambiguate.
- **Roadmap:** make one core path immediately scannable; sections organize
  progress, while recommended, optional, and specialization branches have
  distinct but restrained emphasis.
- **Math / science:** make axes, units, ranges, and assumptions legible when
  supplied. Keep controls secondary to the mathematical object. Schematics
  communicate topology; they do not imply simulation.

## Responsive and diagram rules

- **Wide:** use horizontal hierarchy and show related branches together.
- **Compact:** use multiple readable cards per row when topology allows; keep
  branches grouped. Do not collapse to one column merely because the container
  is narrower than a desktop page.
- **Narrow:** use one or two cards per row only when required by the measured
  container; preserve reading order and avoid horizontal overflow.
- Never shrink cards below a readable width to fit more nodes. Reduce secondary
  detail or split a large request into an overview and focused artifacts.
- An edge must not cross a node. Avoid avoidable crossings, long diagonals,
  hidden arrowheads, and redundant or stacked labels.

| Do | Don’t |
| --- | --- |
| Use 2–3 columns in Compact when card width and topology permit. | Force 15 nodes into one row or one tall column. |
| Use sections, groups, and concise relation labels. | Add a separate edge for information already clear from grouping. |
| Put optional detail behind disclosure or below the diagram. | Put paragraphs inside cards or tiny text on edges. |
| Use color as a consistent semantic cue with another visual signal. | Assign arbitrary colors or rely on color alone. |
| Keep shadows and surfaces quiet so the structure carries the visual weight. | Add decorative gradients, heavy shadows, or unrelated illustrations. |

## Applying and checking this system

Hermes `concept-diagrams` is the single active diagram-authoring skill. The
project's `study-concept-diagrams`, `visual-explain`, and
`native-visual-artifacts` skill files are compatibility pointers. This document
remains the visual reference for project renderers; the installed skill's
educational style rules apply when it generates standalone diagrams.

Check changes against these existing examples before altering shared styles:

- Architecture: `tests/fixtures/architecture/study_overview.json`
- Roadmap: `tests/fixtures/roadmap/b_physics.json` and
  `tests/fixtures/roadmap/c_data_engineering.json`
- Flow: `tests/fixtures/native_visual/a_pipeline.json` and
  `tests/fixtures/native_visual/b_branching.json`
- Math: use a simple function request such as `y = x^2` (domain `[-5, 5]`).

Relevant references: [Google Labs Stitch design-md](https://github.com/google-labs-code/stitch-skills/tree/main/plugins/stitch-utilities/skills/design-md), [Hermes architecture-diagram](https://github.com/NousResearch/hermes-agent/tree/main/skills/creative/architecture-diagram), [Claude Design](https://github.com/chinazane/claude-design), [popular-web-designs](https://github.com/webdevtodayjason/subctl-rust/tree/main/skills/popular-web-designs), and [roadmap.sh](https://roadmap.sh/). Their reusable ideas are evidence-based tokens, clear component roles, restrained visual hierarchy, and an explicit learning backbone; fixed coordinates and site-specific styling are not adopted.
