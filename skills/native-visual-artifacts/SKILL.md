---
name: native-visual-artifacts
description: Build semantic specs for native flow, architecture, roadmap, mathematical, and physics artifacts.
---

# native-visual-artifacts

Use this skill for native visualizations of flows, processes, architectures,
pipelines, roadmaps, mathematics, circuit diagrams, software component relationships, and study or processing workflows
when a diagram improves clarity. Prefer it for requests such as “mostrame
visualmente”, “explicame la arquitectura”, “mostrame el flujo” and “cómo se
conectan estos componentes”. For these cases, use the Native Visual Artifact
Engine as the main presentation instead of Mermaid. Mermaid is an export,
fallback, or the requested format.

`visual-explain` decides whether a visual is useful and classifies its intent.
When the type is `flow`, `process`, `architecture`, `pipeline`, `roadmap`,
`function`, `geometry`, `coordinate_system`, `vector_field`, or `circuit`, this skill
builds the semantic spec and `scripts/visual_router.py` chooses the renderer.
`architecture` uses a Graphviz-layout HTML artifact; `roadmap` uses the editorial
roadmap renderer; mathematical boards use JSXGraph, circuits use Schemdraw,
and flow/process/pipeline use the native flow renderer. Do not
decide teaching strategy here.

## Build the semantic spec

Send a Visual Request to `.venv/bin/python scripts/visual_router.py` from the
repository root (or another Python with requirements-visual.txt installed).
Use the wrapper fields `type`, `title`, optional `subject`, `topic`,
`source`, `subtitle`, `description`, `notes`, `data`, and `output_format`.
For flow/process/architecture/pipeline, `data` contains `nodes` and `edges`;
optional supported fields are `groups` and `annotations`. Roadmap has its own
grammar below. The router also accepts roadmap fields at the top level.

Use `flow`, `process`, `architecture`, `pipeline`, `roadmap`, `function`,
`geometry`, `coordinate_system`, `vector_field`, or `circuit`. Describe meaning,
not presentation. Graph layouts do not take x/y positions; mathematical
coordinates are content in their own specs. Never provide HTML, CSS, SVG,
embedded Mermaid, or external images. The renderer owns layout and drawing.

The node roles and edge styles below apply to flow/process/architecture/pipeline.
Roadmap uses `importance`, `sections`, `main_path`, and `branches` instead.

Each node should have a unique `id`, a brief `title`, a supported `role`, and
only useful optional `subtitle`, `description`, or simple-value `metadata`.
Keep card text short. Put shared context in the request's `description`,
`notes`, or `annotations`. Supported roles are `input`, `process`, `storage`,
`decision`, `output`, `agent`, `source`, and `tool`.

Each edge must connect existing node IDs and represent a real directed
relationship. Add a short `label` only when it clarifies the relationship;
omit labels that repeat the nodes or direction. Supported styles are `normal`,
`dashed`, and `emphasis`. Do not draw arrows or choose anchors: the renderer
calculates connector routing, arrowheads, stacking, and responsive placement.

For `flow`, `process`, and `pipeline`, the V2 renderer measures the artifact's actual container and chooses Wide,
Compact, or Narrow. It packs acyclic graph levels into rows and semantic lanes;
Compact can keep multiple cards per row, while Narrow is used when two readable
cards do not fit. Never prescribe columns, breakpoints, positions, or anchors.
For `flow`, `process`, and `pipeline`, cards remain HTML with orthogonal SVG connectors. Hover/focus highlights direct
relationships; medium/large diagrams put descriptions and metadata in keyboard-
accessible “Detalles” disclosures. Full edge labels remain available in
“Relaciones del diagrama” if there is no clear space to display them inline.

For `architecture`, start with a **component overview**: normally 6–8 nodes
and only the main relationships. Keep one node per real component. In
particular, do not split Hermes into “coordination” and “explanation” or SQLite
into several cards merely to make the graph acyclic. Architecture supports
cycles and reciprocal edges. The Graphviz renderer draws an overview and puts
component descriptions and all relation labels in HTML below it. It uses a
horizontal layout in a wide container, a vertical layout in a compact one,
and readable component cards in a narrow one. The renderer accepts at most 12
nodes and 18 edges for one architecture overview. If the requested system is
larger, generate an overview and separate focused artifacts per subsystem;
do not silently drop requested components or force one overcrowded map.

Keep the artifact focused: show the main stages and components relevant to the
request. Avoid redundant nodes or one node per helper/file unless that detail
answers the question. Use `groups` to name conceptual areas when useful; its
entries are `{ "title": ..., "nodes": [node IDs] }`. Groups now affect layout
as lanes; dependencies can split a group into several segments. If a node is
in multiple groups, the first group controls its placement. Use `notes` or
`annotations` for context that should not become a node.

For architecture, groups are short area summaries below the map; they do not
force repeated visual lanes. Prefer a few meaningful groups over one group per
node. Keep edge labels out of the main map unless the relationship would be
ambiguous without them; the HTML relation list preserves every label.

## Roadmap authoring

Use `roadmap` for learning routes, prerequisites, study progression, and
conceptual stages. Use `architecture` for system components and `flow` for what
happens during execution. Start with the learner's goal, then choose a few
sections, one ordered `main_path`, and short branches attached to its nodes.
Do not begin by enumerating pairwise edges. Spatial grouping carries some of
the relationship; remove redundant concepts and dependencies.

Place `sections`, `nodes`, `main_path`, and optional `branches` inside `data`.
Each section has unique `id`, brief `title`, optional integer `order` and
optional `description`. Each node has unique `id`, brief `title`, a valid
`section`, and `importance`: `core`, `recommended`, `optional`, or
`specialization`. Optional node fields are `subtitle` and `description`.
`main_path` is one ordered list of node IDs, with at least one node per
section. A branch has `from` (main-path ID), `nodes` (ordered IDs), `kind`
(`recommended`, `optional`, or `specialization`), and optional `rejoin`
(later main-path ID) and `label`. Branch nodes stay in the origin section; V1
allows a rejoin only later in that same section. Every node must appear in the
main path or exactly one branch. The renderer assigns rows, anchors, and SVG
connectors; never provide coordinates or hand-written edges.

Keep the main path immediately scannable. Normal target: 8–30 concepts; V1
accepts 1–50 nodes and 1–12 sections. For more than 50 concepts, create an
overview and focused roadmaps by stage, preserving the requested scope rather
than dropping topics silently. Keep titles short and descriptions in the
optional disclosure. When grounded in a course source, retrieve upstream and
preserve only supplied source metadata; do not invent curriculum facts.

If the content is grounded in academic sources, preserve only source metadata
provided by the upstream retrieval, using supported `source` fields `title`,
`chapter`, `section`, and `page`. Do not invent citations or let project
architecture claims stand in for academic evidence. Do not run retrieval here
when another skill already supplied the grounded context.

## Mathematics and physics

Build a semantic Visual Request and let the router produce native standalone
HTML. Use function for an interactive graph: data.expression is a short
arithmetic expression in x, with optional domain [min, max]. For a simple
parameter, add data.parameter with name (one lowercase letter other than
x/y), min, max, and value. SymPy precomputes 41 finite frames for a slider.
Existing data.x/data.y arrays also work. SymPy validates and samples
expressions; JSXGraph renders the board with pan and zoom.

Use geometry for 2D points, segments, vectors, circles, and polygons; use
coordinate_system for an empty coordinate board. Geometry elements have
unique id, kind, optional label, and numeric coordinates: point.at,
segment/vector.from and .to, circle.center and .radius, polygon.points.
Here coordinates describe mathematics, not HTML layout.

Use vector_field with data.fx and data.fy as expressions in x and y; optional
bounds [left, top, right, bottom] and grid (2–17). SymPy samples the field,
and JSXGraph displays arrows. Explain units and that arrow lengths are
normalized for readability; this is not a physics solver.

Use circuit for a Schemdraw schematic. data.elements is an ordered list
of up to 60 components: resistor, capacitor, inductor, battery, source,
ground, diode, switch, or line. Each may have direction right/left/up/down
and a short plain-text label. The SVG is embedded in native HTML.
The current spec draws one sequential path; use lines and directions to
close a simple loop. Do not represent parallel branches or named nets with
this spec. Do not invent missing circuit connections or values.

Visible text may include LaTeX delimited by \( ... \) or $$ ... $$.
KaTeX typesets it; MathJax tries expressions KaTeX rejects. This applies
to mathematical artifacts and to flow, architecture, and roadmap text.
Circuit component labels are plain SVG text; put formulas in subtitle or notes.
Scripts and fonts are embedded when needed, so the artifact opens offline.
These types use output_format html and return presentation_artifact.

## Routing and limits

- `flow`, `process`, `pipeline` → native flow HTML artifact.
- `architecture` → standalone architecture HTML, with Graphviz `dot` used at generation time.
- `roadmap` → standalone editorial roadmap HTML; no Graphviz needed.
- `tree`, `graph`, `dag` → Graphviz for now.
- `function`, `geometry`, `coordinate_system`, `vector_field` → JSXGraph HTML; SymPy prepares expression samples.
- `circuit` → native HTML with Schemdraw SVG.
- `numeric_data`, `study_metrics` → Matplotlib PNG in a standalone HTML wrapper.
- `sequence` → Mermaid.
- Mermaid → export, fallback, or explicitly requested format.

Do not force an unsuitable visual type into the flow renderer. Flows,
processes, and pipelines are acyclic; architecture allows cycles. Roadmap has
one ordered main path and section-local branches, not arbitrary cycles. The schema
permits up to 100 nodes and 200 edges for the flow types, while the architecture
overview has the smaller readability limit above. Mathematical artifacts use
their own 2D primitives and support zoom; circuit simulation and 3D are not provided.
If native rendering fails, use a suitable existing renderer or Mermaid as a
fallback for graph-based types and state what artifact was actually produced.
For roadmap, retain the ordered sections and branches in text if HTML rendering
fails; do not silently flatten it into an arbitrary graph.

Artifacts are written under `diagrams/generated/`; repeated names receive a
suffix. Prefer the router's `presentation_artifact` result. Native output is a
standalone HTML file and can open offline. The router defaults to
`output_format: html`. For flow/process/architecture/pipeline, when the user asks
for Mermaid, set `output_format: source` to add a `.mmd` export; keep HTML as
the main artifact. Roadmap V1 supports HTML only. For the graph-based native
types, an SVG export is attempted only when `output_format` is `svg` and
`mmdc` is installed.

The bundled Hermes `architecture-diagram` skill is a visual-language reference:
semantic component colors, clear edges, and concise summary areas. This skill
still sends a semantic spec to the router; do not copy that skill's fixed-size
SVG template or hand-write SVG/HTML. The architecture output needs Graphviz
`dot` available when it is generated; the resulting HTML needs no tool to open.

## Presentation after rendering

The router also returns graph metrics, `complexity` (`small`, `medium`, or
`large`), `preferred_presentation` (`inline` or `expanded`), and a short
`presentation_reason`. This preference does not change the spec or HTML.
Small diagrams remain inline. Medium diagrams with branches/groups and large
diagrams prefer expanded; a medium linear pipeline may remain inline.
Mathematical artifacts return the same presentation fields: simple boards
remain inline, while dense fields and schematics may prefer expanded.

After the router succeeds, if `preferred_presentation` is `expanded` and the
`desktop_preview` tool is **available in this turn**, call it once with
`{"action":"open", "url":"<absolute path to presentation_artifact>",
"label":"<title>"}`. Resolve the returned relative path against the repository
root. Keep track of paths already opened in this turn; do not open the same
artifact twice. Do not call `desktop_preview` for `inline` or when the tool is absent.
Continue with a short explanation and the HTML artifact path. If preview
reports an error, deliver the HTML path normally; preview failure does not
invalidate the artifact. In CLI and other clients without preview, deliver the
HTML path normally. Do not infer preview availability from OS or environment
variables. Preview is a presentation action, not a renderer or layout step.

When Hermes Desktop is the active client and the artifact is `inline`, show the
standalone HTML natively in the conversation by emitting this as its own
paragraph:

```text
::preview{file="/absolute/path/to/artifact.html"}
```

The directive must occupy the full paragraph. Do not use it for expanded
artifacts; those use `desktop_preview`. In CLI or when Desktop preview
capability is absent, return the artifact path instead of emitting the
directive. The renderer remains standalone and independent of Hermes.

## Examples

User: “Mostrame visualmente cómo funciona nuestro Source Engine.”

Use `type: "flow"` and represent only the main stages:

```json
{
  "type": "flow",
  "title": "Source Engine",
  "data": {
    "nodes": [
      {"id": "material", "title": "Material original", "role": "input"},
      {"id": "ingest", "title": "Ingesta", "role": "process"},
      {"id": "store", "title": "SQLite", "role": "storage"},
      {"id": "retrieve", "title": "Recuperación", "role": "process"},
      {"id": "answer", "title": "Respuesta con citas", "role": "output"}
    ],
    "edges": [
      {"from": "material", "to": "ingest"},
      {"from": "ingest", "to": "store"},
      {"from": "store", "to": "retrieve"},
      {"from": "retrieve", "to": "answer"}
    ]
  }
}
```

User: “Mostrame cómo se relacionan Source Engine, Knowledge Tracking, Study
Sessions y Study Pack.”

Use `type: "architecture"`; include Hermes and SQLite once each, show the
main relationships and branches, and group related nodes if useful. Leave
placement to Graphviz. Use a reciprocal pair only when both directions are
real relationships.

User: “Mostrame un roadmap de Electrostática hasta potencial.”

Use `type: "roadmap"`. Sections can cover campo eléctrico, flujo/Gauss, and
potencial. Put essential concepts on `main_path`; attach symmetry examples as
recommended branches and optional topics as optional branches. Preserve the
course source only if upstream retrieval supplied it.

```json
{
  "type": "roadmap",
  "title": "Electrostática",
  "data": {
    "sections": [
      {"id": "campo", "title": "Campo", "order": 1},
      {"id": "potencial", "title": "Potencial", "order": 2}
    ],
    "nodes": [
      {"id": "field", "title": "Campo eléctrico", "section": "campo", "importance": "core"},
      {"id": "gauss", "title": "Ley de Gauss", "section": "campo", "importance": "core"},
      {"id": "symmetry", "title": "Casos con simetría", "section": "campo", "importance": "recommended"},
      {"id": "voltage", "title": "Potencial", "section": "potencial", "importance": "core"}
    ],
    "main_path": ["field", "gauss", "voltage"],
    "branches": [{"from": "gauss", "nodes": ["symmetry"], "kind": "recommended"}]
  }
}
```

User: “Exportalo también como Mermaid.” (flow or architecture)

Set `output_format: "source"`; keep the HTML artifact as the presentation and
include the `.mmd` export returned by the router.

User: “Mostrame el campo vectorial de F(x,y)=(-y,x).”

Use vector_field with data.fx = -y, data.fy = x and a bounded grid. Explain
that arrows show direction and normalized length; retain units only if supplied.

User: “Dibujá un circuito RC simple con una fuente alterna.”

Use circuit with an ordered source, resistor, capacitor, and connecting lines.
Only include values and topology stated in the request or grounded source.
