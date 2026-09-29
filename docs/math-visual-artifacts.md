# Native Math and Physics Artifacts

> **Legacy backend reference.** Mathematical and physics diagrams use Hermes
> `concept-diagrams`. This
> page documents the specialized renderer constraints, not a separate skill.

The visual router now produces standalone HTML for functions, coordinate
systems, geometry, vector fields, and electrical circuits. It keeps the same
presentation artifact path used by the other native renderers. The generated
HTML embeds the browser code and fonts it needs; opening it does not require
a server or network connection.

## Components

| Component | Responsibility |
| --- | --- |
| SymPy | Validate a restricted arithmetic grammar and sample function/field values in Python. |
| JSXGraph | Draw and interact with coordinate boards, curves, geometry, and field arrows in the HTML. |
| KaTeX | Typeset delimited LaTeX in visible artifact text. |
| MathJax | Render a formula when KaTeX rejects that expression. |
| Schemdraw | Generate circuit SVG at artifact creation time. |

The router chooses the renderer by visual type. It does not execute arbitrary
Python or JavaScript from a request. Expressions allow x/y, numeric literals,
+ - * / ^, pi, E, and common one-argument functions such as sin, cos, exp,
log, and sqrt. SymPy is a calculation tool here, not a source of academic
facts. It does not infer physical assumptions or units.

## Request grammar

- function: data.expression and optional domain [min,max]. An optional
  parameter object with name (one lowercase letter other than x/y), min,
  max, and value adds a slider with 41 SymPy-computed frames. The complete
  sampled domain must remain finite for this mode. The earlier data.x/data.y
  form still works. Output is HTML rather than PNG.
- coordinate_system: an optional bounds [left,top,right,bottom] and an empty
  elements list.
- geometry: data.elements with point (id, at), segment/vector (id, from, to),
  circle (id, center, radius), or polygon (id, points). Every coordinate is
  a finite numeric pair. Maximum 80 elements.
- vector_field: data.fx and data.fy as expressions in x/y; optional bounds
  and grid from 2 to 17. Arrow directions show the sampled field and their
  lengths are normalized for readability.
- circuit: data.elements is a sequence of 1–60 Schemdraw components:
  resistor, capacitor, inductor, battery, source, ground, diode, switch,
  or line. Each accepts optional direction (right/left/up/down) and a
  short plain-text label. Elements form one sequential drawing path; use
  line segments and directions to close a simple circuit. Parallel branches
  and named electrical nets are not in this first semantic spec. This draws
  a schematic; it does not simulate it.

All five types default to output_format html. The result contains artifact
and presentation_artifact pointing to the same file under diagrams/generated.
The router also returns complexity and preferred_presentation. Simple boards
stay inline; fields with grid 7 or more and geometry/circuits with 12 or more
elements prefer expanded preview when Hermes exposes that capability. The
HTML remains available in CLI or if preview fails.
Existing numeric_data and study_metrics continue through Matplotlib.

Visible prose fields accept LaTeX enclosed in \( ... \) or $$ ... $$.
KaTeX is used first; MathJax tries formulas KaTeX cannot parse.
The router also adds this typesetting to flow, architecture, roadmap, and
the numeric HTML wrapper only when such delimiters are present. Circuit
component labels are plain SVG text, so longer formulas belong in subtitle
or notes.

## Setup and checks

Install the Python generation dependencies with:

    .venv/bin/python -m pip install -r requirements-visual.txt

JSXGraph 1.13.3, KaTeX 0.18.9, and MathJax 3.2.2 browser distributions are
vendored under assets/math with their licenses. There is no JavaScript package installation
needed to generate or open an artifact.

Run the unit suite:

    MPLCONFIGDIR=/tmp/hermes-mpl .venv/bin/python -m unittest discover -s tests

With an existing Playwright and Chromium installation, run the optional
browser matrix:

    NODE_PATH=/path/to/node_modules node tests/check_math_browser.cjs

The browser check covers 390, 768, and 1366 px, a parameter slider, and the
offline MathJax fallback. A final Hermes Desktop
preview check still needs a real Hermes session because the CLI cannot open
the host's side panel.
